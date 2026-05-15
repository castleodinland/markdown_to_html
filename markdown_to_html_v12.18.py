# -*- coding: utf-8 -*-
# markdown_to_html_v12.18.py
# 【Markdown 直出 HTML - 在线资源离线嵌入版】
#
# v12.4 更新日志:
# 1. 新增表格预处理功能：自动修复 Markdown 表格与上方文字紧挨导致无法识别的问题
# 2. 逻辑：在解析前扫描内容，若发现表格头前无空行，自动插入空行
# 3. 智能避让：该修复逻辑会自动识别代码块，不修改代码块内的内容
# 4. 继承 v12.3 所有定制参数和功能
# v12.5 更新日志:
# 1. 增加Latex公式转换功能，公式行间距调节待完善
# v12.7 更新日志:
# 1. 附件显示名称使用中括号内名称，下载文件名也使用该名称+原扩展名
# 2. 附件卡片美化：添加文件类型图标、显示文件大小和类型
# 3. 附件下载解压增加进度条UI，避免页面卡住无反馈
# 4. 图片缩放改为max-width模式，小图片不再被强制放大
# 5. 所有图片和脚本生成的视频左对齐
# v12.12 更新日志:
# 1. 新增在线资源离线嵌入：自动下载 http/https 图片、视频、文档等资源并嵌入为 base64 data URI
# 2. 转换后 HTML 完全自包含，可离线使用
# 3. 无在线资源时，转换结果与原有版本完全一致
# v12.13 更新日志:
# 1. 修复 _convert_raw_md_syntax() 仅检查直接父节点导致代码块内文本被误处理的问题
# 2. 原因：Pygments 高亮后代码文本在 <span> 内，父节点非 code/pre，斜体/粗体正则会吃掉注释中的 *
# 3. 修复：改为祖先遍历，任意祖先为 code/pre/script/style 则跳过
# v12.15 更新日志:
# 1. 新增 CSP (Content Security Policy) 安全防护，基于 sha256 哈希绑定内嵌脚本
# 2. 将所有 onclick 内联事件迁移到主脚本的 addEventListener（CSP 兼容）
# 3. 将公式块 onmouseover/onmouseout 迁移到 CSS :hover 伪类
# 4. 浏览器原生阻止：未授权脚本注入、内联事件篡改、网络请求、iframe/object/embed
# v12.17 更新日志:
# 1. 修复 SSL 证书验证被禁用的问题 (CERT_NONE → CERT_REQUIRED)，默认启用验证
# 2. CSP style-src 拆分收紧：style-src-elem 使用 sha256 哈希绑定，style-src-attr 保留 unsafe-inline
# 3. CSP 违规面板改用 DOM API 构建，消除 innerHTML 注入风险
# 4. 新增 require-trusted-types-for 'script' 防范 DOM XSS
# 5. 从 img-src / media-src 中移除 blob: 缩小攻击面
# 6. 下载在线资源时自动计算并输出 SHA256，支持可选的哈希白名单验证
# 7. 生成 HTML 中增加说明注释，提示生产环境应通过 HTTP 响应头部署 CSP
# 8. 新增文件完整性自校验：纯 JS SHA256 实现，浏览器端读取 outerHTML 计算哈希值并显示在页面末尾
#    生成时在同一文件内容上计算 SHA256 并打印在控制台。开发者将控制台哈希值告知客户，
#    客户打开文件对比页面底部显示的哈希值是否一致即可判断文件是否被篡改。
# v12.18 更新日志:
# 1. 移除生成时的 Python 侧 SHA256 计算与打印（[INTEGRITY]），改为通过 Playwright 无头浏览器
#    加载 HTML，自动执行浏览器端完整性校验 JS 并输出浏览器端计算的 SHA256（[BROWSER]）。

import os
import glob
import markdown # 需安装: pip install markdown
from bs4 import BeautifulSoup, Comment
import base64
import re
import mimetypes
from datetime import datetime
import zlib  # 需在顶部添加
import hashlib  # v12.15: CSP sha256 哈希计算
from pathlib import Path
import urllib.request
import urllib.parse
import ssl
import warnings
try:
    from bs4 import MarkupResemblesLocatorWarning
    warnings.filterwarnings('ignore', category=MarkupResemblesLocatorWarning)
except ImportError:
    pass

# 尝试导入 ziamath
try:
    import ziamath
except ImportError:
    ziamath = None

# ==================== 用户可调节参数 (v12.3 定制) ====================
# --- 字体与排版 ---
BODY_FONT_SIZE            = "22px"    # 正文字体大小
BODY_LINE_HEIGHT          = "1.6"     # 正文行间距
MATH_COLOR                = "#58a6ff"  # 公式颜色（适配深色主题）

# --- 标题排版 (H1-H6 边距独立控制) ---
# 添加 !important 确保这些设置绝对生效
H1_MARGIN_TOP             = "30px"
H1_MARGIN_BOTTOM          = "10px"
H2_MARGIN_TOP             = "20px"
H2_MARGIN_BOTTOM          = "6px"
H3_MARGIN_TOP             = "60px"
H3_MARGIN_BOTTOM          = "5px"
# H1-H6 的行高
HEADING_LINE_HEIGHT       = "2.4"

# --- 分割线 ---
HR_HEIGHT                 = "2px"     # 分割线粗细

# --- 布局与媒体 ---
IMAGE_SCALE_PERCENT       = 85        # 图片最大宽度
VIDEO_SCALE_PERCENT       = 85
SIDEBAR_WIDTH             = 500       # 侧边栏宽度
THEME_PHOTO_MAX_HEIGHT_PX = 300
THEME_PHOTO_OBJECT_POSITION = "center"

# --- 代码块设置 ---
CODE_BLOCK_THEME          = "dark"    # 强制使用 dark
CODE_BLOCK_FONT_SIZE      = "16px"
INLINE_CODE_FONT_SIZE     = "16px"
CODE_BLOCK_LINE_HEIGHT    = "1.0"     # 代码块行间距

# --- 侧边栏标签 ---
SIDEBAR_TRIGGER_TEXT      = "展示目录"

# --- 安全设置 ---
SSL_VERIFY_CERT          = True      # 是否验证 HTTPS 服务器证书（关闭有 MITM 风险，仅用于自签名证书场景）
TRUSTED_RESOURCE_HASHES  = {}        # {url: sha256_hex} 可选：指定资源的预期 SHA256 哈希以验证完整性

# --- 离线模式 ---
OFFLINE_MODE             = False      # True=跳过所有在线资源下载（无网络超时等待），False=正常下载
# ===============================================================

VIDEO_EXTENSIONS = ('.mp4', '.mov', '.webm', '.ogg')
DOWNLOADABLE_EXTENSIONS = (
    '.pdf', '.zip', '.rar', '.7z', '.tar', '.gz', '.xz',
    '.xlsx', '.xls', '.docx', '.doc', '.pptx', '.ppt',
    '.exe', '.bin', '.img', '.iso', '.mp3', '.wav', 
    'approjx',
)

# --- 核心 CSS ---
BASE_CSS = f"""
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    line-height: {BODY_LINE_HEIGHT};
    color: #c9d1d9;
    background-color: #0d1117; 
    padding: 30px 50px;
    max-width: 90%;
    margin: 0 auto;
}}

/* 标题通用样式 */
h1, h2, h3, h4, h5, h6 {{ 
    font-weight: 600; 
    line-height: {HEADING_LINE_HEIGHT};
    color: #e6edf3;
}}

/* 独立控制各级标题 (强制生效) */
h1 {{ 
    font-size: 2.2em; 
    margin-top: {H1_MARGIN_TOP} !important; 
    margin-bottom: {H1_MARGIN_BOTTOM} !important; 
    padding-bottom: 0.3em; 
    border-bottom: 1px solid #21262d; 
}}
h2 {{ 
    font-size: 1.7em; 
    margin-top: {H2_MARGIN_TOP} !important; 
    margin-bottom: {H2_MARGIN_BOTTOM} !important; 
    padding-bottom: 0.3em; 
    border-bottom: 1px solid #21262d; 
}}
h3 {{ 
    font-size: 1.4em; 
    margin-top: {H3_MARGIN_TOP} !important; 
    margin-bottom: {H3_MARGIN_BOTTOM} !important; 
}}
h4 {{ margin-top: 24px; margin-bottom: 16px; font-size: 1.2em; }}
h5 {{ margin-top: 24px; margin-bottom: 16px; font-size: 1.0em; }}
h6 {{ margin-top: 24px; margin-bottom: 16px; font-size: 0.85em; color: #8b949e; }}

p {{ margin-top: 0; margin-bottom: 16px; color: #c9d1d9; }}

blockquote {{ 
    padding: 0 1em; color: #8b949e; 
    border-left: 0.25em solid #30363d; 
    margin: 0 0 16px 0; 
    background: rgba(127, 127, 127, 0.05);
}}

ul, ol {{ padding-left: 2em; margin-top: 0; margin-bottom: 16px; }}

/* ============= 表格样式 - 科技感官方风格 ============= */
.table-wrapper {{
    overflow-x: auto;
    margin: 20px 0;
    border-radius: 8px;
    border: 1px solid #30363d;
    background: linear-gradient(145deg, #0d1117 0%, #131921 100%);
    box-shadow: 0 2px 12px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.03);
}}
table {{
    display: table;
    width: 100%;
    table-layout: auto;
    border-spacing: 0;
    border-collapse: collapse;
    font-size: 0.92em;
}}
table thead th {{
    background: linear-gradient(180deg, #1c2333 0%, #161b22 100%);
    color: #e6edf3;
    font-weight: 700;
    font-size: 0.9em;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    padding: 12px 16px;
    border-bottom: 2px solid #58a6ff;
    border-right: 1px solid rgba(88,166,255,0.15);
    position: relative;
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
table thead th:last-child {{
    border-right: none;
}}
table thead th::after {{
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(88,166,255,0.3), transparent);
}}
table tbody tr {{
    border-top: 1px solid rgba(48,54,61,0.6);
    transition: background-color 0.15s ease;
}}
table tbody tr:first-child {{
    border-top: none;
}}
table tbody tr:nth-child(odd) {{
    background-color: rgba(13,17,23,0.5);
}}
table tbody tr:nth-child(even) {{
    background-color: rgba(22,27,34,0.5);
}}
table tbody tr:hover {{
    background-color: rgba(88,166,255,0.06);
}}
table tbody td {{
    padding: 10px 16px;
    border-right: 1px solid rgba(48,54,61,0.4);
    border-bottom: 1px solid rgba(48,54,61,0.3);
    color: #c9d1d9;
    vertical-align: top;
    word-wrap: break-word;
    overflow-wrap: break-word;
    min-width: 50px;
}}
table tbody td:last-child {{
    border-right: none;
}}
table tbody tr:last-child td {{
    border-bottom: none;
}}

/* 分割线高度控制 */
hr {{ 
    height: {HR_HEIGHT}; 
    padding: 0; margin: 24px 0; 
    background-color: #30363d; 
    border: 0; 
}}

a {{ color: #58a6ff; text-decoration: none; }}
a:hover {{ text-decoration: underline; color: #79c0ff; }}

/* 确保图片和视频在任何容器下都能保持响应式，且左对齐 */
img, video {{
    max-width: 90%;
    height: auto;
}}


"""

