# LaTeX 排版组件说明

模板基于 XeLaTeX + ctex，定位于中文观点讲义。本文档列出定制组件的用法。
所有组件都在 `template/main.tex` 中定义，章节文件里直接用即可。

## 可用组件

### 1. `insight` — 核心洞察框（青色）

```latex
\begin{insight}
  这是贯穿一节或一章的核心判断，每章 1~3 个为宜。
\end{insight}
```

用于：反直觉结论、世界观级别的判断、章节主旨。
可跨页（breakable），但尽量安排在引入概念之后。

### 2. `notehot` — 边界/提醒框（赭石色）

```latex
\begin{notehot}
  方法的禁忌、代价、适用边界，以及敏感领域的免责声明。
\end{notehot}
```

用于：风险提示（如「此法急性压力大，不可常用」）、
「这是观点不是专业建议」、整理者延伸结论的不确定性标注。

### 3. `checklist` — 复选框清单

```latex
\begin{checklist}
  \item 第一条可执行条目；
  \item 第二条；
\end{checklist}
```

用于：日常执行清单、自检线索、分层策略。
注意它本质是 itemize，里面也可以放 `\textbf{}` 等。

### 4. `\term{}` — 博主黑话 / 术语强调

```latex
ADHD 是一套\term{广度运算便宜、深度运算昂贵}的算法。
```

用于：博主原生概念首次出现、需要读者记住的参数差异。
同一概念在同一章或同一页内不必重复标。

### 5. `\key{}` — 核心一句

```latex
\key{学历度量的大多是脚手架，不是能力。}
```

用于：节或章的收束金句。每节最多一个，多了就没有重点。

### 6. 表格

- 普通短表：`booktabs` + `p{宽度}` 列（template 已设 `\tabcolsep=4pt`）。
- 概念速查、出处对照这类可能超过一页的表，用 `longtable`（已加载），
  写法见 `template/chapters/appendix.tex`。
- 中文环境下避免使用固定像素或不可断行的英文/BV 号长串导致溢出；
  BV 号中间不断字通常刚好，若溢出则加宽左列或用 `\small`。

### 7. Part / 做部分扉页

```latex
\part{方法论：搞懂自己，然后顺着自己活}
```

四个部分各一个 `\part{}`，视觉上把全书分成四块。

## 编译

```bash
latexmk -xelatex main.tex
# 或手动跑两遍：
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex
```

## 常见溢出处理

| 现象 | 处理 |
|---|---|
| Overfull \hbox，表列太窄 | 调整 p{} 宽度之和（A4 默认版心约 15.8cm）；\small 包裹表格 |
| Overfull \vbox（最后页撑出） | 改为 longtable 或精简该页内容 |
| 目录页也出现页眉 | 目录段用 `\pagestyle{empty}` + `\pagenumbering{roman}`，正文前重置为 arabic |
| 目录没更新 | 跑第二遍 xelatex |
| example-image 占位图替换 | 本模板不含图片；如需插图用 `\includegraphics[width=0.9\linewidth]{x.png}` |
