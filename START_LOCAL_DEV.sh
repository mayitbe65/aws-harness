#!/bin/bash

# 错题宝本地开发启动脚本（一键启动所有服务）
# 使用方法：bash START_LOCAL_DEV.sh

set -e

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "=========================================="
echo "  错题宝 - 本地开发环境启动"
echo "=========================================="
echo ""

# 1. 启动 PostgreSQL 和 Redis（Docker Compose）
echo "📦 [1/4] 启动 PostgreSQL 和 Redis..."
cd "$PROJECT_ROOT"
if command -v docker-compose &> /dev/null; then
    docker-compose up -d
else
    docker compose up -d
fi
echo "✅ PostgreSQL 和 Redis 已启动"
echo ""

# 2. 检查后端虚拟环境
echo "🐍 [2/4] 检查后端环境..."
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo "📌 创建虚拟环境..."
    cd "$BACKEND_DIR"
    python3.11 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    echo "✅ 虚拟环境已创建"
else
    source "$BACKEND_DIR/venv/bin/activate"
    echo "✅ 虚拟环境已就绪"
fi
echo ""

# 3. 检查前端依赖
echo "📦 [3/4] 检查前端依赖..."
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    echo "📌 安装 npm 依赖..."
    npm install
    echo "✅ npm 依赖已安装"
else
    echo "✅ npm 依赖已就绪"
fi
echo ""

# 4. 启动服务提示
echo "=========================================="
echo "✅ 环境准备完成！"
echo "=========================================="
echo ""
echo "🚀 现在需要打开 3 个终端分别运行："
echo ""
echo "📍 终端 1 - 后端 API (port 8000):"
echo "   cd $BACKEND_DIR"
echo "   source venv/bin/activate"
echo "   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "📍 终端 2 - 前端开发服务器 (port 5173):"
echo "   cd $FRONTEND_DIR"
echo "   npm run dev"
echo ""
echo "📍 终端 3 - 访问应用:"
echo "   本地访问: http://localhost:5173"
echo "   API 文档: http://localhost:8000/docs"
echo ""
echo "📋 登录凭证:"
echo "   Email:    student@test.edu"
echo "   Password: Password123"
echo ""
echo "=========================================="
