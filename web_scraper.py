"""
通用网页文档爬取工具
功能：输入任意 URL，自动提取页面正文 + 扫描链接，批量爬取并打包为 Markdown ZIP
运行：pip install flask requests html2text beautifulsoup4 && python web_scraper.py
"""

import re
import os
import sys
import json
import time
import uuid
import shutil
import zipfile
import threading
import webbrowser
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse

import html2text
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, Response, jsonify, send_file

# ============================================================
#  全局配置
# ============================================================
app = Flask(__name__)

BASE_DIR = Path(__file__).parent
OUTPUT_ROOT = BASE_DIR / "web_output"
OUTPUT_ROOT.mkdir(exist_ok=True)

# 任务状态存储（内存）
TASKS = {}  # task_id -> { status, total, done, failed, logs, zip_path, ... }


# ============================================================
#  工具函数
# ============================================================

def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    name = name.strip('. ')
    return name[:100] or "untitled"


def html_to_markdown(html: str) -> str:
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.body_width = 0
    h.unicode_snob = True
    h.protect_links = True
    h.wrap_links = False
    h.single_line_break = False
    return h.handle(html)


def build_headers(token: str = "", extra_cookies: str = "") -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    cookie_parts = []
    if token:
        cookie_parts.append(f"zsxq_access_token={token}")
    if extra_cookies:
        cookie_parts.append(extra_cookies)
    if cookie_parts:
        headers["Cookie"] = "; ".join(cookie_parts)
    return headers


def fetch_page(url: str, headers: dict, timeout: int = 30) -> str:
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


# ============================================================
#  智能正文提取
# ============================================================

def extract_content(html: str) -> str:
    """智能提取页面正文，支持 Quill / article / 通用 div / WordPress"""

    # 预处理：移除脚本和样式
    html_clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html_clean = re.sub(r'<style[^>]*>.*?</style>', '', html_clean, flags=re.DOTALL | re.IGNORECASE)
    # 移除知识星球代码块控制器
    html_clean = re.sub(
        r'<div[^>]*class="[^"]*code-block-control[^"]*"[^>]*>.*?</div>',
        '', html_clean, flags=re.DOTALL
    )
    # 移除水印
    html_clean = re.sub(r'扫码加入星球.*?查看更多优质内容', '', html_clean, flags=re.DOTALL)

    # 策略 1：Quill 编辑器（知识星球）
    match = re.search(
        r'<div[^>]*class="content ql-editor"[^>]*>(.*?)</div>\s*(?:</div>){2,}',
        html_clean, re.DOTALL
    )
    if not match:
        match = re.search(
            r'class="[^"]*ql-editor[^"]*"[^>]*>(.*?)(?=<div[^>]*class="[^"]*(?:toolbar|sidebar|footer|comment))',
            html_clean, re.DOTALL
        )
    if not match:
        match = re.search(
            r'class="content ql-editor"[^>]*>(.*?)知识星球',
            html_clean, re.DOTALL
        )
    if match and len(match.group(1).strip()) > 50:
        return html_to_markdown(match.group(1))

    # 策略 2：HTML 解析 — article / main / [role="main"]
    soup = BeautifulSoup(html_clean, "html.parser")
    content_node = (
        soup.find("article")
        or soup.find("main")
        or soup.find(attrs={"role": "main"})
        or soup.find("div", class_=re.compile(r"(post|entry|article|content|blog)", re.I))
    )
    if content_node and len(content_node.get_text(strip=True)) > 100:
        return html_to_markdown(str(content_node))

    # 策略 3：body 兜底
    body = soup.find("body")
    if body:
        # 去掉导航、页脚
        for tag in body.find_all(["nav", "footer", "header", "aside"]):
            tag.decompose()
        return html_to_markdown(str(body))

    return html_to_markdown(html)


def extract_title(html: str) -> str:
    """提取页面标题"""
    soup = BeautifulSoup(html, "html.parser")
    # h1 优先
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)[:120]
    # title 标签
    if soup.title and soup.title.string:
        return soup.title.string.strip()[:120]
    return "untitled"


