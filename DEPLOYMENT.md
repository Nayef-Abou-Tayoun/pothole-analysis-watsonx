# Deployment Guide - IBM Code Engine

This guide explains how to deploy the Pothole Video Analyzer to IBM Code Engine using Docker.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Deployment](#quick-deployment)
- [Manual Deployment](#manual-deployment)
- [Testing the Deployment](#testing-the-deployment)
- [API Usage](#api-usage)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### 1. IBM Cloud Account
- Sign up at [IBM Cloud](https://cloud.ibm.com)
- Create an API key at [IBM Cloud API Keys](https://cloud.ibm.com/iam/apikeys)

### 2. Required Tools
```bash
# Install IBM Cloud CLI
curl -fsSL https://clis.cloud.ibm.com/install/linux | sh

# Install Code Engine plugin
ibmcloud plugin install code-engine

# Install Docker
# Visit: https://docs.docker.com/get-docker/
```

### 3. watsonx.ai Credentials
- API Key from IBM Cloud
- Project ID from watsonx.ai project

## Quick Deployment

### Option 1: Using Deployment Script (Recommended)

1. **Set Environment Variables**:
```bash
export IBM_CLOUD_API_KEY="your_ibm_cloud_api_key"
export WATSONX_API_KEY="your_watsonx_api_key"
export WATSONX_PROJECT_ID="your_project_id"
```

2. **Run Deployment Script**:
```bash
cd pothole-video-analyzer
./deploy-code-engine.sh
```

The script will:
- Login to IBM Cloud
- Create/select Code Engine project
- Build Docker image
- Push to IBM Container Registry
- Deploy application
- Display the application URL

### Option 2: Using IBM Cloud Console

1. Go to [IBM Code Engine Console](https://cloud.ibm.com/codeengine/overview)
2. Create a new project
3. Create an application from container image
4. Use the pre-built image or build from source
5. Set environment variables (see below)

## Manual Deployment

### Step 1: Login to IBM Cloud

```bash
ibmcloud login --apikey $IBM_CLOUD_API_KEY -r us-south
```

### Step 2: Create Code Engine Project

```bash
# Create project
ibmcloud ce project create --name pothole-analyzer

# Select project
ibmcloud ce project select --name pothole-analyzer
```

### Step 3: Build Docker Image

```bash
# Build image
docker build -t pothole-analyzer:latest .

# Tag for IBM Container Registry
docker tag pothole-analyzer:latest us.icr.io/pothole-analyzer/pothole-analyzer-api:latest
```

### Step 4: Push to Container Registry

```bash
# Login to registry
ibmcloud cr login

# Create namespace
ibmcloud cr namespace-add pothole-analyzer

# Push image
docker push us.icr.io/pothole-analyzer/pothole-analyzer-api:latest
```

### Step 5: Deploy to Code Engine

```bash
ibmcloud ce app create \
  --name pothole-analyzer-api \
  --image us.icr.io/pothole-analyzer/pothole-analyzer-api:latest \
  --env WATSONX_API_KEY=$WATSONX_API_KEY \
  --env WATSONX_PROJECT_ID=$WATSONX_PROJECT_ID \
  --env WATSONX_URL=https://us-south.ml.cloud.ibm.com \
  --env VISION_MODEL_ID=meta-llama/llama-3-2-90b-vision-instruct \
  --env FRAME_EXTRACTION_RATE=1 \
  --cpu 2 \
  --memory 4G \
  --min-scale 0 \
  --max-scale 5 \
  --port 8080 \
  --request-timeout 600
```

### Step 6: Get Application URL

```bash
ibmcloud ce app get --name pothole-analyzer-api
```

## Environment Variables

Configure these in Code Engine:

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `WATSONX_API_KEY` | Yes | IBM Cloud API key | - |
| `WATSONX_PROJECT_ID` | Yes | watsonx.ai project ID | - |
| `WATSONX_URL` | No | watsonx.ai service URL | `https://us-south.ml.cloud.ibm.com` |
| `VISION_MODEL_ID` | No | Vision model to use | `meta-llama/llama-3-2-90b-vision-instruct` |
| `FRAME_EXTRACTION_RATE` | No | Frames per second | `1` |
| `PORT` | No | Application port | `8080` |

## Testing the Deployment

### 1. Health Check

```bash
curl https://your-app-url.codeengine.appdomain.cloud/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "pothole-analyzer",
  "configured": true
}
```

### 2. API Information

```bash
curl https://your-app-url.codeengine.appdomain.cloud/
```

### 3. Analyze a Video

```bash
curl -X POST \
  -F "video=@path/to/video.mp4" \
  https://your-app-url.codeengine.appdomain.cloud/analyze
```

## API Usage

### Endpoints

#### GET /
Returns API information and available endpoints.

#### GET /health
Health check endpoint for monitoring.

#### POST /analyze
Upload and analyze a video file.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: video file with key "video"

**Example:**
```bash
curl -X POST \
  -F "video=@road_video.mp4" \
  https://your-app-url.codeengine.appdomain.cloud/analyze \
  -o analysis_report.json
```

**Response:**
```json
{
  "success": true,
  "filename": "road_video.mp4",
  "analysis": {
    "total_potholes_detected": 8,
    "overall_priority": "high",
    "severity_breakdown": {
      "critical": 1,
      "high": 3,
      "medium": 3,
      "low": 1
    },
    "ranked_potholes": [...]
  }
}
```

#### POST /analyze-url
Analyze a video from a URL.

**Request:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://example.com/video.mp4"}' \
  https://your-app-url.codeengine.appdomain.cloud/analyze-url
```

## Resource Configuration

### Recommended Settings

For production use:
```bash
--cpu 2              # 2 vCPU cores
--memory 4G          # 4GB RAM
--min-scale 0        # Scale to zero when idle
--max-scale 5        # Max 5 instances
--request-timeout 600 # 10 minutes timeout
```

For high-volume processing:
```bash
--cpu 4
--memory 8G
--min-scale 1
--max-scale 10
--request-timeout 900
```

### Cost Optimization

- **Scale to Zero**: Set `--min-scale 0` to avoid charges when idle
- **Right-size Resources**: Start with 2 CPU / 4GB and adjust based on usage
- **Request Timeout**: Set appropriate timeout for video processing time

## Monitoring

### View Logs

```bash
# Real-time logs
ibmcloud ce app logs --name pothole-analyzer-api --follow

# Recent logs
ibmcloud ce app logs --name pothole-analyzer-api --tail 100
```

### Application Metrics

```bash
ibmcloud ce app get --name pothole-analyzer-api
```

### IBM Cloud Console

Monitor your application at:
https://cloud.ibm.com/codeengine/projects

## Updating the Application

### Update with New Image

```bash
# Build new image
docker build -t us.icr.io/pothole-analyzer/pothole-analyzer-api:v2 .
docker push us.icr.io/pothole-analyzer/pothole-analyzer-api:v2

# Update application
ibmcloud ce app update \
  --name pothole-analyzer-api \
  --image us.icr.io/pothole-analyzer/pothole-analyzer-api:v2
```

### Update Environment Variables

```bash
ibmcloud ce app update \
  --name pothole-analyzer-api \
  --env FRAME_EXTRACTION_RATE=2
```

## Troubleshooting

### Application Won't Start

1. **Check logs**:
```bash
ibmcloud ce app logs --name pothole-analyzer-api
```

2. **Verify environment variables**:
```bash
ibmcloud ce app get --name pothole-analyzer-api
```

3. **Test locally**:
```bash
docker run -p 8080:8080 \
  -e WATSONX_API_KEY=$WATSONX_API_KEY \
  -e WATSONX_PROJECT_ID=$WATSONX_PROJECT_ID \
  pothole-analyzer:latest
```

### API Returns 503 Error

- Check if watsonx.ai credentials are valid
- Verify project ID is correct
- Ensure sufficient quota in watsonx.ai

### Video Upload Fails

- Check file size (max 500MB by default)
- Verify video format is supported
- Increase request timeout if needed

### Out of Memory Errors

- Increase memory allocation: `--memory 8G`
- Reduce frame extraction rate
- Process shorter video segments

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use environment variables** for all sensitive data
3. **Rotate API keys** regularly
4. **Enable HTTPS** (automatic with Code Engine)
5. **Implement rate limiting** for production use
6. **Monitor API usage** and set alerts

## Cost Estimation

IBM Code Engine pricing (as of 2024):
- **vCPU**: ~$0.00003/vCPU-second
- **Memory**: ~$0.0000034/GB-second
- **Requests**: First 100K free, then $0.40/million

Example monthly cost (moderate use):
- 100 video analyses/month
- 2 vCPU, 4GB RAM
- 5 minutes per analysis
- **Estimated**: $5-15/month

## Support

- **IBM Code Engine Docs**: https://cloud.ibm.com/docs/codeengine
- **watsonx.ai Docs**: https://www.ibm.com/docs/en/watsonx-as-a-service
- **Project Issues**: Create an issue in the repository

## Next Steps

1. ✅ Deploy the application
2. 🧪 Test with sample videos
3. 📊 Monitor performance and costs
4. 🔧 Adjust resources as needed
5. 🚀 Integrate with your workflow

Happy deploying! 🚗🔍