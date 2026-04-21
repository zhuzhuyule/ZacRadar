# coding=utf-8
"""
跨平台事件聚合

基于标题字符 bigram（中文）或词袋（英文）Jaccard 相似度，
把同一事件的多平台条目合并到 ai_events 表，写入 news_event_map。

用法:
    uv run python -m trendradar.ai.event_clustering --db data/trendradar.db
"""

import argparse
import re
import sqlite3
import sys
from typing import Dict, List, Set, Tuple


CN_RE = re.compile(r'[\u4e00-\u9fff]')
WORD_RE = re.compile(r'[a-zA-Z][a-zA-Z0-9]+')
STOP_CHARS = set('的了在是我有和就不人都一上也很到说要去你会着没有看好这')
STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'on', 'for', 'with',
    'is', 'are', 'was', 'were', 'be', 'been', 'by', 'at', 'as', 'it', 'its',
    'that', 'this', 'from', 'how', 'what', 'why', 'who', 'can', 'will',
}


def tokenize(title: str) -> Set[str]:
    """返回 title 的特征集合，用于 Jaccard"""
    t = (title or '').lower().strip()
    if not t:
        return set()
    is_chinese = len(CN_RE.findall(t)) >= 4  # 至少 4 个中文字符才按中文处理

    tokens: Set[str] = set()
    if is_chinese:
        # 去掉非中文、数字、英文
        cleaned = re.sub(r'[^\u4e00-\u9fff0-9a-zA-Z]', '', t)
        for i in range(len(cleaned) - 1):
            ch1, ch2 = cleaned[i], cleaned[i + 1]
            if ch1 in STOP_CHARS or ch2 in STOP_CHARS:
                continue
            tokens.add(cleaned[i:i + 2])
        # 英文单词也加入
        tokens.update(w for w in WORD_RE.findall(t) if w not in STOP_WORDS and len(w) > 2)
    else:
        tokens.update(w for w in WORD_RE.findall(t) if w not in STOP_WORDS and len(w) > 2)
    return tokens


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


class UnionFind:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def fetch_all_items(conn: sqlite3.Connection) -> List[Tuple[int, str, str, str]]:
    """返回 [(row_id, source_table, native_id, title, platform_name)]"""
    rows: List[Tuple] = []
    cur = conn.cursor()

    # 优先用 title_zh（如已翻译/富化）做聚合特征，回退到 title
    cur.execute("""
        SELECT ni.id, COALESCE(NULLIF(ni.title_zh, ''), ni.title) AS feature_title,
               COALESCE(p.name, ni.platform_id) AS pname
        FROM news_items ni
        LEFT JOIN platforms p ON p.id = ni.platform_id
    """)
    for r in cur.fetchall():
        rows.append(('news', r[0], r[1], r[2]))

    # RSS 条目（若表存在）
    try:
        cur.execute("""
            SELECT r.id, COALESCE(NULLIF(r.title_zh, ''), r.title) AS feature_title,
                   COALESCE(f.name, r.feed_id) AS fname
            FROM rss_items r
            LEFT JOIN rss_feeds f ON f.id = r.feed_id
        """)
        for r in cur.fetchall():
            rows.append(('rss', 10_000_000 + r[0], r[1], r[2]))
    except sqlite3.OperationalError:
        pass

    return rows


def cluster_events(
    items: List[Tuple],
    threshold: float = 0.45,
) -> List[List[int]]:
    """返回索引簇列表，每簇至少 2 元素"""
    tokens = [tokenize(x[2]) for x in items]
    # 倒排索引：token → item indices，减少两两比较
    inverted: Dict[str, List[int]] = {}
    for i, toks in enumerate(tokens):
        for t in toks:
            inverted.setdefault(t, []).append(i)

    uf = UnionFind(len(items))
    seen_pairs: Set[Tuple[int, int]] = set()
    for t, idxs in inverted.items():
        if len(idxs) > 60:  # 跳过极常见 token
            continue
        for i in range(len(idxs)):
            for j in range(i + 1, len(idxs)):
                a, b = idxs[i], idxs[j]
                if a == b:
                    continue
                pair = (a, b) if a < b else (b, a)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                if jaccard(tokens[a], tokens[b]) >= threshold:
                    uf.union(a, b)

    groups: Dict[int, List[int]] = {}
    for i in range(len(items)):
        groups.setdefault(uf.find(i), []).append(i)
    # 只保留含多平台的簇
    clusters = []
    for idxs in groups.values():
        if len(idxs) < 2:
            continue
        platforms = {items[i][3] for i in idxs}
        if len(platforms) >= 2:
            clusters.append(idxs)
    return clusters


def write_events(conn: sqlite3.Connection, items: List[Tuple], clusters: List[List[int]]) -> int:
    cur = conn.cursor()
    # 清空旧事件，便于重算
    cur.execute("DELETE FROM news_event_map")
    cur.execute("DELETE FROM ai_events")
    conn.commit()

    event_count = 0
    for cluster in clusters:
        # 只针对 news（不含 rss）的 id 进入 news_event_map，因为 FK 约束指向 news_items
        news_ids_in_cluster = [items[i][1] for i in cluster if items[i][0] == 'news']
        platforms = {items[i][3] for i in cluster}
        if len(news_ids_in_cluster) < 2 and 'rss' not in {items[i][0] for i in cluster}:
            continue
        # 选最短标题做事件名（通常更概括）
        rep_idx = min(cluster, key=lambda i: len(items[i][2] or ''))
        rep_title = items[rep_idx][2]
        rep_news_id = items[rep_idx][1] if items[rep_idx][0] == 'news' else (news_ids_in_cluster[0] if news_ids_in_cluster else None)

        cur.execute("""
            INSERT INTO ai_events (event_name, event_summary, representative_news_id, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (rep_title, rep_title, rep_news_id))
        event_id = cur.lastrowid

        for news_id in news_ids_in_cluster:
            cur.execute("""
                INSERT OR IGNORE INTO news_event_map (news_item_id, event_id, related_count)
                VALUES (?, ?, ?)
            """, (news_id, event_id, len(platforms) - 1))
        event_count += 1

    conn.commit()
    return event_count


def main():
    parser = argparse.ArgumentParser(description='跨平台事件聚合')
    parser.add_argument('--db', default='data/trendradar.db')
    parser.add_argument('--threshold', type=float, default=0.45)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    items = fetch_all_items(conn)
    print(f"加载 {len(items)} 条（news + rss）")
    clusters = cluster_events(items, threshold=args.threshold)
    print(f"聚合到 {len(clusters)} 个事件簇（≥2 平台）")

    # 打印前 5 个簇预览
    for i, cluster in enumerate(clusters[:5]):
        print(f"\n[Event {i+1}] {len(cluster)} 条，{len({items[j][3] for j in cluster})} 平台")
        for idx in cluster[:5]:
            print(f"  - [{items[idx][3]}] {items[idx][2][:60]}")

    n = write_events(conn, items, clusters)
    print(f"\n写入 {n} 条事件到 ai_events + news_event_map")
    conn.close()


if __name__ == '__main__':
    main()
