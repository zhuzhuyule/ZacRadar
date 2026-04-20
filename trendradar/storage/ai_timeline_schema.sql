-- TrendRadar AI Timeline 扩展表结构
-- 用于存储 AI 分析的结构化结果，支持时间线展示

-- ============================================
-- AI 分析结果表（整体分析）
-- ============================================
CREATE TABLE IF NOT EXISTS ai_analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_date TEXT NOT NULL,          -- YYYY-MM-DD
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- AI 分析的 5 大板块
    core_trends TEXT,                     -- 核心热点与舆情态势
    sentiment_controversy TEXT,           -- 舆论风向与争议
    signals TEXT,                         -- 异动与弱信号
    rss_insights TEXT,                    -- RSS 深度洞察
    outlook_strategy TEXT,                -- 研判与策略建议
    
    -- 独立展示区概括 (JSON)
    standalone_summaries TEXT,
    
    -- 元数据
    ai_model TEXT,                        -- 使用的 AI 模型
    news_count INTEGER,                   -- 分析的新闻数量
    mode TEXT,                            -- 分析模式 (daily/current/incremental)
    tokens_used INTEGER,                  -- 消耗的 Token 数
    analysis_duration_seconds REAL,       -- 分析耗时
    status TEXT DEFAULT 'success',        -- success | failed
    
    -- 错误信息（如果失败）
    error_message TEXT,
    
    -- 原始响应（用于调试）
    raw_response TEXT
);

-- ============================================
-- 新闻 AI 标签表（单条新闻的 AI 分析）
-- ============================================
CREATE TABLE IF NOT EXISTS news_ai_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_item_id INTEGER NOT NULL,
    tag TEXT NOT NULL,                    -- AI 生成的标签
    heat_score INTEGER DEFAULT 0,         -- AI 评分 0-100
    reason TEXT,                          -- 推荐理由
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (news_item_id) REFERENCES news_items(id)
);

-- ============================================
-- AI 事件表（事件聚类）
-- ============================================
CREATE TABLE IF NOT EXISTS ai_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,             -- 事件名称
    event_summary TEXT,                   -- 事件摘要
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    representative_news_id INTEGER,       -- 代表性新闻 ID
    
    FOREIGN KEY (representative_news_id) REFERENCES news_items(id)
);

-- ============================================
-- 新闻 - 事件关联表
-- ============================================
CREATE TABLE IF NOT EXISTS news_event_map (
    news_item_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    related_count INTEGER DEFAULT 0,      -- 相关_source 数量
    PRIMARY KEY (news_item_id, event_id),
    FOREIGN KEY (news_item_id) REFERENCES news_items(id),
    FOREIGN KEY (event_id) REFERENCES ai_events(id)
);

-- ============================================
-- 用户收藏表
-- ============================================
CREATE TABLE IF NOT EXISTS user_bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_item_id INTEGER NOT NULL,
    user_id TEXT,                         -- 用户 ID（预留多用户支持）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (news_item_id) REFERENCES news_items(id),
    UNIQUE(news_item_id, user_id)
);

-- ============================================
-- 系统配置表（Web UI 配置）
-- ============================================
CREATE TABLE IF NOT EXISTS timeline_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- AI 分析历史表（记录每次分析的执行情况）
-- ============================================
CREATE TABLE IF NOT EXISTS ai_analysis_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    news_count INTEGER,
    tokens_used INTEGER,
    status TEXT DEFAULT 'running',        -- running | success | failed
    error_message TEXT,
    duration_seconds REAL
);

-- ============================================
-- 索引优化
-- ============================================
CREATE INDEX IF NOT EXISTS idx_ai_analysis_date ON ai_analysis_results(analysis_date DESC);
CREATE INDEX IF NOT EXISTS idx_ai_analyzed_at ON ai_analysis_results(analyzed_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_tags_news_id ON news_ai_tags(news_item_id);
CREATE INDEX IF NOT EXISTS idx_news_tags_tag ON news_ai_tags(tag);
CREATE INDEX IF NOT EXISTS idx_news_events_news_id ON news_event_map(news_item_id);
CREATE INDEX IF NOT EXISTS idx_news_events_event_id ON news_event_map(event_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_news_id ON user_bookmarks(news_item_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_user_id ON user_bookmarks(user_id);
CREATE INDEX IF NOT EXISTS idx_config_key ON timeline_config(config_key);
CREATE INDEX IF NOT EXISTS idx_analysis_history_started ON ai_analysis_history(started_at DESC);

-- ============================================
-- 视图：完整的新闻数据（包含 AI 分析结果）
-- ============================================
CREATE VIEW IF NOT EXISTS v_news_full AS
SELECT 
    ni.id,
    ni.title,
    ni.platform_id,
    ni.rank,
    ni.url,
    ni.mobile_url,
    ni.first_crawl_time,
    ni.last_crawl_time,
    ni.crawl_count,
    ni.created_at,
    ni.updated_at,
    
    -- AI 标签（JSON 数组）
    (
        SELECT json_group_array(nat.tag)
        FROM news_ai_tags nat
        WHERE nat.news_item_id = ni.id
    ) as ai_tags,
    
    -- 最高热度评分
    (
        SELECT MAX(nat.heat_score)
        FROM news_ai_tags nat
        WHERE nat.news_item_id = ni.id
    ) as ai_heat_score,
    
    -- 推荐理由（取第一个）
    (
        SELECT nat.reason
        FROM news_ai_tags nat
        WHERE nat.news_item_id = ni.id
        ORDER BY nat.heat_score DESC
        LIMIT 1
    ) as ai_reason,
    
    -- 事件 ID
    (
        SELECT nem.event_id
        FROM news_event_map nem
        WHERE nem.news_item_id = ni.id
        LIMIT 1
    ) as event_id,
    
    -- 相关源数量
    (
        SELECT nem.related_count
        FROM news_event_map nem
        WHERE nem.news_item_id = ni.id
        LIMIT 1
    ) as related_count,
    
    -- 平台名称
    p.name as platform_name,
    
    -- 是否已收藏
    CASE WHEN ub.id IS NOT NULL THEN 1 ELSE 0 END as is_bookmarked
    
FROM news_items ni
LEFT JOIN platforms p ON ni.platform_id = p.id
LEFT JOIN user_bookmarks ub ON ni.id = ub.news_item_id
WHERE p.is_active = 1 OR p.is_active IS NULL;

-- ============================================
-- 初始化配置数据
-- ============================================
INSERT OR IGNORE INTO timeline_config (config_key, config_value) VALUES
    ('timeline.enabled', 'true'),
    ('timeline.refresh_interval', '30'),
    ('timeline.items_per_page', '50'),
    ('timeline.default_view', 'featured'),
    ('ui.theme', 'dark'),
    ('ui.language', 'zh-CN');
