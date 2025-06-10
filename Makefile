.PHONY: help build deploy test clean logs invoke setup login verify-ses check-ses

# Load .env file if it exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# Default target
help:
	@echo "Available commands:"
	@echo "  make setup       - Set up project structure and install dependencies"
	@echo "  make build       - Build the SAM application"
	@echo "  make deploy      - Deploy the application to AWS"
	@echo "  make test        - Run local tests"
	@echo "  make invoke      - Manually invoke the Lambda function"
	@echo "  make logs        - Tail CloudWatch logs"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make login       - Login to AWS SSO (if using SSO)"
	@echo "  make verify-ses  - Verify SES email addresses"

# Set up project structure
setup:
	@echo "Setting up project structure..."
	mkdir -p src dependencies
	@echo "Installing dependencies for Lambda layer..."
	cd dependencies && pip install -r requirements.txt -t python/
	@echo "Setup complete!"

# Build the SAM application
build:
	@echo "Building SAM application..."
	@if [ -n "$$AWS_PROFILE" ]; then \
		echo "Using AWS Profile: $$AWS_PROFILE"; \
		sam build --profile $$AWS_PROFILE; \
	else \
		sam build; \
	fi

# Deploy the application
deploy: build
	@echo "Deploying application..."
	@if [ -n "$$AWS_PROFILE" ]; then \
		echo "Using AWS Profile: $$AWS_PROFILE"; \
		sam deploy --guided --profile $$AWS_PROFILE; \
	else \
		sam deploy --guided; \
	fi

# Deploy without guided mode (uses samconfig.toml)
deploy-quick: build
	@echo "Deploying application (non-guided)..."
	@if [ -n "$$AWS_PROFILE" ]; then \
		echo "Using AWS Profile: $$AWS_PROFILE"; \
		sam deploy --profile $$AWS_PROFILE; \
	else \
		sam deploy; \
	fi

# Run local tests
test:
	@echo "Running local tests..."
	python -m pytest tests/ -v

# Invoke the Lambda function manually
invoke:
	@echo "Invoking Lambda function..."
	@if [ -n "$$AWS_PROFILE" ]; then \
		aws lambda invoke \
			--profile $$AWS_PROFILE \
			--function-name SweetwaterAvailabilityChecker \
			--payload '{}' \
			response.json; \
	else \
		aws lambda invoke \
			--function-name SweetwaterAvailabilityChecker \
			--payload '{}' \
			response.json; \
	fi
	@echo "Response:"
	@cat response.json | python -m json.tool

# Tail CloudWatch logs
logs:
	@echo "Tailing CloudWatch logs..."
	@if [ -n "$$AWS_PROFILE" ]; then \
		aws logs tail /aws/lambda/SweetwaterAvailabilityChecker --profile $$AWS_PROFILE --follow; \
	else \
		aws logs tail /aws/lambda/SweetwaterAvailabilityChecker --follow; \
	fi

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf .aws-sam/
	rm -rf dependencies/python/
	rm -f response.json
	rm -f packaged.yaml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete!"

# Login to AWS SSO
login:
	@if [ -n "$$AWS_PROFILE" ]; then \
		echo "Logging in to AWS SSO profile: $$AWS_PROFILE"; \
		aws sso login --profile $$AWS_PROFILE; \
	else \
		echo "No AWS_PROFILE set. Please set it in .env or export it."; \
		echo "Example: echo 'AWS_PROFILE=your-profile-name' > .env"; \
		exit 1; \
	fi

# Verify SES email addresses
verify-ses:
	@echo "Enter sender email address:"
	@read sender_email; \
	if [ -n "$$AWS_PROFILE" ]; then \
		if aws ses verify-email-identity --profile $$AWS_PROFILE --email-address $$sender_email; then \
			echo "✓ Verification email sent to $$sender_email"; \
		else \
			echo "✗ Failed to send verification to $$sender_email"; \
			echo "  Please check your AWS credentials or run: aws sso login --profile $$AWS_PROFILE"; \
			exit 1; \
		fi; \
	else \
		if aws ses verify-email-identity --email-address $$sender_email; then \
			echo "✓ Verification email sent to $$sender_email"; \
		else \
			echo "✗ Failed to send verification to $$sender_email"; \
			echo "  Please check your AWS credentials"; \
			exit 1; \
		fi; \
	fi
	@echo "Enter recipient email address:"
	@read recipient_email; \
	if [ -n "$$AWS_PROFILE" ]; then \
		if aws ses verify-email-identity --profile $$AWS_PROFILE --email-address $$recipient_email; then \
			echo "✓ Verification email sent to $$recipient_email"; \
		else \
			echo "✗ Failed to send verification to $$recipient_email"; \
			echo "  Please check your AWS credentials or run: aws sso login --profile $$AWS_PROFILE"; \
			exit 1; \
		fi; \
	else \
		if aws ses verify-email-identity --email-address $$recipient_email; then \
			echo "✓ Verification email sent to $$recipient_email"; \
		else \
			echo "✗ Failed to send verification to $$recipient_email"; \
			echo "  Please check your AWS credentials"; \
			exit 1; \
		fi; \
	fi

