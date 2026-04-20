# TrendRadar AI Timeline - 实施进度报告

**日期**: 2026-04-20  
**版本**: v1.0  
**状态**: 第一阶段完成

---

## ✅ 已完成的工作

### 1. 数据库扩展 (Completed)

**文件**: `trendradar/storage/ai_timeline_schema.sql`

创建了以下数据库表：

- ✅ `ai_analysis_results` - AI 整体分析结果表
- ✅ `news_ai_tags` - 单条新闻的 AI 标签和评分
- ✅ `ai_events` - 事件聚类表
- ✅ `news_event_map` - 新闻 - 事件关联表
- ✅ `user_bookmarks` - 用户收藏表
- ✅ `timeline_config` - Web UI 配置表
- ✅ `ai_analysis_history` - AI 分析历史表
- ✅ `v_news_full` - 完整新闻数据视图（包含 AI 分析结果）

**关键特性**:
- 索引优化（查询性能）
- 外键约束（数据完整性）
- 视图封装（简化查询）
- 初始化配置数据

### 2. ExtendedAIAnalyzer 实现 (Completed)

**文件**: `trendradar/ai/extended_analyzer.py`

实现了以下功能：

- ✅ 复用原有 `AIAnalyzer` 进行整体分析
- ✅ 将整体分析结果保存到 `ai_analysis_results` 表
- ✅ 批量为单条新闻生成标签和评分
- ✅ 事件聚类（基于标题相似度）
- ✅ 分析历史记录和错误处理
- ✅ 降级策略（AI 失败时使用规则提取）

**核心方法**:
```python
def analyze_and_save(stats, rss_stats, report_mode) -> ExtendedAIResult:
    """执行 AI 分析并保存到数据库"""
    
    # 1. 执行整体 AI 分析
    analysis_result = self.analyzer.analyze(...)
    
    # 2. 保存整体分析结果
    self._save_analysis_result(analysis_result)
    
    # 3. 为单条新闻生成标签
    news_tags = self._extract_news_tags(stats)
    self._save_news_tags(news_tags)
    
    # 4. 事件聚类
    events = self._cluster_events(stats)
    self._save_events(events)
```

### 3. React UI 项目框架 (Completed)

**目录**: `timeline_ui/`

已创建的基础文件:

- ✅ `package.json` - 项目配置和依赖
- ✅ `vite.config.ts` - Vite 构建配置（包含 API 代理）
- ✅ `tsconfig.json` - TypeScript 配置
- ✅ `index.html` - HTML 入口
- ✅ `tailwind.config.js` - Tailwind 配色（暗色主题）
- ✅ `postcss.config.js` - PostCSS 配置
- ✅ `src/main.tsx` - React 入口
- ✅ `src/App.tsx` - 主应用组件
- ✅ `src/styles/globals.css` - 全局样式

**技术栈**:
- React 18 + TypeScript
- Vite (快速构建)
- TailwindCSS (暗色主题)
- Zustand (状态管理)
- Axios (HTTP 请求)

---

## 📝 待完成的工作

### 高优先级 (P0)

#### 4. 实现核心 React 组件 (Todo)

需要创建的组件:

1. **`src/components/NewsCard.tsx`** - 新闻卡片组件
   - 显示标题、摘要
   - AI 标签展示
   - 推荐理由（绿色高亮）
   - 热度分数徽章
   - 多源聚合提示
   - 收藏按钮

2. **`src/components/Timeline.tsx`** - 时间线布局组件
   - 按时间分组显示新闻
   - 时间标记（22:45）
   - 无限滚动/分页

3. **`src/components/Sidebar.tsx`** - 侧边栏导航
   - 筛选选项（精选/全部/收藏）
   - 标签云
   - 来源筛选

4. **`src/components/SearchBar.tsx`** - 搜索框
   - 实时搜索
   - 关键词高亮

5. **`src/store/newsStore.ts`** - Zustand 状态管理
   - 新闻数据
   - 加载状态
   - 筛选逻辑

6. **`src/api/index.ts`** - API 调用层
   - 获取新闻列表
   - 收藏操作
   - 搜索接口

