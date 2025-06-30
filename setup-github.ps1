# GitHub Repository Setup Script for Infortic Scraper
# Run this script after creating your GitHub repository

Write-Host "🚀 Setting up Infortic Scraper GitHub Repository" -ForegroundColor Green
Write-Host ""

# Check if git is installed
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Git is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Git and try again: https://git-scm.com/downloads"
    exit 1
}

# Initialize git repository if not already initialized
if (-not (Test-Path ".git")) {
    Write-Host "📁 Initializing Git repository..." -ForegroundColor Yellow
    git init
    Write-Host "✅ Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "📁 Git repository already exists" -ForegroundColor Green
}

# Add all files to git
Write-Host "📦 Adding files to Git..." -ForegroundColor Yellow
git add .

# Create initial commit
Write-Host "💾 Creating initial commit..." -ForegroundColor Yellow
git commit -m "Initial commit: Infortic Scraper with GitHub Actions automation

- Added daily scraper automation via GitHub Actions
- Scheduled to run at midnight Indonesia time (WIB/UTC+7)
- Includes automatic data cleaning and result committing
- Complete project structure with logging and error handling
- PostgreSQL database integration
- Selenium-based web scraping framework"

# Set main branch
Write-Host "🌟 Setting main branch..." -ForegroundColor Yellow
git branch -M main

Write-Host ""
Write-Host "🎯 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Create a new repository on GitHub"
Write-Host "2. Copy the repository URL (e.g., https://github.com/username/repo-name.git)"
Write-Host "3. Run the following command to add remote and push:"
Write-Host ""
Write-Host "   git remote add origin YOUR_REPOSITORY_URL" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor White
Write-Host ""
Write-Host "4. After pushing, go to GitHub Actions tab to see the workflow"
Write-Host "5. The scraper will automatically run daily at midnight Indonesia time"
Write-Host ""
Write-Host "✨ Setup complete! Your scraper is ready for automation." -ForegroundColor Green
