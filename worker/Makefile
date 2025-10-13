.PHONY: test test-unit test-integration test-all install install-dev clean

# Run unit tests only (fast)
test:
	python -m pytest tests/unit/ -v

# Run unit tests explicitly
test-unit:
	python -m pytest tests/unit/ -v

# Run integration tests (requires OPENAI_API_KEY and test audio files)
test-integration:
	python -m pytest tests/integration/ -v -m integration

# Run all tests
test-all:
	python -m pytest tests/ -v

# Install dependencies
install:
	pip install -r requirements.txt

# Install dev dependencies (includes test tools)
install-dev:
	pip install -r requirements-dev.txt

# Clean cache files
clean:
	rm -rf __pycache__ .pytest_cache tests/__pycache__
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
