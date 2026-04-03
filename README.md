# Pothole Video Analyzer with watsonx.ai

An AI-powered video analysis tool that detects potholes in road videos, assesses their severity, estimates sizes, and generates detailed maintenance reports using IBM watsonx.ai vision models.

## Features

- 🎥 **Video Frame Extraction**: Automatically extracts frames from video files at configurable rates
- 🔍 **AI-Powered Detection**: Uses IBM watsonx.ai vision models to detect potholes
- 📊 **Severity Assessment**: Ranks potholes by severity (low, medium, high, critical)
- 📏 **Size Estimation**: Provides estimated dimensions for each pothole
- 📍 **Location Tracking**: Identifies pothole locations within frames and video timestamps
- 📝 **Maintenance Reports**: Generates detailed reports for road maintenance teams
- 🎯 **Priority Ranking**: Automatically prioritizes repairs based on severity
- 🐳 **Docker Support**: Containerized deployment ready
- ☁️ **Cloud Ready**: Deploy to IBM Code Engine with one command
- 🌐 **REST API**: Web API for integration with other systems

## Prerequisites


## Quick Start Options

### Option 1: Local Python Installation
Follow the [Installation](#installation) section below.

### Option 2: Docker (Recommended for Production)
```bash
# Using Docker Compose
docker-compose up

# Or build and run manually
docker build -t pothole-analyzer .
docker run -p 8080:8080 \
  -e WATSONX_API_KEY=your_key \
  -e WATSONX_PROJECT_ID=your_project_id \
  pothole-analyzer
```

### Option 3: Deploy to IBM Code Engine
```bash
# One-command deployment
export WATSONX_API_KEY="your_key"
export WATSONX_PROJECT_ID="your_project_id"
export IBM_CLOUD_API_KEY="your_ibm_cloud_key"
./deploy-code-engine.sh
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

- Python 3.8 or higher
- IBM Cloud account with watsonx.ai access
- watsonx.ai API key and project ID

## Installation

### 1. Clone or Navigate to the Project Directory

```bash
cd pothole-video-analyzer
```

### 2. Create a Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure watsonx.ai Credentials

1. Copy the example environment file:
```bash
cp config/.env.example config/.env
```

2. Edit `config/.env` and add your credentials:
```env
WATSONX_API_KEY=your_api_key_here
WATSONX_PROJECT_ID=your_project_id_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com
VISION_MODEL_ID=meta-llama/llama-3-2-90b-vision-instruct
FRAME_EXTRACTION_RATE=1
OUTPUT_DIR=output
```

## Getting watsonx.ai Credentials

### Step 1: Create IBM Cloud Account
1. Go to [IBM Cloud](https://cloud.ibm.com)
2. Sign up or log in

### Step 2: Set Up watsonx.ai
1. Navigate to the [watsonx.ai service](https://www.ibm.com/products/watsonx-ai)
2. Create a new watsonx.ai instance
3. Create a new project in watsonx.ai

### Step 3: Get API Key
1. Go to [IBM Cloud API Keys](https://cloud.ibm.com/iam/apikeys)
2. Click "Create an IBM Cloud API key"
3. Give it a name (e.g., "watsonx-pothole-analyzer")
4. Copy the API key (you won't be able to see it again!)

### Step 4: Get Project ID
1. Open your watsonx.ai project
2. Go to the "Manage" tab
3. Copy the Project ID from the project details

## Usage

### Basic Usage

Analyze a video file:

```bash
cd src
python main.py path/to/your/video.mp4
```

### Example

```bash
cd src
python main.py ../samples/road_inspection.mp4
```

### Output

The analyzer will create an output directory with:

```
output/
└── video_name_20260403_180000/
    ├── frames/                    # Extracted video frames
    │   ├── frame_0000_t0.00s.jpg
    │   ├── frame_0001_t1.00s.jpg
    │   └── ...
    ├── pothole_report.json        # Detailed JSON report
    └── SUMMARY.txt                # Human-readable summary
```

### Report Contents

**SUMMARY.txt** includes:
- Total potholes detected
- Severity breakdown (critical, high, medium, low)
- Overall maintenance priority
- Detailed information for each pothole:
  - Location in frame
  - Estimated size
  - Depth assessment
  - Video timestamp
  - Maintenance recommendations

**pothole_report.json** includes:
- Complete analysis data in JSON format
- Frame-by-frame analysis results
- Ranked potholes list
- Video metadata

## Configuration Options

Edit `config/.env` to customize:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `WATSONX_API_KEY` | Your IBM Cloud API key | Required |
| `WATSONX_PROJECT_ID` | Your watsonx.ai project ID | Required |
| `WATSONX_URL` | watsonx.ai service URL | `https://us-south.ml.cloud.ibm.com` |
| `VISION_MODEL_ID` | Vision model to use | `meta-llama/llama-3-2-90b-vision-instruct` |
| `FRAME_EXTRACTION_RATE` | Frames to extract per second | `1` |
| `OUTPUT_DIR` | Output directory for results | `output` |

### Supported Vision Models

- `meta-llama/llama-3-2-90b-vision-instruct` (Recommended)
- `meta-llama/llama-3-2-11b-vision-instruct`

## Project Structure

```
pothole-video-analyzer/
├── src/
│   ├── main.py                 # Main application
│   ├── video_processor.py      # Video frame extraction
│   └── pothole_analyzer.py     # AI analysis with watsonx.ai
├── config/
│   ├── .env                    # Your credentials (not in git)
│   └── .env.example            # Template for credentials
├── output/                     # Analysis results (created automatically)
├── samples/                    # Sample videos (add your own)
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## How It Works

1. **Frame Extraction**: The video is processed to extract frames at the specified rate (default: 1 frame per second)

2. **AI Analysis**: Each frame is analyzed using watsonx.ai's vision model to:
   - Detect potholes
   - Assess severity
   - Estimate size and depth
   - Identify location

3. **Ranking**: Detected potholes are ranked by severity to prioritize maintenance

4. **Report Generation**: Comprehensive reports are generated in both JSON and human-readable formats

## Troubleshooting

### Import Errors
If you see import errors, make sure you've:
1. Activated your virtual environment
2. Installed all dependencies: `pip install -r requirements.txt`

### API Authentication Errors
- Verify your API key is correct in `config/.env`
- Ensure your watsonx.ai project is active
- Check that you have access to the vision model

### Video Processing Errors
- Ensure the video file exists and is readable
- Supported formats: MP4, AVI, MOV, MKV
- Check that OpenCV is properly installed

### Memory Issues
- Reduce `FRAME_EXTRACTION_RATE` to process fewer frames
- Process shorter video segments
- Ensure sufficient disk space for frame extraction

## Performance Tips

1. **Frame Rate**: Adjust `FRAME_EXTRACTION_RATE` based on video speed:
   - Slow-moving vehicle: 0.5-1 fps
   - Normal speed: 1-2 fps
   - Fast-moving: 2-3 fps

2. **Video Quality**: Higher resolution videos provide better detection but take longer to process

3. **Batch Processing**: Process multiple videos by running the script multiple times

## Example Output

```
==============================================================
Analyzing video: road_inspection.mp4
==============================================================

Step 1: Extracting frames from video...
Video info: 1920x1080, 30.00 fps, 60.00s
✓ Extracted 60 frames

Step 2: Analyzing frames for potholes...
Analyzing frames: 100%|████████████████| 60/60 [02:30<00:00]
✓ Analyzed 60 frames

Step 3: Generating maintenance report...
✓ Report saved to: output/road_inspection_20260403_180000/pothole_report.json
✓ Summary report saved to: output/road_inspection_20260403_180000/SUMMARY.txt

==============================================================
ANALYSIS COMPLETE
==============================================================
Total Potholes Detected: 12
Overall Priority: HIGH

Severity Breakdown:
  - Critical: 2
  - High: 4
  - Medium: 5
  - Low: 1

Full report available at: output/road_inspection_20260403_180000
==============================================================
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is provided as-is for educational and commercial use.

## Support

For issues related to:
- **watsonx.ai**: Check [IBM watsonx.ai documentation](https://www.ibm.com/docs/en/watsonx-as-a-service)
- **This tool**: Open an issue in the project repository

## Acknowledgments

- Built with IBM watsonx.ai
- Uses OpenCV for video processing
- Powered by Meta's Llama vision models