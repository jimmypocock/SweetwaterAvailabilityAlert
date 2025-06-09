#!/usr/bin/env python3
"""
Test script for local development and debugging of the product scraper.
This helps test the scraping logic without deploying to AWS.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_scraping(url=None):
    """Test the scraping functionality locally"""
    # Import the function from lambda_function
    try:
        from lambda_function import check_product_availability
    except ImportError:
        logger.error("Could not import lambda_function. Make sure it's in the src/ directory")
        return

    # Use provided URL or default
    if not url:
        url = "https://www.sweetwater.com/store/detail/TAG3CSDB--yamaha-tag3-c-transacoustic-dreadnought-acoustic-electric-guitar-sand-burst"

    logger.info(f"Testing scraping for URL: {url}")

    try:
        is_available, product_info = check_product_availability(url)

        print("\n" + "="*50)
        print("SCRAPING RESULTS")
        print("="*50)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"URL: {url}")
        print(f"Available: {'YES' if is_available else 'NO'}")
        print(f"Product Title: {product_info['title']}")
        print(f"Price: {product_info['price']}")
        print("="*50 + "\n")

        # Save results to file for analysis
        with open('test_results.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'results': product_info
            }, f, indent=2)

        logger.info("Results saved to test_results.json")

    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        import traceback
        traceback.print_exc()

def test_email_notification():
    """Test email notification locally (dry run)"""
    try:
        from lambda_function import send_notification
    except ImportError:
        logger.error("Could not import lambda_function")
        return

    # Mock product info
    product_info = {
        'title': 'Test Product - Yamaha Guitar',
        'price': '$999.99',
        'url': 'https://example.com/product',
        'available': True
    }

    # Set test environment variables
    os.environ['SENDER_EMAIL'] = input("Enter sender email (or press enter to skip): ") or "sender@example.com"
    os.environ['RECIPIENT_EMAIL'] = input("Enter recipient email (or press enter to skip): ") or "recipient@example.com"

    if os.environ['SENDER_EMAIL'] == "sender@example.com":
        logger.info("Skipping actual email send (using example emails)")
        logger.info(f"Would send email from {os.environ['SENDER_EMAIL']} to {os.environ['RECIPIENT_EMAIL']}")
        logger.info(f"Subject: Product Available: {product_info['title']}")
    else:
        try:
            logger.info("Attempting to send test email...")
            message_id = send_notification(product_info)
            logger.info(f"Email sent successfully! Message ID: {message_id}")
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")

def analyze_html_structure(url):
    """Analyze the HTML structure of a page to help customize scraping"""
    import requests
    from bs4 import BeautifulSoup

    logger.info(f"Analyzing HTML structure for: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        print("\n" + "="*50)
        print("HTML STRUCTURE ANALYSIS")
        print("="*50)

        # Look for common e-commerce elements
        elements_to_find = {
            'Product Title': ['h1', 'h2', {'class': 'product-title'}, {'class': 'product-name'}],
            'Price': [{'class': 'price'}, {'class': 'product-price'}, {'itemprop': 'price'}],
            'Add to Cart Button': ['button', {'class': 'add-to-cart'}, {'id': 'add-to-cart'}],
            'Availability': [{'class': 'availability'}, {'class': 'stock-status'}, {'class': 'in-stock'}],
            'Out of Stock': [text for text in soup.stripped_strings if 'out of stock' in text.lower()]
        }

        for element_name, selectors in elements_to_find.items():
            print(f"\n{element_name}:")
            found = False

            if element_name == 'Out of Stock':
                if selectors:
                    print(f"  Found 'out of stock' text in page")
                    found = True
            else:
                for selector in selectors:
                    if isinstance(selector, dict):
                        element = soup.find(attrs=selector)
                    else:
                        element = soup.find(selector)

                    if element:
                        print(f"  Found: {element.name} - {dict(element.attrs) if element.attrs else 'no attributes'}")
                        if element.text:
                            print(f"  Text: {element.text.strip()[:100]}...")
                        found = True
                        break

            if not found:
                print("  Not found with common patterns")

        # Save full HTML for manual inspection
        with open('page_structure.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())

        print("\nFull HTML saved to page_structure.html for manual inspection")
        print("="*50 + "\n")

    except Exception as e:
        logger.error(f"Error analyzing HTML: {str(e)}")

def main():
    """Main test function"""
    print("\nProduct Availability Scraper - Local Test Tool")
    print("=" * 50)

    while True:
        print("\nChoose an option:")
        print("1. Test scraping with default URL")
        print("2. Test scraping with custom URL")
        print("3. Test email notification (dry run)")
        print("4. Analyze HTML structure")
        print("5. Exit")

        choice = input("\nEnter your choice (1-5): ")

        if choice == '1':
            test_scraping()
        elif choice == '2':
            custom_url = input("Enter the product URL: ")
            test_scraping(custom_url)
        elif choice == '3':
            test_email_notification()
        elif choice == '4':
            url = input("Enter URL to analyze (or press enter for default): ")
            if not url:
                url = "https://www.sweetwater.com/store/detail/TAG3CSDB--yamaha-tag3-c-transacoustic-dreadnought-acoustic-electric-guitar-sand-burst"
            analyze_html_structure(url)
        elif choice == '5':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()