# Infortic Scraper Architecture

A scalable web scraping framework designed for easy extension and maintainability.

## 📁 Project Structure

```
infortic/
├─ scraper/
│   ├─ core/
│   │   ├─ __init__.py
│   │   ├─ base_scraper.py      # Abstract base class for all scrapers
│   │   ├─ logger.py            # Singleton logger for centralized logging
│   │   └─ db.py                # Database client interface
│   ├─ lomba/
│   │   ├─ __init__.py
│   │   └─ infolomba_scraper.py # InfoLomba scraper implementation
│   └─ __init__.py
├─ .env                         # Environment variables
├─ requirements.txt             # Python dependencies
├─ run.py                       # Main runner script
└─ README.md                    # This file
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the project
cd infortic

# Install dependencies
pip install -r requirements.txt
```

### Automated Daily Execution

This project includes **GitHub Actions** for automated daily scraping:

- **Schedule**: Runs every day at midnight Indonesia time (WIB/UTC+7)
- **Command**: Automatically executes `python run.py --run-with-cleaning`
- **Auto-commit**: Commits and pushes results if there are changes
- **Manual Trigger**: Can be triggered manually from GitHub Actions tab

**Setup Steps for GitHub Repository:**
1. Create a new GitHub repository
2. Push this code to the repository
3. The workflow will automatically be available in the Actions tab
4. No additional configuration needed - it uses the built-in `GITHUB_TOKEN`

### 2. Configuration

Edit the `.env` file with your database credentials:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=infortic
DB_USER=postgres
DB_PASSWORD=your_password_here
```

### 3. Running Scrapers

```bash
# Run all scrapers
python run.py all

# Run specific scraper
python run.py infolomba

# Show help
python run.py help
```

## 🏗️ Architecture Overview

### Core Interfaces

#### 1. BaseScraper (Abstract Base Class)

All scrapers inherit from `BaseScraper` which provides:

- **Context Manager Support**: Automatic setup and cleanup of browser drivers/HTTP sessions
- **get_page()**: Navigate to a page with optional element waiting
- **fetch_static_page()**: Fetch static HTML content via HTTP
- **save_data()**: Save scraped data to database
- **scrape()**: Abstract method that must be implemented

```python
from scraper.core.base_scraper import BaseScraper

class MyScraper(BaseScraper):
    def scrape(self):
        with self as scraper:
            driver = scraper.get_page("https://example.com")
            # Extract data logic here
            return {"data": extracted_data}
```

#### 2. Logger (Singleton)

Centralized logging with:
- Automatic log rotation (10MB files, 5 backups)
- Console and file output
- Structured log format
- Scraper-specific logging methods

```python
from scraper.core.logger import Logger

logger = Logger()
logger.info("Starting scraper...")
logger.log_scraper_start("MyScraper", "https://example.com")
```

#### 3. DBClient

Database operations with:
- PostgreSQL support
- Environment-based configuration
- Bulk insert operations
- Connection management

```python
from scraper.core.db import DBClient

db = DBClient()
db.insert_many(data_list, "table_name")
```

## 📝 Adding New Scrapers

To add a new scraper, simply:

1. **Create a new scraper file** in the appropriate module directory
2. **Inherit from BaseScraper**
3. **Implement the scrape() method**

Example:

```python
# scraper/news/news_scraper.py
from ..core.base_scraper import BaseScraper

class NewsScraper(BaseScraper):
    def scrape(self):
        with self as scraper:
            driver = scraper.get_page("https://news-site.com")
            # Your scraping logic here
            articles = self._extract_articles(driver)
            self.save_data(articles, "articles")
            return {"articles": articles}
    
    def _extract_articles(self, driver):
        # Implementation details
        pass
```

4. **Register in run.py** (optional):

```python
# Add to run_all_scrapers() function
scrapers = [
    ("InfoLomba", run_infolomba_scraper),
    ("News", run_news_scraper),  # Add your scraper here
]
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | Database host | localhost |
| `DB_PORT` | Database port | 5432 |
| `DB_NAME` | Database name | infortic |
| `DB_USER` | Database user | postgres |
| `DB_PASSWORD` | Database password | (required) |
| `SCRAPER_TIMEOUT` | Default timeout for operations | 30 |
| `SCRAPER_HEADLESS` | Run browser in headless mode | true |
| `LOG_LEVEL` | Logging level | INFO |

### Dependencies

Key dependencies include:
- **selenium**: Browser automation
- **aiohttp**: Async HTTP requests
- **psycopg2-binary**: PostgreSQL adapter
- **beautifulsoup4**: HTML parsing
- **python-dotenv**: Environment variable management

## 📊 Features

- ✅ **Context Manager Support**: Automatic resource management
- ✅ **Singleton Logger**: Centralized logging across all scrapers
- ✅ **Database Abstraction**: Easy data persistence
- ✅ **Async Support**: Both sync and async operation modes
- ✅ **Error Handling**: Comprehensive error logging and recovery
- ✅ **Rate Limiting**: Built-in delays to respect website policies
- ✅ **Headless Operation**: Configurable browser mode
- ✅ **Extensible Design**: Easy to add new scrapers

## 🔍 Example Usage

```python
# Simple usage
from scraper.lomba.infolomba_scraper import InfoLombaScraper

scraper = InfoLombaScraper()
results = scraper.scrape()
print(f"Scraped {len(results['competitions'])} competitions")
```

## Data Cleaning Behavior

The cleaning routine for the `lomba` table in the database ensures that stale data is not processed, maintaining the integrity of new data inserted. Key improvements include:

- **Validated Deletion**: Ensures all records are removed safely using checks for non-null IDs.
- **Comprehensive Logging**: Captures detailed information about the cleaning process for auditability.
- **Robust Error Handling**: Halts the scraping process if cleaning errors occur, preventing further operations with stale data.
- **Improved Exception Management**: Provides clear messaging and prevents data insertion if cleaning fails.
- **Optional Cleaning Control**: The method `insert_lomba_rows()` can skip cleaning if needed by passing `clean_first=False`.

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check your `.env` file configuration
   - Ensure PostgreSQL is running
   - Verify network connectivity

2. **ChromeDriver Issues**
   - Install Chrome browser
   - Update ChromeDriver via webdriver-manager
   - Check PATH environment variable

3. **Import Errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python path configuration

### Logs

Logs are automatically stored in the `logs/` directory with rotation. Check `logs/scraper.log` for detailed information about scraper operations.

## 🤝 Contributing

1. Follow the established patterns in `BaseScraper`
2. Add appropriate logging using the `Logger` singleton
3. Include error handling and cleanup
4. Document your scraper's specific requirements
5. Test thoroughly before committing

## 📄 License

This project is part of the Infortic scraping system.
