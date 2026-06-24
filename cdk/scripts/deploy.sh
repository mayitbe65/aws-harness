#!/bin/bash

##############################################################################
# Deploy CDK Infrastructure
#
# Usage:
#   ./scripts/deploy.sh [environment] [action]
#
# Arguments:
#   environment - Target environment (dev, staging, prod) - default: dev
#   action      - Deploy action (deploy, destroy, diff) - default: deploy
#
# Examples:
#   ./scripts/deploy.sh dev           # Deploy dev environment
#   ./scripts/deploy.sh prod deploy   # Deploy prod environment
#   ./scripts/deploy.sh staging diff  # Show diff for staging
#   ./scripts/deploy.sh dev destroy   # Destroy dev environment
#
##############################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="${1:-dev}"
ACTION="${2:-deploy}"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
  echo -e "${RED}Error: Invalid environment '$ENVIRONMENT'${NC}"
  echo "Valid options: dev, staging, prod"
  exit 1
fi

# Validate action
if [[ ! "$ACTION" =~ ^(deploy|destroy|diff)$ ]]; then
  echo -e "${RED}Error: Invalid action '$ACTION'${NC}"
  echo "Valid options: deploy, destroy, diff"
  exit 1
fi

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Error QA - CDK Deploy Script${NC}"
echo -e "${YELLOW}========================================${NC}"
echo "Environment: $ENVIRONMENT"
echo "Action: $ACTION"
echo ""

# Get project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command -v aws &> /dev/null; then
  echo -e "${RED}Error: AWS CLI not found${NC}"
  echo "Please install AWS CLI: https://aws.amazon.com/cli/"
  exit 1
fi

if ! command -v npm &> /dev/null; then
  echo -e "${RED}Error: npm not found${NC}"
  echo "Please install Node.js: https://nodejs.org/"
  exit 1
fi

if ! command -v docker &> /dev/null; then
  echo -e "${RED}Error: Docker not found${NC}"
  echo "Please install Docker: https://www.docker.com/"
  exit 1
fi

# Verify AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
  echo -e "${RED}Error: AWS credentials not configured${NC}"
  echo "Please configure AWS credentials: aws configure"
  exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}

echo -e "${GREEN}AWS Account ID: $AWS_ACCOUNT_ID${NC}"
echo -e "${GREEN}AWS Region: $AWS_REGION${NC}"
echo ""

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
  echo -e "${BLUE}Installing npm dependencies...${NC}"
  npm install
  echo ""
fi

# Build TypeScript
echo -e "${BLUE}Building TypeScript...${NC}"
npm run build
echo -e "${GREEN}TypeScript build completed${NC}"
echo ""

# Stack name
STACK_NAME="ErrorQaStack${ENVIRONMENT^}"

case $ACTION in
  deploy)
    echo -e "${YELLOW}Deploying $ENVIRONMENT environment...${NC}"
    echo ""

    # Show diff first
    echo -e "${BLUE}Showing diff:${NC}"
    npm run cdk -- diff "$STACK_NAME" \
      --context environment="$ENVIRONMENT" \
      --region="$AWS_REGION" 2>&1 || true
    echo ""

    # Ask for confirmation
    read -p "Do you want to deploy these changes? (yes/no): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
      echo -e "${YELLOW}Deployment cancelled${NC}"
      exit 0
    fi

    # Deploy
    echo -e "${YELLOW}Starting deployment...${NC}"
    npm run cdk -- deploy "$STACK_NAME" \
      --context environment="$ENVIRONMENT" \
      --region="$AWS_REGION" \
      --require-approval never

    echo -e "${GREEN}Deployment completed successfully!${NC}"
    ;;

  destroy)
    if [ "$ENVIRONMENT" = "prod" ]; then
      echo -e "${RED}WARNING: You are about to destroy the PRODUCTION environment!${NC}"
      read -p "Type 'yes' to confirm destruction of $ENVIRONMENT environment: " -r
      if [[ ! $REPLY == "yes" ]]; then
        echo -e "${YELLOW}Destruction cancelled${NC}"
        exit 0
      fi
    else
      read -p "Do you want to destroy $ENVIRONMENT environment? (yes/no): " -r
      echo
      if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${YELLOW}Destruction cancelled${NC}"
        exit 0
      fi
    fi

    echo -e "${YELLOW}Destroying infrastructure...${NC}"
    npm run cdk -- destroy "$STACK_NAME" \
      --context environment="$ENVIRONMENT" \
      --region="$AWS_REGION" \
      --force

    echo -e "${GREEN}Destruction completed!${NC}"
    ;;

  diff)
    echo -e "${YELLOW}Showing diff for $ENVIRONMENT environment...${NC}"
    npm run cdk -- diff "$STACK_NAME" \
      --context environment="$ENVIRONMENT" \
      --region="$AWS_REGION"
    ;;
esac

echo ""
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Deployment script completed!${NC}"
echo -e "${YELLOW}========================================${NC}"
