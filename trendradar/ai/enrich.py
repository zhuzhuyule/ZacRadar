# coding=utf-8
"""
批量富化新闻数据：翻译 + 标签 + 热度分 + 理由，一次 API 调用搞定 5 条。

用法:
    uv run python -m trendradar.ai.enrich --db data/trendradar.db \
        --endpoint http://127.0.0.1:33178/v1 \
        --api-key <key> --model <model_id> \
        --batch 5 --concurrency 4
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import requests


CN_RE = re.compile(r'[\u4e00-\u9fff]')


def is_chinese(s: str) -> bool:
    """过半字符是中文则视为中文标题"""
    if not s:
        return False
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return False
    cn = sum(1 for c in letters if CN_RE.match(c))
    return cn >= len(letters) / 2


def build_prompt(items: List[Tuple[int, str]], translate: bool) -> str:
    """items: [(idx_in_batch, title)]"""
    lines = [f"[{i}] {t}" for i, t in items]
    translate_task = "1) 翻译成简体中文 title_zh（若原文本身是中文，title_zh 原样回传）" if translate else "1) title_zh 原样回传原标题"
    return (
        f"对下列 {len(items)} 条新闻标题，做 3 件事并输出严格 JSON 数组（不要任何解释、不要 markdown 代码块）：\n"
        f"{translate_task}\n"
        "2) 给出 1-3 个简短中文主题标签 tags（如'科技/人工智能/财经/国际/社会'等）\n"
        "3) 评估新闻影响力 0-100 分 score，并用一句中文写 reason\n\n"
        "输入：\n" + "\n".join(lines) + "\n\n"
        '输出格式：[{"id":1,"title_zh":"","tags":["",""],"score":0,"reason":""}, ...]'
    )


def call_llm(endpoint: str, api_key: str, model: str, prompt: str, timeout: int = 60) -> str:
    r = requests.post(
        f"{endpoint.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1200,
            "temperature": 0.2,
        },
        timeout=timeout,
    )
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]


def parse_json_array(text: str) -> Optional[List[Dict]]:
    m = re.search(r'\[.*\]', text, re.DOTALL)
    if not m:
        return None
    try:
        arr = json.loads(m.group(0))
        return arr if isinstance(arr, list) else None
    except Exception:
        return None


def enrich_batch(
    endpoint: str, api_key: str, model: str,
    batch: List[Dict], translate: bool,
) -> List[Dict]:
    """batch: list of dicts {item_id, source, title}"""
    if not batch:
        return []
    items = [(i + 1, x["title"]) for i, x in enumerate(batch)]
    prompt = build_prompt(items, translate=translate)
    try:
        content = call_llm(endpoint, api_key, model, prompt)
    except Exception as e:
        print(f"  [批失败] {e}")
        return []
    arr = parse_json_array(content)
    if not arr or len(arr) < len(batch) // 2:
        # 降批重试（拆成单条）
        if len(batch) > 1:
            print(f"  [解析失败，降级单条重试] {len(batch)} 条")
            results = []
            for item in batch:
                results.extend(enrich_batch(endpoint, api_key, model, [item], translate))
            return results
        return []
    # 对齐回原 item_id
    out = []
    for i, item in enumerate(batch):
        if i < len(arr):
            r = arr[i]
            out.append({
                "item_id": item["item_id"],
                "source": item["source"],
                "title": item["title"],
                "title_zh": str(r.get("title_zh") or "").strip() or item["title"],
                "tags": [str(t).strip() for t in (r.get("tags") or []) if t][:3],
                "score": int(r.get("score") or 0),
                "reason": str(r.get("reason") or "").strip(),
            })
    return out


def load_items(conn: sqlite3.Connection) -> List[Dict]:
    """加载所有未富化条目"""
    items = []
    cur = conn.cursor()
    cur.execute("SELECT id, title, COALESCE(title_zh, '') FROM news_items")
    for r in cur.fetchall():
        if r[2]:  # 已有 title_zh，跳过
            continue
        items.append({"item_id": r[0], "source": "news", "title": r[1]})

    try:
        cur.execute("SELECT id, title, COALESCE(title_zh, '') FROM rss_items")
        for r in cur.fetchall():
            if r[2]:
                continue
            items.append({"item_id": r[0], "source": "rss", "title": r[1]})
    except sqlite3.OperationalError:
        pass
    return items


def write_results(conn: sqlite3.Connection, results: List[Dict]) -> None:
    cur = conn.cursor()
    for r in results:
        if r["source"] == "news":
            cur.execute("UPDATE news_items SET title_zh = ? WHERE id = ?", (r["title_zh"], r["item_id"]))
        else:
            cur.execute("UPDATE rss_items SET title_zh = ? WHERE id = ?", (r["title_zh"], r["item_id"]))

        # news_ai_tags：只为 news_items 写（RSS id 和 news_items id 不同 FK 域）
        if r["source"] == "news" and r["tags"]:
            # 先删该 news_item 旧的 ai tags，避免重复
            cur.execute("DELETE FROM news_ai_tags WHERE news_item_id = ?", (r["item_id"],))
            for tag in r["tags"]:
                cur.execute(
                    "INSERT INTO news_ai_tags (news_item_id, tag, heat_score, reason) VALUES (?, ?, ?, ?)",
                    (r["item_id"], tag, r["score"], r["reason"]),
                )
    conn.commit()


def main():
    p = argparse.ArgumentParser(description="批量 AI 富化（翻译+标签+评分）")
    p.add_argument("--db", default="data/trendradar.db")
    p.add_argument("--endpoint", required=True)
    p.add_argument("--api-key", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--batch", type=int, default=5)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--limit", type=int, default=0, help="只处理前 N 条，用于测试")
    args = p.parse_args()

    conn = sqlite3.connect(args.db)
    items = load_items(conn)
    if args.limit > 0:
        items = items[: args.limit]
    print(f"待处理 {len(items)} 条（已跳过已富化）")
    if not items:
        return

    batches = [items[i : i + args.batch] for i in range(0, len(items), args.batch)]
    print(f"拆分为 {len(batches)} 批 × {args.batch} 条，{args.concurrency} 路并发")

    t0 = time.time()
    completed = 0
    all_results: List[Dict] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        future_to_batch = {
            pool.submit(
                enrich_batch, args.endpoint, args.api_key, args.model, b,
                any(not is_chinese(x["title"]) for x in b),  # translate if any non-Chinese
            ): b
            for b in batches
        }
        for fut in as_completed(future_to_batch):
            res = fut.result()
            all_results.extend(res)
            completed += 1
            if completed % 5 == 0 or completed == len(batches):
                elapsed = time.time() - t0
                print(f"  进度 {completed}/{len(batches)} 批，累计 {len(all_results)} 条，耗时 {elapsed:.1f}s")

    # 一次性写回
    write_results(conn, all_results)
    conn.close()
    print(f"\n完成：{len(all_results)} 条富化已写入 DB，总耗时 {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