# ==================== v12.12 新增：在线资源下载 ====================

# 创建 SSL 上下文（由 SSL_VERIFY_CERT 参数控制是否验证证书）
_ssl_ctx = ssl.create_default_context()
if SSL_VERIFY_CERT:
    _ssl_ctx.check_hostname = True
    _ssl_ctx.verify_mode = ssl.CERT_REQUIRED
else:
    import warnings
    warnings.warn("SSL certificate verification is disabled — HTTPS resources cannot be authenticated. "
                  "This creates a man-in-the-middle vulnerability. Only disable for self-signed certificates.")
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE

def _url_get_extension(url):
    """从 URL 中提取文件扩展名（忽略查询参数和片段）"""
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path)
    ext = os.path.splitext(path)[1].lower()
    return ext

def _guess_mime_from_url(url):
    """根据 URL 猜测 MIME 类型"""
    ext = _url_get_extension(url)
    if ext:
        mime = mimetypes.guess_type(url)[0]
        if mime:
            return mime
    # 尝试从 Content-Type 猜测（通过请求头）
    return None

def download_url_as_base64(url, timeout=30):
    """
    下载在线资源并返回 base64 编码字符串。
    返回 (base64_string, mime_type) 或 None（失败时）。
    """
    if OFFLINE_MODE:
        return None
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx) as resp:
            content_type = resp.headers.get('Content-Type', '')
            # 从 Content-Type 中提取主 MIME 类型（去掉 charset 等参数）
            mime = content_type.split(';')[0].strip()
            # 如果 Content-Type 为空或不可识别，尝试从 URL 猜测
            if not mime or mime == 'application/octet-stream':
                guessed = _guess_mime_from_url(url)
                if guessed:
                    mime = guessed
            if not mime:
                mime = 'application/octet-stream'
            
            data = resp.read()

            # v12.17: 计算并输出 SHA256 哈希，支持可选的白名单验证
            sha256_hex = hashlib.sha256(data).hexdigest()
            if url in TRUSTED_RESOURCE_HASHES:
                expected = TRUSTED_RESOURCE_HASHES[url]
                if sha256_hex != expected:
                    print(f"  [WARN] 资源完整性校验失败: {url}")
                    print(f"    期望 SHA256: {expected}")
                    print(f"    实际 SHA256: {sha256_hex}")
                    return None
            else:
                print(f"  [INFO] 资源 SHA256: {sha256_hex}")

            b64 = base64.b64encode(data).decode('utf-8')
            return (b64, mime)
    except Exception as e:
        if not OFFLINE_MODE:
            print(f"  [INFO] 下载在线资源失败 (跳过): {url} ({e})")
        return None

# ==================== 原有功能函数 ====================

