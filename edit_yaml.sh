#!/bin/bash
# Use this script to directly edit the YAML file

# Make a backup
cp aws-cloudformation-enhanced.yml aws-cloudformation-enhanced.yml.bak2

# Create a simpler version of the CloudFormation template
cat > aws-cloudformation-simplified.yml << 'EOL'
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Simple Crypto Trading Bot on AWS'

Parameters:
  SubnetId:
    Type: AWS::EC2::Subnet::Id
    Description: "Primary subnet ID"
  
  FallbackSubnetId:
    Type: AWS::EC2::Subnet::Id
    Description: "Secondary subnet ID"
  
  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: "VPC ID"
  
  KeyName:
    Type: AWS::EC2::KeyPair::KeyName
    Description: "EC2 key pair name"
  
  DBPassword:
    Type: String
    NoEcho: true
    Description: "Database password"
  
  DockerImageRepo:
    Type: String
    Description: "Docker repository URI"
  
  EnvironmentName:
    Type: String
    Default: prod
    Description: "Environment name"
  
  DomainName:
    Type: String
    Default: "steampunk.holdings"
    Description: "Domain name"
  
  ApiKey:
    Type: String
    NoEcho: true
    Description: "API key"

  EnableSSL:
    Type: String
    Default: "true"
    Description: "Whether to enable SSL"

Conditions:
  IsProduction: !Equals [!Ref EnvironmentName, 'prod']

Mappings:
  RegionMap:
    us-east-1:
      AMI: ami-0f3c7d07486cad139
    us-east-2:
      AMI: ami-024e6efaf93d85776
    us-west-1:
      AMI: ami-0f8e81a3da6e2510a
    us-west-2:
      AMI: ami-03f65b8614a860c29

Resources:
  # VPC Security Groups
  EC2SecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: "Security group for EC2 instance"
      VpcId: !Ref VpcId
      SecurityGroupIngress:
        - CidrIp: "0.0.0.0/0"
          FromPort: 22
          ToPort: 22
          IpProtocol: tcp
          Description: "SSH access"
        - CidrIp: "0.0.0.0/0"
          FromPort: 80
          ToPort: 80
          IpProtocol: tcp
          Description: "HTTP access"
  
  # IAM Role for EC2
  EC2Role:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
        - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess
  
  # EC2 Instance Profile
  EC2InstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      Roles:
        - !Ref EC2Role
  
  # EC2 Instance
  EC2Instance:
    Type: AWS::EC2::Instance
    Properties:
      InstanceType: t3.medium
      ImageId: !FindInMap [RegionMap, !Ref "AWS::Region", AMI]
      KeyName: !Ref KeyName
      IamInstanceProfile: !Ref EC2InstanceProfile
      SubnetId: !Ref SubnetId
      SecurityGroupIds:
        - !GetAtt EC2SecurityGroup.GroupId
  
  # DB Subnet Group
  DBSubnetGroup:
    Type: AWS::RDS::DBSubnetGroup
    Properties:
      DBSubnetGroupDescription: "Subnet group for crypto bot database"
      SubnetIds:
        - !Ref SubnetId
        - !Ref FallbackSubnetId
  
  # RDS PostgreSQL DB Instance
  DBInstance:
    Type: AWS::RDS::DBInstance
    Properties:
      Engine: postgres
      DBInstanceClass: db.t3.small
      AllocatedStorage: 20
      DBName: crypto_bot
      MasterUsername: postgres
      MasterUserPassword: !Ref DBPassword
      BackupRetentionPeriod: 7
      MultiAZ: !If [IsProduction, true, false]
      PubliclyAccessible: false
      DBSubnetGroupName: !Ref DBSubnetGroup
      VPCSecurityGroups:
        - !GetAtt EC2SecurityGroup.GroupId
EOL

echo "Created simplified template. Try deploying with this simpler template first."
