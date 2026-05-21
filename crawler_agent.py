"""
AI 智能体项目文档爬取工具
"""

import re
import os
import time
import json
import html2text
import requests
from datetime import datetime

# ======================== 配置区 ========================
ZSXQ_TOKEN = "0141AA8B-D5DA-4F11-8F33-B48EAF741996_949AFD34429601ED"
OUTPUT_DIR = r"D:\TOOLs\zsxq_crawler\output_agent"
DELAY = 2
# ========================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Cookie": f"zsxq_access_token={ZSXQ_TOKEN}",
    "Referer": "https://wx.zsxq.com/",
}

# 目录结构：(章节, 标题, URL)
ARTICLES = [
    ("项目概要介绍", "项目介绍与核心价值", "https://articles.zsxq.com/id_4rous3koa1g7.html"),
    ("项目概要介绍", "核心架构设计", "https://articles.zsxq.com/id_u3dzh8h3dtmr.html"),
    ("项目概要介绍", "工程化技术概括", "https://articles.zsxq.com/id_1qkr4u9zezzv.html"),
    ("项目概要介绍", "图数据库与知识路由", "https://articles.zsxq.com/id_f89821axd4ow.html"),
    ("项目概要介绍", "文档和视频目录", "https://articles.zsxq.com/id_vkscbgps0hm8.html"),

    ("项目启动讲解", "申请AI模型调用", "https://articles.zsxq.com/id_4cg31jfj4hjp.html"),
    ("项目启动讲解", "如何安装项目需要的中间件环境", "https://articles.zsxq.com/id_530qhhiwugl3.html"),
    ("项目启动讲解", "准备项目启动条件", "https://articles.zsxq.com/id_ojvqasw9zkb0.html"),
    ("项目启动讲解", "后端项目部署启动", "https://articles.zsxq.com/id_nnspm4dwng8q.html"),
    ("项目启动讲解", "前端项目部署启动", "https://articles.zsxq.com/id_znxlkwkzfwfm.html"),
    ("项目启动讲解", "Agent 对话功能如何使用", "https://articles.zsxq.com/id_bs8oc6i46kh2.html"),
    ("项目启动讲解", "知识路由的功能", "https://articles.zsxq.com/id_00fbrzph32ql.html"),

    ("功能学习导览", "功能总览与学习路线", "https://articles.zsxq.com/id_n8msrc4u0rvz.html"),
    ("功能学习导览", "对话入口与生命周期管理", "https://articles.zsxq.com/id_eku6dezmjub1.html"),
    ("功能学习导览", "执行前准备流程（五步决策链）", "https://articles.zsxq.com/id_u76o08inb51z.html"),
    ("功能学习导览", "执行器体系与模式分发", "https://articles.zsxq.com/id_00p8cpjs0uaq.html"),
    ("功能学习导览", "RAG 检索引擎", "https://articles.zsxq.com/id_6li2g3tpmk2a.html"),
    ("功能学习导览", "会话记忆管理", "https://articles.zsxq.com/id_mld0duqii4oq.html"),
    ("功能学习导览", "知识路由（三层漏斗）", "https://articles.zsxq.com/id_wsavi5a1v21c.html"),
    ("功能学习导览", "文档全生命周期管理", "https://articles.zsxq.com/id_c4xsdtpw7iop.html"),
    ("功能学习导览", "图结构查询与工具调用", "https://articles.zsxq.com/id_nkvlowwgf37w.html"),
    ("功能学习导览", "Prompt 模板、可观测与集群安全", "https://articles.zsxq.com/id_f4i9wae5t2v0.html"),

    ("文档上传与异步解析", "上传接口与文档主记录创建", "https://articles.zsxq.com/id_ti9i4foac623.html"),
    ("文档上传与异步解析", "Kafka 消费与文本内容解析", "https://articles.zsxq.com/id_z3w20pibdnd9.html"),
    ("文档上传与异步解析", "结构节点提取的四阶段流水线", "https://articles.zsxq.com/id_fi9wqwsmua0i.html"),
    ("文档上传与异步解析", "解析结果统计与异步收尾", "https://articles.zsxq.com/id_xqsskz0cs7uw.html"),
    ("文档上传与异步解析", "策略推荐与方案持久化", "https://articles.zsxq.com/id_7k690pdwsfli.html"),

    ("文档解析策略执行", "索引构建入口与Kafka消息投递", "https://articles.zsxq.com/id_wmusjfa2romp.html"),
    ("文档解析策略执行", "异步索引构建：初始化与切块执行", "https://articles.zsxq.com/id_8t9i7twfmz4m.html"),
    ("文档解析策略执行", "四种切块策略详解", "https://articles.zsxq.com/id_3vpim0da71e1.html"),
    ("文档解析策略执行", "异步索引构建：落库、向量化与收尾", "https://articles.zsxq.com/id_le8jldbkhbm3.html"),

    ("聊天系统整体架构", "从用户提问到答案返回的总流程", "https://articles.zsxq.com/id_5bxe0mj55bmf.html"),
    ("聊天系统整体架构", "前后端模块划分与调用关系", "https://articles.zsxq.com/id_rd24cak8vmv0.html"),

    ("SSE流式对话与会话生命周期", "stream 接口与 SSE 事件协议", "https://articles.zsxq.com/id_g4oqjni1i2x7.html"),
    ("SSE流式对话与会话生命周期", "聊天架构与执行入口", "https://articles.zsxq.com/id_n31lxprocgo2.html"),

    ("执行器工作前的准备流程", "执行计划准备的入口与整体流程", "https://articles.zsxq.com/id_qxcu3t0ujcb1.html"),
    ("执行器工作前的准备流程", "会话记忆装载与历史上下文构建", "https://articles.zsxq.com/id_zkvlsi0t2j16.html"),
    ("执行器工作前的准备流程", "窗口渲染与历史上下文构建", "https://articles.zsxq.com/id_ehu2o1bbi8u3.html"),
    ("执行器工作前的准备流程", "时间敏感性识别", "https://articles.zsxq.com/id_gah6ld0bp1d3.html"),
    ("执行器工作前的准备流程", "开放式问答模式的快速路由", "https://articles.zsxq.com/id_2w7k5qijb86w.html"),
    ("执行器工作前的准备流程", "文档问答配置检查与问题改写入口", "https://articles.zsxq.com/id_snz59r4rw9w8.html"),
    ("执行器工作前的准备流程", "问题改写服务的完整实现", "https://articles.zsxq.com/id_an2qvdsgc864.html"),
    ("执行器工作前的准备流程", "改写结果处理与兜底机制", "https://articles.zsxq.com/id_13kwidaj60s8.html"),
    ("执行器工作前的准备流程", "AUTO_DOCUMENT 模式的知识范围路由", "https://articles.zsxq.com/id_akzm0p9bg957.html"),
    ("执行器工作前的准备流程", "知识范围路由服务的核心实现（上）", "https://articles.zsxq.com/id_3cgwfe76c75i.html"),
    ("执行器工作前的准备流程", "知识范围路由服务的核心实现（下）", "https://articles.zsxq.com/id_b2jdpx7wb2fa.html"),
    ("执行器工作前的准备流程", "主题路由和文档路由的详细实现", "https://articles.zsxq.com/id_zfk7hihe4adn.html"),
    ("执行器工作前的准备流程", "置信度计算与候选文档选择", "https://articles.zsxq.com/id_mg9ihjpbugwx.html"),
    ("执行器工作前的准备流程", "澄清判断逻辑与执行计划构建", "https://articles.zsxq.com/id_mo8nokt2b3am.html"),
    ("执行器工作前的准备流程", "路由追踪记录与最终路由文档确定", "https://articles.zsxq.com/id_33b3enbclpow.html"),
    ("执行器工作前的准备流程", "文档导航路由与执行模式判定", "https://articles.zsxq.com/id_d2egkuviwven.html"),
    ("执行器工作前的准备流程", "统一意图识别与本地规则引擎", "https://articles.zsxq.com/id_4idordvznkwn.html"),
    ("执行器工作前的准备流程", "LLM 兜底分类与意图解析", "https://articles.zsxq.com/id_57whi9qgltic.html"),
    ("执行器工作前的准备流程", "章节解析三层策略与导航决策构建", "https://articles.zsxq.com/id_th55uwlvar62.html"),
    ("执行器工作前的准备流程", "执行计划的最终装配", "https://articles.zsxq.com/id_o38blkoe63r7.html"),
    ("执行器工作前的准备流程", "执行计划后处理与上下文同步", "https://articles.zsxq.com/id_zc29jdh7m0wm.html"),

    ("RAG模式执行器的流程", "执行器注册表与模式分发机制", "https://articles.zsxq.com/id_8ml55wt0brol.html"),
    ("RAG模式执行器的流程", "RagChatExecutor执行器的主流程", "https://articles.zsxq.com/id_2cxszdckt51h.html"),
    ("RAG模式执行器的流程", "RAG检索引擎的核心流程", "https://articles.zsxq.com/id_g4qb73s7n2sz.html"),
    ("RAG模式执行器的流程", "单个子问题的检索流程", "https://articles.zsxq.com/id_39o2pegmpqbn.html"),
    ("RAG模式执行器的流程", "检索请求的构建流程", "https://articles.zsxq.com/id_secofattexhx.html"),
    ("RAG模式执行器的流程", "向量检索通道的执行流程", "https://articles.zsxq.com/id_4tx8hwjz07xt.html"),
    ("RAG模式执行器的流程", "关键词检索通道的执行流程", "https://articles.zsxq.com/id_4gwh1pgadqqw.html"),
    ("RAG模式执行器的流程", "双通道检索获得结果后的后续处理(RRF 融合)", "https://articles.zsxq.com/id_le0f79vw383d.html"),
    ("RAG模式执行器的流程", "双通道检索获得结果后的后续处理(父块提升)", "https://articles.zsxq.com/id_aogae57lsnjb.html"),
    ("RAG模式执行器的流程", "双通道检索获得结果后的后续处理(Rerank 重排序)", "https://articles.zsxq.com/id_tqsscsw7nzxj.html"),
    ("RAG模式执行器的流程", "FinalTopK 裁剪与检索摘要生成", "https://articles.zsxq.com/id_f7wjwnpje1db.html"),
    ("RAG模式执行器的流程", "检索观测数据记录(通道级观测)", "https://articles.zsxq.com/id_pbjskgq03hm8.html"),
    ("RAG模式执行器的流程", "检索观测数据记录(文档级观测与证据封装)", "https://articles.zsxq.com/id_qbhf34cdq0b2.html"),
    ("RAG模式执行器的流程", "子问题证据汇总与引用编号分配", "https://articles.zsxq.com/id_2wmbw9iobx8g.html"),

    ("图结构模式执行器的流程", "图结构模式的路由选择", "https://articles.zsxq.com/id_2r2nwz9qcm3k.html"),
    ("图结构模式执行器的流程", "两种图结构执行器的定位与场景", "https://articles.zsxq.com/id_tpxxopjwfkbo.html"),
    ("图结构模式执行器的流程", "GraphOnlyExecutor 执行器主流程", "https://articles.zsxq.com/id_wx2agfai0kgt.html"),
    ("图结构模式执行器的流程", "结构图查询引擎的查询细节", "https://articles.zsxq.com/id_pcibzdxswofz.html"),
    ("图结构模式执行器的流程", "图结构答案的渲染逻辑", "https://articles.zsxq.com/id_5wvp0m5dcdfk.html"),
    ("图结构模式执行器的流程", "GraphThenEvidenceExecutor 执行器的流程", "https://articles.zsxq.com/id_ub5so8fp10np.html"),

    ("开放式问答执行器解析", "ReactAgent执行器概述与触发机制", "https://articles.zsxq.com/id_xjhi8m2rq93m.html"),
    ("开放式问答执行器解析", "ReactAgent的Bean配置与组件装配", "https://articles.zsxq.com/id_rnewdevs7v84.html"),
    ("开放式问答执行器解析", "execute方法的核心执行流程", "https://articles.zsxq.com/id_0vsvxjivf136.html"),
    ("开放式问答执行器解析", "流式文本提取与输出控制", "https://articles.zsxq.com/id_dpcgl35a2mws.html"),
    ("开放式问答执行器解析", "Tavily联网搜索工具的执行流程", "https://articles.zsxq.com/id_53hvwm1zfvfb.html"),
    ("开放式问答执行器解析", "拦截器链的源码解析", "https://articles.zsxq.com/id_qwwepc6tsis2.html"),
    ("开放式问答执行器解析", "ReAct推理循环机制详解", "https://articles.zsxq.com/id_xijii62v2v8c.html"),
]


