#!/bin/bash

# API Testing Script for Pothole Video Analyzer
# Tests the deployed API endpoints

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
API_URL=${API_URL:-"http://localhost:8080"}
TEST_VIDEO=${TEST_VIDEO:-"samples/test_video.mp4"}

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Pothole Analyzer API Test${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "API URL: $API_URL"
echo ""

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check${NC}"
response=$(curl -s -w "\n%{http_code}" "$API_URL/health")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Health check passed${NC}"
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
else
    echo -e "${RED}✗ Health check failed (HTTP $http_code)${NC}"
    echo "$body"
fi
echo ""

# Test 2: API Info
echo -e "${YELLOW}Test 2: API Information${NC}"
response=$(curl -s -w "\n%{http_code}" "$API_URL/")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ API info retrieved${NC}"
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
else
    echo -e "${RED}✗ API info failed (HTTP $http_code)${NC}"
    echo "$body"
fi
echo ""

# Test 3: Video Analysis (if test video exists)
if [ -f "$TEST_VIDEO" ]; then
    echo -e "${YELLOW}Test 3: Video Analysis${NC}"
    echo "Uploading: $TEST_VIDEO"
    echo "This may take a few minutes..."
    
    response=$(curl -s -w "\n%{http_code}" -X POST \
        -F "video=@$TEST_VIDEO" \
        "$API_URL/analyze")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Video analysis completed${NC}"
        echo "$body" | jq '.analysis | {total_potholes_detected, overall_priority, severity_breakdown}' 2>/dev/null || echo "$body"
        
        # Save full report
        echo "$body" | jq '.' > test_analysis_report.json 2>/dev/null
        echo -e "${GREEN}Full report saved to: test_analysis_report.json${NC}"
    else
        echo -e "${RED}✗ Video analysis failed (HTTP $http_code)${NC}"
        echo "$body"
    fi
else
    echo -e "${YELLOW}Test 3: Video Analysis - SKIPPED${NC}"
    echo "No test video found at: $TEST_VIDEO"
    echo "To test video analysis, provide a video file:"
    echo "  TEST_VIDEO=path/to/video.mp4 ./test_api.sh"
fi
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "API URL: $API_URL"
echo ""
echo -e "${YELLOW}To analyze your own video:${NC}"
echo "  curl -X POST -F 'video=@your_video.mp4' $API_URL/analyze -o report.json"
echo ""
echo -e "${YELLOW}To analyze from URL:${NC}"
echo "  curl -X POST -H 'Content-Type: application/json' \\"
echo "    -d '{\"video_url\": \"https://example.com/video.mp4\"}' \\"
echo "    $API_URL/analyze-url -o report.json"
echo ""

# Made with Bob
