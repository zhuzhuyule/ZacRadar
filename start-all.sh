#!/bin/bash
# TrendRadar 一体化启动脚本
# 同时启动 MCP 服务、Timeline API 和前端 UI

set -e

cd "$(dirname "$0")"

echo "╔════════════════════════════════════════════════════════╗"
echo "║   TrendRadar - AI Timeline 一体化启动                   ║"
echo "╚════════════════════════════════════════════════════════╝"

# 检查环境
echo ""
echo "步骤 1/4: 检查环境..."

if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 Python 3"
    exit 1
fi
echo "✓ Python: $(python3 --version)"

if ! command -v node &> /dev/null; then
    echo "❌ 错误：未找到 Node.js"
    exit 1
fi
echo "✓ Node.js: $(node --version)"

if ! command -v sqlite3 &> /dev/null; then
    echo "❌ 错误：未找到 sqlite3"
    exit 1
fi
echo "✓ SQLite: $(sqlite3 --version)"

# 检查数据库
echo ""
echo "步骤 2/4: 检查数据库..."

DB_PATH="data/trendradar.db"
mkdir -p data

if [ ! -f "$DB_PATH" ]; then
    echo "  ⚠️  数据库不存在，需要先运行数据爬取"
    echo "  提示：运行 uv run python -m trendradar 进行首次爬取"
fi

if [ -f "trendradar/storage/ai_timeline_schema.sql" ]; then
    echo "  初始化 AI Timeline 扩展表..."
    sqlite3 "$DB_PATH" < trendradar/storage/ai_timeline_schema.sql 2>/dev/null || true
    echo "✓ 数据库初始化完成"
else
    echo "✓ 数据库已就绪"
fi

# 安装前端依赖
echo ""
echo "步骤 3/4: 检查前端依赖..."

cd timeline_ui

if [ ! -d "node_modules" ]; then
    echo "  首次安装依赖..."
    npm install
else
    npm install --silent
fi

echo "✓ 前端依赖已就绪"

# 启动服务
echo ""
echo "步骤 4/4: 启动服务..."

cd ..

# 启动 Timeline API 服务（后台）
echo "  → 启动 Timeline API 服务器 (端口 8001)..."
uv run python -m trendradar --timeline-server &
TIMELINE_PID=$!
sleep 2

# 检查 Timeline API 是否启动成功
if ! kill -0 $TIMELINE_PID 2>/dev/null; then
    echo "❌ Timeline API 启动失败"
    exit 1
fi
echo "✓ Timeline API: PID $TIMELINE_PID"

# 启动前端 UI（后台）
echo "  → 启动前端 UI 服务器 (端口 5173)..."
cd timeline_ui
npm run dev &
FRONTEND_PID=$!
sleep 2

cd ..

# 检查前端是否启动成功
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "❌ 前端 UI 启动失败"
    kill $TIMELINE_PID 2>/dev/null
    exit 1
fi
echo "✓ Frontend UI: PID $FRONTEND_PID"

# 显示启动信息
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║                   🎉 启动成功！                        ║"
echo "╠════════════════════════════════════════════════════════╣"
echo "║  Timeline API:   http://localhost:8001                ║"
echo "║  前端页面：     http://localhost:5173                 ║"
echo "║                                                        ║"
echo "║  API 端点：                                            ║"
echo "║    GET  /api/news    - 获取新闻列表                    ║"
echo "║    GET  /api/tags    - 获取标签列表                    ║"
echo "║    GET  /api/stats   - 获取统计数据                    ║"
echo "║    POST /api/bookmark/:id - 切换收藏                   ║"
echo "║                                                        ║"
echo "║  按 Ctrl+C 停止所有服务                                ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# 等待用户中断
trap "kill $TIMELINE_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
