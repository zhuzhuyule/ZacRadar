# coding=utf-8
"""
TrendRadar Timeline 服务

提供 AI Timeline 前端所需的 API 接口
可作为独立模块运行，也可嵌入主服务
"""

import json
import sqlite3
import threading
from dataclasses import asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse


class TimelineDataLoader:
    """Timeline 数据读取器"""
    
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
    ) -> List[Dict]:
        """
        获取新闻列表
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            filter_type: 筛选类型 (featured/all/bookmarks)
            tag: 标签筛选
            search_query: 搜索关键词
            
        Returns:
            List[Dict]: 新闻列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        base_query = """
            SELECT * FROM v_news_full
            WHERE 1=1
        """
        
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
        
        cursor.execute("""
            SELECT DISTINCT tag
            FROM news_ai_tags
            ORDER BY tag
        """)
        
        tags = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return tags
    
    def toggle_bookmark(self, news_id: int, user_id: str = 'default') -> bool:
        """切换收藏状态"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id FROM user_bookmarks
            WHERE news_item_id = ? AND user_id = ?
        """, (news_id, user_id))
        
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("""
                DELETE FROM user_bookmarks
                WHERE news_item_id = ? AND user_id = ?
            """, (news_id, user_id))
            is_bookmarked = False
        else:
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


class TimelineAPIHandler(BaseHTTPRequestHandler):
    """Timeline API HTTP 处理器"""
    
    loader: Optional[TimelineDataLoader] = None
    
    def do_GET(self):
        """处理 GET 请求"""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        if path == '/api/news':
            limit = int(query.get('limit', [50])[0])
            offset = int(query.get('offset', [0])[0])
            filter_type = query.get('filter', ['featured'])[0]
            tag = query.get('tag', [None])[0]
            search = query.get('search', [None])[0]
            
            news = self.loader.get_news(
                limit=limit,
                offset=offset,
                filter_type=filter_type,
                tag=tag,
                search_query=search
            )
            self.send_json_response(news)
        
        elif path == '/api/tags':
            tags = self.loader.get_all_tags()
            self.send_json_response(tags)
        
        elif path == '/api/stats':
            stats = self.loader.get_statistics()
            self.send_json_response(stats)
        
        else:
            self.send_error(404, 'Not Found')
    
    def do_POST(self):
        """处理 POST 请求"""
        if self.path.startswith('/api/bookmark/'):
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
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[Timeline API] {args[0]}")


class TimelineServer:
    """
    Timeline 服务管理器
    
    可独立运行或嵌入主服务
    """
    
    def __init__(self, db_path: str, host: str = '0.0.0.0', port: int = 8001):
        """
        初始化服务
        
        Args:
            db_path: SQLite 数据库路径
            host: 监听地址
            port: 监听端口
        """
        self.db_path = db_path
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
    
    def start(self, blocking: bool = True):
        """
        启动服务
        
        Args:
            blocking: 是否阻塞运行
        """
        TimelineAPIHandler.loader = TimelineDataLoader(self.db_path)
        
        self.server = HTTPServer((self.host, self.port), TimelineAPIHandler)
        
        print(f"[Timeline Server] 启动服务：http://{self.host}:{self.port}")
        print("  GET  /api/news    - 获取新闻列表")
        print("  GET  /api/tags    - 获取标签列表")
        print("  GET  /api/stats   - 获取统计数据")
        print("  POST /api/bookmark/:id - 切换收藏")
        
        if blocking:
            self.server.serve_forever()
        else:
            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.daemon = True
            self.thread.start()
    
    def stop(self):
        """停止服务"""
        if self.server:
            self.server.shutdown()
            self.server = None
        if self.thread:
            self.thread.join()
            self.thread = None


def create_timeline_server(db_path: Optional[str] = None, host: str = '0.0.0.0', port: int = 8001) -> TimelineServer:
    """
    创建 Timeline 服务实例
    
    Args:
        db_path: 数据库路径（默认：data/trendradar.db）
        host: 监听地址
        port: 监听端口
        
    Returns:
        TimelineServer 实例
    """
    if db_path is None:
        # 尝试常见路径
        possible_paths = [
            'data/trendradar.db',
            Path(__file__).parent.parent / 'data' / 'trendradar.db',
            Path.cwd() / 'data' / 'trendradar.db',
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                db_path = str(path)
                break
        
        if db_path is None:
            raise FileNotFoundError("未找到数据库文件，请指定 db_path")
    
    return TimelineServer(db_path, host, port)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='TrendRadar Timeline Server')
    parser.add_argument('--db', type=str, default='data/trendradar.db', help='数据库路径')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8001, help='监听端口')
    
    args = parser.parse_args()
    
    try:
        server = create_timeline_server(args.db, args.host, args.port)
        server.start(blocking=True)
    except KeyboardInterrupt:
        print("\n[Timeline Server] 服务已停止")
