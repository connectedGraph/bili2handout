# bili2handout — B 站博主系列视频 → AI 提炼 → LaTeX 观点讲义

把一位博主在某个主题下的系列视频，经过**本地语音转写 + AI Agent 提炼重组**，
变成一份连贯、可打印、可交付的中文 LaTeX 讲义（PDF）。

本仓库是一套**工作流模板**，不绑定任何具体博主或主题。
首个完整实例：从 B 站 UP 主「阿卡迪萨」的 24 期 ADHD 视频，
产出 37 页《最舒适的认知：ADHD 自救讲义》——见 [`examples/adhd-handout`](examples/adhd-handout)。

---

## 它解决什么问题

收藏夹里的「干货视频」通常有三个命运：吃灰、只记得几句金句、
真要用时翻不到。而直接把字幕喂给 AI 让它「总结一下」，得到的多半是
分集简介式的正确废话——视频是按发布时间散点排列的，观点体系不是。

这套工作流做两件事：

1. **工程侧**：一条命令把 UP 主的投稿按关键词筛出、下载音频、
   本地 Whisper 转写、合并成 Agent 一次能读完的语料；
2. **认知侧**：一套经过实战的 Agent 工作流（立场校准 → 提炼黑话体系 →
   按认知顺序重排架构 → 分章起草 → 编译质检），逼 AI 产出
   **忠于博主原生概念、但结构比原视频更清晰**的观点讲义，而不是摘要。

## 成品形态

- XeLaTeX + ctex 中文排版，A4，自带封面/目录/页眉/书签；
- 定制组件：核心洞察框、边界提醒框、复选框清单、术语强调、金句；
- 附录：概念黑话速查表、观点 → 视频出处对照表；
- 30~50 页，适合打印出来划线，也适合作为社群内部的「认知底稿」传播。

## 目录结构

```
bili2handout/
├─ scripts/b2h.py        # 语料管线 CLI：list / download / transcribe / corpus
├─ agent/
│  ├─ WORKFLOW.md        # 核心：五阶段 Agent 工作流（含各阶段提示词要点）
│  └─ STYLE.md           # 观点讲义的中文写作风格指南
├─ template/             # 通用 LaTeX 讲义模板（init 时复制）
│  ├─ main.tex
│  └─ chapters/
├─ docs/LAYOUT.md        # LaTeX 组件与排版排错说明
├─ examples/adhd-handout # 完整实例：37 页 ADHD 讲义（tex + pdf + digest）
├─ pyproject.toml        # uv 依赖：yt-dlp、faster-whisper
└─ README.md
```

## 快速开始

### 环境要求

