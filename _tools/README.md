# TechGear HQ — 构建工具

这个目录里的脚本负责把 `_src/` 里的**模板和内容**编译成线上运行的静态 HTML。

## 目录结构

```
aitools/
├─ _src/                  ← 【改内容改这里】
│  ├─ templates/
│  │  ├─ shell.html        页面骨架（{{TITLE}}、{{HEADER}} 等占位符）
│  │  ├─ header-en.html    英文站导航（只有这一份！）
│  │  ├─ header-zh.html    中文站导航
│  │  ├─ footer-en.html
│  │  └─ footer-zh.html
│  └─ pages/
│     ├─ en/index.html     英文内容（front-matter + <main>）
│     ├─ en/articles/*.html
│     ├─ zh/index.html
│     └─ zh/articles/*.html
├─ _tools/                ← 本目录（构建脚本）
│  ├─ build.py             ★ 主编译器
│  ├─ sync_home_dates.py   同步首页卡片的日期/阅读时长
│  └─ README.md
├─ index.html             ← 【自动生成，不要手改】
├─ articles/*.html        ← 【自动生成】
├─ zh/**                  ← 【自动生成】
└─ sitemap.xml            ← 【自动生成】
```

## 日常操作

**改导航 / 页脚 / 页面骨架**
```bash
# 1. 编辑 _src/templates/header-en.html 之类
# 2. 重新编译
python _tools/build.py
# 3. 部署
git add -A && git commit -m "..." && git push
```
→ 一次改动，全部 150 页同步更新。

**改某篇文章的内容**
```bash
# 1. 编辑 _src/pages/en/articles/xxx.html
# 2. python _tools/build.py
# 3. git push
```

**改首页卡片文案/日期**
```bash
python _tools/sync_home_dates.py   # 从各文章读日期，刷新首页卡片
python _tools/build.py
git push
```

## 文章源文件的格式

每个页面文件 = **front-matter 注释** + **`<main>` 内容**（不含 header/footer）：

```html
<!--meta
lang: en
title: Best Mouse For Arthritis Hands — TechGear HQ
description: Expert reviews and buying guide...
canonical: https://techgearhq.com/articles/best-mouse-for-arthritis-hands
date: 2026-09-15
read: 4
-->
<main class="article-page">
<h1>Best Mouse For Arthritis Hands</h1>
<p>正文...</p>
</main>
```

- `date` → 生成 byline 和 JSON-LD 的 `datePublished`，也用于 sitemap 的 `lastmod`
- `read` → 阅读时长（build.py 会按实际字数重算，这里的值仅作后备）
- **byline 和结构化数据都是 build.py 自动生成的，不用手写**

## 路径说明

脚本用**自身位置**推导项目根目录：

```python
SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```

所以在任何机器、任何盘符下 clone 下来都能直接跑，不需要改路径。

## 环境要求

- Python 3.8+
- 不需要任何第三方库（只用标准库）

## 部署

推到 GitHub 后，Cloudflare Pages 会自动拉取并上线，无需手动操作。

## 注意事项

- `_src/` 和 `_tools/` 会被一起部署，但 `robots.txt` 已屏蔽它们，Google 不会索引
- **同一时间只在一台机器上 push**，切换机器前先 `git pull`
