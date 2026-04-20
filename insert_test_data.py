#!/usr/bin/env python3
# coding=utf-8
"""
插入测试数据到数据库
"""

import sqlite3
import json
from datetime import datetime, timedelta

DB_PATH = "data/trendradar.db"

# 测试新闻数据
TEST_NEWS = [
    {
        "title": "OpenAI 发布 GPT-5 模型，性能大幅提升",
        "platform": "zhihu",
        "platform_name": "知乎",
        "url": "https://zhuanlan.zhihu.com/p/123456",
        "rank": 1,
        "minutes_old": 30,
        "tags": ["大模型", "OpenAI", "GPT"],
        "heat_score": 95,
        "reason": "GPT-5 在推理能力和多模态理解方面取得重大突破"
    },
    {
        "title": "Google DeepMind 新论文：AI 学会自我反思",
        "platform": "twitter",
        "platform_name": "推特",
        "url": "https://twitter.com/deepmind/status/789012",
        "rank": 2,
        "minutes_old": 60,
        "tags": ["大模型", "Google", "AI 研究"],
        "heat_score": 88,
        "reason": "自我反思机制让 AI 能够识别并纠正自己的错误"
    },
    {
        "title": "Meta 开源 Llama 4，可商用且性能强劲",
        "platform": "github",
        "platform_name": "GitHub",
        "url": "https://github.com/meta-llama/llama4",
        "rank": 3,
        "minutes_old": 120,
        "tags": ["大模型", "Meta", "开源"],
        "heat_score": 92,
        "reason": "Llama 4 在多个基准测试中超越 GPT-4，且完全开源可商用"
    },
    {
        "title": "Anthropic 推出 Claude 3.5，专注代码生成",
        "platform": "website",
        "platform_name": "官网",
        "url": "https://anthropic.com/claude-3-5",
        "rank": 4,
        "minutes_old": 180,
        "tags": ["大模型", "Anthropic", "代码生成"],
        "heat_score": 85,
        "reason": "Claude 3.5 专注于软件开发场景，代码生成能力提升 3 倍"
    },
    {
        "title": "清华大学开源多模态大模型 GLM-Edge",
        "platform": "zhihu",
        "platform_name": "知乎",
        "url": "https://zhuanlan.zhihu.com/p/789012",
        "rank": 5,
        "minutes_old": 240,
        "tags": ["大模型", "清华", "多模态"],
        "heat_score": 78,
        "reason": "GLM-Edge 在视觉理解和跨模态检索任务中表现出色"
    },
]

def insert_test_data():
    """插入测试数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("插入测试平台数据...")
    
    # 先插入平台
    platforms_data = {}
    for news in TEST_NEWS:
        if news["platform"] not in platforms_data:
            platforms_data[news["platform"]] = news["platform_name"]
    
    for platform_id, platform_name in platforms_data.items():
        cursor.execute("""
            INSERT OR REPLACE INTO platforms (id, name, is_active)
            VALUES (?, ?, 1)
        """, (platform_id, platform_name))
        print(f"  ✓ 平台：{platform_name}")
    
    conn.commit()
    
    print("\n插入测试新闻数据...")
    
    now = datetime.now()
    
    for news in TEST_NEWS:
        # 计算爬取时间
        first_crawl = now - timedelta(minutes=news["minutes_old"])
        last_crawl = now
        
        # 插入 news_items 表
        cursor.execute("""
            INSERT INTO news_items (
                title, platform_id, rank, url,
                first_crawl_time, last_crawl_time, crawl_count
            ) VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (
            news["title"],
            news["platform"],
            news["rank"],
            news["url"],
            first_crawl.isoformat(),
            last_crawl.isoformat()
        ))
        
        news_id = cursor.lastrowid
        
        # 插入 news_ai_tags 表 (为每条新闻生成标签)
        for tag in news["tags"]:
            cursor.execute("""
                INSERT INTO news_ai_tags (
                    news_item_id, tag, heat_score, reason
                ) VALUES (?, ?, ?, ?)
            """, (
                news_id,
                tag,
                news["heat_score"],
                news["reason"]
            ))
        
        print(f"  ✓ 插入：{news['title']}")
    
    conn.commit()
    
    # 验证数据
    print("\n验证数据...")
    cursor.execute("SELECT COUNT(*) FROM news_items")
    news_count = cursor.fetchone()[0]
    print(f"  新闻总数：{news_count}")
    
    cursor.execute("SELECT COUNT(*) FROM news_ai_tags")
    tags_count = cursor.fetchone()[0]
    print(f"  AI 标签数：{tags_count}")
    
    cursor.execute("SELECT id, title, ai_tags, ai_heat_score FROM v_news_full LIMIT 3")
    rows = cursor.fetchall()
    print(f"\n示例数据:")
    for row in rows:
        print(f"  [{row[0]}] {row[1]}")
        print(f"      标签：{row[2]}, 热度：{row[3]}")
    
    conn.close()
    
    print(f"\n✅ 测试数据插入完成!")

if __name__ == "__main__":
    # 检查数据库是否存在
    import os
    if not os.path.exists(DB_PATH):
        print(f"错误：数据库文件不存在：{DB_PATH}")
        exit(1)
    
    insert_test_data()
