#!/bin/bash
# setup-modal-infrastructure.sh - Automated setup for Modal, S3, and RabbitMQ

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Clipzy Modal Infrastructure Setup${NC}"
echo -e "${GREEN}========================================${NC}"

# 1. Check Python version
echo -e "\n${YELLOW}[1/7] Checking Python installation...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python ${python_version} found${NC}"

# 2. Install dependencies
echo -e "\n${YELLOW}[2/7] Installing Python dependencies...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# 3. Install Modal CLI
echo -e "\n${YELLOW}[3/7] Installing Modal CLI...${NC}"
pip install modal
echo -e "${GREEN}✓ Modal CLI installed${NC}"

# 4. Setup Modal authentication
echo -e "\n${YELLOW}[4/7] Setting up Modal authentication...${NC}"
echo "Opening browser for Modal authentication..."
python3 -m modal setup
echo -e "${GREEN}✓ Modal authentication configured${NC}"

# 5. Start Docker services
echo -e "\n${YELLOW}[5/7] Starting RabbitMQ and Redis with Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

docker-compose up -d
echo -e "${GREEN}✓ RabbitMQ and Redis started${NC}"

# 6. Wait for services to be ready
echo -e "\n${YELLOW}[6/7] Waiting for services to be ready...${NC}"
sleep 5
docker-compose exec -T redis redis-cli ping > /dev/null 2>&1 && echo -e "${GREEN}✓ Redis ready${NC}" || echo -e "${RED}✗ Redis not responding${NC}"
docker-compose exec -T rabbitmq rabbitmq-diagnostics ping > /dev/null 2>&1 && echo -e "${GREEN}✓ RabbitMQ ready${NC}" || echo -e "${RED}✗ RabbitMQ not responding${NC}"

# 7. Test S3 connectivity (if credentials provided)
echo -e "\n${YELLOW}[7/7] Testing AWS S3 connectivity...${NC}"
if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    python3 << 'EOF'
from app.services.storage_service import StorageService
try:
    storage = StorageService()
    print("✓ S3 connector initialized successfully")
except Exception as e:
    print(f"Note: S3 connectivity check skipped (not critical): {e}")
EOF
else
    echo -e "${YELLOW}⚠ AWS credentials not set in environment. Skipping S3 test.${NC}"
    echo -e "Update .env with AWS credentials to enable S3."
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Update .env with your AWS credentials:"
echo "   - AWS_ACCESS_KEY_ID"
echo "   - AWS_SECRET_ACCESS_KEY"
echo "   - S3_BUCKET_NAME"
echo ""
echo "2. Start the API server:"
echo "   python main.py"
echo ""
echo "3. Access services:"
echo "   - RabbitMQ: http://localhost:15672 (guest/guest)"
echo "   - Redis: http://localhost:8081"
echo ""
echo "4. Process a video using Modal GPU:"
echo "   python3 -m modal run app.workers.modal_worker::process_job"
echo ""
echo -e "${YELLOW}For detailed documentation, see: MODAL_SETUP.md${NC}"