- Python ≥ 3.10，推荐用 [uv](https://github.com/astral-sh/uv) 管理；
- [ffmpeg](https://ffmpeg.org/)（yt-dlp 抽音频用）；
- XeLaTeX：Windows 装 [MiKTeX](https://miktex.org/)，macOS 装 MacTeX，
  Linux 装 TeX Live（需含 ctex / tcolorbox）；
- 网络能访问 B 站；如在受限网络环境，给终端配好代理再跑下载。

### 第 1 步：准备语料（管线自动完成）

```bash
git clone https://github.com/<你的用户名>/bili2handout.git
cd bili2handout

# 初始化一个讲义项目：mid 是 UP 主空间主页 URL 里的数字
uv run python scripts/b2h.py init ./work/myproj \
  --mid 308598581 --creator 某博主 --keyword "ADHD,注意力"

uv run python scripts/b2h.py list       ./work/myproj   # 拉投稿、按关键词筛选
uv run python scripts/b2h.py download   ./work/myproj   # 下音频（可中断续跑）
uv run python scripts/b2h.py transcribe ./work/myproj   # 本地转写（首次自动下模型）
uv run python scripts/b2h.py corpus     ./work/myproj   # 合并为 corpus/all_transcripts.md
```

说明：

- 转写走本地 [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
  （默认 small / int8 / CPU），不上传任何音频、不需要云端密钥；
  可在 `project.json` 里把模型改成 `medium` / `large-v3`；
- 所有进度逐条写回 `project.json`，中断后重跑即可续；
- 已有字幕的项目可以跳过前两步，直接把字幕整理成
  `corpus/all_transcripts.md`（格式见 `examples`）。

### 第 2 步：让 Agent 把语料变成讲义（核心步骤）

打开任意 AI 编码 Agent（Claude Code、Cursor、Gemini CLI 等），
把仓库根目录和 `./work/myproj` 给它，然后按
[`agent/WORKFLOW.md`](agent/WORKFLOW.md) 的五个阶段执行：

0. **立场校准**——写给谁、什么体裁、忠于什么（先于一切写作）；
1. **通读提炼**——产出 `digest.md`：总纲、世界观模型、黑话词典、
   方法清单、观点冲突、反复母题；
2. **架构设计**——按「认知 → 分层画像 → 方法论 → 思考与清单」
   设计 4 部分章节，找到一条贯穿主轴；
3. **分章起草**——每章一个任务写 `chapters/chXX.tex`，
   强制使用黑话原词、标注 BV 出处、每章配洞察框/清单；
4. **汇编编译**——复制 `template/` 到 `handout/`，替换封面 TODO，
   `xelatex` 跑两遍；
5. **质检**——事实回扣、无发明观点、猜测保留不确定、零排版溢出。

WORKFLOW.md 里每个阶段都附了可以直接复制改写的提示词。

### 第 3 步：编译

```bash
cd work/myproj/handout
latexmk -xelatex main.tex      # 或 xelatex 连跑两遍
```

## 设计原则

1. **语料本地化、观点可溯源**。音频与转写都在本地；讲义里每个关键论断
   都能回溯到 BV 号，附录给出完整出处对照。
2. **提炼，不是总结**。视频按时间散点，讲义按认知顺序重排；
   博主的自创概念（黑话）是最大资产，原样保留而不是翻译成普通话。
3. **人负责立场，Agent 负责力气活**。写给谁、什么体裁、主轴是什么，
   由人在阶段 0/2 拍板；通读、起草、排版检查由 Agent 完成。
4. **工程与认知解耦**。不用 B 站、不用 Whisper 也能用——
   只要你能提供一份合并好的语料 markdown，后半段 Agent 工作流完全通用
   （播客、课程、访谈录同理）。

## 实例：ADHD 自救讲义

`examples/adhd-handout/` 是用本工作流产出的第一份成品：

- 语料：24 期视频、约 12 万余字转写；
- 成品：37 页 PDF，四部分十一章三附录；
- 主轴：同一套大脑特征在「学历上层 / 学历中下层」两种外部条件下的
  不同命运与自救路径；
- 风格：社群内部视角的知乎式认知长文，明确声明是观点与经验、
  不是医学建议。

`digest.md` 是阶段 1 的产物样例，`chapters/` 是阶段 3 的产物样例，
可直接对照 WORKFLOW.md 理解每一步在做什么。

## 合规与版权

- 请仅转写你**有权处理**的内容，遵守 B 站用户协议与博主版权；
  转写语料建议自用，不要随仓库再分发他人作品的音频。
- 讲义是对公开内容的**整理与评论**，传播时注明博主与原视频链接；
  观点属于博主，编排属于整理者，曲解责任在整理一方。
- 涉及医学、心理、法律、投资等主题时，模板与工作流都要求显式标注
  「观点经验，非专业建议」。请勿用本工具生成冒充专业意见的内容。
- `.gitignore` 默认忽略 `work/`、`audio/`、`transcripts/`、模型与构建产物。

## 许可

[MIT](LICENSE)。实例讲义（`examples/` 下的文本与 PDF）同样以 MIT 开放，
转发请保留对原博主的署名与视频出处。