def get_base64_encoded_data(filepath):
    filepath = filepath.replace("\\", "/")
    try:
        from urllib.parse import unquote
        filepath = unquote(filepath)
    except: pass
    
    if not os.path.exists(filepath):
        if os.path.exists(os.path.basename(filepath)):
            filepath = os.path.basename(filepath)
        else:
            return None
            
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def _format_file_size(size_bytes):
    """将字节数格式化为可读的文件大小字符串"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def _get_file_icon(ext):
    """根据文件扩展名返回对应的图标"""
    ext = ext.lower()
    icon_map = {
        '.pdf': '📄', '.zip': '🗜️', '.rar': '🗜️', '.7z': '🗜️',
        '.tar': '🗜️', '.gz': '🗜️', '.xz': '🗜️',
        '.xlsx': '📊', '.xls': '📊', '.csv': '📊',
        '.docx': '📝', '.doc': '📝',
        '.pptx': '📽️', '.ppt': '📽️',
        '.exe': '⚙️', '.bin': '💿', '.img': '💿', '.iso': '💿',
        '.mp3': '🎵', '.wav': '🎵',
        'approjx': '🎵',
    }
    return icon_map.get(ext, '📎')

def _resolve_src_to_base64(src):
    """
    通用资源解析函数：将 src（本地路径或在线 URL）转为 base64 数据。
    返回 (base64_string, mime_type) 或 None。
    """
    if not src or src.startswith('data:'):
        return None
    
    if src.startswith(('http:', 'https:')):
        result = download_url_as_base64(src)
        if result:
            return result
        return None
    
    # 本地文件
    b64 = get_base64_encoded_data(src)
    if b64:
        mime = mimetypes.guess_type(src)[0]
        if src.lower().endswith(VIDEO_EXTENSIONS):
            mime = mime or 'video/mp4'
        else:
            mime = mime or 'image/png'
        return (b64, mime)
    
    return None

def _unwrap_table_formatting(soup):
    """将表格单元格中 markdown 库自动生成的格式化标签还原为纯文本。
    
    表格内容（如 C 函数指针声明 void *func）中的 * 会被 markdown 库误解析为 <em>，
    需要将 td/th 内的 <em>、<strong>、<code> 等标签解包回带原始标记的纯文本。
    """
    # 先收集所有需要处理的标签（避免迭代中修改 DOM）
    replacements = []
    for cell in soup.find_all(['td', 'th']):
        for tag in cell.find_all(['em', 'strong', 'code']):
            text = tag.get_text()
            if tag.name == 'em':
                replacement = f'*{text}*'
            elif tag.name == 'strong':
                replacement = f'**{text}**'
            elif tag.name == 'code':
                replacement = f'`{text}`'
            else:
                replacement = text
            replacements.append((tag, replacement))
    # 再执行替换
    for tag, replacement in replacements:
        tag.replace_with(BeautifulSoup(replacement, 'html.parser'))
    return soup


def _convert_raw_md_syntax(soup):
    """
    v12.12 新增：处理 HTML 块中未被 markdown 库解析的 markdown 语法。
    Python markdown 库不会解析 <div> 等 HTML 块内的 markdown 语法，
    导致标题、粗体、斜体、徽章等作为原始文本输出。

    处理顺序：
    0. ^#{1,6} heading → <h1>~<h6>
    1. [![alt](img_url)](link_url) → 带链接的图片（标记 data-inline）
    2. ![alt](url) → 独立图片（标记 data-inline）
    3. [text](url) → 链接（仅处理 http/https）
    4. **bold** → <strong>
    5. *italic* → <em>
    6. `code` → <code>
    7. 空行(\n\n) → <br>（段落分隔）
    8. 连续行内元素间的单个换行 → 空格（图片同行显示）
    """
    _h_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']

    # ATX 标题: # text, ## text, etc.（必须行首，可选尾部 #）
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+?)(?:\s+#+\s*)?$', re.MULTILINE)

    # 模式1: 链接内包含图片 [![alt](img_url)](link_url) 或 [![alt](img_url)]()
    link_img_pattern = re.compile(
        r'\[\!\[([^\]]*)\]\(([^)]+)\)\]\(([^)]*)\)',
        re.DOTALL
    )
    # 模式2: 图片 ![alt](url)
    img_pattern = re.compile(
        r'\!\[([^\]]*)\]\(([^)]+)\)',
        re.DOTALL
    )
    # 模式3: 链接 [text](url)
    link_pattern = re.compile(
        r'\[([^\]]+)\]\((https?://[^)]+)\)',
        re.DOTALL
    )
    # 模式4: 粗体 **text**
    bold_pattern = re.compile(r'\*\*(.+?)\*\*')
    # 模式5: 斜体 *text*（单星号，不与粗体冲突）
    italic_pattern = re.compile(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)')
    # 模式6: 行内代码 `code`
    inline_code_pattern = re.compile(r'`([^`]+)`')

    def _is_inside_protected_block(node):
        """检查节点是否在受保护的块内（code/pre/script/style/td/th），支持多层嵌套"""
        p = node.parent
        while p:
            if p.name in ('script', 'style', 'code', 'pre', 'td', 'th'):
                return True
            p = p.parent
        return False

    for text_node in soup.find_all(string=True):
        if not text_node.strip():
            continue
        if _is_inside_protected_block(text_node):
            continue

        text = str(text_node)
        original_text = text

        # 步骤0: 处理 ATX 标题
        def _replace_heading(m):
            level = len(m.group(1))
            content_h = m.group(2).strip()
            tag = _h_tags[level - 1]
            return f'<{tag}>{content_h}</{tag}>'
        text = heading_pattern.sub(_replace_heading, text)

        # 步骤1: 处理 [![alt](img_url)](link_url) 或 [![alt](img_url)]()
        def _replace_link_img(m):
            alt, img_url, link_url = m.group(1), m.group(2), m.group(3).strip()
            img_tag = f'<img src="{img_url}" alt="{alt}" data-inline="1" style="max-width: {IMAGE_SCALE_PERCENT}%; height: auto; display: inline-block; margin: 2px 4px; vertical-align: middle;"/>'
            if link_url:
                return f'<a href="{link_url}">{img_tag}</a>'
            return img_tag
        text = link_img_pattern.sub(_replace_link_img, text)

        # 步骤2: 处理 ![alt](url)（独立图片）
        text = img_pattern.sub(
            lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}" data-inline="1" style="max-width: {IMAGE_SCALE_PERCENT}%; height: auto; display: inline-block; margin: 2px 4px; vertical-align: middle;">',
            text
        )

        # 步骤3: 处理 [text](http_url)（链接）
        text = link_pattern.sub(
            lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
            text
        )

        # 步骤4: 处理粗体 **text**
        text = bold_pattern.sub(r'<strong>\1</strong>', text)

        # 步骤5: 处理斜体 *text*
        text = italic_pattern.sub(r'<em>\1</em>', text)

        # 步骤6: 处理行内代码 `code`
        text = inline_code_pattern.sub(r'<code>\1</code>', text)

        # 步骤7: 空行转换为 <br>（段落分隔）
        text = text.replace('\n\n', '<br>\n')

        # 步骤8: 连续行内元素间的单个换行转为空格（确保图片同行显示）
        # 仅匹配 >\n<（标签边界间的单个换行），不匹配 >\n\n<（已被步骤7处理）
        text = re.sub(r'>\n(?!\n)<', '> <', text)

        if text != original_text:
            new_soup = BeautifulSoup(text, 'html.parser')
            text_node.replace_with(new_soup)

    return soup

def replace_with_base64(soup):
    # v12.13 步骤 0a：去除表格单元格中被 markdown 库误解析的格式化标签
    soup = _unwrap_table_formatting(soup)
    # v12.12 步骤 0b：先将 HTML 块中未解析的 markdown 语法转为 HTML 标签
    soup = _convert_raw_md_syntax(soup)
    
    # 1. 优先处理 HTML 原生 video 和 source 标签 (确保已存在的视频标签被合并)
    for vid_node in soup.find_all(['video', 'source']):
        src = vid_node.get('src')
        if src and not src.startswith('data:'):
            b64 = get_base64_encoded_data(src)
            if b64:
                mime = mimetypes.guess_type(src)[0] or 'video/mp4'
                vid_node['src'] = f'data:{mime};base64,{b64}'

    # 2. 处理 img 标签 (增加对"图片语法引用视频"的兼容 + v12.12: 在线图片嵌入)
    for img_tag in soup.find_all('img'):
        src = img_tag.get('src')
        if not src or src.startswith('data:'):
            continue
        
        if src.startswith(('http:', 'https:')):
            # v12.12: 下载在线图片并嵌入
            result = download_url_as_base64(src)
            if result:
                b64_data, mime = result
                img_tag['src'] = f'data:{mime};base64,{b64_data}'
                # 保留 _convert_raw_md_syntax 设置的 inline-block 样式（badge 图片等）
                if not img_tag.get('data-inline'):
                    img_tag['style'] = f"max-width: {IMAGE_SCALE_PERCENT}%; height: auto; display: block; margin: 25px 0; border-radius: 6px;"
            else:
                # 下载失败，保留原始 URL（至少有在线展示）
                pass
            continue
        
        # 本地文件逻辑（原有）
        b64_data = get_base64_encoded_data(src)
        if b64_data:
            # 兼容性修复：如果后缀是视频格式，则将 img 标签替换为 video 标签
            if src.lower().endswith(VIDEO_EXTENSIONS):
                mime = mimetypes.guess_type(src)[0] or 'video/mp4'
                v_tag = soup.new_tag('video', controls=True)
                v_tag['style'] = f"max-width: {VIDEO_SCALE_PERCENT}%; height: auto; display: block; margin: 25px 0; border-radius: 8px; background: #000;"
                v_tag['src'] = f'data:{mime};base64,{b64_data}'
                img_tag.replace_with(v_tag)
            else:
                mime_type = mimetypes.guess_type(src)[0] or 'image/png'
                img_tag['src'] = f'data:{mime_type};base64,{b64_data}'
                img_tag['style'] = f"max-width: {IMAGE_SCALE_PERCENT}%; height: auto; display: block; margin: 25px 0; border-radius: 6px;"

    # 3. 处理 a 标签 (保持原有逻辑：将 Markdown 视频链接转为内嵌播放器 + v12.12: 在线资源嵌入)
    for a_tag in soup.find_all('a'):
        href = a_tag.get('href')
        if not href or href.startswith(('data:', 'mailto:', '#')):
            continue
        
        text = a_tag.get_text(strip=True)
        is_online = href.startswith(('http:', 'https:'))
        
        if href.lower().endswith(VIDEO_EXTENSIONS):
            if is_online:
                # v12.12: 下载在线视频并嵌入
                result = download_url_as_base64(href)
                if result:
                    b64_data, mime = result
                    video_tag = soup.new_tag('video', controls=True)
                    video_tag['style'] = f"max-width: {VIDEO_SCALE_PERCENT}%; height: auto; display: block; margin: 25px 0; border-radius: 8px; background: #000;"
                    source = soup.new_tag('source', src=f'data:{mime};base64,{b64_data}', type=mime)
                    video_tag.append(source)
                    
                    wrapper = soup.new_tag('div')
                    if text and text != href:
                        caption = soup.new_tag('p')
                        caption.string = f"Video: {text}"
                        caption['style'] = "color:#8b949e; font-size:0.9em; margin-bottom:5px; font-style: italic; text-align: center;"
                        wrapper.append(caption)
                    wrapper.append(video_tag)
                    a_tag.replace_with(wrapper)
                    continue
                # 下载失败，保留原始链接
                continue
            
            # 本地视频逻辑（原有）
            b64_data = get_base64_encoded_data(href)
            if b64_data:
                mime = mimetypes.guess_type(href)[0] or 'video/mp4'
                video_tag = soup.new_tag('video', controls=True)
                video_tag['style'] = f"max-width: {VIDEO_SCALE_PERCENT}%; height: auto; display: block; margin: 25px 0; border-radius: 8px; background: #000;"
                # 将 Base64 数据直接写入 source
                source = soup.new_tag('source', src=f'data:{mime};base64,{b64_data}', type=mime)
                video_tag.append(source)
                
                wrapper = soup.new_tag('div')
                if text and text != href:
                    caption = soup.new_tag('p')
                    caption.string = f"Video: {text}"
                    caption['style'] = "color:#8b949e; font-size:0.9em; margin-bottom:5px; font-style: italic; text-align: center;"
                    wrapper.append(caption)
                wrapper.append(video_tag)
                a_tag.replace_with(wrapper)

        elif not is_online and (href.lower().endswith(DOWNLOADABLE_EXTENSIONS) or a_tag.get('download') is not None):
            # 本地可下载附件逻辑（原有）
            if os.path.exists(href):
                with open(href, "rb") as f:
                    raw_data = f.read()
                    # 使用 zlib 最高等级压缩 (9)
                    compressed_data = zlib.compress(raw_data, level=9)
                    b64_data = base64.b64encode(compressed_data).decode('utf-8')
                
                file_name = os.path.basename(href)
                mime = mimetypes.guess_type(href)[0] or 'application/octet-stream'
                
                # 获取中括号内的名称作为显示名称
                display_text = a_tag.get_text(strip=True)
                if display_text and display_text != href:
                    link_display_name = display_text
                else:
                    link_display_name = file_name
                
                # 下载时使用中括号名称+原扩展名
                # ext = os.path.splitext(href)[1]
                ext = "".join(Path(href).suffixes)
                download_name = link_display_name + ext if not link_display_name.lower().endswith(ext.lower()) else link_display_name
                
                # 计算原始文件大小
                file_size = len(raw_data)
                
                # 将 base64 数据存入隐藏 span，onclick 只传 ID（避免大字符串阻塞 onclick 解析）
                b64_id = f'att-data-{id(a_tag)}'
                hidden_span = soup.new_tag('span')
                hidden_span['id'] = b64_id
                hidden_span['style'] = 'display:none;'
                hidden_span['data-mime'] = mime
                hidden_span.string = b64_data
                a_tag.insert_before(hidden_span)

                # v12.15: 使用 data 属性 + 事件委托（CSP 安全，替代 inline onclick）
                a_tag['href'] = "#"
                a_tag['data-unpack-id'] = b64_id
                a_tag['data-filename'] = download_name
                
                # 美化附件卡片
                file_ext = ext.lstrip('.').upper()
                file_size_str = _format_file_size(file_size)
                
                # 根据文件类型选择图标
                icon = _get_file_icon(ext)
                
                a_tag['style'] = (
                    "display: inline-flex; align-items: center; gap: 10px; "
                    "padding: 12px 20px; background: linear-gradient(135deg, #1c2333 0%, #161b22 100%); "
                    "color: #e6edf3 !important; border-radius: 10px; text-decoration: none !important; "
                    "font-weight: 500; font-size: 0.9em; margin: 10px 0; "
                    "border: 1px solid #30363d; transition: all 0.2s ease; "
                    "max-width: 600px; cursor: pointer;"
                )
                a_tag.clear()
                
                # 图标区域
                icon_span = soup.new_tag('span')
                icon_span['style'] = (
                    "display: inline-flex; align-items: center; justify-content: center; "
                    "width: 40px; height: 40px; border-radius: 8px; "
                    "background: rgba(56, 139, 253, 0.15); font-size: 20px; flex-shrink: 0;"
                )
                icon_span.string = icon
                
                # 文件信息区域
                info_div = soup.new_tag('span')
                info_div['style'] = "display: flex; flex-direction: column; gap: 2px; min-width: 0;"
                
                name_span = soup.new_tag('span')
                name_span['style'] = "color: #e6edf3; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
                name_span.string = link_display_name
                
                detail_span = soup.new_tag('span')
                detail_span['style'] = "color: #8b949e; font-size: 0.85em;"
                detail_span.string = f"{file_ext} · {file_size_str}"
                
                info_div.append(name_span)
                info_div.append(detail_span)
                
                a_tag.append(icon_span)
                a_tag.append(info_div)

        elif is_online and (href.lower().endswith(DOWNLOADABLE_EXTENSIONS) or a_tag.get('download') is not None):
            # v12.12: 在线可下载附件 → 下载后嵌入为本地可下载附件（使用同样的 zlib 压缩方案）
            result = download_url_as_base64(href)
            if result:
                raw_data = base64.b64decode(result[0])
                compressed_data = zlib.compress(raw_data, level=9)
                b64_data = base64.b64encode(compressed_data).decode('utf-8')
                mime = result[1]
                
                # 提取文件名
                parsed = urllib.parse.urlparse(href)
                file_name = os.path.basename(urllib.parse.unquote(parsed.path))
                
                # 获取显示名称
                display_text = a_tag.get_text(strip=True)
                if display_text and display_text != href:
                    link_display_name = display_text
                else:
                    link_display_name = file_name
                
                ext = "".join(Path(file_name).suffixes) if '.' in file_name else ""
                if not ext:
                    ext = _url_get_extension(href)
                download_name = link_display_name + ext if ext and not link_display_name.lower().endswith(ext.lower()) else link_display_name
                
                file_size = len(raw_data)
                file_ext = ext.lstrip('.').upper() if ext else 'FILE'
                file_size_str = _format_file_size(file_size)
                icon = _get_file_icon(ext) if ext else '📎'
                
                b64_id = f'att-data-{id(a_tag)}'
                hidden_span = soup.new_tag('span')
                hidden_span['id'] = b64_id
                hidden_span['style'] = 'display:none;'
                hidden_span['data-mime'] = mime
                hidden_span.string = b64_data
                a_tag.insert_before(hidden_span)

                # v12.15: 使用 data 属性 + 事件委托（CSP 安全，替代 inline onclick）
                a_tag['href'] = "#"
                a_tag['data-unpack-id'] = b64_id
                a_tag['data-filename'] = download_name
                
                a_tag['style'] = (
                    "display: inline-flex; align-items: center; gap: 10px; "
                    "padding: 12px 20px; background: linear-gradient(135deg, #1c2333 0%, #161b22 100%); "
                    "color: #e6edf3 !important; border-radius: 10px; text-decoration: none !important; "
                    "font-weight: 500; font-size: 0.9em; margin: 10px 0; "
                    "border: 1px solid #30363d; transition: all 0.2s ease; "
                    "max-width: 600px; cursor: pointer;"
                )
                a_tag.clear()
                
                icon_span = soup.new_tag('span')
                icon_span['style'] = (
                    "display: inline-flex; align-items: center; justify-content: center; "
                    "width: 40px; height: 40px; border-radius: 8px; "
                    "background: rgba(56, 139, 253, 0.15); font-size: 20px; flex-shrink: 0;"
                )
                icon_span.string = icon
                
                info_div = soup.new_tag('span')
                info_div['style'] = "display: flex; flex-direction: column; gap: 2px; min-width: 0;"
                
                name_span = soup.new_tag('span')
                name_span['style'] = "color: #e6edf3; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
                name_span.string = link_display_name
                
                detail_span = soup.new_tag('span')
                detail_span['style'] = "color: #8b949e; font-size: 0.85em;"
                detail_span.string = f"{file_ext} · {file_size_str}"
                
                info_div.append(name_span)
                info_div.append(detail_span)
                
                a_tag.append(icon_span)
                a_tag.append(info_div)

    return soup

def wrap_tables(soup):
    """将所有 table 元素包裹在 table-wrapper div 中，实现均匀列宽和滚动支持"""
    for table_tag in soup.find_all('table'):
        if table_tag.parent and table_tag.parent.name == 'div' and table_tag.parent.get('class') and 'table-wrapper' in table_tag.parent.get('class'):
            continue
        wrapper = soup.new_tag('div')
        wrapper['class'] = ['table-wrapper']
        table_tag.wrap(wrapper)
    return soup

# ==================== 公式渲染核心逻辑 ====================

def render_latex_to_svg(latex_str, inline=True):
    """
    将 LaTeX 字符串转换为具有美化样式的 SVG。
    
    参数:
    latex_str (str): LaTeX 源码字符串。
    inline (bool): 是否为行内公式。
    
    返回:
    str: 包含美化 CSS 的 HTML 字符串。
    """
    if not ziamath:
        return f'<code style="color: #ff7b72; background: rgba(248,81,73,0.1); padding: 2px 4px; border-radius: 4px;">{latex_str} (Please install ziamath)</code>'
    
    try:
        # ziamath 渲染核心，设置颜色和基础大小
        # 提示：size=20 对应约 22px 的正文大小
        math_obj = ziamath.Latex(latex_str, color=MATH_COLOR, size=30)
        svg_code = math_obj.svg()
        
        if inline:
            # --- 行内公式美化 ---
            # 1. 使用 vertical-align 修正基线，使其在中文正文中不显得"漂浮"
            # 2. 限制 max-height 防止超大符号撑破行高
            inline_style = (
                "display: inline-block; "
                "vertical-align: -0.2ex; "
                "margin: 0 0.2em; "
                "max-height: 1.2em; "
                "transition: transform 0.2s ease;"
            )
            return f'<span class="math-inline" style="{inline_style}">{svg_code}</span>'
        else:
            # --- 块级公式美化 ---
            # 1. 强制左对齐 (text-align: left)
            # 2. 添加半透明背景 (rgba) 和微弱边框 (border)
            # 3. 增加圆角 (border-radius) 和内部留白 (padding)
            container_style = "display: flow-root; margin: 40px 0; width: 100%; text-align: left;"
            block_style = (
                f"display: inline-block; "
                f"padding: 16px 28px; "
                f"background: rgba(88, 166, 255, 0.05); "
                f"border: 1px solid rgba(88, 166, 255, 0.15); "
                f"border-radius: 10px; "
                f"margin-left: 15px; "
                f"transition: all 0.3s ease; "
                f"cursor: default;"
            )
            
            # 使用 container 包裹以实现布局控制，内部 block 实现视觉美化
            return (
                f'<div class="math-block-container" style="{container_style}">'
                f'<div class="math-block" style="{block_style}">'
                f'{svg_code}'
                f'</div></div>'
            )
            
    except Exception as e:
        # 容错处理：渲染失败时返回原始 LaTeX 代码，并用醒目颜色标出
        print(f"公式渲染错误 [{latex_str}]: {e}")
        return f'<code style="color: #ffa657;">{latex_str}</code>'
    

def preprocess_math(text):
    """在解析 Markdown 前，处理 LaTeX 公式，避开代码块"""
    code_blocks = []
    def save_code(m):
        code_blocks.append(m.group(0))
        return f"__CODE_BLOCK_{len(code_blocks)-1}__"
    
    # 保护代码块
    text = re.sub(r'```.*?```', save_code, text, flags=re.DOTALL)
    text = re.sub(r'`.*?`', save_code, text)

    # 处理块级公式 $$ ... $$
    def replace_block(m):
        latex = m.group(1).strip()
        return render_latex_to_svg(latex, inline=False)
    text = re.sub(r'\$\$(.*?)\$\$', replace_block, text, flags=re.DOTALL)

    # 处理行内公式 $ ... $
    def replace_inline(m):
        latex = m.group(1).strip()
        return render_latex_to_svg(latex, inline=True)
    text = re.sub(r'\$(.*?)\$', replace_inline, text)

    # 还原代码块
    for i, code in enumerate(code_blocks):
        text = text.replace(f"__CODE_BLOCK_{i}__", code)
        
    return text


def clean_markdown_content(content):
    """
    清洗 Markdown 内容：
    1. 移除 YAML Front Matter
    2. v12.4 新增: 智能修复表格间距问题 (表格头前无空行导致无法识别)
    """
    # 1. 移除 Front Matter
    pattern = r'^---\s*\n.*?\n---\s*\n'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 2. 智能修复表格间距
    lines = content.split('\n')
    result = []
    in_code_block = False
    
    for line in lines:
        # 简单的代码块状态检测 (```)
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            
        # 检测是否为表格分隔线 (例如 |---|---| 或 ---|---)
        # 条件: 不在代码块内, 包含 | 和 -, 且符合分隔线特征
        is_table_sep = False
        if not in_code_block and '|' in line and '-' in line:
             # 正则: 允许开头空格，包含 管道符、冒号、连字符、空格，以管道符或内容结束
             if re.match(r'^\s*\|?[\s\-\:|]+\|[\s\-\:|]*$', line):
                 is_table_sep = True
        
        if is_table_sep:
            # 检查结果列表中的前两行
            # 结构: [..., Text, Header]  <-- 遇到 Separator (当前 line)
            # 我们需要变成: [..., Text, "", Header]
            if len(result) >= 2:
                prev_text_line = result[-2].strip()
                # 如果 Header 上一行不是空行 (且不是注释)
                if prev_text_line and not prev_text_line.startswith('<!--'):
                    # 弹出 Header
                    header = result.pop()
                    # 插入空行
                    result.append("")
                    # 放回 Header
                    result.append(header)
                    
        result.append(line)
        
    return "\n".join(result).strip()

def convert_md_to_html(md_content):
    extensions = [
        'fenced_code', 'tables', 'toc', 'sane_lists', 'nl2br', 'codehilite'
    ]
    extension_configs = {
        'codehilite': { 'use_pygments': True, 'noclasses': False, 'css_class': 'highlight' }
    }
    try:
        html_body = markdown.markdown(md_content, extensions=extensions, extension_configs=extension_configs)
    except ImportError:
        print("提示: 未安装 Pygments。请运行 'pip install Pygments'。")
        extensions.remove('codehilite')
        html_body = markdown.markdown(md_content, extensions=extensions)
        
    return html_body

def process_file(md_file_path):
    base_name = os.path.splitext(md_file_path)[0]
    
    with open(md_file_path, 'r', encoding='utf-8') as f:
        raw_md_content = f.read()

    cleaned_md = clean_markdown_content(raw_md_content)
    cleaned_md = preprocess_math(cleaned_md)
    
    # 提取代码块语言信息（codehilite会丢失语言类，需要后处理恢复）
    # 遍历所有 ``` 行，奇数序号(1,3,5...)为开始标记，偶数序号(2,4,6...)为结束标记
    code_langs = []
    in_code = False
    for line in cleaned_md.split('\n'):
        stripped = line.strip()
        if stripped.startswith('```'):
            if not in_code:
                # 这是开始标记，提取语言
                lang = stripped[3:].strip()
                code_langs.append(lang)
                in_code = True
            else:
                # 这是结束标记
                in_code = False
    
    html_body_content = convert_md_to_html(cleaned_md)

    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{os.path.basename(base_name)}</title>
    </head>
    <body>
        {html_body_content}
    </body>
    </html>
    """
    
    soup = BeautifulSoup(html_template, 'html.parser')

    # 恢复代码块语言类（codehilite会丢失此信息）
    highlight_divs = soup.find_all('div', class_='highlight')
    for idx, div in enumerate(highlight_divs):
        if idx < len(code_langs) and code_langs[idx]:
            code_tag = div.find('code')
            if code_tag:
                existing_classes = code_tag.get('class', [])
                if isinstance(existing_classes, str):
                    existing_classes = [existing_classes]
                existing_classes.append(f'language-{code_langs[idx]}')
                code_tag['class'] = existing_classes

    for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        theme_path = base_name + ext
        if os.path.exists(theme_path):
            b64 = get_base64_encoded_data(theme_path)
            if b64:
                mime = mimetypes.guess_type(theme_path)[0]
                container = soup.new_tag('div', **{'class': 'theme-photo-container'})
                img = soup.new_tag('img', src=f'data:{mime};base64,{b64}')
                container.append(img)
                soup.body.insert(0, container)
            break

    tags = soup.find_all(['h1', 'h2', 'h3'])
    sidebar_ul = soup.new_tag('ul', **{'class': 'sidebar-level'})
    has_sidebar = False
    anchor_counts = {}

    for tag in tags:
        has_sidebar = True
        level = int(tag.name[1])
        text = tag.get_text(strip=True)
        
        if not tag.get('id'):
            anchor = re.sub(r'[^a-zA-Z0-9_-]+', '-', text.lower()).strip('-') or "h"
            if anchor in anchor_counts:
                anchor_counts[anchor] += 1
                anchor = f"{anchor}-{anchor_counts[anchor]}"
            else:
                anchor_counts[anchor] = 0
            tag['id'] = anchor
        
        li = soup.new_tag('li', style=f"margin-left: {(level-1)*15}px;")
        a = soup.new_tag('a', href=f"#{tag['id']}")
        a.string = text
        li.append(a)
        sidebar_ul.append(li)

    if has_sidebar:
        sidebar = soup.new_tag('div', id='sidebar')
        sidebar.append(sidebar_ul)
        soup.body.insert(0, sidebar) 
        
        trigger = soup.new_tag('div', **{'class': 'sidebar-trigger'})
        trigger.string = SIDEBAR_TRIGGER_TEXT
        soup.body.append(trigger)

    # Pygments Highlighting (VS Code Dark+ Enhanced)
    # 更丰富的色彩：关键字区分控制流/声明/命名空间，字符串区分普通/文档/转义，
    # 数字区分整数/浮点，类型区分类/枚举/函数/装饰器，注释区分单行/多行/文档
    syntax_highlighting_css = """
    /* === 注释 === */
    .c  { color: #6a9955; font-style: italic; }           /* 单行注释 */
    .cm { color: #6a9955; font-style: italic; }           /* 多行注释 */
    .c1 { color: #6a9955; font-style: italic; }           /* 单行注释(备选) */
    .cs { color: #6a9955; font-style: italic; }           /* 注释特殊标记 */
    .cp { color: #569cd6; font-weight: bold; }            /* 预处理指令 #include/#define */
    .sd { color: #6a9955; font-style: italic; }           /* 文档字符串 */

    /* === 错误 === */
    .err { color: #f44747; background-color: rgba(244,71,71,0.1); }
    .gd { color: #f44747; background-color: rgba(244,71,71,0.15); }  /* 删除行 */
    .gr { color: #f44747; }                                           /* 运行时错误 */

    /* === 关键字 - 按语义区分颜色 === */
    .k  { color: #569cd6; }                                /* 控制流关键字: if/else/for/while/return */
    .kc { color: #569cd6; }                                /* 常量关键字: true/false/null */
    .kd { color: #c586c0; }                                /* 声明关键字: var/let/const/function/class */
    .kn { color: #c586c0; }                                /* 命名空间关键字: import/from/as */
    .kp { color: #569cd6; }                                /* 伪关键字 */
    .kr { color: #569cd6; }                                /* 保留关键字 */
    .kt { color: #4ec9b0; }                                /* 类型关键字: int/string/void/bool */
    .ow { color: #569cd6; font-weight: bold; }             /* 运算符关键字: in/is/and/or/not */

    /* === 运算符 === */
    .o { color: #d4d4d4; }                                 /* 算术/逻辑运算符 */

    /* === 字符串 - 按语义区分颜色 === */
    .s  { color: #ce9178; }                                /* 双引号字符串 */
    .s1 { color: #ce9178; }                                /* 单引号字符串 */
    .s2 { color: #ce9178; }                                /* 双引号字符串(备选) */
    .sb { color: #ce9178; }                                /* 反引号字符串 */
    .sc { color: #ce9178; }                                /* 字符 */
    .sh { color: #ce9178; }                                /* heredoc字符串 */
    .si { color: #ce9178; }                                /* 插值字符串 */
    .sx { color: #ce9178; }                                /* 其他字符串 */
    .se { color: #d7ba7d; }                                /* 转义字符 \n \t */
    .sr { color: #d16969; }                                /* 正则表达式 */
    .ss { color: #ce9178; }                                /* 字符串特殊符号 */

    /* === 数字 === */
    .m  { color: #b5cea8; }                                /* 数值 */
    .mf { color: #b5cea8; }                                /* 浮点数 */
    .mh { color: #b5cea8; }                                /* 十六进制 */
    .mi { color: #b5cea8; }                                /* 整数 */
    .mo { color: #b5cea8; }                                /* 八进制 */
    .il { color: #b5cea8; }                                /* 长整数 */

    /* === 名称 - 最丰富的颜色区分 === */
    .na { color: #9cdcfe; }                                /* HTML/XML 属性名 */
    .nb { color: #4ec9b0; }                                /* 内置名称: self/None/True/False */
    .nc { color: #4ec9b0; font-weight: bold; }             /* 类名 */
    .nd { color: #dcdcaa; font-weight: bold; }             /* 装饰器 @xxx */
    .ne { color: #f44747; font-weight: bold; }             /* 异常类名 */
    .nf { color: #dcdcaa; }                                /* 函数/方法名 */
    .ni { color: #4ec9b0; }                                /* 枚举成员名 */
    .nl { color: #9cdcfe; font-weight: bold; }             /* 标签名 */
    .nn { color: #4ec9b0; }                                /* 命名空间名 */
    .no { color: #4ec9b0; font-weight: bold; }             /* 常量名 */
    .nt { color: #569cd6; }                                /* HTML/XML 标签名 */
    .nv { color: #9cdcfe; }                                /* 变量名 */
    .bp { color: #4ec9b0; }                                /* 内置伪名称 */

    /* === 其他 === */
    .gh { color: #9cdcfe; font-weight: bold; }             /* 标题 */
    .gi { color: #6a9955; background-color: rgba(106,153,85,0.15); }  /* 新增行 */
    .go { color: #6a9955; }                                /* 输出 */
    .gp { color: #6a9955; font-weight: bold; }             /* 提示符 >>> */
    .gs { font-weight: bold; }                             /* 强调 */
    .gu { color: #9cdcfe; font-weight: bold; }             /* 子标题 */
    .gt { color: #f44747; }                                /* 跟踪 */
    .ge { font-style: italic; }                            /* 斜体 */
    .vc { color: #9cdcfe; }                                /* 类变量名 */
    .vg { color: #9cdcfe; }                                /* 全局变量名 */
    .vi { color: #9cdcfe; }                                /* 实例变量名 */
    .w  { color: #d4d4d4; }                                /* 空白 */
    """

    CODE_THEMES = {
        "dark": f"""
        pre {{
            background: #161b22 !important;
            padding: 16px !important;
            border-radius: 8px !important;
            overflow-x: auto;
            overflow-y: hidden;
            position: relative;
            border: 1px solid #30363d;
            line-height: {CODE_BLOCK_LINE_HEIGHT} !important;
        }}
        code {{
            font-family: 'Consolas', 'Courier New', monospace !important;
            font-size: {CODE_BLOCK_FONT_SIZE} !important;
            line-height: {CODE_BLOCK_LINE_HEIGHT} !important; 
        }}
        pre code {{
            color: #e6edf3;
            background: transparent !important;
            padding: 0 !important;
        }}
        :not(pre) > code {{
            background: rgba(110, 118, 129, 0.4) !important;
            color: #e6edf3 !important;
            padding: 0.2em 0.4em !important;
            border-radius: 6px !important;
            font-size: {INLINE_CODE_FONT_SIZE} !important;
        }}
        .highlight, .codehilite {{ background: transparent !important; margin: 0 !important; padding: 0 !important; }}
        """ + syntax_highlighting_css
    }
    
    LAYOUT_CSS = f"""
    html {{ font-size: {BODY_FONT_SIZE}; }}
    
    #sidebar {{
        position: fixed; top: 0; bottom: 0; left: -{SIDEBAR_WIDTH}px; width: {SIDEBAR_WIDTH}px;
        background: #161b22; color: #c9d1d9; padding: 20px; overflow-y: auto;
        transition: left 0.3s cubic-bezier(0.25, 0.8, 0.25, 1); /* 更平滑的动画 */
        z-index: 9999; box-shadow: 5px 0 15px rgba(0,0,0,0.5);
        font-size: 15px; border-right: 1px solid #30363d;
        box-sizing: border-box; 
    }}
    #sidebar::-webkit-scrollbar {{ width: 6px; }}
    #sidebar::-webkit-scrollbar-track {{ background: #0d1117; }}
    #sidebar::-webkit-scrollbar-thumb {{ background: #30363d; border-radius: 3px; }}
    #sidebar::-webkit-scrollbar-thumb:hover {{ background: #58a6ff; }}
    
    #sidebar ul {{ list-style: none; padding: 0; margin: 0; }}
    #sidebar li {{ padding: 6px 0; }}
    #sidebar a {{ color: #c9d1d9; text-decoration: none; display: block; transition: color 0.2s; }}
    #sidebar a:hover {{ color: #58a6ff; text-decoration: underline; }}
    
    /* 侧边栏标签样式 */
    .sidebar-trigger {{
        position: fixed; 
        left: 0; 
        top: 50%; 
        transform: translateY(-50%);
        width: 24px; 
        padding: 15px 2px;
        background: rgba(22, 27, 34, 0.8); /* 半透明深色背景 */
        color: #c9d1d9;
        font-size: 14px;
        font-weight: bold;
        text-align: center;
        line-height: 1.2;
        border-top-right-radius: 8px;
        border-bottom-right-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        cursor: pointer;
        z-index: 10000;
        transition: background 0.2s, opacity 0.3s;
        writing-mode: vertical-lr; /* 竖排文字 */
        letter-spacing: 2px;
    }}
    .sidebar-trigger:hover {{
        background: #58a6ff;
        color: #fff;
    }}
    
    .theme-photo-container {{
        width: 100%; max-height: {THEME_PHOTO_MAX_HEIGHT_PX}px;
        overflow: hidden; margin-bottom: 40px; border-radius: 8px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    }}
    .theme-photo-container img {{
        width: 100%; height: 100%; object-fit: cover;
        object-position: {THEME_PHOTO_OBJECT_POSITION};
    }}
    
    a[download] {{
        display: inline-block; padding: 10px 20px; background: #238636;
        color: #fff !important; border-radius: 6px; text-decoration: none !important;
        font-weight: bold; font-size: 0.9em; margin: 10px 0; border: 1px solid rgba(240,246,252,0.1);
    }}
    a[download]:hover {{ background: #2ea043; }}

    /* 附件卡片悬停效果 */
    a[data-unpack-id]:hover {{
        border-color: #58a6ff !important;
        box-shadow: 0 4px 16px rgba(56, 139, 253, 0.2);
        transform: translateY(-1px);
    }}

    /* v12.15: 公式块 hover 效果（替代 onmouseover/onmouseout 内联事件，CSP 兼容） */
    .math-block {{
        transition: background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
    }}
    .math-block:hover {{
        background: rgba(88, 166, 255, 0.1) !important;
        border-color: rgba(88, 166, 255, 0.4) !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
    }}

    .copy-code-btn {{
        position: absolute; top: 8px; right: 8px;
        background: rgba(177, 186, 196, 0.15); color: #c9d1d9;
        border: 1px solid rgba(240, 246, 252, 0.1); border-radius: 6px;
        font-size: 12px; padding: 4px 10px; cursor: pointer;
        opacity: 0; transition: all 0.2s; z-index: 2;
    }}
    pre:hover .copy-code-btn {{ opacity: 1; }}
    .copy-code-btn:hover {{ background: rgba(177, 186, 196, 0.3); color: #fff; }}
    .copy-code-btn.copied {{ background: #238636; color: #fff; border-color: #238636; }}

    /* 代码语言标签 */
    .code-lang-label {{
        position: absolute; top: 0; right: 0;
        background: rgba(56, 139, 253, 0.15); color: #79c0ff;
        border-bottom-left-radius: 6px; border-top-right-radius: 7px;
        font-size: 11px; padding: 2px 10px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        letter-spacing: 0.5px; text-transform: uppercase; font-weight: 600;
        pointer-events: none; z-index: 1;
    }}
    @keyframes spin {{
        to {{ transform: rotate(360deg); }}
    }}
    """

    # v12.17: 计算样式哈希用于 style-src-elem CSP 绑定
    style_content = BASE_CSS + LAYOUT_CSS + CODE_THEMES.get("dark", "")
    style_hash = hashlib.sha256(style_content.encode('utf-8')).digest()
    style_hash_b64 = base64.b64encode(style_hash).decode('utf-8')
    style_tag = soup.new_tag('style')
    style_tag.string = style_content
    soup.head.append(style_tag)

    # 8. 注入 JS (交互逻辑优化)
    js_code = f"""
    // v12.16: CSP 违规可视化 - 收集并显示安全策略违规信息
    var __cspViolations = [];
    document.addEventListener('securitypolicyviolation', function(e) {{
        __cspViolations.push({{
            violatedDirective: e.violatedDirective || 'unknown',
            blockedURI: e.blockedURI || '(inline)',
            documentURI: e.documentURI || '',
            lineNumber: e.lineNumber || '-',
            columnNumber: e.columnNumber || '-',
            sourceFile: e.sourceFile || '(inline)',
            originalPolicy: e.originalPolicy ? e.originalPolicy.substring(0, 80) + '...' : '',
            timestamp: new Date().toLocaleTimeString()
        }});
        __cspShowViolations();
    }});

    function __cspShowViolations() {{
        var existing = document.getElementById('__csp-violation-panel');
        if (existing) existing.remove();

        var count = __cspViolations.length;
        var banner = document.createElement('div');
        banner.id = '__csp-violation-panel';
        banner.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:999999;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;';

        // 顶部警示横幅
        var bar = document.createElement('div');
        bar.style.cssText = 'background:linear-gradient(135deg,#da3633 0%,#b62324 100%);color:#fff;padding:14px 20px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 4px 20px rgba(218,54,51,0.4);';
        var left = document.createElement('div');
        left.style.cssText = 'display:flex;align-items:center;gap:12px;';
        var icon = document.createElement('span');
        icon.style.cssText = 'font-size:28px;';
        icon.textContent = '\\u26A0\\uFE0F';
        var title = document.createElement('span');
        title.style.cssText = 'font-size:16px;font-weight:700;';
        title.textContent = 'CSP \\u5B89\\u5168\\u8B66\\u544A: \\u68C0\\u6D4B\\u5230 ' + count + ' \\u6B21\\u8FDD\\u89C4 (\\u5DF2\\u62E6\\u622A)';
        left.appendChild(icon);
        left.appendChild(title);

        var closeBtn = document.createElement('button');
        closeBtn.style.cssText = 'background:rgba(255,255,255,0.2);color:#fff;border:none;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:13px;font-weight:600;';
        closeBtn.textContent = '\\u5173\\u95ED';
        closeBtn.onclick = function() {{ banner.remove(); }};

        bar.appendChild(left);
        bar.appendChild(closeBtn);
        banner.appendChild(bar);

        // 详情面板
        var details = document.createElement('div');
        details.style.cssText = 'background:#0d1117;border:2px solid #da3633;border-top:none;max-height:50vh;overflow-y:auto;padding:16px 20px;';
        details.onclick = function(e) {{ e.stopPropagation(); }};

        // v12.17: 使用 DOM API 构建表格，消除 innerHTML 注入风险
        var table = document.createElement('table');
        table.style.cssText = 'width:100%;border-collapse:collapse;font-size:13px;color:#c9d1d9;';

        var thead = document.createElement('thead');
        var headerRow = document.createElement('tr');
        headerRow.style.background = '#161b22';
        var headerCells = [
            {{text: '#', css: 'padding:8px 12px;text-align:left;border-bottom:2px solid #da3633;color:#f85149;font-weight:700;'}},
            {{text: '\\u8FDD\\u89C4\\u6307\\u4EE4', css: 'padding:8px 12px;text-align:left;border-bottom:2px solid #da3633;color:#f85149;font-weight:700;'}},
            {{text: '\\u88AB\\u62E6\\u622A URI', css: 'padding:8px 12px;text-align:left;border-bottom:2px solid #da3633;color:#f85149;font-weight:700;'}},
            {{text: '\\u4F4D\\u7F6E', css: 'padding:8px 12px;text-align:left;border-bottom:2px solid #da3633;color:#f85149;font-weight:700;'}},
            {{text: '\\u65F6\\u95F4', css: 'padding:8px 12px;text-align:left;border-bottom:2px solid #da3633;color:#f85149;font-weight:700;'}}
        ];
        for (var hi = 0; hi < headerCells.length; hi++) {{
            var th = document.createElement('th');
            th.style.cssText = headerCells[hi].css;
            th.textContent = headerCells[hi].text;
            headerRow.appendChild(th);
        }}
        thead.appendChild(headerRow);
        table.appendChild(thead);

        var tbody = document.createElement('tbody');
        for (var i = 0; i < __cspViolations.length; i++) {{
            var v = __cspViolations[i];
            var rowBg = i % 2 === 0 ? '#0d1117' : '#161b22';
            var loc = (v.sourceFile !== '(inline)' ? v.sourceFile : '') + (v.lineNumber !== '-' ? ':' + v.lineNumber : '');
            if (!loc) loc = '(inline)';

            var tr = document.createElement('tr');
            tr.style.background = rowBg;

            // # 列
            var td1 = document.createElement('td');
            td1.style.cssText = 'padding:6px 12px;border-bottom:1px solid #21262d;color:#8b949e;';
            td1.textContent = '' + (i + 1);
            tr.appendChild(td1);

            // 违规指令列
            var td2 = document.createElement('td');
            td2.style.cssText = 'padding:6px 12px;border-bottom:1px solid #21262d;';
            var code2 = document.createElement('code');
            code2.style.cssText = 'background:rgba(218,54,51,0.15);color:#f85149;padding:2px 6px;border-radius:4px;font-size:12px;';
            code2.textContent = v.violatedDirective;
            td2.appendChild(code2);
            tr.appendChild(td2);

            // 被拦截 URI 列
            var td3 = document.createElement('td');
            td3.style.cssText = 'padding:6px 12px;border-bottom:1px solid #21262d;word-break:break-all;max-width:300px;';
            td3.textContent = v.blockedURI;
            tr.appendChild(td3);

            // 位置列
            var td4 = document.createElement('td');
            td4.style.cssText = 'padding:6px 12px;border-bottom:1px solid #21262d;color:#8b949e;font-size:12px;';
            td4.textContent = loc;
            tr.appendChild(td4);

            // 时间列
            var td5 = document.createElement('td');
            td5.style.cssText = 'padding:6px 12px;border-bottom:1px solid #21262d;color:#8b949e;font-size:12px;white-space:nowrap;';
            td5.textContent = v.timestamp;
            tr.appendChild(td5);

            tbody.appendChild(tr);
        }}
        table.appendChild(tbody);
        details.appendChild(table);

        // 底部说明
        var note = document.createElement('div');
        note.style.cssText = 'margin-top:12px;padding:10px 14px;background:rgba(218,54,51,0.08);border:1px solid rgba(218,54,51,0.2);border-radius:8px;color:#8b949e;font-size:12px;';
        note.textContent = '\\u2714 \\u4EE5\\u4E0A\\u8FDD\\u89C4\\u5747\\u5DF2\\u88AB\\u6D4F\\u89C8\\u5668 CSP \\u6210\\u529F\\u62E6\\u622A\\uFF0C\\u4E0D\\u4F1A\\u6267\\u884C\\u3002\\u5982\\u679C\\u60A8\\u672A\\u6CE8\\u5165\\u4EFB\\u4F55\\u653B\\u51FB\\u4EE3\\u7801\\uFF0C\\u8BF4\\u660E\\u6587\\u4EF6\\u5728\\u4F20\\u8F93\\u8FC7\\u7A0B\\u4E2D\\u88AB\\u7BE1\\u6539\\uFF0C\\u8BF7\\u4E0D\\u8981\\u76F8\\u4FE1\\u8BE5\\u6587\\u4EF6\\u3002';
        details.appendChild(note);

        banner.appendChild(details);
        document.body.prepend(banner);

        // 滚动到顶部显示警告
        window.scrollTo(0, 0);
    }}

    document.addEventListener('DOMContentLoaded', function() {{
        // --- 侧边栏逻辑 ---
        var sidebar = document.getElementById('sidebar');
        var trigger = document.querySelector('.sidebar-trigger');
        
        if(sidebar && trigger) {{
            trigger.addEventListener('mouseenter', function() {{ 
                sidebar.style.left = '0px'; 
                trigger.style.opacity = '0'; 
            }});
            
            sidebar.addEventListener('mouseleave', function() {{ 
                sidebar.style.left = '-{SIDEBAR_WIDTH}px'; 
                trigger.style.opacity = '1'; 
            }});
        }}

        // --- 代码复制按钮逻辑 ---
        document.querySelectorAll('pre').forEach(function(pre) {{
            var btn = document.createElement('button');
            btn.className = 'copy-code-btn';
            btn.textContent = 'Copy';
            pre.appendChild(btn);
            
            btn.addEventListener('click', function() {{
                var code = pre.querySelector('code');
                var text = code ? code.innerText : pre.innerText;
                text = text.replace(/Copy$/, '');
                
                var area = document.createElement('textarea');
                area.value = text;
                document.body.appendChild(area);
                area.select();
                document.execCommand('copy');
                document.body.removeChild(area);
                
                btn.textContent = 'Copied!';
                btn.classList.add('copied');
                setTimeout(function() {{
                    btn.textContent = 'Copy';
                    btn.classList.remove('copied');
                }}, 2000);
            }});

            // --- 代码语言标签 ---
            var code = pre.querySelector('code');
            if (code) {{
                var classes = code.className || '';
                var langMatch = classes.match(/language-(\\w+)/);
                if (langMatch && langMatch[1]) {{
                    var lang = langMatch[1].toLowerCase();
                    var label = document.createElement('span');
                    label.className = 'code-lang-label';
                    label.textContent = lang;
                    pre.appendChild(label);
                }}
            }}
        }});

        // v12.15: 附件下载事件委托（CSP 安全: 替代 inline onclick）
        document.querySelectorAll('a[data-unpack-id]').forEach(function(a) {{
            a.addEventListener('click', function(e) {{
                e.preventDefault();
                unpackAndDownload(this.getAttribute('data-unpack-id'), this.getAttribute('data-filename'));
            }});
        }});
    }});

    // --- 新增：附件解压与下载逻辑 (点击即显示进度，异步分块处理) ---
    async function unpackAndDownload(dataId, fileName) {{
        // 立即创建进度浮层（在任何耗时操作之前）
        var overlay = document.createElement('div');
        overlay.id = 'unpack-overlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);z-index:99999;display:flex;align-items:center;justify-content:center;';

        var card = document.createElement('div');
        card.style.cssText = 'background:#161b22;border:1px solid #30363d;border-radius:12px;padding:28px 36px;min-width:320px;max-width:480px;box-shadow:0 8px 32px rgba(0,0,0,0.5);text-align:center;';

        var titleEl = document.createElement('div');
        titleEl.style.cssText = 'color:#e6edf3;font-size:16px;font-weight:600;margin-bottom:16px;';
        titleEl.textContent = '📎 正在准备下载文件';

        var fileNameEl = document.createElement('div');
        fileNameEl.style.cssText = 'color:#8b949e;font-size:13px;margin-bottom:20px;word-break:break-all;';
        fileNameEl.textContent = fileName;

        var progressBar = document.createElement('div');
        progressBar.style.cssText = 'width:100%;height:6px;background:#30363d;border-radius:3px;overflow:hidden;margin-bottom:12px;';

        var progressFill = document.createElement('div');
        progressFill.style.cssText = 'width:0%;height:100%;background:linear-gradient(90deg,#388bfd,#58a6ff);border-radius:3px;transition:width 0.3s ease;';
        progressBar.appendChild(progressFill);

        var statusEl = document.createElement('div');
        statusEl.style.cssText = 'color:#8b949e;font-size:12px;';
        statusEl.textContent = '正在初始化...';

        // 旋转动画指示器
        var spinner = document.createElement('div');
        spinner.style.cssText = 'display:inline-block;width:14px;height:14px;border:2px solid #30363d;border-top-color:#58a6ff;border-radius:50%;animation:spin 0.8s linear infinite;vertical-align:middle;margin-right:6px;';

        card.appendChild(titleEl);
        card.appendChild(fileNameEl);
        card.appendChild(progressBar);
        card.appendChild(statusEl);
        overlay.appendChild(card);
        document.body.appendChild(overlay);

        async function updateProgress(percent, statusText) {{
            progressFill.style.width = percent + '%';
            if (statusText) {{
            statusEl.textContent = '';
            var sp = spinner.cloneNode(true);
            statusEl.appendChild(sp);
            statusEl.appendChild(document.createTextNode(statusText));
            }}
            // 让 UI 有时间刷新
            await new Promise(function(r) {{ setTimeout(r, 20); }});
        }}

        try {{
            // 等待浮层渲染完成
            await new Promise(function(r) {{ requestAnimationFrame(function() {{ requestAnimationFrame(r); }}); }});

            // 从隐藏 span 中获取数据
            var dataEl = document.getElementById(dataId);
            if (!dataEl) throw new Error('找不到附件数据');
            var base64 = dataEl.textContent;
            var mimeType = dataEl.getAttribute('data-mime') || 'application/octet-stream';

            await updateProgress(2, '正在解码 Base64 数据...');

            // 分块 Base64 解码（避免 atob 大字符串阻塞主线程）
            var totalLen = base64.length;
            var DECODE_CHUNK = 32768; // 每次解码的字符数（必须是4的倍数）
            var binaryParts = [];
            for (var offset = 0; offset < totalLen; offset += DECODE_CHUNK) {{
                var chunk = base64.substring(offset, Math.min(offset + DECODE_CHUNK, totalLen));
                binaryParts.push(atob(chunk));
                if (offset % (DECODE_CHUNK * 8) === 0) {{
                    var pct = 2 + Math.floor((offset / totalLen) * 20);
                    await updateProgress(pct, '正在解码 Base64... ' + pct + '%');
                }}
            }}
            // 合并解码后的字符串
            var binaryString = binaryParts.join('');
            await updateProgress(23, 'Base64 解码完成，正在转换二进制...');

            var bytes = new Uint8Array(binaryString.length);
            var chunkSize = 65536;
            for (var i = 0; i < binaryString.length; i += chunkSize) {{
                var end = Math.min(i + chunkSize, binaryString.length);
                for (var j = i; j < end; j++) {{
                    bytes[j] = binaryString.charCodeAt(j);
                }}
                var pct = 23 + Math.floor((i / binaryString.length) * 20);
                await updateProgress(pct, '正在转换二进制数据... ' + pct + '%');
            }}

            // 步骤2: 解压缩
            await updateProgress(45, '正在解压缩数据...');
            var stream = new ReadableStream({{
                start(controller) {{
                    controller.enqueue(bytes);
                    controller.close();
                }}
            }}).pipeThrough(new DecompressionStream('deflate'));

            // 步骤3: 收集解压后的数据 (带进度)
            var reader = stream.getReader();
            var chunks = [];
            var totalReceived = 0;
            while (true) {{
                var result = await reader.read();
                if (result.done) break;
                chunks.push(result.value);
                totalReceived += result.value.length;
                var pct = 45 + Math.min(Math.floor((totalReceived / (totalLen * 2)) * 45), 45);
                await updateProgress(pct, '正在解压缩... ' + pct + '%');
            }}

            await updateProgress(92, '正在合并数据...');

            // 合并 chunks
            var blob = new Blob(chunks, {{ type: mimeType }});
            await updateProgress(96, '正在生成下载链接...');

            var url = URL.createObjectURL(blob);
            var link = document.createElement('a');
            link.href = url;
            link.download = fileName;
            document.body.appendChild(link);

            await updateProgress(100, '下载已开始！');

            // 短暂展示完成状态
            await new Promise(function(r) {{ setTimeout(r, 600); }});

            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

        }} catch (err) {{
            console.error('解压失败:', err);
            statusEl.textContent = '❌ 解压失败: ' + err.message;
            statusEl.style.color = '#f85149';
            progressFill.style.background = '#f85149';
            await new Promise(function(r) {{ setTimeout(r, 3000); }});
        }} finally {{
            document.body.removeChild(overlay);
        }}
    }}
    """
    script_tag = soup.new_tag('script')
    script_tag.string = js_code
    soup.body.append(script_tag)

    # v12.15/v12.17: CSP 安全策略 - 计算所有内联脚本的 SHA256 哈希

    # v12.15/v12.17: CSP 安全策略 - 计算所有内联脚本的 SHA256 哈希
    # 收集 body 中所有 inline script（不含空/外部脚本）的哈希
    all_script_hashes = []
    for sc in soup.body.find_all('script', src=None):
        sc_text = sc.string or ''
        if sc_text.strip():
            h = hashlib.sha256(sc_text.encode('utf-8')).digest()
            all_script_hashes.append(base64.b64encode(h).decode('utf-8'))

    script_src_part = ' '.join(f"'sha256-{h}'" for h in all_script_hashes)
    csp_value = (
        f"default-src 'none'; "
        f"script-src {script_src_part}; "
        f"style-src-elem 'sha256-{style_hash_b64}'; "
        f"style-src-attr 'unsafe-inline'; "
        f"img-src data:; "
        f"media-src data:; "
        f"font-src data:; "
        f"connect-src 'none'; "
        f"frame-src 'none'; "
        f"object-src 'none'; "
        f"base-uri 'none'; "
        f"form-action 'none'; "
        f"require-trusted-types-for 'script'"
    )
    csp_meta = soup.new_tag('meta')
    csp_meta['http-equiv'] = 'Content-Security-Policy'
    csp_meta['content'] = csp_value
    soup.head.append(csp_meta)

    # v12.17: 提示生产环境应通过 HTTP 响应头部署 CSP
    csp_note = Comment(
        ' 注意: 当前 CSP 通过 <meta> 标签设置。'
        '部分指令（如 frame-ancestors、sandbox、report-uri、report-to）不被 <meta> 支持。'
        '生产环境部署建议通过 HTTP 响应头设置完整的 CSP 。'
    )
    soup.head.append(csp_note)

    return soup

