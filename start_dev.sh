#!/bin/bash
# Script để khởi động cả Backend và Frontend

echo "🚀 Starting Backend and Frontend..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend is running
if ! pgrep -f "manage.py runserver" > /dev/null; then
    echo -e "${BLUE}📦 Starting Backend...${NC}"
    cd backend/hue_portal
    source ../venv/bin/activate
    python3 manage.py runserver 0.0.0.0:8000 > ../../backend.log 2>&1 &
    BACKEND_PID=$!
    echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
    echo -e "${YELLOW}   Backend URL: http://localhost:8000${NC}"
    cd ../..
else
    echo -e "${GREEN}✅ Backend already running${NC}"
fi

# Check if frontend is running
if ! pgrep -f "vite" > /dev/null; then
    echo -e "${BLUE}📦 Starting Frontend...${NC}"
    cd frontend
    npm run dev > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
    echo -e "${YELLOW}   Frontend URL: http://localhost:3000${NC}"
    cd ..
else
    echo -e "${GREEN}✅ Frontend already running${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Both services are running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${BLUE}Backend:  http://localhost:8000${NC}"
echo -e "${BLUE}Frontend: http://localhost:3000${NC}"
echo ""
echo -e "${YELLOW}To stop services:${NC}"
echo "  pkill -f 'manage.py runserver'"
echo "  pkill -f 'vite'"
echo ""
echo -e "${YELLOW}To view logs:${NC}"
echo "  tail -f backend.log"
echo "  tail -f frontend.log"




