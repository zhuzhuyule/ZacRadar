# TrendRadar AI Timeline 集成指南

## 架构说明

AI Timeline 服务已集成到 TrendRadar 主程序中，提供以下功能：

- **前端 UI**：基于 Vite + React + Tailwind CSS
- **Timeline API**：提供新闻列表、标签、搜索、收藏等接口
- **数据库**：SQLite 存储 AI 分析结果

## 启动方式

### 方式 1：一体化启动脚本（推荐）

```bash
./start-all.sh
```

此脚本会同时启动：
- Timeline API 服务器（端口 8001）
- 前端 UI 服务器（端口 5173）
- 自动检查并初始化数据库

### 方式 2：仅启动 Timeline 服务

```bash
./start-timeline.sh
```

### 方式 3：使用主程序命令

```bash
# 启动 Timeline 服务
python -m trendradar --timeline-server

# 然后手动启动前端
cd timeline_ui && npm run dev
```

### 方式 4：独立启动 API 服务

```bash
python trendradar/timeline_server.py --db data/trendradar.db
```

## 配置选项

在 `config/config.yaml` 中添加以下配置：

```yaml
TIMELINE:
  PORT: 8001        # API 端口
  HOST: "0.0.0.0"   # 监听地址
```

数据库路径配置：

```yaml
STORAGE:
  SQLITE:
    DB_PATH: "data/trendradar.db"
```

## API 端点

### 获取新闻列表

```
GET /api/news?limit=50&offset=0&filter=featured&tag=AI&search=关键词
```

参数：
- `limit`: 返回数量（默认 50）
- `offset`: 偏移量（默认 0）
- `filter`: 筛选类型 `featured` | `all` | `bookmarks`
- `tag`: 标签筛选
- `search`: 搜索关键词

### 获取标签列表

```
GET /api/tags
```

### 获取统计数据

```
GET /api/stats
```

### 切换收藏

```
POST /api/bookmark/:news_id
Content-Type: application/json

{
  "user_id": "default"
}
```

## 前端功能

- **时间线布局**：左侧连续垂直线 + 圆点节点
- **卡片宽度**：800 / 1000 / 1200 px 可调
- **视图缩放**：90% - 150% 滑块调节
- **主题切换**：深色/浅色主题
- **侧边栏**：导航、标签筛选、统计信息
- **搜索**：按标题、简讯、推荐理由搜索
- **收藏**：收藏/取消收藏功能

## 文件结构

```
trendradar/
├── timeline_server.py        # Timeline 服务模块
├── timeline_api/
│   └── data_loader.py        # 数据读取层（向后兼容）
├── storage/
│   └── ai_timeline_schema.sql # 数据库扩展 schema
└── ai/
    └── extended_analyzer.py  # AI 分析扩展

timeline_ui/                   # 前端应用
├── src/
│   ├── App.tsx               # 主应用
│   ├── components/
│   │   ├── Timeline.tsx      # 时间线组件
│   │   ├── NewsCard.tsx      # 新闻卡片
│   │   ├── Sidebar.tsx       # 侧边栏
│   │   └── SearchBar.tsx     # 搜索框
│   ├── store/
│   │   └── newsStore.ts      # Zustand 状态管理
│   └── styles/
│       └── globals.css       # 全局样式
└── index.html
```

## 数据库扩展

AI Timeline 使用以下数据库表和视图：

- `ai_events`：AI 事件表
- `event_timeline_items`：时间线索引表
- `news_ai_analysis`：AI 分析结果表
- `news_ai_tags`：AI 标签表
- `news_event_relations`：事件关联表
- `user_bookmarks`：用户收藏表
- `v_news_full`：完整新闻视图（包含所有 AI 分析结果）

详见：[trendradar/storage/ai_timeline_schema.sql](trendradar/storage/ai_timeline_schema.sql)

## 开发模式

### 前端开发

```bash
cd timeline_ui
npm run dev          # 开发模式（热重载）
npm run build        # 生产构建
npm run preview      # 预览生产构建
```

### API 调试

```bash
# 使用 curl 测试
curl http://localhost:8001/api/stats
curl "http://localhost:8001/api/news?limit=10"
curl http://localhost:8001/api/tags
```

## 与 MCP 服务集成

Timeline 服务可以独立运行，也可以与 MCP 服务同时运行：

```bash
# 在两个终端中分别运行
python -m trendradar                    # MCP 服务（stdio 模式）
python -m trendradar --timeline-server  # Timeline HTTP API
```

## 注意事项

1. **数据库初始化**：首次使用前，需要运行主程序爬取数据
2. **端口占用**：默认使用 8001 和 5173 端口，确保未被占用
3. **跨域访问**：API 支持 CORS，可用于跨域访问
4. **性能优化**：大量数据时建议添加索引

## 故障排查

### 数据库不存在

```
❌ 数据库文件未找到：data/trendradar.db

解决方案：
1. 运行主程序爬取数据：python -m trendradar
2. 或手动创建数据库：sqlite3 data/trendradar.db < trendradar/storage/ai_timeline_schema.sql
```

### 端口被占用

```
Address already in use: 0.0.0.0:8001

解决方案：
1. 检查占用进程：lsof -ti:8001
2. 停止占用进程：kill -9 $(lsof -ti:8001)
3. 或修改配置文件更改端口
```

### 前端无法连接 API

检查浏览器控制台是否有 CORS 错误，确认：
- API 服务器已启动
- 端口号正确
- 防火墙允许访问

## 更新日志

- **2026-04-20**: 集成 Timeline 服务到 TrendRadar 主程序
- **2026-04-20**: 添加一体化启动脚本
- **2026-04-20**: 支持卡片宽度和视图缩放调节
