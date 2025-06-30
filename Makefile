.PHONY: run test install clean help

# Default target
help:
	@echo "Available commands:"
	@echo "  make run     - Run the scraper in headless mode"
	@echo "  make test    - Run all tests"
	@echo "  make install - Install dependencies"
	@echo "  make clean   - Clean up temporary files"
	@echo "  make env     - Create .env.example file"

# Run the scraper in headless mode
run:
	@echo "Running InfoLomba scraper in headless mode..."
	@echo "Setting SCRAPER_HEADLESS=true for headless operation"
	@set SCRAPER_HEADLESS=true && python run.py

# Run tests
test:
	@echo "Running unit tests..."
	@python -m pytest tests/ -v

# Install dependencies
install:
	@echo "Installing dependencies..."
	@pip install -r requirements.txt
	@pip install pytest  # Add pytest for testing

# Create .env.example file
env:
	@echo "Creating .env.example file..."
	@echo "# Supabase Configuration" > .env.example
	@echo "SUPABASE_URL=your_supabase_url_here" >> .env.example
	@echo "SUPABASE_ANON_KEY=your_supabase_anon_key_here" >> .env.example
	@echo "" >> .env.example
	@echo "# Scraper Configuration" >> .env.example
	@echo "SCRAPER_TIMEOUT=30" >> .env.example
	@echo "SCRAPER_HEADLESS=true" >> .env.example
	@echo "" >> .env.example
	@echo "# Logging Configuration" >> .env.example
	@echo "LOG_LEVEL=INFO" >> .env.example
	@echo "LOG_FILE_MAX_SIZE=10485760  # 10MB in bytes" >> .env.example
	@echo "LOG_BACKUP_COUNT=5" >> .env.example
	@echo "" >> .env.example
	@echo "# Optional: Rate limiting" >> .env.example
	@echo "RATE_LIMIT_DELAY=1  # seconds between requests" >> .env.example
	@echo "MAX_RETRIES=3" >> .env.example
	@echo ".env.example created successfully!"

# Clean up temporary files
clean:
	@echo "Cleaning up temporary files..."
	@if exist "__pycache__" rmdir /s /q __pycache__
	@if exist "*.pyc" del /q *.pyc
	@if exist ".pytest_cache" rmdir /s /q .pytest_cache
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
	@echo "Cleanup completed!"
