# coding=utf-8
"""
Timeline 数据读取层

从 SQLite 数据库读取 AI 分析结果，提供 API 接口
"""

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class NewsItem:
    """新闻数据项（包含 AI 分析结果）"""
    id: int
    title: str
    platform_name: str
    rank: int
    url: str
    first_crawl_time: str
    last_crawl_time: str
    crawl_count: int
    ai_tags: List[str]
    ai_heat_score: int
    ai_reason: str
    event_id: Optional[int]
    related_count: int
    is_bookmarked: bool


class TimelineDataLoader:
    """
    Timeline 数据读取器
    
    从 TrendRadar SQLite 数据库读取 AI 分析结果
    """
    
    def __init__(self, db_path: str):
        """
        初始化数据读取器
        
        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = db_path
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """确保数据库文件存在"""
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
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
    ) -> List[NewsItem]:
        """
        获取新闻列表
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            filter_type: 筛选类型 (featured/all/bookmarks)
            tag: 标签筛选
            search_query: 搜索关键词
            
        Returns:
            List[NewsItem]: 新闻列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 构建查询
        base_query = """
            SELECT * FROM v_news_full
            WHERE 1=1
        """
        
        params = []
        
        # 按筛选类型过滤
        if filter_type == 'featured':
            base_query += " AND ai_heat_score >= 80"
        elif filter_type == 'bookmarks':
            base_query += " AND is_bookmarked = 1"
        
        # 按标签过滤
        if tag:
            base_query += " AND ai_tags LIKE ?"
            params.append(f'%{tag}%')
        
        # 按搜索关键词过滤
        if search_query:
            base_query += " AND (title LIKE ? OR ai_reason LIKE ?)"
            search_pattern = f'%{search_query}%'
            params.extend([search_pattern, search_pattern])
        
        # 排序和分页
        base_query += " ORDER BY first_crawl_time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # 执行查询
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # 转换为 NewsItem 对象
        news_list = []
        for row in rows:
            # 解析 AI 标签（JSON 数组）
            ai_tags = []
            if row['ai_tags']:
                try:
                    ai_tags = json.loads(row['ai_tags'])
                except:
                    ai_tags = []
            
            news_list.append(NewsItem(
                id=row['id'],
                title=row['title'],
                platform_name=row['platform_name'] or 'Unknown',
                rank=row['rank'],
                url=row['url'] or '',
                first_crawl_time=row['first_crawl_time'],
                last_crawl_time=row['last_crawl_time'],
                crawl_count=row['crawl_count'] or 1,
                ai_tags=ai_tags,
                ai_heat_score=row['ai_heat_score'] or 0,
                ai_reason=row['ai_reason'] or '',
                event_id=row['event_id'],
                related_count=row['related_count'] or 0,
                is_bookmarked=bool(row['is_bookmarked']),
            ))
        
        return news_list
    
    def get_all_tags(self) -> List[str]:
        """获取所有标签"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT tag
            FROM news_ai_tags
            ORDER BY tag
        """)
        
        tags = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return tags
    
    def get_all_sources(self) -> List[str]:
        """获取所有数据来源"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT name
            FROM platforms
            WHERE is_active = 1
            ORDER BY name
        """)
        
        sources = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return sources
    
    def toggle_bookmark(self, news_id: int, user_id: str = 'default') -> bool:
        """
        切换收藏状态
        
        Args:
            news_id: 新闻 ID
            user_id: 用户 ID（预留多用户支持）
            
        Returns:
            bool: 新的收藏状态
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 检查是否已收藏
        cursor.execute("""
            SELECT id FROM user_bookmarks
            WHERE news_item_id = ? AND user_id = ?
        """, (news_id, user_id))
        
        existing = cursor.fetchone()
        
        if existing:
            # 取消收藏
            cursor.execute("""
                DELETE FROM user_bookmarks
                WHERE news_item_id = ? AND user_id = ?
            """, (news_id, user_id))
            is_bookmarked = False
        else:
            # 添加收藏
            cursor.execute("""
                INSERT INTO user_bookmarks (news_item_id, user_id)
                VALUES (?, ?)
            """, (news_id, user_id))
            is_bookmarked = True
        
        conn.commit()
        conn.close()
        
        return is_bookmarked
    
    def get_statistics(self) -> Dict:
        """获取统计数据"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # 总新闻数
        cursor.execute("SELECT COUNT(*) FROM news_items")
        stats['total_news'] = cursor.fetchone()[0]
        
        # 已分析新闻数
        cursor.execute("SELECT COUNT(DISTINCT news_item_id) FROM news_ai_tags")
        stats['analyzed_news'] = cursor.fetchone()[0]
        
        # 标签总数
        cursor.execute("SELECT COUNT(DISTINCT tag) FROM news_ai_tags")
        stats['total_tags'] = cursor.fetchone()[0]
        
        # 事件总数
        cursor.execute("SELECT COUNT(*) FROM ai_events")
        stats['total_events'] = cursor.fetchone()[0]
        
        # 收藏总数
        cursor.execute("SELECT COUNT(*) FROM user_bookmarks")
        stats['total_bookmarks'] = cursor.fetchone()[0]
        
        conn.close()
        
        return stats
    
    def search_news(self, query: str, limit: int = 20) -> List[NewsItem]:
        """
        搜索新闻
        
        Args:
            query: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            List[NewsItem]: 搜索结果
        """
        return self.get_news(
            limit=limit,
            search_query=query
        )


# 简单的 HTTP API 服务器（用于开发测试）
if __name__ == '__main__':
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json
    
    class TimelineAPIHandler(BaseHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            self.loader = TimelineDataLoader('data/trendradar.db')
            super().__init__(*args, **kwargs)
        
        def do_GET(self):
            """处理 GET 请求"""
            path = self.path
            
            if path == '/api/news':
                # 获取新闻列表
                news = self.loader.get_news()
                self.send_json_response([asdict(n) for n in news])
            
            elif path == '/api/tags':
                # 获取标签列表
                tags = self.loader.get_all_tags()
                self.send_json_response(tags)
            
            elif path == '/api/sources':
                # 获取来源列表
                sources = self.loader.get_all_sources()
                self.send_json_response(sources)
            
            elif path == '/api/stats':
                # 获取统计数据
                stats = self.loader.get_statistics()
                self.send_json_response(stats)
            
            else:
                self.send_error(404, 'Not Found')
        
        def do_POST(self):
            """处理 POST 请求"""
            if self.path.startswith('/api/bookmark/'):
                # 切换收藏
                news_id = int(self.path.split('/')[-1])
                content_length = int(self.headers['Content-Length'])
                post_data = json.loads(self.rfile.read(content_length))
                user_id = post_data.get('user_id', 'default')
                
                is_bookmarked = self.loader.toggle_bookmark(news_id, user_id)
                self.send_json_response({'is_bookmarked': is_bookmarked})
            else:
                self.send_error(404, 'Not Found')
        
        def send_json_response(self, data):
            """发送 JSON 响应"""
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
        
        def do_OPTIONS(self):
            """处理 CORS 预检请求"""
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
    
    # 启动服务器
    port = 8001
    server = HTTPServer(('localhost', port), TimelineAPIHandler)
    print(f"Timeline API Server running at http://localhost:{port}")
    print("Endpoints:")
    print("  GET  /api/news    - 获取新闻列表")
    print("  GET  /api/tags    - 获取标签列表")
    print("  GET  /api/sources - 获取来源列表")
    print("  GET  /api/stats   - 获取统计数据")
    print("  POST /api/bookmark/:id - 切换收藏")
    server.serve_forever()
