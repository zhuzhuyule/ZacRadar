# coding=utf-8
"""
扩展 AI 分析器

将 AI 分析结果持久化到数据库，支持时间线展示
"""

import json
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from trendradar.ai.analyzer import AIAnalyzer, AIAnalysisResult
from trendradar.ai.client import AIClient


@dataclass
class NewsTagResult:
    """单条新闻的 AI 标签结果"""
    news_item_id: int
    title: str
    tags: List[str] = field(default_factory=list)
    heat_score: int = 0
    reason: str = ""


@dataclass 
class EventClusterResult:
    """事件聚类结果"""
    event_name: str
    event_summary: str
    news_ids: List[int] = field(default_factory=list)
    representative_news_id: Optional[int] = None
    related_count: int = 0


@dataclass
class ExtendedAIResult:
    """扩展 AI 分析结果（包含整体分析和单条新闻标签）"""
    # 整体分析结果
    analysis_result: AIAnalysisResult = field(default_factory=AIAnalysisResult)
    
    # 单条新闻的标签和评分
    news_tags: List[NewsTagResult] = field(default_factory=list)
    
    # 事件聚类结果
    events: List[EventClusterResult] = field(default_factory=list)
    
    # 执行元数据
    analysis_id: Optional[int] = None         # 数据库中的分析记录 ID
    duration_seconds: float = 0.0
    tokens_used: int = 0


