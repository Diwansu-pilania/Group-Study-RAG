#!/bin/bash
# ============================================
#  AI Learning Agent — Start All Services
# ============================================

echo ""
echo "🤖 AI Learning Agent — Starting Up"
echo "===================================="
echo ""

# Check .env exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  .env file created from .env.example"
    echo "   → Edit .env and add your OPENROUTER_API_KEY"
    echo ""
fi

# Install deps if needed
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt --quiet
else
    source .venv/bin/activate
fi

echo "🚀 Starting FastAPI backend on http://localhost:8000"
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

sleep 2

echo "🎨 Starting Streamlit frontend on http://localhost:8501"
streamlit run frontend/app.py --server.port 8501 &
FRONTEND_PID=$!

echo ""
echo "✅ Both services running!"
echo "   Backend  → http://localhost:8000"
echo "   Frontend → http://localhost:8501"
echo "   API Docs → http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep running
wait $BACKEND_PID $FRONTEND_PID
