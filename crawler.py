"""
知识星球文档爬取工具
功能：解析目录结构，提取文档链接，访问并保存为 Markdown 文件
"""

import re
import os
import time
import json
import html2text
import requests
from pathlib import Path
from datetime import datetime

# ======================== 配置区 ========================
ZSXQ_TOKEN = "0141AA8B-D5DA-4F11-8F33-B48EAF741996_949AFD34429601ED"
OUTPUT_DIR = r"D:\TOOLs\zsxq_crawler\output"
DELAY_BETWEEN_REQUESTS = 2  # 请求间隔秒数，避免被封
# ========================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Cookie": f"zsxq_access_token={ZSXQ_TOKEN}",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://wx.zsxq.com/",
}

# 目录结构文本
DIRECTORY_TEXT = """
黑马点评 Plus 文档和视频目录

项目特点介绍

1. 黑马点评升级版：价值与亮点
文档：https://articles.zsxq.com/id_4d0i3fpgfdol.html
2. 黑马点评升级版：变化综览
文档：https://articles.zsxq.com/id_5uqnuxniwg8t.html
3. 黑马点评升级版：简历模板参考
文档：https://articles.zsxq.com/id_5px4203b6zbj.html
4. 黑马点评普通版本的文档和视频
文档：https://articles.zsxq.com/id_wvzwfmkzn9jh.html

项目启动讲解

1. 准备项目启动条件
文档：https://articles.zsxq.com/id_upc0gan63eja.html
2. 如何安装项目需要的中间件环境
文档：https://articles.zsxq.com/id_nhej5j6amirl.html
3. 后端项目部署启动
文档：https://articles.zsxq.com/id_25811xlp4b7w.html
4. 前端项目部署启动
文档：https://articles.zsxq.com/id_0cbvooscn73l.html

项目基础讲解

1. 数据库表关系
文档：https://articles.zsxq.com/id_rod5buipiojf.html
2. 相关数据的更新
文档：https://articles.zsxq.com/id_m3kp1hb9gbu4.html

分库分表的设计

1. 全面剖析分库分表
文档：https://articles.zsxq.com/id_z6ecmsd4mod1.html
2. 分库分表的具体实现-上
文档：https://articles.zsxq.com/id_un2ktwjdcomp.html
3. 分库分表的具体实现-下
文档：https://articles.zsxq.com/id_x8h3x5tv1460.html

高并发下的缓存体系设计与风险防护

1. 如何完美解决缓存击穿-上
文档：https://articles.zsxq.com/id_jsagivzdx3fn.html
2. 如何完美解决缓存击穿-下
文档：https://articles.zsxq.com/id_mpg6uq8nl9gu.html
3. 如何完美解决缓存穿透
文档：https://articles.zsxq.com/id_7w7i3tl82r7w.html
4. 百万并发的终极杀招 "多级缓存"
文档：https://articles.zsxq.com/id_qgosgsw7g8kg.html
5. 如何确保多级缓存的一致性？
文档：https://articles.zsxq.com/id_5qjhnu577g2i.html
6. 消息发送失败处理与 DLQ 补偿流程
文档：https://articles.zsxq.com/id_jpv4anrie6t5.html
7. 商铺信息的查询
文档：https://articles.zsxq.com/id_na0rh89io55n.html

高并发下的优惠券抢购实现与优化

1. 异步秒杀的可靠性重构升级
文档：https://articles.zsxq.com/id_jf6z5bn5e74z.html
2. 如何在异步消费中可靠地生成订单
文档：https://articles.zsxq.com/id_2vdj1de1wcec.html
3. 异步消费超时的最佳处理方案
文档：https://articles.zsxq.com/id_wgu3zfwwg2u5.html
4. 消费生成订单异常的处理与补偿机制
文档：https://articles.zsxq.com/id_lda0odwjz9l6.html

秒杀的护城河：动态令牌与防刷体系

1. 高并发下的限流守卫-动态令牌桶
文档：https://articles.zsxq.com/id_z3xarmw1ctz6.html
2. 高并发下的限流守卫-滑动窗口
文档：https://articles.zsxq.com/id_3a1lescwfbo9.html
3. 令牌签发-从凭证到通行证
文档：https://articles.zsxq.com/id_wr0x504u0ro4.html

到券提醒系统设计与最佳实践

1. 无库存订阅与到券通知全流程
文档：https://articles.zsxq.com/id_zwc3nqlad7r4.html
2. 如何公平性的自动分配已订阅用户
文档：https://articles.zsxq.com/id_cit58kv2p53g.html

券务运维与一致性保障

1. 订单取消与数据清理的正确姿势
文档：https://articles.zsxq.com/id_lsff8xmnso8w.html
2. 库存修改的双轨一致性
文档：https://articles.zsxq.com/id_envdb3nw920f.html
3. 并发与锁实践：数据一致性策略
文档：https://articles.zsxq.com/id_n7v0xtwwkq6b.html
4. Redis 和数据库的数据对比和补偿执行
文档：https://articles.zsxq.com/id_m7f7oiw489av.html
5. Kafka宕机场景与消息可靠性优化说明
文档：https://articles.zsxq.com/id_uswml7okdwqs.html
6. 添加秒杀优惠券的额外处理
文档：https://articles.zsxq.com/id_svjirftaav62.html
7. 指标监控详解
文档：https://articles.zsxq.com/id_2jdm26u8lbav.html
8. 用户登录的额外处理
文档：https://articles.zsxq.com/id_ntac0p4tshwa.html

视频错误和遗漏内容补充

帮你面试通过总结篇

1. Redis 组件中用到的所有键
文档：https://articles.zsxq.com/id_wr337dwmwx2z.html
2. Redis 过期删除与内存淘汰策略总结
文档：https://articles.zsxq.com/id_wn4gitxo2ck4.html

架构组件讲解

1. 分布式ID生成器揭秘，保障数据唯一性的核心组件
文档：https://articles.zsxq.com/id_klczimfi17nm.html
2. 分布式锁使用全攻略，轻松掌握并发控制的利器
文档：https://articles.zsxq.com/id_59d3zb9rkge6.html
3. 分布式锁原理的详细剖析-上
文档：https://articles.zsxq.com/id_jc0qvdqa4jk5.html
4. 分布式锁原理的详细剖析-下
文档：https://articles.zsxq.com/id_zbk9x1wk948p.html
5. 如何打造高效幂等组件，确保数据一致性
文档：https://articles.zsxq.com/id_bv11xfnh2m8b.html
6. 如何实现高性能延迟队列-发送消息
文档：https://articles.zsxq.com/id_6i9wzffvnp0r.html
7. 如何实现高性能延迟队列-消费消息
文档：https://articles.zsxq.com/id_r7ek2pfgax90.html
8. 如何对Redis进行高效封装
文档：https://articles.zsxq.com/id_nsgbafbsknew.html
9. 布隆过滤器的优雅设计原理
文档：https://articles.zsxq.com/id_basi73whjfha.html
10. Kafka 生产者抽象组件详细指南
文档：https://articles.zsxq.com/id_0xuh7zs4wsdc.html
11. Kafka 消费者抽象组件详细指南
文档：https://articles.zsxq.com/id_li2se4djjaw2.html
12. 触发报警和上报指标
文档：https://articles.zsxq.com/id_tx2pds8fd05l.html

技术精华

1. 雪花算法完全解读
文档：https://articles.zsxq.com/id_3nd90w1oz7bi.html
2. 为什么MybatisPlus生成的id在k8s环境会发生重复
文档：https://articles.zsxq.com/id_bd0ui0f4h0w4.html
3. 完全解读 Redisson 的分布式锁原理
文档：https://articles.zsxq.com/id_min0dfil896f.html
4. 深入剖析分布式锁与事务在生产中的"疑难杂症"
文档：https://articles.zsxq.com/id_7wo087eejo5d.html
5. 如何设计高效的延迟队列
文档：https://articles.zsxq.com/id_8r8pz669nj4c.html
6. Redisson 分布式延迟队列原理解析
文档：https://articles.zsxq.com/id_9b1kua2bwmlg.html
7. 全面解析Spring事务的失效以及如何避免
文档：https://articles.zsxq.com/id_s5kbwwfkphne.html
8. 完全解读布隆过滤器
文档：https://articles.zsxq.com/id_f4hie9ezgvu2.html
9. Redis-hash-tag
文档：https://articles.zsxq.com/id_7k4qtb2mofst.html

项目的面试注意问题

视频地址：https://articles.zsxq.com/id_b7d1nz7d4d08.html
"""


