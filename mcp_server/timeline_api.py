# coding=utf-8
"""
Timeline API 扩展模块

为 TrendRadar 提供 AI Timeline 相关的 API 端点和静态资源服务
可嵌入 HTTP 模式的 MCP 服务器或独立运行
"""

import json
import sqlite3
import os
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles


# 创建 APIRouter
router = APIRouter(prefix="/api/timeline", tags=["timeline"])


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
            
            news_list.append({
                'id': row['id'],
                'title': row['title'],
                'platform_name': row['platform_name'] or 'Unknown',
                'rank': row['rank'],
                'url': row['url'] or '',
                'first_crawl_time': row['first_crawl_time'],
                'last_crawl_time': row['last_crawl_time'],
                'crawl_count': row['crawl_count'] or 1,
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
    limit: int = Query(default=50, ge=1, le=200),
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
    
    args = parser.parse_args()
    
    app = create_timeline_app(args.db)
    
    print(f"[Timeline API] 启动服务：http://{args.host}:{args.port}")
    print("  GET  /api/timeline/news    - 获取新闻列表")
    print("  GET  /api/timeline/tags    - 获取标签列表")
    print("  GET  /api/timeline/stats   - 获取统计数据")
    print("  POST /api/timeline/bookmark/:id - 切换收藏")
    
    uvicorn.run(app, host=args.host, port=args.port)
