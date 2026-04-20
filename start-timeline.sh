#!/bin/bash
# TrendRadar AI Timeline 快速启动脚本

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║   TrendRadar AI Timeline - 快速启动                    ║"
echo "╚════════════════════════════════════════════════════════╝"

# 切换到项目目录
cd "$(dirname "$0")"

echo ""
echo "步骤 1/5: 检查环境..."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 Python 3"
    exit 1
fi
echo "✓ Python: $(python3 --version)"

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 错误：未找到 Node.js"
    exit 1
fi
echo "✓ Node.js: $(node --version)"

# 检查 SQLite
if ! command -v sqlite3 &> /dev/null; then
    echo "❌ 错误：未找到 sqlite3"
    exit 1
fi
echo "✓ SQLite: $(sqlite3 --version)"

echo ""
echo "步骤 2/5: 初始化数据库..."

DB_PATH="data/trendradar.db"
mkdir -p data

# 如果数据库不存在，创建基础表
if [ ! -f "$DB_PATH" ]; then
    echo "  创建数据库..."
    # 这里应该运行 TrendRadar 的初始化脚本
    # sqlite3 "$DB_PATH" < trendradar/storage/schema.sql
fi

# 初始化 AI Timeline 扩展表
echo "  初始化 AI Timeline 扩展表..."
sqlite3 "$DB_PATH" < trendradar/storage/ai_timeline_schema.sql
echo "✓ 数据库初始化完成"

echo ""
echo "步骤 3/5: 安装前端依赖..."

cd timeline_ui

if [ ! -d "node_modules" ]; then
    echo "  首次安装依赖，这可能需要几分钟..."
    npm install
else
    echo "  依赖已安装，检查更新..."
    npm install --silent
fi

echo "✓ 前端依赖安装完成"

echo ""
echo "步骤 4/5: 启动 Timeline 服务..."

cd ..

# 启动 Timeline 服务器
python3 trendradar/timeline_server.py --db data/trendradar.db &
TIMELINE_PID=$!
echo "✓ Timeline 服务器已启动 (PID: $TIMELINE_PID)"

# 等待启动
sleep 2

# 检查是否成功
if ! kill -0 $TIMELINE_PID 2>/dev/null; then
    echo "❌ Timeline 服务器启动失败"
    exit 1
fi

echo ""
echo "步骤 5/5: 启动前端开发服务器..."

cd timeline_ui

# 启动前端
npm run dev &
FRONTEND_PID=$!
echo "✓ 前端服务器已启动 (PID: $FRONTEND_PID)"

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║                   🎉 启动成功！                        ║"
echo "╠════════════════════════════════════════════════════════╣"
echo "║  Timeline API:   http://0.0.0.0:8001                  ║"
echo "║  前端页面：     http://0.0.0.0:5173                   ║"
echo "║                                                        ║"
echo "║  按 Ctrl+C 停止所有服务                                ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# 等待用户中断
trap "kill $TIMELINE_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