def parse_directory(text: str) -> list[dict]:
    """
    解析目录文本，返回结构化的章节和文档链接列表
    [
        {"chapter": "章节名", "title": "文档标题", "url": "https://..."},
        ...
    ]
    """
    results = []
    current_chapter = ""

    lines = text.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue

        # 检测是否是文档链接行
        doc_match = re.match(r'^文档[：:]\s*(https://articles\.zsxq\.com/id_\w+\.html)', line)
        if doc_match:
            url = doc_match.group(1)
            # 往回找标题（上一个非空行）
            title = ""
            for j in range(i - 2, -1, -1):
                prev = lines[j].strip()
                if prev and not prev.startswith("文档") and not prev.startswith("视频"):
                    # 去掉前面的序号如 "1. "
                    title = re.sub(r'^\d+\.\s*', '', prev)
                    break
            if title:
                results.append({
                    "chapter": current_chapter,
                    "title": title,
                    "url": url,
                })
            continue

        # 检测是否是章节标题
        # 章节标题的特征：不以数字+点开头，不是"文档："或"视频："，不是空白
        if (not re.match(r'^\d+[\.\、]', line)
            and not line.startswith("文档")
            and not line.startswith("视频")
            and not line.startswith("第")
            and not line.startswith("来自")
            and not line.startswith("用户头像")
            and not line.startswith("阿星")
            and not line.startswith("2025")
            and not line.startswith("黑马点评 Plus")
            and not line.startswith("扫码")
            and not line.startswith("查看更多")
            and not line.startswith("知识星球")
            and len(line) < 50):
            current_chapter = line

    return results


