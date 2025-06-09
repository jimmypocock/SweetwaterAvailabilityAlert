import os
import json
import logging
import cloudscraper
from bs4 import BeautifulSoup
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SES client
ses_client = boto3.client('ses', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

def check_product_availability(url, max_retries=3):
    """
    Scrape the product URL and check if it's available.
    Returns tuple: (is_available: bool, product_info: dict)
    """
    import time
    
    for attempt in range(max_retries):
        try:
            # Create a cloudscraper instance
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',  # More common user agent
                    'desktop': True
                },
                delay=10  # Delay between retries
            )
            
            logger.info(f"Fetching URL: {url} (attempt {attempt + 1}/{max_retries})")
            response = scraper.get(url, timeout=30)
            response.raise_for_status()
            
            if response.status_code == 200:
                break
                
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))  # Exponential backoff
                continue
            else:
                raise
    
    try:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract product title - Sweetwater uses h1 with class "product__name"
        title_element = soup.find('h1', {'class': 'product__name'}) or \
                       soup.find('h1', {'itemprop': 'name'}) or \
                       soup.find('h1')
        product_title = title_element.text.strip() if title_element else "Unknown Product"

        # Sweetwater uses <component> tags for Add to Cart
        add_to_cart_component = soup.find('component', string=lambda t: t and 'add to cart' in t.lower() if t else False)
        
        # Look for "In Stock!" text with check icon
        in_stock_indicator = soup.find('strong', string=lambda t: t and 'in stock!' in t.lower() if t else False)
        
        # Check for out of stock indicators
        page_text = response.text.lower()
        
        # Look for "Notify me when in stock" which is a clear out of stock indicator
        notify_me_element = soup.find(string=lambda t: t and 'notify me when in stock' in t.lower() if t else False)
        
        # Check for dimension25 tracking parameter which indicates stock status
        has_out_of_stock_tracking = "'dimension25':'out of stock'" in response.text
        has_in_stock_tracking = "'dimension25':'in stock'" in response.text
        
        # Determine availability based on multiple factors
        is_available = False
        
        # Primary logic: If there's an "Add to Cart" component and NO "Notify me" text, it's available
        if add_to_cart_component and not notify_me_element:
            is_available = True
        
        # Override: If we find explicit out of stock indicators, mark as unavailable
        if notify_me_element or has_out_of_stock_tracking:
            is_available = False
            
        # Additional validation: If we found "In Stock!" text, definitely available
        if in_stock_indicator:
            is_available = True

        # Extract price - Sweetwater uses various price classes
        price = "Price not found"
        
        # Try different price selectors
        price_element = soup.find('span', {'class': 'product__price'}) or \
                       soup.find('span', {'itemprop': 'price'}) or \
                       soup.find('meta', {'itemprop': 'price'}) or \
                       soup.find('div', {'class': lambda x: x and 'price' in x if x else False})
        
        if price_element:
            if price_element.name == 'meta':
                price = f"${price_element.get('content', 'N/A')}"
            else:
                price_text = price_element.text.strip()
                # Extract price from text that might contain other content
                import re
                price_match = re.search(r'\$[\d,]+\.?\d*', price_text)
                if price_match:
                    price = price_match.group()
                else:
                    price = price_text

        product_info = {
            'title': product_title,
            'price': price,
            'url': url,
            'available': is_available
        }

        logger.info(f"Product check complete: {product_info}")
        
        # Log additional debug info
        logger.debug(f"Add to cart found: {add_to_cart_component is not None}")
        logger.debug(f"Notify element found: {notify_me_element is not None}")
        logger.debug(f"Out of stock tracking: {has_out_of_stock_tracking}")
        
        return is_available, product_info

    except Exception as e:
        logger.error(f"Error parsing product page {url}: {str(e)}")
        raise

def send_notification(product_info):
    """
    Send email notification using Amazon SES
    """
    sender = os.environ.get('SENDER_EMAIL')
    recipient = os.environ.get('RECIPIENT_EMAIL')

    if not sender or not recipient:
        raise ValueError("SENDER_EMAIL and RECIPIENT_EMAIL environment variables must be set")

    subject = f"Product Available: {product_info['title']}"

    # HTML body
    body_html = f"""
    <html>
    <head></head>
    <body>
        <h2>Good news! The product you're tracking is now available!</h2>
        <p><strong>Product:</strong> {product_info['title']}</p>
        <p><strong>Price:</strong> {product_info['price']}</p>
        <p><strong>URL:</strong> <a href="{product_info['url']}">{product_info['url']}</a></p>
        <br>
        <p><a href="{product_info['url']}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">View Product</a></p>
    </body>
    </html>
    """

    # Text body (fallback)
    body_text = f"""
    Good news! The product you're tracking is now available!

    Product: {product_info['title']}
    Price: {product_info['price']}
    URL: {product_info['url']}
    """

    try:
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [recipient],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': 'UTF-8',
                        'Data': body_html,
                    },
                    'Text': {
                        'Charset': 'UTF-8',
                        'Data': body_text,
                    },
                },
                'Subject': {
                    'Charset': 'UTF-8',
                    'Data': subject,
                },
            },
            Source=sender,
        )
        logger.info(f"Email sent! Message ID: {response['MessageId']}")
        return response['MessageId']
    except ClientError as e:
        logger.error(f"Error sending email: {e.response['Error']['Message']}")
        raise

def lambda_handler(event, context):
    """
    Main Lambda handler function
    """
    logger.info(f"Lambda function invoked with event: {json.dumps(event)}")

    # Get product URL from environment variable
    product_url = os.environ.get('PRODUCT_URL')
    if not product_url:
        raise ValueError("PRODUCT_URL environment variable must be set")

    try:
        # Check if we should skip notification (for testing or if already notified)
        skip_notification = os.environ.get('SKIP_NOTIFICATION', 'false').lower() == 'true'

        # Check product availability
        is_available, product_info = check_product_availability(product_url)

        response_body = {
            'statusCode': 200,
            'product_info': product_info,
            'notification_sent': False
        }

        if is_available:
            logger.info("Product is available!")
            if not skip_notification:
                # Send notification
                message_id = send_notification(product_info)
                response_body['notification_sent'] = True
                response_body['message_id'] = message_id

                # Optionally, set SKIP_NOTIFICATION to true to avoid repeated notifications
                # This would require updating the Lambda environment variable
            else:
                logger.info("Skipping notification as SKIP_NOTIFICATION is set to true")
        else:
            logger.info("Product is not available yet")

        return {
            'statusCode': 200,
            'body': json.dumps(response_body)
        }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }