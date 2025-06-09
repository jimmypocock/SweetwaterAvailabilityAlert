# Sweetwater Availability Alert

An AWS serverless application that monitors product availability on Sweetwater.com and sends email notifications when products become available. Uses CloudScraper to bypass anti-bot protections for reliable monitoring.

> This project is for educational purposes. Sweetwater allows you to sign up for email alerts when inventory is back in stock.

## Overview

This application checks a Sweetwater product URL every hour and sends you an email notification when the item becomes available. It's designed to be cost-effective (runs within AWS free tier limits) and reliable.

### Key Features

- 🔍 Hourly product availability checks
- 📧 Email notifications when products come in stock
- 🛡️ CloudScraper integration to bypass anti-bot measures
- 💰 Cost-effective (stays within AWS free tier)
- 🔄 Retry logic with exponential backoff
- 📊 CloudWatch monitoring and error alerts

## Architecture

- **AWS Lambda**: Runs the scraping logic (Python 3.12)
- **Amazon EventBridge**: Triggers the Lambda function every hour
- **Amazon SES**: Sends email notifications
- **CloudScraper**: Bypasses anti-bot protections
- **AWS SAM**: Infrastructure as code for easy deployment

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **AWS SAM CLI** installed
4. **Python 3.12** installed locally
5. **Git** (to clone this repository)

### Installing Prerequisites

#### AWS CLI

