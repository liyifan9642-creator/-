# 网页文档爬取工具集

将网页内容批量提取为 Markdown 文档的工具集合。

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `web_scraper.py` | **通用网页爬取工具** — Web UI 界面，输入任意 URL 即可爬取 |
| `crawler.py` | 知识星球专用爬取脚本（目录文本解析版） |
| `crawler_agent.py` | AI 智能体项目文档爬取脚本（硬编码链接版） |
| `web_output/` | 通用爬取工具的输出目录 |
| `output/` | 黑马点评文档输出目录 |
| `output_agent/` | AI 智能体文档输出目录 |

---

## 通用网页爬取工具（推荐）

### 安装依赖

```bash
pip install flask requests html2text beautifulsoup4
```

### 运行

```bash
python web_scraper.py
```

浏览器自动打开 `http://localhost:5000`。

### 使用流程

```
输入目标网址 + 可选 Token
    → 点击「开始解析」
    → 查看提取到的链接列表，勾选需要的
    → 点击「开始爬取」
    → 等待进度完成
    → 下载 ZIP 包
```

### 功能特性

- **智能正文提取**：自动适配 Quill 编辑器（知识星球）、通用 article/main 标签、WordPress 等
- **链接过滤**：自动跳过图片、视频、压缩包等非文档链接
- **认证支持**：粘贴 Token 即可访问需登录的页面（如知识星球）
- **断点续爬**：已下载的文件自动跳过，中断后重新运行不会重复爬取
- **实时进度**：进度条 + 彩色日志实时刷新
- **ZIP 打包**：爬取完成后一键下载全部 Markdown 文件

### 常见用法

**知识星球文章**
1. 获取 Token：浏览器登录知识星球 → F12 → Application → Cookies → 复制 `zsxq_access_token` 的值
2. 粘贴到网页 Token 输入框
3. 输入文章目录页 URL，开始解析

**普通网页**
1. Token 留空
2. 输入目标 URL，开始解析
3. 勾选感兴趣的链接，开始爬取
