#!/usr/bin/env python3
# b2h — B 站系列视频 -> 本地语料 的命令行工具
#
# 典型流程：
#   uv run b2h init ./myproj --mid 308598581 --creator 阿卡迪萨 --keyword ADHD
#   uv run b2h list     ./myproj      # 拉取 UP 主投稿，按关键词生成候选清单
#   uv run b2h download ./myproj      # 下载候选视频的音频
#   uv run b2h transcribe ./myproj    # 本地 faster-whisper 转写
#   uv run b2h corpus   ./myproj      # 合并为 Agent 可直接读的语料
#
# 之后进入 agent/ 目录下的 Agent 工作流（见 README 第 3 步）。

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 项目配置
# ---------------------------------------------------------------------------

def load_config(project: Path) -> dict:
    cfg_path = project / "project.json"
    if not cfg_path.exists():
        sys.exit(f"找不到 {cfg_path}，请先在该目录运行 `b2h init`。")
    with open(cfg_path, encoding="utf-8") as f:
        return json.load(f)


def save_config(project: Path, cfg: dict) -> None:
    with open(project / "project.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def cmd_init(args: argparse.Namespace) -> None:
    project = Path(args.path).resolve()
    if project.exists() and any(project.iterdir()):
        sys.exit(f"目录 {project} 已存在且非空，换一个目录或清空后重试。")

    repo_root = Path(__file__).resolve().parent.parent
    template = repo_root / "template"

    for d in ("audio", "transcripts", "corpus", "handout"):
        (project / d).mkdir(parents=True, exist_ok=True)
    # LaTeX 模板直接放入 handout/，Agent 阶段在其中写章节
    shutil.copytree(template, project / "handout", dirs_exist_ok=True)

    cfg = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "platform": "bilibili",
            "creator_name": args.creator,
            "mid": args.mid,
            "profile_url": f"https://space.bilibili.com/{args.mid}",
            "upload_url": f"https://space.bilibili.com/{args.mid}/upload/video",
        },
        "keywords": [k.strip() for k in args.keyword.split(",") if k.strip()],
        "whisper": {"model": args.model, "device": "cpu", "compute_type": "int8"},
        "videos": [],
    }
    save_config(project, cfg)
    print(f"已初始化项目：{project}")
    print("下一步：b2h list <项目目录>")


# ---------------------------------------------------------------------------
# 1) 拉取投稿清单（flat 提取，只取元数据，不下载）
# ---------------------------------------------------------------------------

def cmd_list(args: argparse.Namespace) -> None:
    project = Path(args.path).resolve()
    cfg = load_config(project)
    keywords = cfg["keywords"]

    from yt_dlp import YoutubeDL

    upload_url = cfg["source"]["upload_url"]
    opts = {
        "quiet": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "noplaylist": False,
        "ignoreerrors": True,
    }
    print(f"正在拉取 {cfg['source']['creator_name']} 的投稿清单（可能需要一两分钟）……")
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(upload_url, download=False)

    entries = (info or {}).get("entries", [])
    picked = []
    for e in entries:
        if not e:
            continue
        title = e.get("title") or ""
        if keywords and not any(k in title for k in keywords):
            continue
        picked.append({
            "bvid": e.get("id"),
            "title": title,
            "duration_seconds": e.get("duration"),
            "video_url": f"https://www.bilibili.com/video/{e.get('id')}",
            "status": "listed",
        })

    cfg["videos"] = picked
    cfg["list_updated_at"] = datetime.now(timezone.utc).isoformat()
    save_config(project, cfg)
    print(f"投稿总数约 {len(entries)}，关键词 {keywords} 命中 {len(picked)} 条，已写入 project.json。")
    for v in picked:
        mins = (v["duration_seconds"] or 0) // 60
        print(f"  {v['bvid']}  {mins:>3d} 分钟  {v['title']}")


# ---------------------------------------------------------------------------
# 2) 下载音频
# ---------------------------------------------------------------------------

def cmd_download(args: argparse.Namespace) -> None:
    project = Path(args.path).resolve()
    cfg = load_config(project)
    audio_dir = project / "audio"
    audio_dir.mkdir(exist_ok=True)

    from yt_dlp import YoutubeDL

    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(audio_dir / "%(id)s.%(ext)s"),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}],
        "quiet": False,
        "ignoreerrors": True,
        "retries": 3,
    }
    targets = [v for v in cfg["videos"] if v["status"] == "listed" or args.force]
    if not targets:
        print("没有待下载的条目（status=listed）。")
        return

    with YoutubeDL(opts) as ydl:
        for v in targets:
            audio_path = audio_dir / f"{v['bvid']}.m4a"
            if audio_path.exists() and not args.force:
                v["status"] = "downloaded"
                v["audio_path"] = str(audio_path)
                print(f"跳过已存在：{v['bvid']}")
                continue
            print(f"下载 {v['bvid']}  {v['title']}")
            ydl.download([v["video_url"]])
            if audio_path.exists():
                v["status"] = "downloaded"
                v["audio_path"] = str(audio_path)
                v["audio_bytes"] = audio_path.stat().st_size
            save_config(project, cfg)  # 每条落盘，中断可续

    save_config(project, cfg)


