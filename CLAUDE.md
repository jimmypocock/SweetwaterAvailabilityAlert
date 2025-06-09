# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AWS serverless application that monitors product availability on Sweetwater.com and sends email notifications when products become available. It uses AWS Lambda (Python 3.11), EventBridge for scheduling, and SES for email notifications, deployed via AWS SAM.

## Architecture

The application consists of:
- **Lambda Function** (`src/lambda_function.py`): Scrapes product pages and sends notifications
- **EventBridge Rule**: Triggers the Lambda function hourly
- **SES Integration**: Sends email notifications when products become available
- **SAM Template** (`template.yaml`): Defines AWS infrastructure

## Development Commands

### Setup and Dependencies
```bash
# Set up project structure and install dependencies
make setup

# Install dependencies for Lambda layer
cd dependencies && pip install -r requirements.txt -t python/
```

### Build and Deploy
```bash
# Build the SAM application
make build
sam build

# Deploy with guided mode (first time)
make deploy
sam deploy --guided

# Quick deploy (uses existing samconfig.toml)
make deploy-quick
sam deploy
```

### Testing
```bash
# Run local test script (interactive testing tool)
python test_scraper.py

# Test Lambda function locally
sam local invoke ProductAvailabilityFunction

# Invoke deployed function
make invoke
aws lambda invoke --function-name ProductAvailabilityChecker output.json
```

### Monitoring and Logs
```bash
# Tail CloudWatch logs
make logs
sam logs -n ProductAvailabilityChecker --tail
```

### Email Configuration
```bash
# Verify SES email addresses
make verify-ses

# Check SES verification status
make check-ses

# Enable/disable notifications
make enable-notifications
make disable-notifications
```

### Maintenance
```bash
# Clean build artifacts
make clean

# Get stack information
make info

# Delete the stack
make delete
```

## Key Implementation Details

### Scraping Logic (src/lambda_function.py)
- Uses CloudScraper to bypass anti-bot protections (replaced requests library)
- The `check_product_availability()` function looks for Sweetwater-specific patterns:
  - `<component>` tags with "Add to Cart" text
  - "Notify me when in stock" text (indicates out of stock)
  - "In Stock!" indicators
  - dimension25 tracking parameters for stock status
- Implements retry logic with exponential backoff
- Uses BeautifulSoup4 for HTML parsing
- Returns availability status and product information

### Environment Variables
- `PRODUCT_URL`: The Sweetwater product URL to monitor
- `SENDER_EMAIL`: Email address to send from (must be SES verified)
- `RECIPIENT_EMAIL`: Email address to receive notifications
- `SKIP_NOTIFICATION`: Set to "true" to test without sending emails

### Testing Approach
The `test_scraper.py` script provides an interactive tool for:
1. Testing scraping with default or custom URLs
2. Testing email notifications (dry run)
3. Analyzing HTML structure of product pages
4. Saving results for debugging

When making changes to the scraping logic, use `test_scraper.py` option 4 to analyze the HTML structure and identify the correct selectors.