# Crypto Trading Bot Cleanup Analysis

Generated on: 2025-04-27 02:22:50

## Summary

- **Duplicate Files**: 3 (2 sets)
- **Empty Files**: 1
- **Nearly Empty Files**: 0
- **Dashboard Scripts**: 6
- **Deployment Scripts**: 13
- **AWS Scripts**: 1
- **Testing Scripts**: 1
- **Other Scripts**: 2
- **AWS Deployment Files**: 17

## Duplicate Files

- **Set with 2 identical files**:
  - `./aws-cloudformation-enhanced.yml`
  - `./aws-cloudformation-enhanced.yml.bak2`

- **Set with 3 identical files**:
  - `./src/exchange/__init__.py`
  - `./src/models/__init__.py`
  - `./tests/__init__.py`

## Empty Files

- `./code_analysis_reports/crypto_security_issues.txt`

## Nearly Empty Files (< 10 bytes)

No nearly empty files found.


## Dashboard Scripts

- `./deploy_production_dashboard.sh`
- `./run_dashboard.sh`
- `./install_dashboard_service.sh`
- `./setup_venv_and_deploy.sh`
- `./run_paper_trading.sh`
- `./start_website.sh`

## Deployment Scripts

- `./deploy_final.sh`
- `./deploy-to-aws.sh`
- `./setup-aws-deployment.sh`
- `./check_deployment.sh`
- `./deploy_crypto_app.sh`
- `./setup_aws_permissions.sh`
- `./Dockerfile`
- `./deploy-steampunk.sh`
- `./deploy_enhanced_aws.sh`
- `./deploy_x86.sh`
- `./check_x86_deployment.sh`
- `./deploy_simple.sh`
- `./scripts/deploy_microservices.sh`

## AWS Scripts

- `./edit_yaml.sh`

## Testing Scripts

- `./code_analysis_script.sh`

## AWS Deployment Files

- `./deploy-to-aws.sh`
- `./docker-compose.aws.yml`
- `./setup_aws_venv.py`
- `./aws-cloudformation-enhanced.yml.bak`
- `./aws-cloudformation-enhanced.fixed.yml`
- `./setup-aws-deployment.sh`
- `./aws-cloudformation-simplified.yml`
- `./aws-cloudformation-enhanced.yml`
- `./setup_aws_permissions.sh`
- `./aws-cloudformation.yml`
- `./fix_cloudformation.py`
- `./AWS_SETUP_README.md`
- `./AWS_DEPLOYMENT_TROUBLESHOOTING.md`
- `./aws-cloudformation-enhanced.yml.bak2`
- `./AWS_DEPLOYMENT_SUMMARY.md`
- `./deploy_enhanced_aws.sh`
- `./AWS_DEPLOYMENT_GUIDE.md`

## Cleanup Recommendations

### Duplicate Files

For each set of duplicate files, keep only one copy. Suggested approach:

- Keep: `./aws-cloudformation-enhanced.yml`
  Remove:
  - `./aws-cloudformation-enhanced.yml.bak2`

- Keep: `./tests/__init__.py`
  Remove:
  - `./src/models/__init__.py`
  - `./src/exchange/__init__.py`

### Empty Files

Consider removing these empty files if they serve no purpose:

- `./code_analysis_reports/crypto_security_issues.txt`

### Dashboard Script Consolidation

Consider consolidating these dashboard-related scripts into a single script with parameters:

- `./deploy_production_dashboard.sh`
- `./run_dashboard.sh`
- `./install_dashboard_service.sh`
- `./setup_venv_and_deploy.sh`
- `./run_paper_trading.sh`
- `./start_website.sh`

### Deployment Script Consolidation

Consider consolidating these deployment scripts into a single script with parameters:

- `./deploy_final.sh`
- `./deploy-to-aws.sh`
- `./setup-aws-deployment.sh`
- `./check_deployment.sh`
- `./deploy_crypto_app.sh`
- `./setup_aws_permissions.sh`
- `./Dockerfile`
- `./deploy-steampunk.sh`
- `./deploy_enhanced_aws.sh`
- `./deploy_x86.sh`
- `./check_x86_deployment.sh`
- `./deploy_simple.sh`
- `./scripts/deploy_microservices.sh`

### AWS Deployment Files

Consider consolidating or organizing these AWS deployment files:

- `./deploy-to-aws.sh`
- `./docker-compose.aws.yml`
- `./setup_aws_venv.py`
- `./aws-cloudformation-enhanced.yml.bak`
- `./aws-cloudformation-enhanced.fixed.yml`
- `./setup-aws-deployment.sh`
- `./aws-cloudformation-simplified.yml`
- `./aws-cloudformation-enhanced.yml`
- `./setup_aws_permissions.sh`
- `./aws-cloudformation.yml`
- `./fix_cloudformation.py`
- `./AWS_SETUP_README.md`
- `./AWS_DEPLOYMENT_TROUBLESHOOTING.md`
- `./aws-cloudformation-enhanced.yml.bak2`
- `./AWS_DEPLOYMENT_SUMMARY.md`
- `./deploy_enhanced_aws.sh`
- `./AWS_DEPLOYMENT_GUIDE.md`

### General Organization

1. Create a dedicated `deploy/` directory for all deployment scripts
2. Create a dedicated `scripts/` directory for utility scripts
3. Consolidate similar functionality into single parameterized scripts
4. Improve documentation for each script to clarify its purpose