# ---------------------------------------------------------------------------
# 3) 本地转写（faster-whisper，默认 small / int8 / CPU，无需联网与云端密钥）
# ---------------------------------------------------------------------------

def cmd_transcribe(args: argparse.Namespace) -> None:
    project = Path(args.path).resolve()
    cfg = load_config(project)
    wcfg = cfg["whisper"]
    out_dir = project / "transcripts"
    out_dir.mkdir(exist_ok=True)

    from faster_whisper import WhisperModel

    print(f"加载模型 {wcfg['model']}（首次运行会自动下载，约数百 MB）……")
    model = WhisperModel(wcfg["model"], device=wcfg["device"], compute_type=wcfg["compute_type"])

    def fmt_ts(t: float) -> str:
        ms = int(t * 1000)
        h, ms = divmod(ms, 3_600_000)
        m, ms = divmod(ms, 60_000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    targets = [v for v in cfg["videos"] if v.get("status") in ("downloaded", "transcribed")]
    for v in targets:
        txt_path = out_dir / f"{v['bvid']}.txt"
        srt_path = out_dir / f"{v['bvid']}.srt"
        if txt_path.exists() and not args.force:
            v["status"] = "transcribed"
            print(f"跳过已转写：{v['bvid']}")
            continue

        audio_path = Path(v.get("audio_path") or project / "audio" / f"{v['bvid']}.m4a")
        if not audio_path.exists():
            print(f"缺少音频，跳过：{audio_path}")
            continue

        print(f"转写 {v['bvid']}  {v['title']}")
        t0 = time.time()
        segments, info = model.transcribe(str(audio_path), language=wcfg.get("language"))
        lines, srt_blocks = [], []
        for i, seg in enumerate(segments, 1):
            text = seg.text.strip()
            lines.append(text)
            srt_blocks.append(f"{i}\n{fmt_ts(seg.start)} --> {fmt_ts(seg.end)}\n{text}\n")

        txt_path.write_text("\n".join(lines), encoding="utf-8")
        srt_path.write_text("\n".join(srt_blocks), encoding="utf-8")
        v.update({
            "status": "transcribed",
            "transcript_path": str(txt_path),
            "srt_path": str(srt_path),
            "transcript_chars": sum(len(x) for x in lines),
            "detected_language": info.language,
        })
        print(f"  完成，{len(lines)} 段，耗时 {time.time() - t0:.0f}s")
        save_config(project, cfg)

    save_config(project, cfg)


# ---------------------------------------------------------------------------
# 4) 合并语料：Agent 一次读完的 markdown
# ---------------------------------------------------------------------------

def cmd_corpus(args: argparse.Namespace) -> None:
    project = Path(args.path).resolve()
    cfg = load_config(project)
    tr_dir = project / "transcripts"
    corpus_dir = project / "corpus"
    corpus_dir.mkdir(exist_ok=True)

    done = [v for v in cfg["videos"] if v.get("status") == "transcribed"]
    done.sort(key=lambda v: v.get("duration_seconds") or 0)

    out = corpus_dir / "all_transcripts.md"
    total_chars = 0
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# {cfg['source']['creator_name']} 系列视频转写合辑\n\n")
        f.write(f"- 平台：哔哩哔哩（{cfg['source']['profile_url']}）\n")
        f.write(f"- 关键词：{', '.join(cfg['keywords'])}\n")
        f.write(f"- 视频数：{len(done)}\n\n---\n\n")
        for v in done:
            txt = Path(v.get("transcript_path") or tr_dir / f"{v['bvid']}.txt")
            body = txt.read_text(encoding="utf-8") if txt.exists() else ""
            total_chars += len(body)
            f.write(f"## {v['title']}\n\n")
            f.write(f"- BV：{v['bvid']}　链接：{v['video_url']}　时长：{v.get('duration_seconds', 0)//60} 分钟\n\n")
            f.write(body.strip() + "\n\n---\n\n")

    print(f"已合并 {len(done)} 期、约 {total_chars:,} 字到 {out}")
    print("下一步：把 corpus/all_transcripts.md 交给 Agent，按 agent/WORKFLOW.md 提炼讲义。")


# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(prog="b2h", description="B站系列视频 -> 语料 -> 观点讲义")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="初始化一个讲义项目")
    p.add_argument("path")
    p.add_argument("--mid", required=True, help="UP 主的数字 mid（空间主页 URL 里）")
    p.add_argument("--creator", required=True, help="UP 主名称")
    p.add_argument("--keyword", default="", help="按标题筛选的关键词，逗号分隔；留空取全部投稿")
    p.add_argument("--model", default="small", help="faster-whisper 模型：tiny/base/small/medium/large-v3")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("list", help="拉取投稿并按关键词生成候选清单")
    p.add_argument("path")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("download", help="下载清单内视频的音频")
    p.add_argument("path")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("transcribe", help="本地 Whisper 转写音频")
    p.add_argument("path")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_transcribe)

    p = sub.add_parser("corpus", help="合并全部转写为单个 markdown")
    p.add_argument("path")
    p.set_defaults(func=cmd_corpus)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