#### 5. 创建数据库读取层 (Todo)

**文件**: `trendradar/timeline_api/data_loader.py`

需要实现:

```python
class TimelineDataLoader:
    """从数据库读取 AI 分析结果"""
    
    def get_news(self, limit=50, filter='featured') -> List[Dict]
    def get_by_tag(self, tag: str) -> List[Dict]
    def search(self, query: str) -> List[Dict]
    def toggle_bookmark(self, news_id: int, user_id: str) -> bool
```

#### 6. 集成到 TrendRadar 主流程 (Todo)

**文件**: `trendradar/__main__.py`

需要修改:

```python
def main():
    # 1. 原有流程（数据采集、AI 分析、推送）
    analyzer = NewsAnalyzer(config)
    stats = analyzer.fetch_and_analyze()
    
    # 2. 如果启用 Timeline，执行扩展 AI 分析
    if config.get('TIMELINE', {}).get('ENABLED', False):
        from trendradar.ai.extended_analyzer import ExtendedAIAnalyzer
        
        ext_analyzer = ExtendedAIAnalyzer(
            ai_config=config['ai'],
            analysis_config=config['ai_analysis'],
            db_path=get_db_path(),
        )
        
        ext_result = ext_analyzer.analyze_and_save(stats=stats)
        print(f"[Timeline] AI 分析完成，保存到数据库")
    
    # 3. 原有推送逻辑
    push_engine.run()
```

---

## 🎯 下一步计划

### 立即执行

1. **创建核心 React 组件** (预计 1-2 天)
   - NewsCard
   - Timeline
   - Sidebar
   - SearchBar

2. **实现数据读取层** (预计 0.5 天)
   - TimelineDataLoader
   - API 路由（可选）

3. **集成测试** (预计 0.5 天)
   - 运行完整流程
   - 验证数据持久化
   - 测试 UI 展示

### 后续优化

4. **配置页面**（可选）
   - AI 模型配置
   - 分析频率设置
   - 数据源管理

5. **部署文档**
   - Docker 部署指南
   - 本地运行说明
   - 常见问题 FAQ

---

## 📊 当前进度

```
总体进度：50%

✅ 已完成:
████████████████████░░░░░░░░ 50%

📋 任务分解:
1. 数据库扩展          ✅ 100%
2. ExtendedAIAnalyzer  ✅ 100%
3. React 项目框架       ✅ 100%
4. 核心 React 组件       ⏳ 0%
5. 数据读取层          ⏳ 0%
6. 集成到主流程        ⏳ 0%
7. 测试与部署          ⏳ 0%
```

---

## 🚀 快速测试

### 数据库测试

```bash
cd /tmp/trendradar

# 初始化数据库扩展
sqlite3 data/trendradar.db < trendradar/storage/ai_timeline_schema.sql

# 验证表创建
sqlite3 data/trendradar.db ".tables"
```

### React UI 开发测试

```bash
cd timeline_ui

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问 http://localhost:3000
```

---

## 💡 关键设计决策

### 1. 为什么选择扩展而不是重写？

✅ **优势**:
- 复用现有 AI 分析逻辑
- 不影响 TrendRadar 原有功能
- 维护成本低
- 数据一致性好

### 2. 为什么数据库优先？

✅ **原因**:
- 数据结构决定 API 设计
- 持久化后可以离线开发 UI
- 方便调试和验证

### 3. 为什么选择 React？

✅ **原因**:
- 组件化开发
- 生态系统成熟
- 参考图 UI 是 React 实现的
- 开发效率高

---

## ❓ 需要确认的问题

1. **API 层是否需要独立的 FastAPI 服务？**
   - 方案 A：静态页面 + 直接读取数据库（更轻量）
   - 方案 B：FastAPI 后端 + 前端分离（更灵活）
   
   **建议**：先用方案 A，后续需要再升级到方案 B

2. **是否立即实现配置页面？**
   - 建议放到 P2 阶段（后续迭代）
   - 当前优先保证核心展示功能

3. **部署方式？**
   - 推荐 Docker 一键部署
   - 或本地 Python + npm 运行

---

**下一步**: 继续创建核心 React 组件
