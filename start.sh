#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 先加载环境变量配置文件
for env_file in "$SCRIPT_DIR/.default.env" "$SCRIPT_DIR/.local.env"; do
    if [ -f "$env_file" ]; then
        export $(grep -v '^#' "$env_file" | xargs)
    fi
done

# 环境变量加载后，再应用默认值并打印
CLIENT_BACKEND="${CLIENT_BACKEND:-hybrid}"
ENABLE_LOCAL_ADAPTER="${ENABLE_LOCAL_ADAPTER:-false}"
echo "[ERP Agent MVP] CLIENT_BACKEND=$CLIENT_BACKEND, ENABLE_LOCAL_ADAPTER=$ENABLE_LOCAL_ADAPTER"

# 安装 Backend 依赖
cd "$SCRIPT_DIR"
echo "[ERP Agent] Installing backend dependencies..."
pip install -r app/requirements.txt

# 安装 MCP Service 依赖
echo "[ERP Agent] Installing MCP Service dependencies..."
pip install -r erp_mcp_service/requirements.txt

BACKEND_PORT="${BACKEND_PORT:-9000}"
MCP_SERVICE_PORT="${MCP_SERVICE_PORT:-9001}"

# 检查端口是否被占用
echo "[ERP Agent] Checking if ports are available..."

check_port() {
    local port=$1
    if command -v netstat &> /dev/null; then
        if netstat -ano 2>/dev/null | grep -E ":$port.*LISTENING" > /dev/null 2>&1; then
            echo "[ERP Agent] Warning: Port $port is already in use"
            netstat -ano 2>/dev/null | grep -E ":$port.*LISTENING"
            return 1
        fi
    elif command -v lsof &> /dev/null; then
        if lsof -i :$port > /dev/null 2>&1; then
            echo "[ERP Agent] Warning: Port $port is already in use"
            return 1
        fi
    fi
    return 0
}

check_port $MCP_SERVICE_PORT || true
check_port $BACKEND_PORT || true

# ========== 阶段 1: 启动 MCP Service ==========
echo ""
echo "=========================================="
echo "[Stage 1/3] Starting MCP Service"
echo "=========================================="
echo "[ERP Agent] Starting MCP Service on http://localhost:$MCP_SERVICE_PORT"
cd "$SCRIPT_DIR/erp_mcp_service"
python main.py &
MCP_PID=$!

# 等待 MCP Service 启动并检查状态
MAX_WAIT=30
WAIT_INTERVAL=1
echo "[ERP Agent] Waiting for MCP Service to start (max ${MAX_WAIT}s)..."

for i in $(seq 1 $MAX_WAIT); do
    MCP_HEALTH_URL="http://localhost:$MCP_SERVICE_PORT/health"
    if curl -s --max-time 2 "$MCP_HEALTH_URL" > /dev/null 2>&1; then
        echo "[ERP Agent] ✓ MCP Service is ready at $MCP_HEALTH_URL (${i}s)"
        break
    fi
    if [ $i -eq $MAX_WAIT ]; then
        echo "[ERP Agent] ✗ MCP Service failed to start within ${MAX_WAIT}s"
        echo "[ERP Agent] Check logs for errors: kill $MCP_PID"
    fi
    sleep $WAIT_INTERVAL
done

# 额外等待确保服务完全初始化
sleep 2

# ========== 阶段 2: 启动 Backend ==========
echo ""
echo "=========================================="
echo "[Stage 2/3] Starting Backend Agent"
echo "=========================================="
echo "[ERP Agent] Starting backend on http://localhost:$BACKEND_PORT"
cd "$SCRIPT_DIR"
python -m app.main &
BACKEND_PID=$!

# 等待 Backend 启动并检查状态
MAX_WAIT=30
WAIT_INTERVAL=1
echo "[ERP Agent] Waiting for Backend to start (max ${MAX_WAIT}s)..."

for i in $(seq 1 $MAX_WAIT); do
    BACKEND_HEALTH_URL="http://localhost:$BACKEND_PORT/health"
    if curl -s --max-time 2 "$BACKEND_HEALTH_URL" > /dev/null 2>&1; then
        echo "[ERP Agent] ✓ Backend is ready at $BACKEND_HEALTH_URL (${i}s)"

        # 检查工具注册状态
        TOOLS_URL="http://localhost:$BACKEND_PORT/api/tools"
        TOOLS_RESPONSE=$(curl -s --max-time 5 "$TOOLS_URL" 2>/dev/null)
        if [ -n "$TOOLS_RESPONSE" ]; then
            TOOL_COUNT=$(echo "$TOOLS_RESPONSE" | grep -o '"name"' | wc -l 2>/dev/null || echo "0")
            echo "[ERP Agent] ✓ Tools registered: $TOOL_COUNT"
        fi
        break
    fi
    if [ $i -eq $MAX_WAIT ]; then
        echo "[ERP Agent] ✗ Backend failed to start within ${MAX_WAIT}s"
        echo "[ERP Agent] Check logs for errors: kill $BACKEND_PID"
    fi
    sleep $WAIT_INTERVAL
done

# 额外等待确保服务完全初始化
sleep 2

# ========== 阶段 3: 启动 Frontend ==========
echo ""
echo "=========================================="
echo "[Stage 3/3] Starting Frontend"
echo "=========================================="
echo "[ERP Agent] Starting frontend on http://localhost:5173"
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# 等待 Frontend 启动
sleep 5

echo ""
echo "=========================================="
echo "[ERP Agent] All services started successfully!"
echo "=========================================="
echo "[ERP Agent] Frontend:      http://localhost:5173"
echo "[ERP Agent] Backend:       http://localhost:$BACKEND_PORT"
echo "[ERP Agent] MCP Service:   http://localhost:$MCP_SERVICE_PORT"
echo ""
echo "[ERP Agent] Process IDs: MCP=$MCP_PID, Backend=$BACKEND_PID, Frontend=$FRONTEND_PID"
echo "[ERP Agent] Press Ctrl+C to stop all servers."
echo ""

# 捕获 Ctrl+C 信号，优雅停止所有服务
cleanup() {
    echo ""
    echo "[ERP Agent] Stopping all services..."
    [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
    [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null
    [ -n "$MCP_PID" ] && kill $MCP_PID 2>/dev/null
    echo "[ERP Agent] All services stopped."
    exit 0
}

trap cleanup EXIT INT TERM

# 保持脚本运行
wait