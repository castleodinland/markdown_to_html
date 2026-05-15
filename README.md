# Markdown → HTML 转换器

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Version](https://img.shields.io/badge/Version-v12.18-blue)

> 🎯 **一个把 `.md` 文件变成完整离线 HTML 网页的工具** —— 纯 Python 实现，自带深色主题、代码高亮、公式渲染、附件下载、CSP 安全防护、在线资源离线嵌入……

---

## 📚 面向初学者的学习路线

如果你是 Python / HTML / JavaScript 的初学者，以下是你需要提前掌握的基础知识（本项目的学习顺序建议）：

### 1. Python 基础（必须）

| 知识点 | 说明 | 对应本项目位置 |
|--------|------|----------------|
| **变量与数据类型** | `str`, `int`, `bool`, `list`, `dict` 等 | 配置参数区域（第 75~114 行） |
| **函数定义** | `def function_name():` 和 `return` | 几乎每个函数（如 `clean_markdown_content`） |
| **文件读写** | `open()`, `.read()`, `.write()` | `process_file()` 中的文件操作 |
| **正则表达式 re** | `re.sub()`, `re.search()`, `re.match()` | 公式预处理、表格修复、Markdown 语法转换 |
| **异常处理** | `try / except` | 在线资源下载、代码高亮降级、Playwright |
| **第三方库导入** | `import` 与 `pip install` | 开头导入部分 + `requirements_v12.18.txt` |

**推荐学习资源：**
- [Python 官方教程（中文）](https://docs.python.org/zh-cn/3/tutorial/)
- [Python 菜鸟教程](https://www.runoob.com/python3/python3-tutorial.html)
- 练习：试着修改第 75~114 行的 `用户可调节参数`，观察生成的 HTML 变化

### 2. HTML + CSS 基础（重要）

| 知识点 | 说明 | 对应本项目位置 |
|--------|------|----------------|
| **HTML 基本结构** | `<!DOCTYPE html>`, `<html>`, `<head>`, `<body>` | 第 1025~1037 行 HTML 模板 |
| **常用标签** | `<div>`, `<span>`, `<a>`, `<img>`, `<table>`, `<pre>`, `<code>` | 全书随处可见 |
| **CSS 选择器** | 类选择器 `.class`、ID 选择器 `#id`、伪类 `:hover` | `BASE_CSS`, `LAYOUT_CSS`, `CODE_THEMES` |
| **Flexbox 布局** | `display: flex`, `align-items`, `gap` | 附件卡片样式（第 713~720 行） |
| **CSS 动画** | `transition`, `@keyframes` | 侧边栏滑入、复制按钮、旋转动画 |

**推荐学习资源：**
- [MDN HTML 教程](https://developer.mozilla.org/zh-CN/docs/Learn/HTML)
- [MDN CSS 教程](https://developer.mozilla.org/zh-CN/docs/Learn/CSS)
- 练习：修改 `BASE_CSS` 中的颜色值，变成浅色主题

### 3. JavaScript 基础（建议）

| 知识点 | 说明 | 对应本项目位置 |
|--------|------|----------------|
| **DOM 操作** | `document.getElementById`, `createElement`, `appendChild` | 第 1330~1680 行 JS 代码 |
| **事件监听** | `addEventListener`, `click`, `mouseenter` | 侧边栏、复制按钮、附件下载 |
| **异步编程** | `async/await`, `Promise`, `setTimeout` | 附件解压下载（`unpackAndDownload`） |
| **Fetch / Stream** | `ReadableStream`, `DecompressionStream` | 浏览器端解压 zlib 压缩数据 |
| **Base64 处理** | `atob`, `btoa`, `Uint8Array` | 附件解码与转换 |

**推荐学习资源：**
- [MDN JavaScript 教程](https://developer.mozilla.org/zh-CN/docs/Learn/JavaScript)
- [JavaScript.info 中文](https://zh.javascript.info/)
- 练习：修改 JS 中附件下载的进度条颜色

### 4. 第三方库速览

| 库名 | 用途 | 安装命令 |
|------|------|---------|
| `markdown` | 将 Markdown 文本转为 HTML | `pip install markdown` |
| `beautifulsoup4` | 解析/修改 HTML DOM 树 | `pip install beautifulsoup4` |
| `Pygments` | 代码语法高亮着色 | `pip install Pygments` |
| `ziamath` | 将 LaTeX 公式渲染为 SVG（可选） | `pip install ziamath` |
| `playwright` | 无头浏览器校验（可选） | `pip install playwright` |

---

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements_v12.18.txt
playwright install chromium   # 可选，用于浏览器端完整性校验

# 2. 准备一个 .md 文件
echo "# Hello World" > test.md

# 3. 运行转换
python markdown_to_html_v12.18.py

# 4. 用浏览器打开生成的 test.release.html
start test.release.html
```

---

## 🧠 处理流程全解析（初学者必读）

以下是从 **输入 `.md` 文件** 到 **输出 `.release.html`** 的完整处理流水线。每个步骤都用 ① ② ③ ... 编号，建议对照源码阅读。

### 总体流程图

```
  [.md 文件]
      ↓
① clean_markdown_content()      ← 移除 YAML Front Matter + 修复表格间距
      ↓
② preprocess_math()             ← 将 $$...$$ 和 $...$ 转为 SVG 公式
      ↓
③ convert_md_to_html()          ← 调用 markdown 库将 Markdown 转为 HTML
      ↓
④ process_file() 核心处理       ← 组装完整 HTML，附加各种功能
      ├─ 生成 HTML 模板
      ├─ 恢复代码块语言标签
      ├─ 嵌入主题照片
      ├─ 生成侧边栏目录
      ├─ 注入 CSS（深色主题 + 代码高亮 + 布局）
      ├─ 注入 JS（交互逻辑 + CSP 违规可视化）
      └─ 注入 CSP 安全策略
      ↓
⑤ replace_with_base64()         ← 图片/视频/附件全部转为 base64 内嵌
      ├─ 表格特殊符号修复
      ├─ HTML 块内 Markdown 语法二次转换
      ├─ 图片嵌入（本地 + 在线）
      ├─ 视频嵌入（本地 + 在线）
      └─ 附件压缩嵌入（本地 + 在线）
      ↓
⑥ wrap_tables()                 ← 美化表格外层 wrapper
      ↓
⑦ 写入 .release.html
      └─ 追加完整性校验 JS
      └─ 更新 CSP 以包含完整性 JS 哈希
      └─ (可选) Playwright 无头浏览器验证完整性
```

---

### ① `clean_markdown_content()` — 清洗原始 Markdown

**文件位置：** 第 935~980 行

**做什么：**
- **移除 YAML Front Matter** —— 很多 Markdown 文件开头有 `---\ntitle: xxx\n---` 这样的元数据区，正则表达式将其删除。
- **智能修复表格间距** —— Markdown 表格要求表头前有空行。如果用户写了：

  ```markdown
  这是一段文字
  | 列1 | 列2 |
  |-----|-----|
  ```
  表格会被 Markdown 库忽略。本函数发现 `分隔行` 前两行不是空行时，自动插入空行，变成：

  ```markdown
  这是一段文字

  | 列1 | 列2 |
  |-----|-----|
  ```

**初学者注意：**
- `re.sub(pattern, '', content, flags=re.DOTALL)` 的 `.` 能匹配换行符，所以 `.*?` 能匹配跨行内容。
- 代码块检测通过 `in_code_block` 布尔开关实现——遇到 ````` 就翻转状态，保证不修改代码块内的表格。

---

### ② `preprocess_math()` — 公式预处理

**文件位置：** 第 905~932 行

**做什么：**

在 Markdown 库解析之前，先把 LaTeX 公式变成 HTML。处理顺序：

1. **保护代码块** —— 将 ` ```...``` ` 和 `` `...` `` 替换为占位符 `__CODE_BLOCK_0__`，避免公式正则误伤。
2. **块级公式** —— `$$...$$` 调用 `render_latex_to_svg()` 渲染为带 CSS 美化的 SVG。
3. **行内公式** —— `$...$` 渲染为行内 SVG（带 `max-height` 限制，不会撑破行高）。
4. **还原代码块** —— 把占位符替换回原始代码。

**初学者注意：**
- 占位符技巧（`save_code` / 还原）在复杂文本处理中很常见。先"藏起来"，处理完再"放回去"。
- 如果未安装 `ziamath`，公式会显示为红色提示文本，不会报错崩溃。

---

### ③ `convert_md_to_html()` — Markdown 库核心转换

**文件位置：** 第 982~996 行

**做什么：**

调用 Python 的 `markdown` 库，启用以下扩展：

| 扩展名 | 作用 |
|--------|------|
| `fenced_code` | 支持 ` ```python ` 围栏代码块 |
| `tables` | 支持 `| ` 表格语法 |
| `toc` | 生成锚点（本工具自己实现侧边栏） |
| `sane_lists` | 智能列表（避免数字列表和普通段落混淆） |
| `nl2br` | 换行转 `<br>` |
| `codehilite` | 基于 Pygments 的代码高亮 |

**初学者注意：**
- 如果未安装 `Pygments`，程序自动降级移除 `codehilite` 扩展，不会崩溃。
- 这是整个流程中**唯一的第三方 Markdown 解析步骤**，其他步骤都是本工具的增强处理。

---

### ④ `process_file()` — 核心组装工厂

**文件位置：** 第 998~1725 行

这是最复杂的一个函数。它将 Markdown 库产出的 HTML 片段组装成完整的、功能丰富的 HTML 页面。

#### 4.1 HTML 模板生成（第 1025~1037 行）

```python
html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{文件名}</title>
</head>
<body>
    {markdown 转换的 HTML 内容}
</body>
</html>
"""
```

然后用 `BeautifulSoup(html_template, 'html.parser')` 将其解析为 Soup 对象，方便后续 DOM 操作。

#### 4.2 恢复代码块语言标签（第 1042~1051 行）

`codehilite` 扩展在渲染代码块时会丢弃语言信息（如 `python`、`javascript`）。本工具通过预扫描原始 Markdown 提取语言，然后重新注入到 `<code>` 标签的 `class` 中，例如 `language-python`。

**初学者注意：**
- `soup.find_all('div', class_='highlight')` 找到所有代码块的外层 div。
- 之所以叫"恢复"，是因为第三方库丢弃了信息，我们自己抢救回来。

#### 4.3 嵌入主题照片（第 1053~1063 行）

如果 `.md` 文件同目录存在同名的 `.png` / `.jpg` / `.webp` 文件（例如 `readme.jpg` 对应 `readme.md`），自动读取并转为 base64，插入到 `<body>` 最前面作为封面图。使用了 `object-fit: cover` 确保图片自适应。

#### 4.4 生成侧边栏目录（第 1065~1097 行）

遍历 `<h1>`、`<h2>`、`<h3>` 标签，为每个标题生成锚点 ID（自动处理重复 ID），然后构建一个 `<ul>` 列表，缩进表示层级：

```html
<div id="sidebar">
  <ul>
    <li style="margin-left: 0px;"><a href="#标题1">标题1</a></li>
    <li style="margin-left: 15px;"><a href="#子标题">子标题</a></li>
  </ul>
</div>
<div class="sidebar-trigger">展示目录</div>
```

侧边栏默认隐藏在屏幕左侧之外（`left: -500px`），鼠标悬停"展示目录"标签时滑入。

**初学者注意：**
- `anchor_counts` 字典用来处理重复标题（如两个"总结" → "总结" 和 "总结-1"）。
- 侧边栏 0px/15px/30px 缩进对应 h1/h2/h3 的层次感。

#### 4.5 注入 CSS（第 1100~1319 行）

三大 CSS 块：

| CSS 块 | 行号 | 内容 |
|--------|------|------|
| `BASE_CSS` | 第 126~275 行 | 正文、标题、引用、表格、分割线等基础样式 |
| `CODE_THEMES["dark"]` | 第 1180~1210 行 | 代码块专属样式 —— 暗色背景 + 等宽字体 |
| `syntax_highlighting_css` | 第 1102~1178 行 | Pygments 语法高亮颜色：关键字紫色、字符串橙色、函数黄色…… |
| `LAYOUT_CSS` | 第 1213~1319 行 | 侧边栏、主题照片、附件、公式、复制按钮、语言标签 |

通过 `hashlib.sha256()` 计算 CSS 内容的哈希值，用于 CSP `style-src-elem` 绑定。

#### 4.6 注入 JavaScript（第 1330~1683 行）

JS 代码做了以下几件事：

| 功能 | 行号 | 说明 |
|------|------|------|
| **CSP 违规可视化** | 1332~1466 | 监听 `securitypolicyviolation` 事件，若检测到安全违规，在页面顶部弹出红色警告面板（含违规指令、被拦截 URI、时间等），信息通过 DOM API 构建（不使用 innerHTML） |
| **侧边栏交互** | 1469~1483 | 鼠标悬停"展示目录" → 侧边栏滑入；鼠标离开侧边栏 → 侧边栏滑出 |
| **代码复制按钮** | 1486~1525 | 在每个 `<pre>` 右上角添加"Copy"按钮，点击复制代码文本，2 秒后恢复 |
| **代码语言标签** | 1512~1524 | 从 `<code>` 的 `class` 提取 `language-xxx`，在 `<pre>` 右上角显示语言标签 |
| **附件下载** | 1528~1533 | `click` 事件委托，调用 `unpackAndDownload()` |
| **附件解压与下载** | 1537~1679 | 从隐藏 `<span>` 读取 base64 数据 → 分块解码 → `Uint8Array` 转换 → `DecompressionStream` 解压 → `Blob` → `URL.createObjectURL` → 触发下载，全程进度条 UI |

**初学者注意：**
- `addEventListener('DOMContentLoaded', ...)` 确保 HTML 加载完毕后才执行 JS。
- 进度条通过 `requestAnimationFrame` 和 `await Promise(r => setTimeout(r, 20))` 给浏览器喘息机会。
- 附件使用 **zlib 最高压缩等级（level=9）**，在 Python 侧先压缩，浏览器端用 `DecompressionStream('deflate')` 解压。

#### 4.7 注入 CSP 安全策略（第 1685~1723 行）

内容安全策略是本工具的安全防线。策略内容：

```
default-src 'none';                 ← 默认不允许任何资源
script-src 'sha256-xxx' ...;        ← 只允许哈希匹配的内联脚本
style-src-elem 'sha256-yyy';        ← 只允许哈希匹配的内联样式
style-src-attr 'unsafe-inline';     ← 允许 style 属性
img-src data:;                       ← 只允许内嵌 base64 图片
media-src data:;                     ← 只允许内嵌 base64 媒体
font-src data:;                      ← 只允许内嵌 base64 字体
connect-src 'none';                  ← 禁止网络请求
frame-src 'none';                    ← 禁止 iframe
object-src 'none';                   ← 禁止插件
base-uri 'none';                     ← 禁止修改 base URL
form-action 'none';                  ← 禁止表单提交
require-trusted-types-for 'script';  ← 防范 DOM XSS
```

**初学者注意：**
- CSP 通过 `<meta http-equiv="Content-Security-Policy">` 设置。
- 每段内联脚本的 SHA256 哈希在生成时计算并写进策略，浏览器只执行哈希匹配的脚本，任何注入的脚本都会被阻止。
- 代码中有注释提醒：生产环境应通过 **HTTP 响应头** 设置 CSP（`<meta>` 方式不支持 `frame-ancestors` 等指令）。

---

### ⑤ `replace_with_base64()` — 离线嵌入核心

**文件位置：** 第 564~828 行

这是让 HTML **完全自包含、可离线使用** 的关键步骤。处理顺序：

#### 5.0 预处理（第 566~568 行）

1. `_unwrap_table_formatting()` — 表格单元格中的 `*text*` 被 markdown 库误解析为 `<em>`，本函数将其还原为纯文本 `*text*`（保留原始标记）。
2. `_convert_raw_md_syntax()` — HTML 块（如 `<div>` 内）中的 Markdown 语法不会被 markdown 库解析，本函数手动转换：标题、图片、链接、粗体、斜体、代码、空行。**祖先遍历**（第 495~502 行）确保代码块内不被误处理。

#### 5.1 视频标签处理（第 571~577 行）

直接处理 HTML 中的 `<video>` 和 `<source>` 标签，把 `src` 转为 base64。

#### 5.2 图片处理（第 580~612 行）

| 图片来源 | 处理方式 |
|---------|---------|
| **本地图片**（`./pic/xxx.png`） | 读取文件 → base64 → `data:image/png;base64,...` |
| **在线图片**（`https://...`） | 调用 `download_url_as_base64()` 下载 → base64 |
| **视频伪装成图片**（`img` 标签引用 `.mp4`） | 替换 `<img>` 为 `<video controls>` |
| **下载失败** | 保留原始 URL（至少在线能看） |

所有非 `data-inline` 的图片设置 `display: block; margin: 25px 0; border-radius: 6px;`。

#### 5.3 超链接处理（第 614~826 行）

对 `<a href="...">` 标签按类型分类处理：

**视频链接**（`.mp4` / `.mov` / `.webm` / `.ogg`）：
- 本地 → base64 嵌入
- 在线 → 下载后 base64 嵌入
- 包装成带标题的 `<div>` + `<video controls>`

**下载附件**（`.pdf` / `.zip` / `.docx` / `.xlsx` 等）：
- 本地文件 → 用 zlib level 9 压缩 → base64 → 存到隐藏 `<span>` → 替换 `<a>` 为精美卡片（带图标、文件名、大小、类型）
- 在线文件 → 下载 → 同样压缩嵌入
- 卡片样式：渐变背景、圆角、悬停发光效果

---

### ⑥ `wrap_tables()` — 表格美化

**文件位置：** 第 830~838 行

每个 `<table>` 外层包一个 `<div class="table-wrapper">`，实现：
- 水平滚动支持（表格太宽时不会撑破页面）
- 科技感渐变背景 + 蓝色表头 + 隔行变色 + 悬停高亮

---

### ⑦ 写入与完整性校验

**文件位置：** 第 1747~1830 行

1. **写文件**（第 1804~1807 行）：最终的 HTML 通过 `soup.encode(formatter='html5')` 序列化后写入 `.release.html`。

2. **追加完整性校验 JS**（第 1750~1790 行）：一个纯 JavaScript 实现的 SHA-256 算法，在浏览器端计算 `document.body.outerHTML` 的哈希值，显示在页面底部：
   ```
   File Integrity SHA-256: abcdef1234567890...
   ```

3. **更新 CSP**（第 1793~1802 行）：将完整性 JS 的哈希追加到 `script-src` 中，否则它自己会被 CSP 阻止。

4. **Playwright 无头浏览器验证**（第 1812~1826 行）：自动启动 Chromium 加载生成的 HTML，等待 `#__integrity-hash` 元素出现，输出浏览器端计算的哈希值（标记为 `[BROWSER]`）。开发者可以将这个哈希告知客户，客户打开文件对照验证即可判断文件是否被篡改。

---

## ⚙️ 用户可调节参数

文件顶部（第 74~114 行）有丰富的定制参数，修改后运行即可生效：

```python
BODY_FONT_SIZE       = "22px"     # 正文字体大小
BODY_LINE_HEIGHT     = "1.6"      # 行间距
MATH_COLOR           = "#58a6ff"  # 公式颜色

H1_MARGIN_TOP        = "30px"     # H1 上边距
H2_MARGIN_TOP        = "20px"     # H2 上边距
H3_MARGIN_TOP        = "60px"     # H3 上边距（特意设置更大，用于章节分隔）

IMAGE_SCALE_PERCENT  = 85         # 图片最大宽度 (%)
VIDEO_SCALE_PERCENT  = 85         # 视频最大宽度 (%)
SIDEBAR_WIDTH        = 500        # 侧边栏宽度

CODE_BLOCK_THEME     = "dark"     # 代码块主题
CODE_BLOCK_FONT_SIZE = "16px"     # 代码字体大小

SSL_VERIFY_CERT      = True       # 是否验证 HTTPS 证书
TRUSTED_RESOURCE_HASHES = {}      # 资源 SHA256 白名单
OFFLINE_MODE         = False      # True=跳过在线资源下载
```

---

## 🛡️ 安全机制详解

本工具有多层安全防护：

| 层级 | 技术 | 作用 |
|------|------|------|
| **CSP** | Content-Security-Policy | 阻止 XSS、数据外泄、iframe 嵌入 |
| **哈希绑定** | `'sha256-xxx'` | 只执行生成时计算好的脚本/样式 |
| **Trusted Types** | `require-trusted-types-for 'script'` | 防止 DOM XSS（如 innerHTML 注入） |
| **SSL 验证** | `ssl.CERT_REQUIRED` | 防止中间人攻击（可关闭） |
| **资源完整性** | SHA256 白名单验证 | 在线资源下载后校验哈希 |
| **文件完整性** | 浏览器端 outerHTML SHA256 | 打开网页即可肉眼验证文件是否被篡改 |
| **无 innerHTML** | DOM API 构建 UI | CSP 违规面板完全用 createElement / appendChild |

---

## 📂 文件结构

```
markdown_to_html/
├── markdown_to_html_v12.18.py   ← 主程序（本文主角）
├── markdown_to_html_v12.17.py   ← 旧版本
├── markdown_to_html_v12.16.py   ← 更早版本
├── requirements_v12.18.txt      ← 依赖清单
├── build_bat_user_manual.md     ← 示例输入（markdown 源文件）
├── build_bat_user_manual.jpg    ← 示例封面图
├── pic2/                        ← 示例图片/视频目录
├── files/                       ← 示例附件目录
├── env.bat                      ← 环境配置脚本
└── output.log                   ← 运行日志
```

运行后生成 `*.release.html`（如 `build_bat_user_manual.release.html`）。

---

## 🔍 常见问题（FAQ）

### Q：生成的 HTML 没有网络也能用吗？
**是的。** 所有本地和在线资源（图片、视频、附件）都会被下载并转为 base64 嵌入 HTML，唯一的限制是：**在线资源下载失败时会保留原始 URL**，这时需要网络。

### Q：公式显示为红色代码怎么办？
安装 `ziamath` 库：`pip install ziamath`。如果安装后仍显示红色，可能是公式语法不兼容。

### Q：如何跳过在线资源下载？
设置 `OFFLINE_MODE = True`（第 114 行），所有 http/https 资源都会被跳过，转换速度更快。

### Q：CSP 弹出了红色警告面板？
这表示有未授权的脚本或资源被浏览器成功拦截。如果你的文件没有被篡改，忽略即可。如果频繁出现，检查是否有外部资源没有转为 base64。

### Q：我改了什么让程序出错了？
大多数错误来自：1) 缩进错误（Python 对缩进敏感）；2) 字符串引号不匹配；3) `BASE_CSS` 中 CSS 语法错误。检查控制台输出的 `[ERROR]` 信息。

---

## 🧪 测试与验证

```bash
# 查看运行日志
cat output.log

# 浏览器端完整性校验
# 打开 .release.html，滚动到底部，看到：
# File Integrity SHA-256: xxxxx...
# 与控制台输出的 [BROWSER] xxxxx... 一致则文件完整
```

---

## 📝 版本历史摘要

| 版本 | 新增功能 |
|------|---------|
| v12.4 | 表格间距智能修复 |
| v12.5 | LaTeX 公式转换 |
| v12.7 | 附件卡片美化 + 下载进度条 |
| v12.12 | 在线资源离线嵌入（图片/视频/附件自动下载为 base64） |
| v12.13 | 修复代码块内 Markdown 语法被误转换 |
| v12.15 | CSP 安全防护 + inline onclick 迁移到 addEventListener |
| v12.17 | SSL 验证加固 + SHA256 完整性校验 + Trusted Types |
| v12.18 | 浏览器端完整性校验（Playwright 无头浏览器） |

---

## 📖 给初学者的学习建议

1. **先跑起来，再读代码。** 找一个 `.md` 文件运行程序，看看生成的 HTML 长什么样，再回头对照源码。
2. **从 `main()` 开始读。** 第 1727 行 `main()` 是入口，它调用 `process_file()` → `replace_with_base64()` → `wrap_tables()`，按这个主线追踪。
3. **善用 print 调试。** 在关键位置加 `print()` 输出变量值，理解数据如何流动。
4. **不要怕改坏。** 有 Git 版本控制，改坏了就 `git checkout -- README.md` 恢复。大胆尝试修改 CSS 颜色、字体大小。
5. **理解"分层"思想。** 这个程序分三层：Markdown 原文层 → BeautifulSoup DOM 层 → 最终 HTML 字符串层。每一层做不同的事情。
6. **关注安全。** 这个项目展示了真实世界中的安全实践（CSP、Trusted Types、完整性校验），虽然初学者可能觉得复杂，但这是专业软件的标配。
