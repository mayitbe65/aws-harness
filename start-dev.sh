#!/bin/bash

# 错题宝 - 本地开发快速启动脚本
# 使用方法：bash start-dev.sh
# 或者直接运行每个命令在不同的终端中

set -e

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                   错题宝项目 - 本地开发启动                        ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# 检查环境
echo "🔍 环境检查..."
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装"
    exit 1
fi
NODE_VERSION=$(node --version)
echo "✅ Node.js: $NODE_VERSION"

# 检查 npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm 未安装"
    exit 1
fi
NPM_VERSION=$(npm --version)
echo "✅ npm: $NPM_VERSION"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 未安装"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "✅ $PYTHON_VERSION"

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo ""

# 后端初始化检查
echo "📦 检查后端环境..."
BACKEND_DIR="$PROJECT_ROOT/backend"
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo "   创建虚拟环境..."
    cd "$BACKEND_DIR"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    alembic upgrade head
    echo "✅ 后端环境就绪"
else
    echo "✅ 后端虚拟环境已存在"
fi

echo ""

# 前端初始化检查
echo "📦 检查前端环境..."
FRONTEND_DIR="$PROJECT_ROOT/frontend"
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "   安装 npm 依赖..."
    cd "$FRONTEND_DIR"
    npm install
    echo "✅ 前端依赖已安装"
else
    echo "✅ 前端依赖已存在"
fi

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "✨ 环境准备完成！现在需要在 3 个不同的终端中运行："
echo ""
echo "📍 终端 1 - 后端 API (port 8000):"
echo "   cd $BACKEND_DIR"
echo "   source venv/bin/activate"
echo "   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "📍 终端 2 - 前端服务器 (port 5173):"
echo "   cd $FRONTEND_DIR"
echo "   npm run dev"
echo ""
echo "📍 终端 3 - 浏览器访问:"
echo "   http://localhost:5173"
echo ""
echo "📋 登录凭证:"
echo "   Email:    student@test.edu"
echo "   Password: Password123"
echo ""
echo "📚 完整文档:"
echo "   本地开发指南: LOCAL_DEV_GUIDE.md"
echo "   快速参考:    QUICK_START.txt"
echo "   访问指南:    ACCESS_GUIDE.md"
echo ""
echo "════════════════════════════════════════════════════════════════════"
