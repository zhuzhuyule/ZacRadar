# coding=utf-8
"""
Timeline API 扩展模块

为 TrendRadar 提供 AI Timeline 相关的 API 端点和静态资源服务
可嵌入 HTTP 模式的 MCP 服务器或独立运行
"""

import asyncio
import json
import sqlite3
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles


# 创建 APIRouter
router = APIRouter(prefix="/api/timeline", tags=["timeline"])


# 平台分类映射（按内容属性聚合）
PLATFORM_CATEGORY: Dict[str, str] = {
    'toutiao': '综合资讯',
    'baidu': '综合资讯',
    'ifeng': '综合资讯',
    'thepaper': '综合资讯',
    'zhihu': '社区问答',
    'tieba': '社区问答',
    'weibo': '社交热搜',
    'douyin': '短视频',
    'bilibili-hot-search': '短视频',
    'wallstreetcn-hot': '财经',
    'cls-hot': '财经',
}

# 平台品牌色（前端未传色时使用）
PLATFORM_COLOR: Dict[str, str] = {
    'toutiao': '#FA2A2D',
    'baidu': '#2932E1',
    'ifeng': '#C4161C',
    'thepaper': '#003D7C',
    'zhihu': '#056DE8',
    'tieba': '#4E6EF2',
    'weibo': '#E6162D',
    'douyin': '#FE2C55',
    'bilibili-hot-search': '#FB7299',
    'wallstreetcn-hot': '#DB241E',
    'cls-hot': '#E74C3C',
    # RSS 源（feed_id → color / category）
    'rss:hacker-news': '#FF6600',
    'rss:yahoo-finance': '#720E9E',
}

RSS_CATEGORY: Dict[str, str] = {
    'hacker-news': '海外科技',
    'yahoo-finance': '海外财经',
}


# 平台权威权重（影响 personal_score）
PLATFORM_WEIGHT: Dict[str, float] = {
    'thepaper': 1.2,
    'wallstreetcn-hot': 1.2,
    'cls-hot': 1.2,
    'zhihu': 1.1,
    'toutiao': 1.0,
    'baidu': 1.0,
    'ifeng': 1.0,
    'weibo': 0.95,
    'bilibili-hot-search': 0.85,
    'tieba': 0.8,
    'douyin': 0.8,
    'rss:hacker-news': 1.15,
    'rss:yahoo-finance': 1.1,
}


def compute_personal_score(
    relevance: float, heat: int, related: int, platform_weight: float
) -> float:
    """统一打分公式（见设计文档）"""
    return (
        0.6 * relevance * 100
        + 0.15 * heat
        + 0.15 * min(related * 15, 100)
        + 0.10 * platform_weight * 100
    )


def is_breakthrough(heat: int, related: int) -> bool:
    """兜底：全网级 breaking — 即使兴趣 0 分也放行"""
    return heat >= 90 and related >= 3