def extract_links(html: str, base_url: str) -> list[dict]:
    """提取页面中所有有意义的链接"""
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc
    seen = set()
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        full_url = urljoin(base_url, href)
        if full_url in seen:
            continue
        seen.add(full_url)

        parsed = urlparse(full_url)
        # 过滤非文档链接
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in (
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
            ".mp4", ".mp3", ".wav", ".avi", ".mov",
            ".zip", ".rar", ".7z", ".tar", ".gz",
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".css", ".js", ".woff", ".woff2", ".ttf", ".eot",
        )):
            continue

        text = a.get_text(strip=True)[:100] or href[:80]

        # 判断是否同域（优先级更高）
        is_same_domain = parsed.netloc == base_domain or parsed.netloc == ""
        links.append({
            "url": full_url,
            "text": text,
            "domain": parsed.netloc,
            "same_domain": is_same_domain,
        })

    # 同域链接排前面
    links.sort(key=lambda x: (not x["same_domain"], x["text"]))
    return links


# ============================================================
#  爬取任务执行
# ============================================================

def run_crawl_task(task_id: str, urls: list[dict], token: str, delay: float):
    """后台线程：批量爬取选中的链接"""
    task = TASKS[task_id]
    task["status"] = "running"
    task["total"] = len(urls)
    task["done"] = 0
    task["failed"] = 0
    task["logs"] = []

    # 创建任务输出目录
    task_dir = OUTPUT_ROOT / task_id
    task_dir.mkdir(exist_ok=True)

    headers = build_headers(token)

    for idx, item in enumerate(urls, 1):
        url = item["url"]
        title = item.get("text", "") or f"page_{idx}"
        safe_name = sanitize_filename(title)
        filepath = task_dir / f"{safe_name}.md"

        # 断点续爬：文件已存在则跳过
        if filepath.exists() and filepath.stat().st_size > 100:
            log_msg = f"[SKIP] {title} (已存在)"
            task["logs"].append({"type": "skip", "msg": log_msg, "idx": idx})
            task["done"] += 1
            continue

        task["logs"].append({"type": "progress", "msg": f"[{idx}/{len(urls)}] 正在爬取: {title}", "idx": idx})

        try:
            html = fetch_page(url, headers)

            # 检查登录状态
            if "请先登录" in html[:1500]:
                log_msg = f"[FAIL] {title} - 需要登录（Token 已过期？）"
                task["logs"].append({"type": "fail", "msg": log_msg, "idx": idx})
                task["failed"] += 1
                task["done"] += 1
                continue

            md_content = extract_content(html)

            # 添加头部
            header = f"# {title}\n\n> 来源：[{url}]({url})\n\n---\n\n"
            full_md = header + md_content.strip()

            filepath.write_text(full_md, encoding="utf-8")
            size_kb = filepath.stat().st_size / 1024

            log_msg = f"[OK] {title} ({size_kb:.1f} KB)"
            task["logs"].append({"type": "ok", "msg": log_msg, "idx": idx})
            task["done"] += 1

        except Exception as e:
            log_msg = f"[ERROR] {title} - {str(e)[:100]}"
            task["logs"].append({"type": "fail", "msg": log_msg, "idx": idx})
            task["failed"] += 1
            task["done"] += 1

        # 请求间隔
        if idx < len(urls) and delay > 0:
            time.sleep(delay)

    # 打包 ZIP
    task["logs"].append({"type": "info", "msg": "正在打包 ZIP 文件..."})
    zip_path = OUTPUT_ROOT / f"{task_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for md_file in task_dir.rglob("*.md"):
            zf.write(md_file, md_file.relative_to(task_dir))
    task["zip_path"] = str(zip_path)
    task["status"] = "done"
    task["logs"].append({"type": "done", "msg": f"全部完成！成功 {task['done'] - task['failed']}, 失败 {task['failed']}"})


# ============================================================
#  Flask 路由
# ============================================================

@app.route("/")
def index():
    return INDEX_HTML


