# Complete AWS Setup Guide for Crypto Trading Bot

This guide provides comprehensive instructions for setting up your AWS environment and deploying the Crypto Trading Bot to AWS Cloud.

## AWS Setup Process Overview

1. **AWS Account & Environment Setup**
2. **IAM Permissions Configuration**
3. **Virtual Environment Creation**
4. **AWS Resource Deployment**
5. **Post-Deployment Configuration**

## 1. AWS Account & Environment Setup

### AWS Account Requirements

- AWS Account with billing set up
- Access to the AWS Management Console
- Ability to create resources in AWS regions (us-east-1 recommended for best coverage)

### Installing Required Tools

Ensure you have the following installed on your local machine:

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version
```

## 2. IAM Permissions Configuration

Our project includes a helper script to set up the necessary IAM permissions for deploying and running the trading bot infrastructure.

### Required AWS Permissions

The following AWS permissions are required for full functionality:

- **AmazonS3FullAccess**: For storing website assets, configuration files, and deployment artifacts
- **AmazonEC2FullAccess**: Essential for managing EC2 instances where your trading bot and website will run
- **AWSKeyManagementServicePowerUser**: For encrypting sensitive trading data and credentials
- **AWSCloudFormationFullAccess**: For deploying infrastructure as code
- **AmazonDynamoDBFullAccess**: If your bot stores trading data or state
- **AWSLambda_FullAccess**: If your architecture uses serverless components
- **CloudWatchFullAccess**: For monitoring both your trading bot and website
- **AmazonRoute53FullAccess**: If you're using custom domains for your website
- **AmazonRDSFullAccess**: If your application uses a database
- **ElasticLoadBalancingFullAccess**: If you're load balancing your website traffic
- **AmazonVPCFullAccess**: For network configuration
- **IAMFullAccess**: Since your script will be creating and managing roles
- **AWSCertificateManagerFullAccess**: If you're using HTTPS for your website

### Using the Permissions Setup Script

```bash
# Make the script executable
chmod +x setup_aws_permissions.sh

# List required permissions without making changes
./setup_aws_permissions.sh --list-only

# Check if current user has all required permissions
./setup_aws_permissions.sh --check

# Attach all required policies to current user
./setup_aws_permissions.sh

# Create a new dedicated deployment user
./setup_aws_permissions.sh --create-user crypto-bot-deployer
```

If you created a new user, you'll need to configure the AWS CLI with the new credentials:

```bash
aws configure
# Enter the Access Key ID and Secret Access Key from the generated access_keys_*.json file
# Set the default region (e.g., us-east-1)
# Set the output format (recommended: json)
```

## 3. AWS Virtual Environment Creation

We provide a specialized AWS virtual environment script to ensure you have all the required dependencies for AWS deployment.

```bash
# Make the script executable
chmod +x setup_aws_venv.py

# Create the AWS virtual environment
./setup_aws_venv.py

# Activate the virtual environment
source aws_venv/bin/activate

# Verify the environment
aws --version
python -c "import boto3; print(boto3.__version__)"
```

## 4. AWS Resource Deployment

### Prerequisites

Before deployment, gather the following information:

- **EC2 Key Pair**: Create an EC2 key pair in the AWS Console if you don't have one
- **VPC ID**: Find your VPC ID in the AWS Console (VPC service)
- **Subnet ID**: Find a subnet ID in the AWS Console (VPC service)
- **Database Password**: Choose a secure password for the PostgreSQL database
- **Domain Name**: (Optional) If you want to use a custom domain

### Enhanced Deployment

Our enhanced deployment script provides additional security, monitoring, and reliability features:

```bash
# Ensure you have activated the AWS environment
source aws_venv/bin/activate

# Deploy with enhanced features
./deploy_enhanced_aws.sh \
  --key-name your-ec2-key-pair \
  --vpc-id vpc-your-vpc-id \
  --subnet-id subnet-your-subnet-id \
  --db-password YourSecurePassword \
  --domain your-domain.com \
  --email your-email@example.com

# For help and additional options
./deploy_enhanced_aws.sh --help
```

### Standard Deployment (Alternative)

Alternatively, you can use our standard deployment script with environment variables:

```bash
# Set required parameters
export EC2_KEY_NAME=your-key-pair
export VPC_ID=vpc-xxxxxxxxx
export SUBNET_ID=subnet-xxxxxxxxx
export DB_PASSWORD=secure-password

# Optional parameters
export DOMAIN_NAME=steampunk.holdings
export EMAIL=admin@steampunk.holdings
export INITIAL_BTC_PRICE=84000
export ENABLE_SSL=true

# Run the deployment script
./deploy-steampunk.sh
```

## 5. Post-Deployment Configuration

### DNS Configuration

If you specified a domain name, you'll need to configure your DNS settings:

1. Go to your domain registrar's website
2. Find the DNS management section
3. Add an A record pointing your domain to the EC2 Public IP address
4. Add a CNAME record for `www` subdomain

### Accessing Your Dashboard

After deployment and DNS propagation (which can take up to 24 hours):

1. Access your dashboard at `https://your-domain.com`
2. Log in with the default credentials:
   - Username: `admin`
   - Password: The database password you specified during deployment

### Monitoring Your System

Your deployment includes monitoring tools:

- **CloudWatch**: Access through the AWS Console for logs and metrics
- **Prometheus**: Access at `https://your-domain.com:9090`
- **Grafana**: Access at `https://your-domain.com:3000` with admin/your-db-password

### SSH Access

To access your EC2 instance:

```bash
ssh -i /path/to/your-key-pair.pem ubuntu@ec2-public-dns
```

## Troubleshooting

### Deployment Failures

If your deployment fails:

1. Check the CloudFormation console in the AWS Management Console
2. Look for failed resources and their error messages
3. Review CloudWatch logs for detailed error information

Common issues:
- Insufficient permissions: Verify all IAM permissions
- VPC/Subnet issues: Ensure your VPC has internet access
- Service limits: Check if you've hit AWS service limits

### Post-Deployment Issues

If your system is deployed but not functioning correctly:

1. SSH into the EC2 instance
2. Check Docker container status:
   ```bash
   cd /app
   docker-compose ps
   docker-compose logs
   ```
3. Check if the dashboard is running:
   ```bash
   curl http://localhost:5003/health
   ```

## Security Considerations

1. **API Keys**: The deployment creates an API key for the dashboard. Keep this secure.
2. **Database Password**: Choose a strong password for your RDS instance.
3. **IAM Permissions**: Consider using least privilege principles in production.
4. **SSL/TLS**: Always use HTTPS for your dashboard in production.

## Cost Management

The deployed resources will incur AWS charges. To manage costs:

- Use t3.micro or t3.small instances for testing/development
- Consider shutting down resources when not in use
- Set up AWS Budgets to monitor spending
- Use AWS Cost Explorer to identify expensive resources

## Next Steps

After successful deployment:
- Set up your trading strategies via the dashboard
- Connect exchange APIs if you want to use real market data
- Configure alerts and notifications
- Set up backup procedures for your database

For more detailed information, refer to the [AWS_DEPLOYMENT_GUIDE.md](AWS_DEPLOYMENT_GUIDE.md).