class TimelineDataService:
    """Timeline 数据服务"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        if not Path(db_path).exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_news(
        self,
        limit: int = 50,
        offset: int = 0,
        filter_type: str = 'featured',
        tag: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[Dict]:
        """获取新闻列表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        base_query = "SELECT * FROM v_news_full WHERE 1=1"
        params = []
        
        if filter_type == 'featured':
            base_query += " AND ai_heat_score >= 80"
        elif filter_type == 'bookmarks':
            base_query += " AND is_bookmarked = 1"
        
        if tag:
            base_query += " AND ai_tags LIKE ?"
            params.append(f'%{tag}%')
        
        if search_query:
            base_query += " AND (title LIKE ? OR ai_reason LIKE ?)"
            search_pattern = f'%{search_query}%'
            params.extend([search_pattern, search_pattern])
        
        base_query += " ORDER BY first_crawl_time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        conn.close()
        
        news_list = []
        for row in rows:
            ai_tags = []
            if row['ai_tags']:
                try:
                    ai_tags = json.loads(row['ai_tags'])
                except:
                    ai_tags = []
            
            keys = row.keys()
            news_list.append({
                'id': row['id'],
                'title': row['title'],
                'title_zh': (row['title_zh'] if 'title_zh' in keys else '') or '',
                'platform_id': row['platform_id'],
                'platform_name': row['platform_name'] or 'Unknown',
                'platform_category': PLATFORM_CATEGORY.get(row['platform_id'], '其它'),
                'rank': row['rank'],
                'url': row['url'] or '',
                'mobile_url': row['mobile_url'] or '',
                'first_crawl_time': row['first_crawl_time'],
                'last_crawl_time': row['last_crawl_time'],
                'crawl_count': row['crawl_count'] or 1,
                # 上游元数据
                'description': (row['description'] if 'description' in keys else '') or '',
                'hot_value': (row['hot_value'] if 'hot_value' in keys else '') or '',
                'icon_url': (row['icon_url'] if 'icon_url' in keys else '') or '',
                'upstream_id': (row['upstream_id'] if 'upstream_id' in keys else '') or '',
                'source_updated_ts': (row['source_updated_ts'] if 'source_updated_ts' in keys else 0) or 0,
                # AI 分析
                'ai_tags': ai_tags,
                'ai_heat_score': row['ai_heat_score'] or 0,
                'ai_reason': row['ai_reason'] or '',
                'event_id': row['event_id'],
                'related_count': row['related_count'] or 0,
                'is_bookmarked': bool(row['is_bookmarked']),
            })
        
        return news_list
    
    def get_all_tags(self) -> List[str]:
        """获取所有标签"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT tag FROM news_ai_tags ORDER BY tag")
        tags = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tags
    
    def toggle_bookmark(self, news_id: int, user_id: str = 'default') -> bool:
        """切换收藏状态"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM user_bookmarks WHERE news_item_id = ? AND user_id = ?", (news_id, user_id))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("DELETE FROM user_bookmarks WHERE news_item_id = ? AND user_id = ?", (news_id, user_id))
            is_bookmarked = False
        else:
            cursor.execute("INSERT INTO user_bookmarks (news_item_id, user_id) VALUES (?, ?)", (news_id, user_id))
            is_bookmarked = True
        
        conn.commit()
        conn.close()
        return is_bookmarked
    
    def get_events(self) -> List[Dict]:
        """获取所有跨平台事件 + 聚合统计"""
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT
                    e.id AS event_id,
                    e.event_name,
                    COALESCE(e.event_summary, e.event_name) AS summary,
                    COUNT(m.news_item_id) AS news_count,
                    GROUP_CONCAT(DISTINCT p.name) AS platform_names,
                    GROUP_CONCAT(DISTINCT p.id) AS platform_ids,
                    MAX(COALESCE(heat.max_heat, 0)) AS heat,
                    r.title AS rep_title,
                    r.url AS rep_url
                FROM ai_events e
                LEFT JOIN news_event_map m ON m.event_id = e.id
                LEFT JOIN news_items n ON n.id = m.news_item_id
                LEFT JOIN platforms p ON p.id = n.platform_id
                LEFT JOIN (
                    SELECT news_item_id, MAX(heat_score) AS max_heat
                    FROM news_ai_tags GROUP BY news_item_id
                ) heat ON heat.news_item_id = m.news_item_id
                LEFT JOIN news_items r ON r.id = e.representative_news_id
                GROUP BY e.id
                ORDER BY news_count DESC, heat DESC
            """)
            rows = cur.fetchall()
        except sqlite3.OperationalError:
            rows = []
        conn.close()

        out = []
        for r in rows:
            platforms = [x for x in (r['platform_names'] or '').split(',') if x]
            platform_ids = [x for x in (r['platform_ids'] or '').split(',') if x]
            out.append({
                'event_id': r['event_id'],
                'event_name': r['event_name'],
                'summary': r['summary'] or '',
                'news_count': r['news_count'] or 0,
                'platforms': platforms,
                'platform_ids': platform_ids,
                'heat': int(r['heat'] or 0),
                'rising': (r['heat'] or 0) >= 85,
                'rep_title': r['rep_title'] or '',
                'rep_url': r['rep_url'] or '',
            })
        return out

    def get_interests(self) -> List[Dict]:
        """获取兴趣方向 + 各方向命中数 + 平均相关度"""
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT
                    t.id, t.tag, t.description, t.priority,
                    COUNT(r.id) AS hits,
                    COALESCE(AVG(r.relevance_score), 0) AS avg_score
                FROM ai_filter_tags t
                LEFT JOIN ai_filter_results r ON r.tag_id = t.id AND r.status='active'
                WHERE t.status='active'
                GROUP BY t.id
                ORDER BY t.priority
            """)
            rows = cur.fetchall()
        except sqlite3.OperationalError:
            rows = []
        conn.close()
        return [
            {
                'id': r['id'],
                'tag': r['tag'],
                'description': r['description'] or '',
                'priority': r['priority'],
                'hits': r['hits'] or 0,
                'avg_score': round(r['avg_score'] or 0, 2),
            }
            for r in rows
        ]

    def get_feed(
        self,
        min_relevance: float = 0.3,
        include_breakthrough: bool = True,
        limit: int = 200,
    ) -> List[Dict]:
        """
        我的关注 feed：按 personal_score 排序
        包含: 兴趣命中（relevance ≥ min_relevance）+ 兜底放行（heat≥90 且 related≥3）
        """
        # 复用 get_news 拿全部 news_items（无论是否命中），再合并 ai_filter_results
        all_news = self.get_news(limit=10000, offset=0, filter_type='all')
        all_rss = self.get_rss(limit=1000)

        conn = self._get_connection()
        cur = conn.cursor()
        # 一次拉所有 active relevance
        try:
            cur.execute("""
                SELECT r.news_item_id, r.source_type, r.tag_id, r.relevance_score, t.tag, t.priority
                FROM ai_filter_results r
                JOIN ai_filter_tags t ON t.id = r.tag_id
                WHERE r.status='active' AND t.status='active'
            """)
            rel_rows = cur.fetchall()
        except sqlite3.OperationalError:
            rel_rows = []
        conn.close()

        # key: (source_type, news_item_id) → list of {tag, relevance, priority}
        rel_map: Dict[Tuple[str, int], List[Dict]] = {}
        for r in rel_rows:
            key = (r['source_type'], r['news_item_id'])
            rel_map.setdefault(key, []).append({
                'tag': r['tag'],
                'relevance': r['relevance_score'],
                'priority': r['priority'],
            })

        # 合并 news + rss
        items = []
        for n in all_news:
            n['_source_type'] = 'hotlist'
            n['_native_id'] = n['id']
            items.append(n)
        for r in all_rss:
            r['_source_type'] = 'rss'
            r['_native_id'] = r['id'] - 10_000_000  # 还原 RSS native id
            items.append(r)

        feed = []
        for it in items:
            key = (it['_source_type'], it['_native_id'])
            matches = rel_map.get(key, [])
            best = max(matches, key=lambda x: x['relevance'], default=None)
            best_relevance = best['relevance'] if best else 0.0
            heat = it.get('ai_heat_score') or 0
            related = it.get('related_count') or 0
            pw = PLATFORM_WEIGHT.get(it['platform_id'], 1.0)

            # 入选条件
            qualified = (best_relevance >= min_relevance) or (
                include_breakthrough and is_breakthrough(heat, related)
            )
            if not qualified:
                continue

            score = compute_personal_score(best_relevance, heat, related, pw)
            it_out = {**it}
            it_out.pop('_source_type', None)
            it_out.pop('_native_id', None)
            it_out['relevance_score'] = round(best_relevance, 2)
            it_out['matched_interests'] = sorted(
                [{'tag': m['tag'], 'relevance': round(m['relevance'], 2), 'priority': m['priority']}
                 for m in matches if m['relevance'] >= min_relevance],
                key=lambda x: -x['relevance'],
            )[:3]
            it_out['personal_score'] = round(score, 1)
            it_out['is_breakthrough'] = best_relevance < min_relevance and is_breakthrough(heat, related)
            it_out['primary_interest'] = (best['tag'] if best and best['relevance'] >= min_relevance else '')
            feed.append(it_out)

        feed.sort(key=lambda x: -x['personal_score'])
        return feed[:limit]

    def get_platforms(self) -> List[Dict]:
        """获取各平台聚合信息（含最新的 source_updated_ts），含 RSS 源"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                p.id,
                p.name,
                COUNT(ni.id) AS news_count,
                MAX(ni.source_updated_ts) AS latest_updated_ts,
                MAX(ni.last_crawl_time) AS latest_crawl_time
            FROM platforms p
            LEFT JOIN news_items ni ON ni.platform_id = p.id
            GROUP BY p.id, p.name
        """)
        platforms = [
            {
                'id': r['id'],
                'name': r['name'],
                'category': PLATFORM_CATEGORY.get(r['id'], '其它'),
                'color': PLATFORM_COLOR.get(r['id'], '#6B7280'),
                'news_count': r['news_count'] or 0,
                'latest_updated_ts': r['latest_updated_ts'] or 0,
                'latest_crawl_time': r['latest_crawl_time'] or '',
            }
            for r in cursor.fetchall()
        ]

        # RSS 源合并（若表存在）
        try:
            cursor.execute("""
                SELECT
                    f.id,
                    f.name,
                    COUNT(r.id) AS item_count,
                    MAX(r.published_at) AS latest_published_at,
                    MAX(r.last_crawl_time) AS latest_crawl_time
                FROM rss_feeds f
                LEFT JOIN rss_items r ON r.feed_id = f.id
                GROUP BY f.id, f.name
            """)
            for r in cursor.fetchall():
                pid = f"rss:{r['id']}"
                # published_at 是 ISO 字符串，转 ms
                latest_ts = 0
                if r['latest_published_at']:
                    try:
                        from datetime import datetime
                        latest_ts = int(datetime.fromisoformat(r['latest_published_at']).timestamp() * 1000)
                    except Exception:
                        latest_ts = 0
                platforms.append({
                    'id': pid,
                    'name': r['name'],
                    'category': RSS_CATEGORY.get(r['id'], 'RSS'),
                    'color': PLATFORM_COLOR.get(pid, '#6366F1'),
                    'news_count': r['item_count'] or 0,
                    'latest_updated_ts': latest_ts,
                    'latest_crawl_time': r['latest_crawl_time'] or '',
                })
        except sqlite3.OperationalError:
            pass  # 无 RSS 表

        conn.close()
        platforms.sort(key=lambda p: p['news_count'], reverse=True)
        return platforms

    def get_rss(self, limit: int = 100) -> List[Dict]:
        """获取 RSS 条目（转成 NewsItem 形状）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    r.id,
                    r.title,
                    COALESCE(r.title_zh, '') AS title_zh,
                    r.feed_id,
                    f.name AS feed_name,
                    r.url,
                    r.published_at,
                    r.summary,
                    r.author,
                    r.first_crawl_time,
                    r.last_crawl_time
                FROM rss_items r
                LEFT JOIN rss_feeds f ON f.id = r.feed_id
                ORDER BY r.published_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            conn.close()
            return []
        conn.close()

        from datetime import datetime
        items = []
        for idx, r in enumerate(rows, 1):
            pid = f"rss:{r['feed_id']}"
            ts = 0
            if r['published_at']:
                try:
                    ts = int(datetime.fromisoformat(r['published_at']).timestamp() * 1000)
                except Exception:
                    ts = 0
            # Description：截断 summary 的 URL 前缀（HN 的 summary 以 "Article URL: ..." 开头）
            summary = (r['summary'] or '').strip()
            items.append({
                'id': 10_000_000 + (r['id'] or 0),  # 避开 news_items ID 空间
                'title': r['title'],
                'title_zh': r['title_zh'] or '',
                'platform_id': pid,
                'platform_name': r['feed_name'] or r['feed_id'],
                'platform_category': RSS_CATEGORY.get(r['feed_id'], 'RSS'),
                'rank': idx,
                'url': r['url'] or '',
                'mobile_url': '',
                'first_crawl_time': r['first_crawl_time'] or '',
                'last_crawl_time': r['last_crawl_time'] or '',
                'crawl_count': 1,
                'description': summary,
                'hot_value': '',
                'icon_url': '',
                'upstream_id': '',
                'source_updated_ts': ts,
                'ai_tags': [],
                'ai_heat_score': 0,
                'ai_reason': r['author'] or '',
                'event_id': None,
                'related_count': 0,
                'is_bookmarked': False,
            })
        return items

    def get_statistics(self) -> Dict:
        """获取统计数据"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        cursor.execute("SELECT COUNT(*) FROM news_items")
        stats['total_news'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT news_item_id) FROM news_ai_tags")
        stats['analyzed_news'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT tag) FROM news_ai_tags")
        stats['total_tags'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ai_events")
        stats['total_events'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_bookmarks")
        stats['total_bookmarks'] = cursor.fetchone()[0]
        
        conn.close()
        return stats


# 全局服务实例（延迟初始化）
_service: Optional[TimelineDataService] = None


def get_service() -> TimelineDataService:
    """获取服务实例"""
    global _service
    if _service is None:
        # 尝试常见路径
        possible_paths = [
            'data/trendradar.db',
            Path(__file__).parent.parent / 'data' / 'trendradar.db',
            Path.cwd() / 'data' / 'trendradar.db',
        ]
        
        db_path = None
        for path in possible_paths:
            if Path(path).exists():
                db_path = str(path)
                break
        
        if db_path is None:
            raise FileNotFoundError("未找到数据库文件")
        
        _service = TimelineDataService(db_path)
    
    return _service


@router.get("/news")
async def get_news(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    filter: str = Query(default='featured', regex='^(featured|all|bookmarks)$'),
    tag: Optional[str] = None,
    search: Optional[str] = None,
):
    """获取 AI Timeline 新闻列表"""
    try:
        service = get_service()
        news = service.get_news(limit=limit, offset=offset, filter_type=filter, tag=tag, search_query=search)
        return {"success": True, "data": news, "total": len(news)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags")
async def get_tags():
    """获取所有 AI 标签"""
    try:
        service = get_service()
        tags = service.get_all_tags()
        return {"success": True, "data": tags, "total": len(tags)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """获取统计数据"""
    try:
        service = get_service()
        stats = service.get_statistics()
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _db_signal() -> str:
    """
    返回 news_items 的「变化指纹」—— 最新 updated_at + 行数。
    任一新增或更新都会让该字符串变化。
    `last_crawl_time` 是 HH-MM 短文本，分钟内不会变化，不适合做信号。
    """
    try:
        service = get_service()
        with sqlite3.connect(service.db_path) as conn:
            cur = conn.execute(
                "SELECT COALESCE(MAX(updated_at), ''), COUNT(*) FROM news_items"
            )
            mtime, count = cur.fetchone()
            return f"{mtime}|{count}"
    except Exception:
        return ''


_crawl_lock = asyncio.Lock()
_crawl_state: Dict[str, object] = {"running": False, "started_at": 0.0, "finished_at": 0.0, "rc": None, "tail": ""}


async def _run_crawl_subprocess():
    import time
    project_root = Path(__file__).resolve().parent.parent
    _crawl_state.update({"running": True, "started_at": time.time(), "finished_at": 0.0, "rc": None, "tail": ""})
    try:
        proc = await asyncio.create_subprocess_exec(
            "python", "-m", "trendradar",
            cwd=str(project_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        tail = (stdout or b"").decode("utf-8", errors="replace")[-2000:]
        _crawl_state.update({"rc": proc.returncode, "tail": tail})
    except Exception as e:
        _crawl_state.update({"rc": -1, "tail": f"spawn failed: {e}"})
    finally:
        _crawl_state.update({"running": False, "finished_at": time.time()})


@router.post("/crawl")
async def trigger_crawl():
    """开发模式：强制触发一次 `python -m trendradar` 抓取。"""
    if _crawl_state.get("running"):
        return {"success": False, "status": "running", "state": _crawl_state}
    async with _crawl_lock:
        if _crawl_state.get("running"):
            return {"success": False, "status": "running", "state": _crawl_state}
        asyncio.create_task(_run_crawl_subprocess())
    return {"success": True, "status": "started"}


@router.get("/crawl/status")
async def crawl_status():
    """查询上次/当前抓取的状态。"""
    return {"success": True, "data": _crawl_state}


@router.get("/stream")
async def stream_updates(request: Request):
    """
    SSE：当 news_items 出现新抓取写入时，推送 `event: update`。
    客户端用 EventSource 订阅即可；每 25 秒发一次心跳防代理掐线。
    """
    async def gen():
        last = _db_signal()
        yield f"event: hello\ndata: {json.dumps({'signal': last})}\n\n"
        tick = 0
        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(5)
            tick += 5
            try:
                cur_sig = _db_signal()
                if cur_sig and cur_sig != last:
                    last = cur_sig
                    yield f"event: update\ndata: {json.dumps({'signal': cur_sig})}\n\n"
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'msg': str(e)})}\n\n"
            if tick >= 25:
                tick = 0
                yield f"event: ping\ndata: {{}}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/feed")
async def get_feed(
    min_relevance: float = Query(default=0.3, ge=0.0, le=1.0),
    include_breakthrough: bool = Query(default=True),
    limit: int = Query(default=300, ge=1, le=1000),
):
    """我的关注 feed：按 personal_score 排序"""
    try:
        service = get_service()
        items = service.get_feed(
            min_relevance=min_relevance,
            include_breakthrough=include_breakthrough,
            limit=limit,
        )
        return {"success": True, "data": items, "total": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
async def get_events():
    """跨平台事件列表"""
    try:
        service = get_service()
        return {"success": True, "data": service.get_events()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interests")
async def get_interests():
    """兴趣方向 + 命中数"""
    try:
        service = get_service()
        return {"success": True, "data": service.get_interests()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rss")
async def get_rss(limit: int = Query(default=100, ge=1, le=1000)):
    """获取 RSS 条目（形状与 /news 一致，platform_id 前缀 rss:）"""
    try:
        service = get_service()
        items = service.get_rss(limit=limit)
        return {"success": True, "data": items, "total": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platforms")
async def get_platforms():
    """获取所有平台的聚合统计（含分类、品牌色、最新更新时间）"""
    try:
        service = get_service()
        platforms = service.get_platforms()
        return {"success": True, "data": platforms, "total": len(platforms)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bookmark/{news_id}")
async def toggle_bookmark(news_id: int, user_id: str = "default"):
    """切换新闻收藏状态"""
    try:
        service = get_service()
        is_bookmarked = service.toggle_bookmark(news_id, user_id)
        return {"success": True, "data": {"news_id": news_id, "is_bookmarked": is_bookmarked}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def create_timeline_app(db_path: Optional[str] = None, serve_static: bool = False):
    """
    创建独立的 Timeline API 应用（用于开发测试）
    
    Args:
        db_path: 数据库路径（可选）
        serve_static: 是否提供静态资源（默认 False）
    
    Returns:
        FastAPI 应用实例
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(title="TrendRadar Timeline API")
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 如果指定了数据库路径，初始化服务
    global _service
    if db_path:
        _service = TimelineDataService(db_path)
    
    # 注册 API 路由
    app.include_router(router)
    
    # 提供静态资源（生产环境）
    if serve_static:
        static_path = Path(__file__).parent.parent / 'timeline_ui' / 'dist'
        if static_path.exists():
            app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
            print(f"[Timeline API] 静态资源目录：{static_path}")
        else:
            print(f"[Timeline API] 警告：静态资源目录不存在：{static_path}")
    
    return app


if __name__ == '__main__':
    import argparse
    import uvicorn
    
    parser = argparse.ArgumentParser(description='TrendRadar Timeline API Server')
    parser.add_argument('--db', type=str, default='data/trendradar.db', help='数据库路径')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8001, help='监听端口')
    parser.add_argument('--serve-static', action='store_true', help='提供静态资源（生产模式）')
    
    args = parser.parse_args()
    
    app = create_timeline_app(args.db, serve_static=args.serve_static)
    
    print(f"[Timeline API] 启动服务：http://{args.host}:{args.port}")
    print("  GET  /api/timeline/news    - 获取新闻列表")
    print("  GET  /api/timeline/tags    - 获取标签列表")
    print("  GET  /api/timeline/stats   - 获取统计数据")
    print("  POST /api/timeline/bookmark/:id - 切换收藏")
    
    uvicorn.run(app, host=args.host, port=args.port)
