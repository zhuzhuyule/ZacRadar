# coding=utf-8
"""
独立驱动：跑 L2 兴趣分类（绕开 LiteLLM 直连本地 OpenAI 兼容端点）

用法:
    uv run python -m trendradar.ai.run_interest_filter --db data/trendradar.db
"""

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from trendradar.core import load_config


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_prompt(filename: str) -> Tuple[str, str]:
    """从 config/ai_filter/<filename> 读取 [system] / [user] 段"""
    path = Path(__file__).parent.parent.parent / "config" / "ai_filter" / filename
    txt = path.read_text(encoding="utf-8")
    sys_m = re.search(r'\[system\](.*?)(?=\[user\]|\Z)', txt, re.DOTALL)
    usr_m = re.search(r'\[user\](.*)', txt, re.DOTALL)
    return (
        (sys_m.group(1).strip() if sys_m else ""),
        (usr_m.group(1).strip() if usr_m else txt.strip()),
    )


def call_llm(endpoint: str, api_key: str, model: str, system: str, user: str, max_tokens: int = 2000) -> str:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": user})
    r = requests.post(
        f"{endpoint.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": 0.2,
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def extract_json(text: str) -> Optional[str]:
    """从模型输出中抽取 JSON（数组或对象）"""
    # 优先去掉 ```json 包裹
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    for opener, closer in [('[', ']'), ('{', '}')]:
        i = text.find(opener)
        if i < 0:
            continue
        depth = 0
        for j in range(i, len(text)):
            if text[j] == opener:
                depth += 1
            elif text[j] == closer:
                depth -= 1
                if depth == 0:
                    return text[i : j + 1]
    return None


def compute_interests_hash(content: str, filename: str = "ai_interests.txt") -> str:
    lines = [ln.strip() for ln in content.strip().splitlines() if ln.strip() and not ln.strip().startswith("#")]
    return f"{filename}:{hashlib.md5('\n'.join(lines).encode('utf-8')).hexdigest()}"


def upsert_tags(conn: sqlite3.Connection, tags: List[Dict], interests_hash: str) -> List[Dict]:
    cur = conn.cursor()
    cur.execute("UPDATE ai_filter_tags SET status='deprecated', deprecated_at=? WHERE status='active'", (now_str(),))
    cur.execute("SELECT COALESCE(MAX(version),0) FROM ai_filter_tags")
    version = cur.fetchone()[0] + 1
    written = []
    for i, t in enumerate(tags):
        cur.execute("""
            INSERT INTO ai_filter_tags (tag, description, priority, status, version, prompt_hash, interests_file, created_at)
            VALUES (?, ?, ?, 'active', ?, ?, 'ai_interests.txt', ?)
        """, (t["tag"], t.get("description", ""), i + 1, version, interests_hash, now_str()))
        written.append({"id": cur.lastrowid, "tag": t["tag"], "description": t.get("description", ""), "priority": i + 1})
    conn.commit()
    return written


def load_titles(conn: sqlite3.Connection) -> List[Dict]:
    items = []
    cur = conn.cursor()
    cur.execute("SELECT id, COALESCE(NULLIF(title_zh,''), title) FROM news_items")
    for r in cur.fetchall():
        items.append({"id": r[0], "title": r[1], "source_type": "hotlist"})
    try:
        cur.execute("SELECT id, COALESCE(NULLIF(title_zh,''), title) FROM rss_items")
        for r in cur.fetchall():
            items.append({"id": r[0], "title": r[1], "source_type": "rss"})
    except sqlite3.OperationalError:
        pass
    return items


def classify_one_batch(
    endpoint: str, api_key: str, model: str,
    classify_sys: str, classify_user_tpl: str,
    titles: List[Dict], tags: List[Dict], interests: str,
) -> List[Dict]:
    """对一批 titles 分类，返回 [{news_item_id, source_type, tag_id, relevance_score}]"""
    if not titles or not tags:
        return []

    tags_list = "\n".join(f"{t['id']}. {t['tag']}: {t.get('description','')}" for t in tags)
    # 用 batch 局部 id（1..N）方便 LLM 引用，再映射回 (news_item_id, source_type)
    local_idx = {(t["id"], t["source_type"]): i + 1 for i, t in enumerate(titles)}
    rev_idx = {v: k for k, v in local_idx.items()}
    news_list = "\n".join(f"{i}. [{t['source_type']}] {t['title']}" for i, t in enumerate(titles, 1))

    user_prompt = (
        classify_user_tpl
        .replace("{interests_content}", interests)
        .replace("{tags_list}", tags_list)
        .replace("{news_count}", str(len(titles)))
        .replace("{news_list}", news_list)
    )
    try:
        resp = call_llm(endpoint, api_key, model, classify_sys, user_prompt, max_tokens=600)
    except Exception as e:
        print(f"  [批失败 {len(titles)} 条] {e}")
        return []
    js = extract_json(resp)
    if not js:
        return []
    try:
        arr = json.loads(js)
    except Exception:
        return []
    out = []
    valid_tag_ids = {t["id"] for t in tags}
    for r in arr if isinstance(arr, list) else []:
        if not isinstance(r, dict):
            continue
        local_id = r.get("id")
        tid = r.get("tag_id")
        score = r.get("score")
        if local_id not in rev_idx or tid not in valid_tag_ids:
            continue
        try:
            score = float(score)
        except (TypeError, ValueError):
            continue
        nid, src = rev_idx[local_id]
        out.append({
            "news_item_id": nid,
            "source_type": src,
            "tag_id": tid,
            "relevance_score": max(0.0, min(1.0, score)),
        })
    return out


def write_classifications(conn, results, interests_hash: str) -> int:
    cur = conn.cursor()
    cur.execute("UPDATE ai_filter_results SET status='deprecated', deprecated_at=? WHERE status='active'", (now_str(),))
    written = 0
    for r in results:
        try:
            cur.execute("""
                INSERT OR REPLACE INTO ai_filter_results
                (news_item_id, source_type, tag_id, relevance_score, status, created_at)
                VALUES (?, ?, ?, ?, 'active', ?)
            """, (r["news_item_id"], r["source_type"], r["tag_id"], r["relevance_score"], now_str()))
            written += 1
        except sqlite3.Error as e:
            print(f"  写入失败 {e}")
    conn.commit()
    return written


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/trendradar.db")
    p.add_argument("--batch", type=int, default=15)
    p.add_argument("--concurrency", type=int, default=3)
    args = p.parse_args()

    cfg = load_config()
    ai = cfg.get("AI", {})
    endpoint = ai.get("API_BASE", "")
    api_key = ai.get("API_KEY", "")
    model = (ai.get("MODEL", "") or "").split("/", 1)[-1]  # 去掉 openai/ 前缀
    if not (endpoint and api_key and model):
        print("config.yaml 中 ai.api_base/api_key/model 必填")
        sys.exit(1)
    print(f"endpoint={endpoint}  model={model}")

    interests_path = Path(__file__).parent.parent.parent / "config" / "ai_interests.txt"
    interests = interests_path.read_text(encoding="utf-8").strip()
    interests_hash = compute_interests_hash(interests)
    print(f"兴趣 hash: {interests_hash}")

    print("\n[1/3] 从 ai_interests.txt 解析编号方向作为标签（跳过 AI 提取，节省调用）...")
    raw_tags: List[Dict] = []
    for line in interests.splitlines():
        m = re.match(r'^\s*(\d{1,2})[\.、]\s*([^：:]+)[：:]\s*(.+)$', line.strip())
        if m:
            short_name = m.group(2).strip()
            desc = m.group(3).strip()
            # 标签名截短到 8 字以内
            if len(short_name) > 8:
                short_name = short_name[:8]
            raw_tags.append({"tag": short_name, "description": desc[:200]})
    if not raw_tags:
        print("解析失败：ai_interests.txt 未发现编号条目")
        sys.exit(1)
    print(f"  得到 {len(raw_tags)} 个标签:")
    for t in raw_tags:
        print(f"    - {t.get('tag')}: {t.get('description','')[:70]}")

    conn = sqlite3.connect(args.db)
    tags_with_ids = upsert_tags(conn, raw_tags, interests_hash)
    print(f"  已写入 ai_filter_tags（{len(tags_with_ids)} 条）")

    print("\n[2/3] 加载新闻标题...")
    titles = load_titles(conn)
    print(f"  共 {len(titles)} 条")

    classify_sys, classify_user_tpl = load_prompt("prompt.txt")

    print(f"\n[3/3] 分类，batch={args.batch} 并发={args.concurrency}")
    batches = [titles[i : i + args.batch] for i in range(0, len(titles), args.batch)]
    all_results: List[Dict] = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {
            pool.submit(classify_one_batch, endpoint, api_key, model, classify_sys, classify_user_tpl, b, tags_with_ids, interests): b
            for b in batches
        }
        done = 0
        for fut in as_completed(futures):
            res = fut.result()
            all_results.extend(res)
            done += 1
            if done % 3 == 0 or done == len(batches):
                print(f"  进度 {done}/{len(batches)} 批，匹配累计 {len(all_results)}，{time.time()-t0:.1f}s")

    n = write_classifications(conn, all_results, interests_hash)
    print(f"\n完成：{n} 条 relevance 写入；总耗时 {time.time()-t0:.1f}s")

    # 简要分布
    cur = conn.cursor()
    cur.execute("""
        SELECT t.tag, COUNT(r.id) AS hits, AVG(r.relevance_score) AS avg_score
        FROM ai_filter_tags t LEFT JOIN ai_filter_results r ON r.tag_id = t.id AND r.status='active'
        WHERE t.status='active' GROUP BY t.id ORDER BY t.priority
    """)
    print("\n各兴趣方向命中分布：")
    for tag, hits, avg in cur.fetchall():
        print(f"  {tag:15} {hits:4} 条  avg={avg or 0:.2f}")
    conn.close()


if __name__ == "__main__":
    main()