- **macOS**: `brew install awscli`
- **Windows**: Download from [AWS CLI Downloads](https://aws.amazon.com/cli/)
- **Linux**:
  ```bash
  curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
  unzip awscliv2.zip
  sudo ./aws/install
  ```

#### SAM CLI

- **macOS**: `brew tap aws/tap && brew install aws-sam-cli`
- **Windows**: Download from [SAM CLI Downloads](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
- **Linux**:
  ```bash
  wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
  unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
  sudo ./sam-installation/install
  ```

#### Configure AWS Credentials

**Option 1: Standard AWS Credentials**

```bash
aws configure
```

Enter your AWS Access Key ID, Secret Access Key, and preferred region (e.g., us-east-1).

**Option 2: AWS SSO (Multiple Accounts)**
If you use AWS SSO with multiple accounts:

```bash
# List available SSO profiles
aws configure list-profiles

# Login to your desired profile
aws sso login --profile your-profile-name

# Export the profile for all subsequent commands
export AWS_PROFILE=your-profile-name

# Or use inline with commands
sam deploy --guided --profile your-profile-name
```

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd SweetwaterAvailabilityAlert
```

### 2. (Optional) Set Up AWS Profile

If using AWS SSO or multiple AWS accounts, create a `.env` file:

```bash
# Copy the example file
cp .env.example .env

# Edit .env to set your AWS profile
echo "AWS_PROFILE=your-profile-name" > .env
```

This way you won't need to export the profile each time - the Makefile will automatically use it.

### 3. Verify Email Addresses in Amazon SES

**This step is REQUIRED before deployment!**

```bash
# Use the convenient make command
make verify-ses

# Or manually:
aws ses verify-email-identity --email-address your-sender@email.com
aws ses verify-email-identity --email-address your-recipient@email.com
```

After running the commands:

1. Check your email inbox for verification emails from AWS
2. Click the verification links
3. Verify the emails are confirmed: `make check-ses`

**Important SES Notes:**

- **Sender email**: Always requires verification
- **Recipient email**: Requires verification only if SES is in Sandbox mode (default)
- **Sandbox mode**: Limited to 200 emails/day, can only send to verified emails
- **Production mode**: No recipient verification needed (requires AWS approval)

### 4. Build and Deploy

```bash
# Build the application
make build

# Deploy (first time - interactive mode)
make deploy

# Or using SAM directly:
sam deploy --guided
```

During deployment, you'll be prompted for:

- **Stack Name**: `[default: product-availability-scraper]`
- **AWS Region**: `[default: us-east-1]`
- **ProductUrl**: The Sweetwater URL to monitor
- **SenderEmail**: Your verified sender email
- **RecipientEmail**: Email to receive notifications
- **SkipNotification**: `[default: false]` Set to true for testing without emails

### 5. Test the Deployment

```bash
# Manually trigger the Lambda function
make invoke

# Check CloudWatch logs
make logs
```

## Configuration

### Environment Variables

The Lambda function uses these environment variables:

| Variable            | Description                                       | Required |
| ------------------- | ------------------------------------------------- | -------- |
| `PRODUCT_URL`       | Sweetwater product URL to monitor                 | Yes      |
| `SENDER_EMAIL`      | Email address to send from (must be SES verified) | Yes      |
| `RECIPIENT_EMAIL`   | Email address to receive notifications            | Yes      |
| `SKIP_NOTIFICATION` | Set to "true" to test without sending emails      | No       |

### Updating Configuration

```bash
# Update environment variables
aws lambda update-function-configuration \
  --function-name SweetwaterAvailabilityChecker \
  --environment Variables="{PRODUCT_URL='https://new-url',SENDER_EMAIL='sender@email.com',RECIPIENT_EMAIL='recipient@email.com'}"

# Enable/disable notifications
make enable-notifications   # Set SKIP_NOTIFICATION=false
make disable-notifications  # Set SKIP_NOTIFICATION=true
```

### Changing Check Frequency

By default, the function runs every hour. To change this, modify the `Schedule` in `template.yaml`:

```yaml
Schedule: rate(30 minutes)  # Check every 30 minutes
Schedule: rate(2 hours)     # Check every 2 hours
```

Then redeploy: `make deploy-quick`

## Development

### Project Structure

```
SweetwaterAvailabilityAlert/
├── src/
│   └── lambda_function.py      # Main Lambda function
├── dependencies/
│   └── requirements.txt        # Python dependencies
├── template.yaml              # SAM/CloudFormation template
├── Makefile                   # Convenience commands
├── test_scraper.py           # Local testing tool
└── README.md                 # This file
```

### Local Testing

Test the scraper locally before deploying:

```bash
# Interactive testing tool
python test_scraper.py

# Test with SAM local
sam local invoke ProductAvailabilityFunction
```

### How the Scraper Works

The scraper uses CloudScraper to bypass Sweetwater's anti-bot protections and looks for:

- `<component>` tags containing "Add to Cart" text (indicates available)
- "Notify me when in stock" text (indicates out of stock)
- Product title and price information

Key features:

- Retry logic with exponential backoff
- Detailed logging for debugging
- Graceful error handling

## Monitoring

### View Logs

```bash
# Tail CloudWatch logs
make logs

# Or with SAM
sam logs -n SweetwaterAvailabilityChecker --tail
```

### Set Up Error Alerts

An SNS topic is created for function errors. Subscribe to it:

```bash
aws sns subscribe \
  --topic-arn <ErrorTopicArn from stack outputs> \
  --protocol email \
  --notification-endpoint your-email@example.com
```

### Check Execution History

```bash
# Recent Lambda invocations
aws lambda list-functions --query "Functions[?FunctionName=='SweetwaterAvailabilityChecker']"

# CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=SweetwaterAvailabilityChecker \
  --statistics Sum \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-31T23:59:59Z \
  --period 86400
```

## Cost Estimation

Running within AWS free tier limits:

- **Lambda**: 1 million free requests/month (you'll use ~730)
- **CloudWatch Logs**: 5GB free ingestion/month
- **SES**: $0.10 per 1,000 emails
- **EventBridge**: Free for this use case

**Estimated monthly cost**: < $0.10 (mainly SES email costs)

## Troubleshooting

### Lambda Function Not Running

1. Check EventBridge rule is enabled:

   ```bash
   aws events describe-rule --name ProductAvailabilityCheck
   ```

2. Check Lambda permissions:
   ```bash
   aws lambda get-policy --function-name SweetwaterAvailabilityChecker
   ```

### Emails Not Sending

1. Verify SES identities:

   ```bash
   make check-ses
   ```

2. Check if in SES sandbox:

   - Sandbox mode requires all recipients to be verified
   - Request production access if needed

3. Check Lambda logs for SES errors:
   ```bash
   make logs
   ```

### Scraping Not Working

1. Test locally first:

   ```bash
   python test_scraper.py
   ```

2. Check if Sweetwater changed their HTML structure
3. Review CloudWatch logs for specific errors

### 403 Forbidden Errors

The application uses CloudScraper to handle anti-bot measures. If you still get 403 errors:

1. The site may have updated their protection
2. Check CloudScraper GitHub for updates
3. Consider increasing retry delays

## Maintenance

### Update Dependencies

```bash
# Update Python packages
cd dependencies
pip install -r requirements.txt -t python/ --upgrade

# Rebuild and deploy
make build && make deploy-quick
```

### Delete the Stack

```bash
# Remove all AWS resources
make delete

# Or with SAM
sam delete
```

## Available Make Commands

```bash
make help                # Show all available commands
make setup              # Set up project structure
make build              # Build SAM application
make deploy             # Deploy with guided mode
make deploy-quick       # Deploy without guided mode
make test               # Run local tests
make invoke             # Manually trigger Lambda
make logs               # View CloudWatch logs
make clean              # Clean build artifacts
make login              # Login to AWS SSO (if using SSO)
make verify-ses         # Verify SES email addresses
make check-ses          # Check SES verification status
make update-env         # Update Lambda environment variables
make enable-notifications  # Enable email notifications
make disable-notifications # Disable notifications (testing)
make info               # Show stack information
make delete             # Delete the entire stack
```

## Security Considerations

- IAM roles follow least privilege principle
- Email addresses stored as environment variables
- No sensitive data in CloudWatch logs
- All AWS resources are tagged for easy management

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test your changes locally
4. Submit a pull request

## License

This project is licensed under the MIT License.
