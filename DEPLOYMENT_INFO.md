# Crypto Trading Bot Deployment Information

## Stack Details
- **Stack Name**: crypto-trading-x86
- **Region**: us-east-1
- **Environment**: prod
- **Domain**: steampunk.holdings

## Access Credentials
- **Dashboard URL**: https://steampunk.holdings
- **Username**: admin
- **Password**: Pizza&Pandas23
- **API Key**: f3bf7dca6b4afdf971d88ad133baea13

## Infrastructure
- **VPC ID**: vpc-092474c87e259b68d
- **Primary Subnet**: subnet-0c09b256fbef7d14d
- **Secondary Subnet**: subnet-01ddc43cba8ea1ca2
- **EC2 Key Pair**: Trading_App_PairKey1
- **ECR Repository**: 970547360838.dkr.ecr.us-east-1.amazonaws.com/crypto-trading-bot
- **AMI Architecture**: x86_64 (amd64)

## Deployment Date
Sun Apr 13 17:45:13 EDT 2025

## Next Steps
1. Monitor the stack creation in the AWS CloudFormation console
2. Once deployed, update your DNS records to point to the EC2 instance
3. Log in using the admin credentials provided above
4. Configure your trading strategies through the dashboard

## Instance Details
- **EC2 Instance ID**: i-0a647be0188f8831b
- **EC2 Public IP**: 3.220.9.26
- **RDS Instance ID**: crypto-trading-x86-dbinstance-oqk9b07az0zt
- **RDS Endpoint**: crypto-trading-x86-dbinstance-oqk9b07az0zt.citay02wsl50.us-east-1.rds.amazonaws.com

## DNS Configuration
To configure your domain to point to the EC2 instance:
1. Log in to your domain registrar
2. Create an A record for steampunk.holdings pointing to 3.220.9.26
3. Wait for DNS propagation (can take up to 24-48 hours)
