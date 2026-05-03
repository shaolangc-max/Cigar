#!/bin/bash
# 本地开发启动脚本（SQLite，无需 Docker）
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$REPO/backend"
FRONTEND="$REPO/frontend"
VENV="$BACKEND/.venv"
DB="sqlite+aiosqlite:///./dev.db"

# ── 检查 venv ─────────────────────────────────────────────────────────────────
if [ ! -f "$VENV/bin/python" ]; then
  echo "创建 venv..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -r "$BACKEND/requirements.txt" aiosqlite
fi

# ── 数据库迁移 + 种子 ─────────────────────────────────────────────────────────
echo "▶ 迁移数据库..."
cd "$BACKEND"
PYTHONPATH="$BACKEND" DATABASE_URL="$DB" "$VENV/bin/alembic" upgrade head

echo "▶ 写入种子数据..."
PYTHONPATH="$BACKEND" DATABASE_URL="$DB" "$VENV/bin/python" -m app.scrapers.sources_seed
PYTHONPATH="$BACKEND" DATABASE_URL="$DB" "$VENV/bin/python" -m app.scrapers.cigars_seed
PYTHONPATH="$BACKEND" DATABASE_URL="$DB" "$VENV/bin/python" -m app.scrapers.rates_seed

# ── 启动后端 ──────────────────────────────────────────────────────────────────
echo "▶ 启动后端 → http://127.0.0.1:8000"
PYTHONPATH="$BACKEND" DATABASE_URL="$DB" \
  "$VENV/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# ── 启动调度器 ────────────────────────────────────────────────────────────────
echo "▶ 启动调度器（爬虫每4h / 汇率每24h）"
PYTHONPATH="$BACKEND" DATABASE_URL="$DB" \
  "$VENV/bin/python" -m app.scheduler.runner &
SCHEDULER_PID=$!

# ── 安装前端依赖 ──────────────────────────────────────────────────────────────
cd "$FRONTEND"
if [ ! -d node_modules ]; then
  echo "▶ 安装前端依赖..."
  npm install
fi

# ── 启动前端 ──────────────────────────────────────────────────────────────────
echo "▶ 启动前端 → http://localhost:3001"
NO_PROXY=localhost,127.0.0.1,::1 \
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1 \
  npm run dev -- --port 3001 &
FRONTEND_PID=$!

echo ""
echo "✅ 服务已启动："
echo "   后端 API : http://localhost:8001/api/v1"
echo "   前端     : http://localhost:3001"
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "kill $BACKEND_PID $SCHEDULER_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