class ExtendedAIAnalyzer:
    """
    扩展 AI 分析器
    
    在原有 AIAnalyzer 基础上，增加：
    1. 将整体分析结果保存到 ai_analysis_results 表
    2. 为单条新闻生成标签和评分，保存到 news_ai_tags 表
    3. 事件聚类，保存到 ai_events 表
    """
    
    def __init__(
        self,
        ai_config: Dict[str, Any],
        analysis_config: Dict[str, Any],
        db_path: str,
        get_time_func: Optional[Callable] = None,
        debug: bool = False,
    ):
        """
        初始化扩展 AI 分析器
        
        Args:
            ai_config: AI 模型配置（LiteLLM 格式）
            analysis_config: AI 分析功能配置
            db_path: SQLite 数据库路径
            get_time_func: 获取当前时间的函数
            debug: 是否开启调试模式
        """
        self.db_path = db_path
        self.ai_config = ai_config
        self.analysis_config = analysis_config
        self.debug = debug
        
        # 创建基础 AI 分析器
        self.analyzer = AIAnalyzer(
            ai_config=ai_config,
            analysis_config=analysis_config,
            get_time_func=get_time_func,
            debug=debug,
        )
        
        # 加载 AI 标签提取的 prompt
        self.tag_prompt = self._load_tag_prompt()
        
    def _load_tag_prompt(self) -> str:
        """加载标签提取 prompt"""
        return """
你是一名 AI 资讯标签提取助手。请为以下新闻提取 2-4 个关键词标签，并评分。

新闻标题：{title}
新闻摘要：{summary}
来源：{source}

请输出 JSON 格式：
{{
    "tags": ["标签 1", "标签 2", "标签 3"],
    "heat_score": 85,
    "reason": "推荐理由（50 字以内）"
}}

标签要求：
- 简洁明了（2-5 个字）
- 能准确概括新闻主题
- 避免过于宽泛的标签（如"新闻"、"热点"）

评分标准（0-100）：
- 90-100: 重大突破/影响深远
- 80-89: 重要进展/值得关注
- 70-79: 一般热点/有一定价值
- 60-69: 普通新闻/价值有限
- 0-59: 低质量/广告/营销
"""

    def analyze_and_save(
        self,
        stats: List[Dict],
        rss_stats: Optional[List[Dict]] = None,
        report_mode: str = "daily",
        report_type: str = "当日汇总",
        platforms: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        standalone_data: Optional[Dict] = None,
    ) -> ExtendedAIResult:
        """
        执行 AI 分析并保存到数据库
        
        Args:
            stats: 热榜统计数据
            rss_stats: RSS 统计数据
            report_mode: 报告模式
            report_type: 报告类型
            platforms: 平台列表
            keywords: 关键词列表
            
        Returns:
            ExtendedAIResult: 扩展分析结果
        """
        start_time = time.time()
        
        # 1. 创建分析历史记录
        history_id = self._create_analysis_history(len(stats))
        
        try:
            # 2. 执行原有 AI 分析（整体分析）
            print("[ExtendedAI] 开始执行整体 AI 分析...")
            analysis_result = self.analyzer.analyze(
                stats=stats,
                rss_stats=rss_stats,
                report_mode=report_mode,
                report_type=report_type,
                platforms=platforms,
                keywords=keywords,
                standalone_data=standalone_data,
            )
            
            # 3. 保存整体分析结果
            print("[ExtendedAI] 保存整体分析结果到数据库...")
            analysis_id = self._save_analysis_result(
                result=analysis_result,
                history_id=history_id,
            )
            
            # 4. 为单条新闻生成标签和评分
            print("[ExtendedAI] 为单条新闻生成标签和评分...")
            news_tags = self._extract_news_tags(stats, rss_stats)
            self._save_news_tags(news_tags)
            
            # 5. 事件聚类
            print("[ExtendedAI] 执行事件聚类...")
            events = self._cluster_events(stats, rss_stats)
            self._save_events(events)
            
            # 6. 更新分析历史记录
            duration = time.time() - start_time
            self._complete_analysis_history(
                history_id=history_id,
                status='success',
                duration=duration,
            )
            
            # 7. 返回结果
            result = ExtendedAIResult(
                analysis_result=analysis_result,
                news_tags=news_tags,
                events=events,
                analysis_id=analysis_id,
                duration_seconds=duration,
            )
            
            print(f"[ExtendedAI] ✅ AI 分析完成，耗时 {duration:.2f}秒")
            return result
            
        except Exception as e:
            # 记录失败
            self._complete_analysis_history(
                history_id=history_id,
                status='failed',
                error=str(e),
            )
            raise
    
    def _create_analysis_history(self, news_count: int) -> int:
        """创建分析历史记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ai_analysis_history (started_at, news_count, status)
            VALUES (?, ?, 'running')
        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), news_count))
        
        history_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return history_id
    
    def _complete_analysis_history(
        self,
        history_id: int,
        status: str,
        duration: float = 0,
        error: str = None,
    ):
        """完成分析历史记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE ai_analysis_history
            SET completed_at = ?,
                status = ?,
                duration_seconds = ?,
                error_message = ?
            WHERE id = ?
        """, (
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            status,
            duration,
            error,
            history_id,
        ))
        
        conn.commit()
        conn.close()
    
    def _save_analysis_result(
        self,
        result: AIAnalysisResult,
        history_id: int,
    ) -> int:
        """保存整体分析结果到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ai_analysis_results (
                analysis_date,
                core_trends,
                sentiment_controversy,
                signals,
                rss_insights,
                outlook_strategy,
                standalone_summaries,
                ai_model,
                news_count,
                mode,
                status,
                raw_response
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime('%Y-%m-%d'),
            result.core_trends,
            result.sentiment_controversy,
            result.signals,
            result.rss_insights,
            result.outlook_strategy,
            json.dumps(result.standalone_summaries, ensure_ascii=False),
            self.ai_config.get('MODEL', 'unknown'),
            result.total_news,
            result.ai_mode,
            'success' if result.success else 'failed',
            result.raw_response,
        ))
        
        analysis_id = cursor.lastrowid
        
        # 关联分析历史记录
        cursor.execute("""
            UPDATE ai_analysis_results
            SET analysis_history_id = ?
            WHERE id = ?
        """, (history_id, analysis_id))
        
        conn.commit()
        conn.close()
        
        return analysis_id
    
    def _extract_news_tags(
        self,
        stats: List[Dict],
        rss_stats: Optional[List[Dict]] = None,
    ) -> List[NewsTagResult]:
        """
        为单条新闻生成标签和评分
        
        为了节省 Token，使用批量处理策略
        """
        all_news = []
        
        # 收集所有新闻
        for stat in stats:
            for key, value in stat.items():
                if isinstance(value, dict) and 'title' in value:
                    all_news.append({
                        'news_item_id': value.get('id'),
                        'title': value['title'],
                        'summary': value.get('summary', ''),
                        'source': value.get('source', 'Unknown'),
                    })
        
        if rss_stats:
            for stat in rss_stats:
                for key, value in stat.items():
                    if isinstance(value, dict) and 'title' in value:
                        all_news.append({
                            'news_item_id': value.get('id'),
                            'title': value['title'],
                            'summary': value.get('summary', ''),
                            'source': value.get('source', 'RSS'),
                        })
        
        # 批量处理（每 10 条新闻调用一次 AI）
        news_tags = []
        batch_size = 10
        
        for i in range(0, len(all_news), batch_size):
            batch = all_news[i:i+batch_size]
            batch_results = self._process_news_batch(batch)
            news_tags.extend(batch_results)
        
        return news_tags
    
    def _process_news_batch(self, news_batch: List[Dict]) -> List[NewsTagResult]:
        """批量处理新闻标签生成"""
        # 构建批量 prompt
        news_items_str = "\n\n".join([
            f"新闻 {i+1}:\n标题：{n['title']}\n摘要：{n['summary']}\n来源：{n['source']}"
            for i, n in enumerate(news_batch)
        ])
        
        batch_prompt = f"""
你是 AI 资讯标签提取助手。请为以下 {len(news_batch)} 条新闻分别提取标签和评分。

{news_items_str}

请输出 JSON 数组格式，每个元素对应一条新闻：
[
    {{
        "index": 1,
        "tags": ["标签 1", "标签 2"],
        "heat_score": 85,
        "reason": "推荐理由"
    }},
    ...
]
"""
        
        try:
            # 调用 AI
            client = AIClient(self.ai_config)
            response = client.chat([
                {"role": "system", "content": "你是专业的 AI 资讯标签提取助手。"},
                {"role": "user", "content": batch_prompt},
            ])
            
            # 解析响应
            results = json.loads(response)
            
            news_tags = []
            for result in results:
                idx = result.get('index', 0) - 1
                if 0 <= idx < len(news_batch):
                    news = news_batch[idx]
                    news_tags.append(NewsTagResult(
                        news_item_id=news.get('news_item_id'),
                        title=news['title'],
                        tags=result.get('tags', []),
                        heat_score=result.get('heat_score', 0),
                        reason=result.get('reason', ''),
                    ))
            
            return news_tags
            
        except Exception as e:
            print(f"[ExtendedAI] 批量处理失败：{e}，降级为简单规则提取")
            # 降级方案：使用简单规则提取
            return self._extract_tags_by_rules(news_batch)
    
    def _extract_tags_by_rules(self, news_batch: List[Dict]) -> List[NewsTagResult]:
        """降级方案：基于规则提取标签"""
        news_tags = []
        
        # 关键词映射表
        keyword_to_tag = {
            'AI': '人工智能',
            '大模型': '大模型',
            'GPT': '大模型',
            'Claude': '大模型',
            '发布': '产品发布',
            '开源': '开源',
            '融资': '投融资',
            '收购': '并购',
        }
        
        for news in news_batch:
            title = news['title'].lower()
            tags = []
            
            for keyword, tag in keyword_to_tag.items():
                if keyword.lower() in title:
                    tags.append(tag)
            
            # 默认标签
            if not tags:
                tags = ['科技', '热点']
            
            news_tags.append(NewsTagResult(
                news_item_id=news.get('news_item_id'),
                title=news['title'],
                tags=tags[:4],  # 最多 4 个标签
                heat_score=70,  # 默认评分
                reason="基于关键词匹配",
            ))
        
        return news_tags
    
    def _cluster_events(
        self,
        stats: List[Dict],
        rss_stats: Optional[List[Dict]] = None,
    ) -> List[EventClusterResult]:
        """
        事件聚类
        
        基于标题相似度识别相同事件的多个报道
        """
        # 收集所有新闻
        all_news = []
        for stat in stats:
            for key, value in stat.items():
                if isinstance(value, dict) and 'title' in value:
                    all_news.append({
                        'id': value.get('id'),
                        'title': value['title'],
                        'source': value.get('source', 'Unknown'),
                    })
        
        # 基于标题相似度分组（简化版）
        event_groups = {}
        for news in all_news:
            # 提取标题关键词（简化处理）
            title_keywords = self._extract_keywords(news['title'])
            group_key = title_keywords
            
            if group_key not in event_groups:
                event_groups[group_key] = []
            event_groups[group_key].append(news)
        
        # 转换为事件聚类结果
        events = []
        for key, news_list in event_groups.items():
            if len(news_list) > 1:  # 只有多个报道才视为事件
                events.append(EventClusterResult(
                    event_name=news_list[0]['title'],
                    event_summary=f"共有 {len(news_list)} 个源报道",
                    news_ids=[n['id'] for n in news_list],
                    representative_news_id=news_list[0]['id'],
                    related_count=len(news_list) - 1,
                ))
        
        return events
    
    def _extract_keywords(self, title: str) -> str:
        """提取标题关键词（用于聚类）"""
        # 简化实现：去除标点符号和停用词
        import re
        words = re.findall(r'[\w\u4e00-\u9fa5]+', title)
        
        # 停用词表
        stopwords = {'的', '了', '在', '是', '和', '与', '或', '等', '着', '就'}
        keywords = [w for w in words if w.lower() not in stopwords and len(w) > 1]
        
        return ''.join(sorted(keywords[:5]))  # 取前 5 个关键词作为分组 key
    
    def _save_news_tags(self, news_tags: List[NewsTagResult]):
        """保存新闻标签到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for tag_result in news_tags:
            for tag in tag_result.tags:
                cursor.execute("""
                    INSERT OR REPLACE INTO news_ai_tags 
                    (news_item_id, tag, heat_score, reason)
                    VALUES (?, ?, ?, ?)
                """, (
                    tag_result.news_item_id,
                    tag,
                    tag_result.heat_score,
                    tag_result.reason,
                ))
        
        conn.commit()
        conn.close()
    
    def _save_events(self, events: List[EventClusterResult]):
        """保存事件聚类结果到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for event in events:
            # 插入事件
            cursor.execute("""
                INSERT INTO ai_events (event_name, event_summary, representative_news_id)
                VALUES (?, ?, ?)
            """, (event.event_name, event.event_summary, event.representative_news_id))
            
            event_id = cursor.lastrowid
            
            # 插入新闻 - 事件映射
            for news_id in event.news_ids:
                related_count = len(event.news_list) - 1 if hasattr(event, 'news_list') else event.related_count
                cursor.execute("""
                    INSERT INTO news_event_map (news_item_id, event_id, related_count)
                    VALUES (?, ?, ?)
                """, (news_id, event_id, related_count))
        
        conn.commit()
        conn.close()