@app.route("/api/parse", methods=["POST"])
def api_parse():
    data = request.json or {}
    url = data.get("url", "").strip()
    token = data.get("token", "").strip()

    if not url:
        return jsonify({"error": "URL 不能为空"}), 400

    try:
        headers = build_headers(token)
        html = fetch_page(url, headers)
    except requests.RequestException as e:
        return jsonify({"error": f"请求失败: {str(e)[:200]}"}), 500

    title = extract_title(html)
    content = extract_content(html)
    links = extract_links(html, url)

    # 正文预览
    preview = content[:500] + ("..." if len(content) > 500 else "")

    return jsonify({
        "title": title,
        "content_preview": preview,
        "content_length": len(content),
        "links": links,
        "links_count": len(links),
    })


@app.route("/api/crawl", methods=["POST"])
def api_crawl():
    data = request.json or {}
    urls = data.get("urls", [])
    token = data.get("token", "").strip()
    delay = float(data.get("delay", 2))

    if not urls:
        return jsonify({"error": "没有选中任何链接"}), 400

    task_id = uuid.uuid4().hex[:12]
    TASKS[task_id] = {"status": "starting", "total": 0, "done": 0, "failed": 0, "logs": [], "zip_path": None}

    thread = threading.Thread(target=run_crawl_task, args=(task_id, urls, token, delay), daemon=True)
    thread.start()

    return jsonify({"task_id": task_id})


@app.route("/api/progress/<task_id>")
def api_progress(task_id):
    """SSE 实时推送爬取进度"""
    def generate():
        last_idx = 0
        while True:
            task = TASKS.get(task_id)
            if not task:
                yield f"data: {json.dumps({'error': 'task not found'})}\n\n"
                break

            # 推送新日志
            logs = task["logs"]
            if len(logs) > last_idx:
                for log in logs[last_idx:]:
                    yield f"data: {json.dumps(log)}\n\n"
                last_idx = len(logs)

            # 推送状态
            yield f"data: {json.dumps({'type': 'state', 'status': task['status'], 'total': task['total'], 'done': task['done'], 'failed': task['failed']})}\n\n"

            if task["status"] == "done":
                yield f"data: {json.dumps({'type': 'complete', 'zip_ready': bool(task['zip_path'])})}\n\n"
                break

            time.sleep(0.3)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/download/<task_id>")
def api_download(task_id):
    task = TASKS.get(task_id)
    if not task or not task.get("zip_path"):
        return jsonify({"error": "文件不存在"}), 404
    zip_path = Path(task["zip_path"])
    if not zip_path.exists():
        return jsonify({"error": "ZIP 文件不存在"}), 404
    return send_file(zip_path, as_attachment=True, download_name=f"crawl_{task_id}.zip")


