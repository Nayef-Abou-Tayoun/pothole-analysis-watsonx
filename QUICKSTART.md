# Quick Start Guide

Get up and running with the Pothole Video Analyzer in 5 minutes!

## Step 1: Install Dependencies (2 minutes)

```bash
cd pothole-video-analyzer

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

## Step 2: Configure watsonx.ai (2 minutes)

1. Copy the configuration template:
```bash
cp config/.env.example config/.env
```

2. Edit `config/.env` and add your credentials:
```env
WATSONX_API_KEY=your_actual_api_key
WATSONX_PROJECT_ID=your_actual_project_id
```

**Don't have credentials?** See [Getting watsonx.ai Credentials](README.md#getting-watsonxai-credentials) in the README.

## Step 3: Run Analysis (1 minute)

```bash
cd src
python main.py path/to/your/video.mp4
```

Example:
```bash
python main.py ../samples/road_video.mp4
```

## What Happens Next?

The analyzer will:
1. ✅ Extract frames from your video
2. 🔍 Analyze each frame for potholes using AI
3. 📊 Rank potholes by severity
4. 📝 Generate detailed reports

## View Results

Check the `output/` directory for:
- `SUMMARY.txt` - Human-readable report
- `pothole_report.json` - Detailed JSON data
- `frames/` - Extracted video frames

## Example Output

```
==============================================================
ANALYSIS COMPLETE
==============================================================
Total Potholes Detected: 8
Overall Priority: HIGH

Severity Breakdown:
  - Critical: 1
  - High: 3
  - Medium: 3
  - Low: 1
==============================================================
```

## Need Help?

- 📖 Full documentation: [README.md](README.md)
- 🐛 Issues? Check the [Troubleshooting](README.md#troubleshooting) section
- 💡 Questions? Review the [Configuration Options](README.md#configuration-options)

## Tips for Best Results

1. **Video Quality**: Use clear, well-lit road footage
2. **Frame Rate**: Adjust based on vehicle speed (default: 1 fps)
3. **Video Length**: Start with shorter clips (30-60 seconds) for testing

Happy analyzing! 🚗🔍