def main():
    mimetypes.init()
    md_files = [f for f in os.listdir('.') if f.endswith('.md')]
    
    if not md_files:
        print("未找到 .md 文件。")
        return

    print(f"v12.18 启动: Markdown 直出 HTML [在线资源离线嵌入版 + CSP 安全防护增强 + 违规可视化] (共找到 {len(md_files)} 个 MD 文件, OFFLINE_MODE={'ON' if OFFLINE_MODE else 'OFF'})\n")
    try:
        import pygments
    except ImportError:
        print("!!! 警告: 未检测到 Pygments 库。如需代码高亮，请运行 'pip install Pygments'。\n")

    for md_file in md_files:
        print(f"正在处理: {md_file} ...")
        try:
            soup = process_file(md_file)
            soup = replace_with_base64(soup)
            soup = wrap_tables(soup)
            output_file = md_file.replace('.md', '.release.html')

            # 添加完整性校验 JS（动态计算 body.outerHTML 的 SHA256）
            integrity_js = '''
(function(){
    var H=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19],b=new TextEncoder().encode(document.body.outerHTML),l=b.length,bl=l*8,off=0,W=Array(64),blks=[],K=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
    function R(a,b){return a>>>b|a<<32-b}
    function S(a,b){return a>>>b}
    function Ch(x,y,z){return(x&y)^(~x&z)}
    function Mj(x,y,z){return(x&y)^(x&z)^(y&z)}
    function Z0(x){return R(x,2)^R(x,13)^R(x,22)}
    function Z1(x){return R(x,6)^R(x,11)^R(x,25)}
    function z0(x){return R(x,7)^R(x,18)^S(x,3)}
    function z1(x){return R(x,17)^R(x,19)^S(x,10)}
    while(off+64<=l){blks.push(b.subarray(off,off+64));off+=64}
    var la=b.subarray(off),pa=[128];
    while((la.length+pa.length)%64!=56)pa.push(0);
    for(var i=7;i>=0;i--)pa.push((bl>>>(i*8))&255);
    var fb=new Uint8Array(la.length+pa.length);
    fb.set(la);fb.set(pa,la.length);blks.push(fb);
    if(fb.length>64)blks.push(fb.subarray(64));
    for(var q=0;q<blks.length;q++){
        for(var t=0;t<16;t++)W[t]=blks[q][t*4]<<24|blks[q][t*4+1]<<16|blks[q][t*4+2]<<8|blks[q][t*4+3];
        for(var t=16;t<64;t++)W[t]=(z1(W[t-2])+W[t-7]+z0(W[t-15])+W[t-16])|0;
        var a=H[0],b=H[1],c=H[2],d=H[3],e=H[4],f=H[5],g=H[6],h=H[7];
        for(var t=0;t<64;t++){
            var T1=(h+Z1(e)+Ch(e,f,g)+K[t]+W[t])|0,T2=(Z0(a)+Mj(a,b,c))|0;
            h=g;g=f;f=e;e=(d+T1)|0;d=c;c=b;b=a;a=(T1+T2)|0;
        }
        H[0]=(H[0]+a)|0;H[1]=(H[1]+b)|0;H[2]=(H[2]+c)|0;H[3]=(H[3]+d)|0;
        H[4]=(H[4]+e)|0;H[5]=(H[5]+f)|0;H[6]=(H[6]+g)|0;H[7]=(H[7]+h)|0;
    }
    var hx='';
    for(var i=0;i<8;i++)for(var j=7;j>=0;j--)hx+=((H[i]>>>(j*4))&15).toString(16);
    var d=document.createElement('div');
    d.id='__integrity-hash';
    d.style.cssText='margin-top:60px;padding:14px 20px;background:#0d1117;border-top:1px solid #30363d;color:#8b949e;font-size:12px;font-family:Consolas,monospace;text-align:center;word-break:break-all;line-height:1.6;';
    d.textContent='File Integrity SHA-256: '+hx;
    document.body.appendChild(d);
})();
'''
            integrity_tag = soup.new_tag('script')
            integrity_tag.string = integrity_js
            soup.body.append(integrity_tag)

            # 将完整性 JS 的哈希追加到 CSP script-src
            integrity_hash_b64 = base64.b64encode(
                hashlib.sha256(integrity_js.encode('utf-8')).digest()
            ).decode('utf-8')
            csp_meta = soup.find('meta', attrs={'http-equiv': 'Content-Security-Policy'})
            if csp_meta:
                old_csp = csp_meta['content']
                new_csp = old_csp.replace(
                    "script-src ", f"script-src 'sha256-{integrity_hash_b64}' "
                )
                csp_meta['content'] = new_csp

            # 写文件
            final_html = soup.encode(formatter='html5').decode('utf-8')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(final_html)

            print(f"[OK] 成功生成: {output_file}")

            # v12.17+: 使用 Playwright 无头浏览器加载 HTML，提取浏览器端完整性校验结果
            try:
                from playwright.sync_api import sync_playwright
                abs_path = os.path.abspath(output_file)
                file_url = 'file:///' + abs_path.replace('\\', '/')
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True, channel='chrome')
                    page = browser.new_page()
                    page.goto(file_url, wait_until='networkidle')
                    # 等待完整性校验 JS 执行完成
                    page.wait_for_selector('#__integrity-hash', timeout=15000)
                    integrity_text = page.text_content('#__integrity-hash')
                    print(f"[BROWSER] {integrity_text}")
                    browser.close()
            except Exception as e:
                print(f"[BROWSER] Playwright 加载 HTML 失败: {e}")

            print()
        except Exception as e:
            print(f"[ERROR] 处理 {md_file} 时出错: {e}\n")

    print("全部完成！")

if __name__ == "__main__":
    main()
