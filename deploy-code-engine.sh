#!/bin/bash

# IBM Code Engine Deployment Script for Pothole Video Analyzer
# This script deploys the application to IBM Code Engine

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}IBM Code Engine Deployment${NC}"
echo -e "${GREEN}Pothole Video Analyzer${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if required environment variables are set
if [ -z "$WATSONX_API_KEY" ] || [ -z "$WATSONX_PROJECT_ID" ]; then
    echo -e "${RED}Error: Required environment variables not set${NC}"
    echo "Please set the following environment variables:"
    echo "  export WATSONX_API_KEY='your_api_key'"
    echo "  export WATSONX_PROJECT_ID='your_project_id'"
    exit 1
fi

# Configuration
PROJECT_NAME=${PROJECT_NAME:-"pothole-analyzer"}
APP_NAME=${APP_NAME:-"pothole-analyzer-api"}
REGION=${REGION:-"us-south"}
RESOURCE_GROUP=${RESOURCE_GROUP:-"Default"}
REGISTRY=${REGISTRY:-"us.icr.io"}
NAMESPACE=${NAMESPACE:-"pothole-analyzer"}

echo -e "${YELLOW}Configuration:${NC}"
echo "  Project: $PROJECT_NAME"
echo "  App Name: $APP_NAME"
echo "  Region: $REGION"
echo "  Registry: $REGISTRY"
echo "  Namespace: $NAMESPACE"
echo ""

# Step 1: Login to IBM Cloud
echo -e "${YELLOW}Step 1: Logging in to IBM Cloud...${NC}"
ibmcloud login --apikey $IBM_CLOUD_API_KEY -r $REGION -g $RESOURCE_GROUP || {
    echo -e "${RED}Failed to login to IBM Cloud${NC}"
    echo "Please ensure IBM_CLOUD_API_KEY is set"
    exit 1
}

# Step 2: Target Code Engine
echo -e "${YELLOW}Step 2: Targeting Code Engine project...${NC}"
ibmcloud ce project select --name $PROJECT_NAME || {
    echo -e "${YELLOW}Project not found. Creating new project...${NC}"
    ibmcloud ce project create --name $PROJECT_NAME
    ibmcloud ce project select --name $PROJECT_NAME
}

# Step 3: Build and push Docker image
echo -e "${YELLOW}Step 3: Building Docker image...${NC}"
IMAGE_NAME="$REGISTRY/$NAMESPACE/$APP_NAME:latest"

# Login to container registry
ibmcloud cr login

# Create namespace if it doesn't exist
ibmcloud cr namespace-add $NAMESPACE || echo "Namespace already exists"

# Build and push image
docker build -t $IMAGE_NAME .
docker push $IMAGE_NAME

echo -e "${GREEN}✓ Image pushed: $IMAGE_NAME${NC}"

# Step 4: Deploy to Code Engine
echo -e "${YELLOW}Step 4: Deploying to Code Engine...${NC}"

# Check if application exists
if ibmcloud ce app get --name $APP_NAME &> /dev/null; then
    echo "Updating existing application..."
    ibmcloud ce app update --name $APP_NAME \
        --image $IMAGE_NAME \
        --env WATSONX_API_KEY=$WATSONX_API_KEY \
        --env WATSONX_PROJECT_ID=$WATSONX_PROJECT_ID \
        --env WATSONX_URL=${WATSONX_URL:-"https://us-south.ml.cloud.ibm.com"} \
        --env VISION_MODEL_ID=${VISION_MODEL_ID:-"meta-llama/llama-3-2-90b-vision-instruct"} \
        --env FRAME_EXTRACTION_RATE=${FRAME_EXTRACTION_RATE:-"1"} \
        --env MAX_WORKERS=${MAX_WORKERS:-"4"} \
        --cpu 2 \
        --memory 4G \
        --min-scale 0 \
        --max-scale 5 \
        --port 8080 \
        --request-timeout 600
else
    echo "Creating new application..."
    ibmcloud ce app create --name $APP_NAME \
        --image $IMAGE_NAME \
        --env WATSONX_API_KEY=$WATSONX_API_KEY \
        --env WATSONX_PROJECT_ID=$WATSONX_PROJECT_ID \
        --env WATSONX_URL=${WATSONX_URL:-"https://us-south.ml.cloud.ibm.com"} \
        --env VISION_MODEL_ID=${VISION_MODEL_ID:-"meta-llama/llama-3-2-90b-vision-instruct"} \
        --env FRAME_EXTRACTION_RATE=${FRAME_EXTRACTION_RATE:-"1"} \
        --env MAX_WORKERS=${MAX_WORKERS:-"4"} \
        --cpu 2 \
        --memory 4G \
        --min-scale 0 \
        --max-scale 5 \
        --port 8080 \
        --request-timeout 600
fi

# Step 5: Get application URL
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

APP_URL=$(ibmcloud ce app get --name $APP_NAME --output json | grep -o '"url":"[^"]*' | cut -d'"' -f4)

echo -e "${GREEN}Application URL:${NC} $APP_URL"
echo ""
echo -e "${YELLOW}Test the API:${NC}"
echo "  Health check: curl $APP_URL/health"
echo "  API info: curl $APP_URL/"
echo ""
echo -e "${YELLOW}Analyze a video:${NC}"
echo "  curl -X POST -F 'video=@path/to/video.mp4' $APP_URL/analyze"
echo ""
echo -e "${GREEN}Deployment successful!${NC}"

# Made with Bob