def fetch_article(url: str) -> str:
    """访问文章URL，返回HTML内容"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        return resp.text
    except Exception as e:
        print(f"  [ERROR] 请求失败: {e}")
        return ""


def html_to_markdown(html: str) -> str:
    """将HTML转换为Markdown"""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.body_width = 0  # 不自动换行
    h.unicode_snob = True
    h.protect_links = True
    h.wrap_links = False
    h.single_line_break = False

    md = h.handle(html)
    return md


def extract_article_content(html: str) -> str:
    """
    从知识星球文章页面HTML中提取正文内容
    知识星球使用 Quill 编辑器，正文在 class="content ql-editor" 的 div 中
    """
    # 预处理：去掉代码块的语言选择器（会污染输出）
    html = re.sub(
        r'<div[^>]*class="[^"]*code-block-control[^"]*"[^>]*>.*?</div>',
        '', html, flags=re.DOTALL
    )
    # 去掉页面导航、水印等非正文内容
    html = re.sub(r'<div[^>]*class="[^"]*logo[^"]*"[^>]*>.*?</div>', '', html, flags=re.DOTALL)
    html = re.sub(r'扫码加入星球.*?查看更多优质内容', '', html, flags=re.DOTALL)

    # 方法1：匹配 Quill 编辑器内容区域（最准确）
    match = re.search(
        r'<div[^>]*class="content ql-editor"[^>]*>(.*?)</div>\s*(?:</div>){2,}',
        html, re.DOTALL
    )
    if not match:
        # 备选：更宽松的 ql-editor 匹配
        match = re.search(
            r'class="[^"]*ql-editor[^"]*"[^>]*>(.*?)(?=<div[^>]*class="[^"]*(?:toolbar|sidebar|footer|comment))',
            html, re.DOTALL
        )
    if not match:
        # 最后兜底：匹配从 ql-editor 到页面底部水印之前
        match = re.search(
            r'class="content ql-editor"[^>]*>(.*?)知识星球',
            html, re.DOTALL
        )

    if match:
        content_html = match.group(1)
        if len(content_html) > 50:
            return html_to_markdown(content_html)

    # 方法2：提取 body 内容（去掉头尾）
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    if body_match:
        body = body_match.group(1)
        body = re.sub(r'知识星球.*?查看更多优质内容', '', body, flags=re.DOTALL)
        return html_to_markdown(body)

    return html_to_markdown(html)


def sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    illegal = r'[<>:"/\\|?*\x00-\x1f]'
    name = re.sub(illegal, '_', name)
    name = name.strip('. ')
    return name[:100]  # 限制长度


def main():
    print("=" * 60)
    print("  知识星球文档爬取工具")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"  请求间隔: {DELAY_BETWEEN_REQUESTS}s")
    print("=" * 60)

    # 1. 解析目录
    articles = parse_directory(DIRECTORY_TEXT)
    print(f"\n[解析完成] 共找到 {len(articles)} 篇文档\n")

    # 打印解析结果
    chapters = {}
    for a in articles:
        ch = a["chapter"] or "未分类"
        if ch not in chapters:
            chapters[ch] = []
        chapters[ch].append(a["title"])

    print("章节结构:")
    for ch, titles in chapters.items():
        print(f"  {ch}/ ({len(titles)} 篇)")
        for t in titles:
            print(f"    - {t}")
    print()

    # 2. 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 3. 爬取并保存
    success = 0
    failed = 0
    failed_list = []

    for idx, article in enumerate(articles, 1):
        chapter = sanitize_filename(article["chapter"] or "未分类")
        title = sanitize_filename(article["title"])
        url = article["url"]

        # 创建章节目录
        chapter_dir = os.path.join(OUTPUT_DIR, chapter)
        os.makedirs(chapter_dir, exist_ok=True)

        # 文件路径
        filepath = os.path.join(chapter_dir, f"{title}.md")

        # 如果文件已存在，跳过
        if os.path.exists(filepath) and os.path.getsize(filepath) > 100:
            print(f"[{idx}/{len(articles)}] 已存在，跳过: {chapter}/{title}.md")
            success += 1
            continue

        print(f"[{idx}/{len(articles)}] 正在获取: {chapter}/{title}")
        print(f"  URL: {url}")

        # 获取页面
        html = fetch_article(url)
        if not html:
            failed += 1
            failed_list.append(f"{chapter}/{title}: 请求失败")
            continue

        # 检查是否是登录页或错误页
        if "请先登录" in html or "login" in html.lower()[:500]:
            print(f"  [WARN] 可能需要重新登录（Token已过期？）")
            failed += 1
            failed_list.append(f"{chapter}/{title}: 需要登录")
            continue

        # 转换为 Markdown
        md_content = extract_article_content(html)

        # 检查内容是否有效
        if len(md_content.strip()) < 50:
            print(f"  [WARN] 内容过短（{len(md_content)}字符），可能提取失败")
            # 仍然保存，但标记

        # 添加标题头
        header = f"# {article['title']}\n\n"
        header += f"> 来源：[{url}]({url})\n\n---\n\n"
        md_content = header + md_content.strip()

        # 保存文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)

        size_kb = os.path.getsize(filepath) / 1024
        print(f"  [OK] 保存成功 ({size_kb:.1f} KB)")
        success += 1

        # 请求间隔
        if idx < len(articles):
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # 4. 输出汇总
    print("\n" + "=" * 60)
    print(f"  爬取完成！")
    print(f"  成功: {success} 篇")
    print(f"  失败: {failed} 篇")
    print(f"  输出目录: {OUTPUT_DIR}")
    print("=" * 60)

    if failed_list:
        print("\n失败列表:")
        for item in failed_list:
            print(f"  - {item}")

    # 保存爬取报告
    report = {
        "time": datetime.now().isoformat(),
        "total": len(articles),
        "success": success,
        "failed": failed,
        "failed_list": failed_list,
    }
    report_path = os.path.join(OUTPUT_DIR, "_crawl_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    main()
