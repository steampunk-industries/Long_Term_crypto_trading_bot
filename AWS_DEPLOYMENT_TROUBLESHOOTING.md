# AWS Deployment Troubleshooting and Resolution

## Initial Deployment Issues

During our AWS deployment process, we encountered several issues that required troubleshooting and resolution:

### 1. CloudFormation Template Syntax Errors

**Issue**: The original CloudFormation template contained syntax errors with intrinsic functions.
- `!If` statements were missing commas between parameters
- `!FindInMap` functions had incorrect syntax
- `!Equals` conditions were improperly formatted

**Resolution**: 
- Fixed all intrinsic function syntax by adding required commas between parameters
- Example: Changed `!If [IsProduction true false]` to `!If [IsProduction, true, false]`

### 2. Missing Conditions Section

**Issue**: The template referenced conditions that weren't properly defined in a Conditions section.

**Resolution**:
- Added a proper `Conditions` section with the `IsProduction` condition
- Defined the condition as `IsProduction: !Equals [!Ref EnvironmentName, 'prod']`

### 3. AMI ID Not Found

**Issue**: The deployment failed with error: "The image id '[ami-0f3c7d07486cad139]' does not exist"

**Resolution**:
- Used AWS CLI to find the latest Ubuntu 22.04 LTS AMI: `ami-0b3377628d4878cc7`
- Updated the RegionMap in the CloudFormation template with the current AMI ID
- Created a script to automatically update AMI IDs in the template

### 4. RDS Database Creation Issues

**Issue**: The RDS database instance creation failed during the initial deployment.

**Resolution**:
- Simplified the template to use direct resource references
- Ensured proper subnet group configuration with subnets in different availability zones
- Set appropriate security group rules for database access

### 5. Stack Deletion Problems

**Issue**: When a stack creation failed, the rollback process sometimes got stuck due to database snapshot issues.

**Resolution**:
- Manually deleted the stack using AWS CLI
- Created a new stack with a different name to avoid conflicts with resources in deletion state

## Final Solution

Our final solution involved:

1. **Simplified Template**: Created a streamlined CloudFormation template focusing on essential resources
2. **Updated AMI References**: Used the latest available Ubuntu 22.04 AMI
3. **Proper Parameter Handling**: Ensured all required parameters were correctly passed
4. **Improved Deployment Script**: Created a robust deployment script with error handling
5. **Documentation**: Generated comprehensive deployment documentation

## Current Deployment Status

The final deployment has been initiated with stack name `crypto-trading-final`. The deployment is expected to take 15-20 minutes to complete.

You can monitor the progress in the AWS CloudFormation console or by running:
```bash
aws cloudformation describe-stacks --stack-name crypto-trading-final --query "Stacks[0].StackStatus"
```

## Lessons Learned

1. **Always validate AMI IDs**: AMI IDs change over time and should be verified before deployment
2. **Use proper CloudFormation syntax**: Pay careful attention to the syntax of intrinsic functions
3. **Test with simplified templates**: Start with a minimal template and add complexity incrementally
4. **Document deployment parameters**: Save all deployment parameters for future reference
5. **Use unique stack names**: When redeploying after failures, use new stack names to avoid conflicts

All deployment information has been saved to `DEPLOYMENT_INFO.md` for future reference.

## Architecture Mismatch Issue

**Issue**: The deployment failed with error: "The architecture 'x86_64' of the specified instance type does not match the architecture 'arm64' of the specified AMI"

**Resolution**:
- The AMI we initially selected (ami-0b3377628d4878cc7) was for ARM64 architecture
- We updated the template to use an x86_64 (AMD64) AMI: ami-0651e7743c2ad304f
- This matches the architecture of the t3.medium instance type we're using

**Finding the Right AMI**:
```bash
aws ec2 describe-images --owners 099720109477 --filters "Name=name,Values=*ubuntu*22.04*" "Name=architecture,Values=x86_64" --query 'sort_by(Images, &CreationDate)[-1].[ImageId,Name,Architecture]' --region us-east-1
```

This command finds the latest Ubuntu 22.04 AMI with x86_64 architecture from Canonical.
