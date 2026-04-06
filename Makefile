.PHONY: help install dev redis worker test lint format clean

help:
	@echo "Clipzy Video Processing Backend"
	@echo ""
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make dev          - Run dev server"
	@echo "  make redis        - Start Redis (Docker)"
	@echo "  make worker       - Run video processing worker"
	@echo "  make test         - Run API tests"
	@echo "  make lint         - Run code linting"
	@echo "  make format       - Format code with black"
	@echo "  make clean        - Clean up generated files"

install:
	pip install -r requirements.txt

dev:
	python main.py

redis:
	docker-compose up -d redis redis-commander
	@echo ""
	@echo "Redis is running on localhost:6379"
	@echo "Redis Commander UI: http://localhost:8081"

redis-down:
	docker-compose down

worker:
	python run_worker.py --worker-id worker-1

test:
	python test_api.py

lint:
	flake8 app/
	mypy app/

format:
	black app/ main.py run_worker.py test_api.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf *.egg-info/
	rm -rf dist/
	rm -rf build/
	rm -rf storage/
	rm -f *.log