# ============================================================
#  内嵌前端 HTML
# ============================================================

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>通用网页文档爬取工具</title>
<style>
:root {
  --bg: #0f1117; --card: #1a1d2e; --border: #2a2d3e;
  --text: #e4e4e7; --text2: #a1a1aa; --accent: #6366f1;
  --accent-hover: #818cf8; --green: #22c55e; --red: #ef4444;
  --orange: #f59e0b; --blue: #3b82f6;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.6;
  min-height: 100vh; padding: 20px;
}
.container { max-width: 900px; margin: 0 auto; }
h1 { font-size: 1.6rem; margin-bottom: 8px; display: flex; align-items: center; gap: 10px; }
h1 .icon { font-size: 1.8rem; }
.subtitle { color: var(--text2); font-size: 0.9rem; margin-bottom: 24px; }
.card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 12px; padding: 24px; margin-bottom: 16px;
}
label { display: block; font-size: 0.85rem; color: var(--text2); margin-bottom: 6px; font-weight: 500; }
input[type="text"], input[type="number"] {
  width: 100%; padding: 10px 14px; background: var(--bg);
  border: 1px solid var(--border); border-radius: 8px;
  color: var(--text); font-size: 0.95rem; outline: none; transition: border 0.2s;
}
input:focus { border-color: var(--accent); }
.row { display: flex; gap: 12px; align-items: flex-end; }
.row > * { flex: 1; }
.row .narrow { flex: 0 0 120px; }
.btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 10px 20px; border: none; border-radius: 8px;
  font-size: 0.9rem; font-weight: 600; cursor: pointer;
  transition: all 0.2s;
}
.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover { background: var(--accent-hover); transform: translateY(-1px); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
.btn-secondary { background: var(--border); color: var(--text); }
.btn-secondary:hover { background: #3a3d4e; }
.btn-green { background: var(--green); color: #fff; }
.btn-green:hover { background: #16a34a; }
.btn-group { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.section-title {
  font-size: 1rem; font-weight: 600; margin-bottom: 12px;
  display: flex; align-items: center; gap: 8px;
}
.preview-box {
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 8px; padding: 16px; margin: 12px 0;
  max-height: 200px; overflow-y: auto; font-size: 0.85rem;
  color: var(--text2); white-space: pre-wrap; word-break: break-all;
}
.links-container {
  max-height: 350px; overflow-y: auto; border: 1px solid var(--border);
  border-radius: 8px; padding: 4px; margin: 12px 0;
}
.link-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; border-radius: 6px; transition: background 0.15s;
}
.link-item:hover { background: rgba(99,102,241,0.08); }
.link-item input[type="checkbox"] {
  accent-color: var(--accent); width: 16px; height: 16px; cursor: pointer;
}
.link-text { flex: 1; font-size: 0.85rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.link-domain { font-size: 0.75rem; color: var(--text2); white-space: nowrap; }
.badge {
  display: inline-block; padding: 2px 8px; border-radius: 10px;
  font-size: 0.7rem; font-weight: 600;
}
.badge-same { background: rgba(34,197,94,0.15); color: var(--green); }
.badge-ext { background: rgba(245,158,11,0.15); color: var(--orange); }
.progress-bar-bg {
  width: 100%; height: 8px; background: var(--bg);
  border-radius: 4px; overflow: hidden; margin: 12px 0;
}
.progress-bar-fill {
  height: 100%; background: linear-gradient(90deg, var(--accent), var(--green));
  border-radius: 4px; transition: width 0.3s;
  width: 0%;
}
.progress-text { font-size: 0.85rem; color: var(--text2); margin-bottom: 8px; }
.log-box {
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 8px; padding: 12px; max-height: 300px;
  overflow-y: auto; font-family: 'Cascadia Code', 'Fira Code', monospace;
  font-size: 0.8rem; line-height: 1.8;
}
.log-ok { color: var(--green); }
.log-fail { color: var(--red); }
.log-skip { color: var(--text2); }
.log-progress { color: var(--blue); }
.log-info { color: var(--orange); }
.log-done { color: var(--green); font-weight: 700; font-size: 0.9rem; }
.hidden { display: none !important; }
.spinner {
  display: inline-block; width: 16px; height: 16px;
  border: 2px solid var(--border); border-top-color: var(--accent);
  border-radius: 50%; animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.select-count { font-size: 0.85rem; color: var(--accent); font-weight: 600; }
.filter-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.filter-input {
  flex: 1; padding: 6px 10px; background: var(--bg);
  border: 1px solid var(--border); border-radius: 6px;
  color: var(--text); font-size: 0.8rem; outline: none;
}
</style>
</head>
<body>
<div class="container">
  <h1><span class="icon">🌐</span> 通用网页文档爬取工具</h1>
  <p class="subtitle">输入任意 URL，自动提取页面正文和链接，批量爬取并打包下载 Markdown</p>

  <!-- 输入区 -->
  <div class="card" id="input-section">
    <div class="row" style="margin-bottom:12px">
      <div>
        <label>目标网址</label>
        <input type="text" id="url-input" placeholder="https://example.com/article-list" />
      </div>
    </div>
    <div class="row">
      <div>
        <label>认证 Token（可选，知识星球等需登录平台）</label>
        <input type="text" id="token-input" placeholder="粘贴 Cookie Token..." />
      </div>
      <div class="narrow">
        <label>请求间隔（秒）</label>
        <input type="number" id="delay-input" value="2" min="0" max="30" step="0.5" />
      </div>
      <div style="flex:0 0 auto">
        <label>&nbsp;</label>
        <button class="btn btn-primary" id="parse-btn" onclick="doParse()">
          🔍 开始解析
        </button>
      </div>
    </div>
  </div>

  <!-- 解析结果 -->
  <div class="card hidden" id="result-section">
    <div class="section-title">📄 解析结果</div>
    <p><strong>页面标题：</strong><span id="page-title"></span></p>
    <p style="margin-top:4px"><strong>发现链接：</strong><span id="links-count" class="select-count"></span> 个</p>

    <details style="margin-top:8px">
      <summary style="cursor:pointer;color:var(--text2);font-size:0.85rem">📝 正文预览（点击展开）</summary>
      <div class="preview-box" id="content-preview"></div>
    </details>

    <div class="filter-row" style="margin-top:12px">
      <input type="text" class="filter-input" id="link-filter" placeholder="🔍 搜索/过滤链接..." oninput="filterLinks()" />
      <span class="select-count" id="selected-count">已选 0</span>
    </div>

    <div class="links-container" id="links-list"></div>

    <div class="btn-group">
      <button class="btn btn-secondary" onclick="selectAll()">全选</button>
      <button class="btn btn-secondary" onclick="selectNone()">全不选</button>
      <button class="btn btn-secondary" onclick="selectInvert()">反选</button>
      <button class="btn btn-secondary" onclick="selectSameDomain()">仅同域</button>
      <button class="btn btn-green" id="crawl-btn" onclick="doCrawl()">
        🚀 开始爬取
      </button>
    </div>
  </div>

  <!-- 爬取进度 -->
  <div class="card hidden" id="progress-section">
    <div class="section-title"><span class="spinner" id="progress-spinner"></span> 爬取进度</div>
    <div class="progress-text" id="progress-text">准备中...</div>
    <div class="progress-bar-bg">
      <div class="progress-bar-fill" id="progress-bar"></div>
    </div>
    <div class="log-box" id="log-box"></div>
  </div>

  <!-- 下载区 -->
  <div class="card hidden" id="download-section">
    <div class="section-title">📦 下载</div>
    <p style="color:var(--text2);font-size:0.9rem;margin-bottom:12px" id="download-summary"></p>
    <button class="btn btn-green" id="download-btn" onclick="doDownload()">
      📦 下载 ZIP 包
    </button>
  </div>
</div>

<script>
let parsedLinks = [];
let currentTaskId = null;

async function doParse() {
  const url = document.getElementById("url-input").value.trim();
  const token = document.getElementById("token-input").value.trim();
  if (!url) { alert("请输入目标网址"); return; }

  const btn = document.getElementById("parse-btn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> 解析中...';

  try {
    const resp = await fetch("/api/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, token }),
    });
    const data = await resp.json();
    if (!resp.ok) { alert(data.error || "解析失败"); return; }

    document.getElementById("page-title").textContent = data.title;
    document.getElementById("links-count").textContent = data.links_count;
    document.getElementById("content-preview").textContent = data.content_preview;
    document.getElementById("result-section").classList.remove("hidden");

    parsedLinks = data.links;
    renderLinks(parsedLinks);
    updateSelectedCount();
  } catch (e) {
    alert("请求出错: " + e.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = "🔍 开始解析";
  }
}

function renderLinks(links) {
  const container = document.getElementById("links-list");
  container.innerHTML = links.map((link, i) => `
    <label class="link-item" data-idx="${i}">
      <input type="checkbox" class="link-cb" data-idx="${i}" ${link.same_domain ? "checked" : ""} onchange="updateSelectedCount()" />
      <span class="link-text" title="${link.url}">${escapeHtml(link.text)}</span>
      <span class="badge ${link.same_domain ? 'badge-same' : 'badge-ext'}">${link.same_domain ? '同域' : '外域'}</span>
    </label>
  `).join("");
  updateSelectedCount();
}

function filterLinks() {
  const keyword = document.getElementById("link-filter").value.toLowerCase();
  document.querySelectorAll(".link-item").forEach(item => {
    const idx = parseInt(item.dataset.idx);
    const link = parsedLinks[idx];
    const match = !keyword || link.text.toLowerCase().includes(keyword) || link.url.toLowerCase().includes(keyword);
    item.style.display = match ? "" : "none";
  });
}

function getSelectedUrls() {
  const selected = [];
  document.querySelectorAll(".link-cb:checked").forEach(cb => {
    const idx = parseInt(cb.dataset.idx);
    selected.push(parsedLinks[idx]);
  });
  return selected;
}

function selectAll() {
  document.querySelectorAll(".link-item:not([style*='display: none']) .link-cb").forEach(cb => cb.checked = true);
  updateSelectedCount();
}
function selectNone() {
  document.querySelectorAll(".link-cb").forEach(cb => cb.checked = false);
  updateSelectedCount();
}
function selectInvert() {
  document.querySelectorAll(".link-item:not([style*='display: none']) .link-cb").forEach(cb => cb.checked = !cb.checked);
  updateSelectedCount();
}
function selectSameDomain() {
  document.querySelectorAll(".link-cb").forEach(cb => {
    const idx = parseInt(cb.dataset.idx);
    cb.checked = parsedLinks[idx].same_domain;
  });
  updateSelectedCount();
}
function updateSelectedCount() {
  const count = document.querySelectorAll(".link-cb:checked").length;
  document.getElementById("selected-count").textContent = `已选 ${count}`;
}

async function doCrawl() {
  const urls = getSelectedUrls();
  if (urls.length === 0) { alert("请至少选择一个链接"); return; }

  const token = document.getElementById("token-input").value.trim();
  const delay = parseFloat(document.getElementById("delay-input").value) || 2;

  document.getElementById("crawl-btn").disabled = true;
  document.getElementById("progress-section").classList.remove("hidden");
  document.getElementById("download-section").classList.add("hidden");
  document.getElementById("log-box").innerHTML = "";
  document.getElementById("progress-bar").style.width = "0%";
  document.getElementById("progress-spinner").style.display = "inline-block";

  try {
    const resp = await fetch("/api/crawl", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls, token, delay }),
    });
    const data = await resp.json();
    if (!resp.ok) { alert(data.error); return; }

    currentTaskId = data.task_id;
    startSSE(currentTaskId);
  } catch (e) {
    alert("启动爬取出错: " + e.message);
    document.getElementById("crawl-btn").disabled = false;
  }
}

function startSSE(taskId) {
  const es = new EventSource(`/api/progress/${taskId}`);
  const logBox = document.getElementById("log-box");

  es.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "state") {
      const pct = data.total > 0 ? Math.round((data.done / data.total) * 100) : 0;
      document.getElementById("progress-bar").style.width = pct + "%";
      document.getElementById("progress-text").textContent =
        `${data.done}/${data.total} (${pct}%)　成功 ${data.done - data.failed}　失败 ${data.failed}`;
    } else if (data.type === "complete") {
      es.close();
      document.getElementById("progress-spinner").style.display = "none";
      document.getElementById("crawl-btn").disabled = false;
      if (data.zip_ready) {
        document.getElementById("download-section").classList.remove("hidden");
        document.getElementById("download-summary").textContent =
          `爬取完成，共 ${document.getElementById("progress-text").textContent}`;
      }
    } else {
      // 日志
      const cls = `log-${data.type || "info"}`;
      const div = document.createElement("div");
      div.className = cls;
      div.textContent = data.msg || JSON.stringify(data);
      logBox.appendChild(div);
      logBox.scrollTop = logBox.scrollHeight;
    }
  };

  es.onerror = () => {
    es.close();
    document.getElementById("progress-spinner").style.display = "none";
    document.getElementById("crawl-btn").disabled = false;
  };
}

function doDownload() {
  if (!currentTaskId) return;
  window.location.href = `/api/download/${currentTaskId}`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// Enter 键触发解析
document.getElementById("url-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") doParse();
});
</script>
</body>
</html>"""


# ============================================================
#  主入口
# ============================================================

def main():
    port = 5000
    url = f"http://localhost:{port}"
    print("=" * 60)
    print("  [Web Scraper] 通用网页文档爬取工具")
    print(f"  访问地址: {url}")
    print("  按 Ctrl+C 停止服务")
    print("=" * 60)

    # 延迟打开浏览器
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