def html_to_markdown(html: str) -> str:
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0
    h.unicode_snob = True
    h.protect_links = True
    h.wrap_links = False
    h.single_line_break = False
    return h.handle(html)


def fetch_article(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        return resp.text
    except Exception as e:
        print(f"  [ERROR] {e}")
        return ""


def extract_content(html: str) -> str:
    # 去掉代码块语言选择器
    html = re.sub(r'<div[^>]*class="[^"]*code-block-control[^"]*"[^>]*>.*?</div>', '', html, flags=re.DOTALL)
    # 去掉水印
    html = re.sub(r'扫码加入星球.*?查看更多优质内容', '', html, flags=re.DOTALL)

    match = re.search(r'<div[^>]*class="content ql-editor"[^>]*>(.*?)</div>\s*(?:</div>){2,}', html, re.DOTALL)
    if not match:
        match = re.search(r'class="[^"]*ql-editor[^"]*"[^>]*>(.*?)(?=<div[^>]*class="[^"]*(?:toolbar|sidebar|footer|comment))', html, re.DOTALL)
    if not match:
        match = re.search(r'class="content ql-editor"[^>]*>(.*?)知识星球', html, re.DOTALL)

    if match and len(match.group(1)) > 50:
        return html_to_markdown(match.group(1))

    body = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    if body:
        b = re.sub(r'知识星球.*?查看更多优质内容', '', body.group(1), flags=re.DOTALL)
        return html_to_markdown(b)
    return html_to_markdown(html)


def sanitize(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    return name.strip('. ')[:100]


def main():
    print("=" * 60)
    print("  AI 智能体项目文档爬取")
    print(f"  共 {len(ARTICLES)} 篇文档")
    print(f"  输出: {OUTPUT_DIR}")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    success, failed, failed_list = 0, 0, []

    for idx, (chapter, title, url) in enumerate(ARTICLES, 1):
        ch_dir = os.path.join(OUTPUT_DIR, sanitize(chapter))
        os.makedirs(ch_dir, exist_ok=True)
        filepath = os.path.join(ch_dir, f"{sanitize(title)}.md")

        if os.path.exists(filepath) and os.path.getsize(filepath) > 100:
            print(f"[{idx}/{len(ARTICLES)}] 已存在，跳过: {chapter}/{title}")
            success += 1
            continue

        print(f"[{idx}/{len(ARTICLES)}] {chapter}/{title}")
        html = fetch_article(url)
        if not html:
            failed += 1
            failed_list.append(f"{chapter}/{title}")
            continue

        if "请先登录" in html[:1000]:
            print("  [FATAL] Token 已过期！")
            break

        md = extract_content(html)
        header = f"# {title}\n\n> 来源：[{url}]({url})\n\n---\n\n"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(header + md.strip())

        kb = os.path.getsize(filepath) / 1024
        print(f"  OK ({kb:.1f} KB)")
        success += 1
        if idx < len(ARTICLES):
            time.sleep(DELAY)

    print(f"\n{'='*60}")
    print(f"  完成！成功 {success} / 失败 {failed}")
    print(f"  输出: {OUTPUT_DIR}")
    if failed_list:
        print("  失败列表:")
        for item in failed_list:
            print(f"    - {item}")
    print("=" * 60)


if __name__ == "__main__":
    main()
