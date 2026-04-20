#!/usr/bin/env python3
# coding=utf-8
"""
简易 API 服务器 - 不依赖 TrendRadar 模块
"""

import sqlite3
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

DB_PATH = 'data/trendradar.db'

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_news(limit=50, offset=0, filter_type='featured', tag=None, search_query=None):
    conn = get_connection()
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
        base_query += " AND (title LIKE ? OR ai_reason LIKE ? OR ai_tags LIKE ?)"
        sq = f'%{search_query}%'
        params.extend([sq, sq, sq])
    
    base_query += " ORDER BY first_crawl_time DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(base_query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_all_tags():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT tag FROM news_ai_tags ORDER BY tag")
    tags = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tags

def get_all_sources():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT platform_name FROM v_news_full ORDER BY platform_name")
    sources = [row[0] for row in cursor.fetchall()]
    conn.close()
    return sources

def get_statistics():
    conn = get_connection()
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

class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/news':
            news = get_news()
            self.send_json_response(news)
        elif self.path == '/api/tags':
            tags = get_all_tags()
            self.send_json_response(tags)
        elif self.path == '/api/sources':
            sources = get_all_sources()
            self.send_json_response(sources)
        elif self.path == '/api/stats':
            stats = get_statistics()
            self.send_json_response(stats)
        else:
            self.send_error(404, 'Not Found')
    
    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        pass  # 静默日志

if __name__ == '__main__':
    port = 8001
    server = HTTPServer(('localhost', port), APIHandler)
    print(f"✅ API Server running at http://localhost:{port}")
    print("Endpoints:")
    print("  GET /api/news    - 获取新闻列表")
    print("  GET /api/tags    - 获取标签列表")
    print("  GET /api/sources - 获取来源列表")
    print("  GET /api/stats   - 获取统计数据")
    print("Press Ctrl+C to stop")
    server.serve_forever()
