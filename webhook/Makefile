.PHONY: test install install-dev clean

# Run tests
test:
	pytest tests/ -v

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
