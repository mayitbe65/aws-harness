#!/bin/bash

##############################################################################
# Build and Push Docker Images to ECR
#
# Usage:
#   ./scripts/build-docker.sh [environment] [build-backend] [build-frontend]
#
# Arguments:
#   environment    - Target environment (dev, staging, prod) - default: dev
#   build-backend  - Build backend image (true/false) - default: true
#   build-frontend - Build frontend image (true/false) - default: true
#
# Examples:
#   ./scripts/build-docker.sh dev           # Build both images for dev
#   ./scripts/build-docker.sh prod true false # Build only backend for prod
#
##############################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="${1:-dev}"
BUILD_BACKEND="${2:-true}"
BUILD_FRONTEND="${3:-true}"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
  echo -e "${RED}Error: Invalid environment '$ENVIRONMENT'${NC}"
  echo "Valid options: dev, staging, prod"
  exit 1
fi

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Error QA - Docker Build & Push Script${NC}"
echo -e "${YELLOW}========================================${NC}"
echo "Environment: $ENVIRONMENT"
echo "Build Backend: $BUILD_BACKEND"
echo "Build Frontend: $BUILD_FRONTEND"
echo ""

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-us-east-1}
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"
echo "ECR Registry: $ECR_REGISTRY"
echo ""

# Login to ECR
echo -e "${YELLOW}Logging in to ECR...${NC}"
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "$ECR_REGISTRY"

echo -e "${GREEN}Successfully logged in to ECR${NC}"
echo ""

# Build and push backend
if [ "$BUILD_BACKEND" = "true" ]; then
  echo -e "${YELLOW}Building backend Docker image...${NC}"

  BACKEND_REPO="${ENVIRONMENT}-errorqa-backend"
  BACKEND_TAG="latest"

  # Create ECR repository if it doesn't exist
  aws ecr describe-repositories \
    --repository-names "$BACKEND_REPO" \
    --region "$AWS_REGION" 2>/dev/null || \
  aws ecr create-repository \
    --repository-name "$BACKEND_REPO" \
    --region "$AWS_REGION"

  # Build Docker image
  docker build \
    -t "$ECR_REGISTRY/$BACKEND_REPO:$BACKEND_TAG" \
    -t "$ECR_REGISTRY/$BACKEND_REPO:$(date +%s)" \
    -f backend/Dockerfile \
    --build-arg ENVIRONMENT=$ENVIRONMENT \
    backend/

  echo -e "${GREEN}Built backend image${NC}"
  echo ""

  # Push to ECR
  echo -e "${YELLOW}Pushing backend image to ECR...${NC}"
  docker push "$ECR_REGISTRY/$BACKEND_REPO:$BACKEND_TAG"
  docker push "$ECR_REGISTRY/$BACKEND_REPO:$(date +%s)"

  echo -e "${GREEN}Pushed backend image to ECR${NC}"
  echo "Backend Image URI: $ECR_REGISTRY/$BACKEND_REPO:$BACKEND_TAG"
  echo ""
fi

# Build and push frontend
if [ "$BUILD_FRONTEND" = "true" ]; then
  echo -e "${YELLOW}Building frontend Docker image...${NC}"

  FRONTEND_REPO="${ENVIRONMENT}-errorqa-frontend"
  FRONTEND_TAG="latest"

  # Create ECR repository if it doesn't exist
  aws ecr describe-repositories \
    --repository-names "$FRONTEND_REPO" \
    --region "$AWS_REGION" 2>/dev/null || \
  aws ecr create-repository \
    --repository-name "$FRONTEND_REPO" \
    --region "$AWS_REGION"

  # Build Docker image
  docker build \
    -t "$ECR_REGISTRY/$FRONTEND_REPO:$FRONTEND_TAG" \
    -t "$ECR_REGISTRY/$FRONTEND_REPO:$(date +%s)" \
    -f frontend/Dockerfile \
    --build-arg REACT_APP_API_URL="http://localhost:8000" \
    --build-arg ENVIRONMENT=$ENVIRONMENT \
    frontend/

  echo -e "${GREEN}Built frontend image${NC}"
  echo ""

  # Push to ECR
  echo -e "${YELLOW}Pushing frontend image to ECR...${NC}"
  docker push "$ECR_REGISTRY/$FRONTEND_REPO:$FRONTEND_TAG"
  docker push "$ECR_REGISTRY/$FRONTEND_REPO:$(date +%s)"

  echo -e "${GREEN}Pushed frontend image to ECR${NC}"
  echo "Frontend Image URI: $ECR_REGISTRY/$FRONTEND_REPO:$FRONTEND_TAG"
  echo ""
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Docker build and push completed!${NC}"
echo -e "${GREEN}========================================${NC}"

# Print next steps
echo ""
echo "Next steps:"
echo "1. If you made changes to infrastructure, run:"
echo "   npm run cdk:diff -- --environment=$ENVIRONMENT"
echo ""
echo "2. Deploy the infrastructure:"
echo "   npm run cdk:deploy:$ENVIRONMENT"
echo ""
echo "3. Monitor the ECS service:"
echo "   aws ecs describe-services \\"
echo "     --cluster $ENVIRONMENT-errorqa-backend \\"
echo "     --services $ENVIRONMENT-errorqa-backend \\"
echo "     --region $AWS_REGION"
echo ""
