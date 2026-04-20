#!/bin/bash
# TrendRadar 一体化启动脚本（集成 MCP + Timeline API + 前端）

cd /tmp/trendradar

echo "╔═════════════════════════════════════════════╗"
echo "║   TrendRadar - 一体化服务 (MCP + Timeline)  ║"
echo "╚═════════════════════════════════════════════╝"

# 检查数据库
if [ ! -f "data/trendradar.db" ]; then
    echo "❌ 数据库不存在，请先运行数据爬取"
    exit 1
fi

echo "✓ 数据库：data/trendradar.db"

# 检查前端构建
if [ ! -d "timeline_ui/dist" ]; then
    echo "⚠️  前端未构建，正在构建..."
    cd timeline_ui && npm run build && cd ..
fi

# 启动 Timeline API + 前端（3333 端口）
echo "→ 启动 Timeline API + 前端服务 (3333 端口)..."
python3 mcp_server/timeline_api.py --db data/trendradar.db --port 3333 --serve-static &
TIMELINE_PID=$!
sleep 3

# 检测服务是否启动成功
if curl -s http://localhost:3333/api/timeline/stats > /dev/null; then
    echo "✓ Timeline API 运行正常"
else
    echo "❌ Timeline API 启动失败"
    kill $TIMELINE_PID 2>/dev/null
    exit 1
fi

if curl -s http://localhost:3333/ | grep -q "AI 资讯时间线"; then
    echo "✓ 前端 UI 运行正常"
else
    echo "⚠️  前端可能有问题"
fi

echo ""
echo "═════════════════════════════════════════════"
echo "  服务已启动："
echo "  🌐 前端 UI:   http://localhost:3333/"
echo "  📡 Timeline API: http://localhost:3333/api/timeline/*"
echo ""
echo "  按 Ctrl+C 停止服务"
echo "═════════════════════════════════════════════"

# 等待中断
trap "kill $TIMELINE_PID 2>/dev/null; echo '服务已停止'" EXIT
wait