# Check SES verification status
check-ses:
	@echo "Verified email addresses:"
	@if [ -n "$$AWS_PROFILE" ]; then \
		aws ses list-identities --profile $$AWS_PROFILE --identity-type EmailAddress; \
	else \
		aws ses list-identities --identity-type EmailAddress; \
	fi

# Update environment variables
update-env:
	@echo "Updating Lambda environment variables..."
	@echo "Enter new product URL (or press enter to skip):"
	@read product_url; \
	if [ -n "$$product_url" ]; then \
		aws lambda update-function-configuration \
			--function-name SweetwaterAvailabilityChecker \
			--environment Variables="{PRODUCT_URL='$$product_url'}"; \
	fi

# Enable notifications
enable-notifications:
	@echo "Enabling notifications..."
	@if [ -n "$$AWS_PROFILE" ]; then \
		aws lambda get-function-configuration \
			--profile $$AWS_PROFILE \
			--function-name SweetwaterAvailabilityChecker \
			--query 'Environment.Variables' \
			--output json > /tmp/env_vars.json; \
		python -c "import json; vars=json.load(open('/tmp/env_vars.json')); vars['SKIP_NOTIFICATION']='false'; print(json.dumps(vars))" > /tmp/new_env_vars.json; \
		aws lambda update-function-configuration \
			--profile $$AWS_PROFILE \
			--function-name SweetwaterAvailabilityChecker \
			--environment Variables=file:///tmp/new_env_vars.json; \
	else \
		aws lambda get-function-configuration \
			--function-name SweetwaterAvailabilityChecker \
			--query 'Environment.Variables' \
			--output json > /tmp/env_vars.json; \
		python -c "import json; vars=json.load(open('/tmp/env_vars.json')); vars['SKIP_NOTIFICATION']='false'; print(json.dumps(vars))" > /tmp/new_env_vars.json; \
		aws lambda update-function-configuration \
			--function-name SweetwaterAvailabilityChecker \
			--environment Variables=file:///tmp/new_env_vars.json; \
	fi
	@rm -f /tmp/env_vars.json /tmp/new_env_vars.json
	@echo "✅ Notifications enabled!"

# Disable notifications
disable-notifications:
	@echo "Disabling notifications..."
	@if [ -n "$$AWS_PROFILE" ]; then \
		aws lambda get-function-configuration \
			--profile $$AWS_PROFILE \
			--function-name SweetwaterAvailabilityChecker \
			--query 'Environment.Variables' \
			--output json > /tmp/env_vars.json; \
		python -c "import json; vars=json.load(open('/tmp/env_vars.json')); vars['SKIP_NOTIFICATION']='true'; print(json.dumps(vars))" > /tmp/new_env_vars.json; \
		aws lambda update-function-configuration \
			--profile $$AWS_PROFILE \
			--function-name SweetwaterAvailabilityChecker \
			--environment Variables=file:///tmp/new_env_vars.json; \
	else \
		aws lambda get-function-configuration \
			--function-name SweetwaterAvailabilityChecker \
			--query 'Environment.Variables' \
			--output json > /tmp/env_vars.json; \
		python -c "import json; vars=json.load(open('/tmp/env_vars.json')); vars['SKIP_NOTIFICATION']='true'; print(json.dumps(vars))" > /tmp/new_env_vars.json; \
		aws lambda update-function-configuration \
			--function-name SweetwaterAvailabilityChecker \
			--environment Variables=file:///tmp/new_env_vars.json; \
	fi
	@rm -f /tmp/env_vars.json /tmp/new_env_vars.json
	@echo "✅ Notifications disabled!"

# Get stack info
info:
	@echo "Stack information:"
	@aws cloudformation describe-stacks \
		--stack-name product-availability-scraper \
		--query 'Stacks[0].Outputs' \
		--output table

# Delete the stack
delete:
	@echo "Are you sure you want to delete the stack? [y/N]"
	@read confirm; \
	if [ "$$confirm" = "y" ]; then \
		sam delete --no-prompts; \
	else \
		echo "Deletion cancelled."; \
	fi