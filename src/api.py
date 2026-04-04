"""
Flask API for pothole video analysis - designed for IBM Code Engine deployment.
"""
import os
import json
import tempfile
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from video_processor import VideoProcessor
from pothole_analyzer import PotholeAnalyzer

# Load environment variables
load_dotenv('config/.env')

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
app.config['OUTPUT_FOLDER'] = '/tmp/output'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Allowed video extensions
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def initialize_analyzer():
    """Initialize the pothole analyzer with configuration."""
    api_key = os.getenv('WATSONX_API_KEY')
    project_id = os.getenv('WATSONX_PROJECT_ID')
    url = os.getenv('WATSONX_URL', 'https://us-south.ml.cloud.ibm.com')
    model_id = os.getenv('VISION_MODEL_ID', 'meta-llama/llama-3-2-90b-vision-instruct')
    frame_rate = int(os.getenv('FRAME_EXTRACTION_RATE', '1'))
    
    if not api_key or not project_id:
        raise ValueError("Missing WATSONX_API_KEY or WATSONX_PROJECT_ID")
    
    video_processor = VideoProcessor(frame_rate=frame_rate)
    pothole_analyzer = PotholeAnalyzer(
        api_key=api_key,
        project_id=project_id,
        url=url,
        model_id=model_id
    )
    
    return video_processor, pothole_analyzer


@app.route('/', methods=['GET'])
def home():
    """Serve the web UI or API information based on Accept header."""
    # Check if request is from a browser (wants HTML)
    if 'text/html' in request.headers.get('Accept', ''):
        return render_template('index.html')
    
    # Return JSON for API clients
    return jsonify({
        'service': 'Pothole Video Analyzer API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'GET /': 'Web UI or API information',
            'POST /analyze': 'Upload and analyze a video file',
            'POST /analyze-url': 'Analyze video from URL',
            'GET /health': 'Health check endpoint',
            'GET /api': 'API information (JSON)'
        }
    })


@app.route('/api', methods=['GET'])
def api_info():
    """API information endpoint."""
    return jsonify({
        'service': 'Pothole Video Analyzer API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'GET /': 'Web UI',
            'POST /analyze': 'Upload and analyze a video file',
            'POST /analyze-url': 'Analyze video from URL',
            'GET /health': 'Health check endpoint',
            'GET /api': 'This information page'
        }
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for Code Engine."""
    try:
        # Check if credentials are configured
        api_key = os.getenv('WATSONX_API_KEY')
        project_id = os.getenv('WATSONX_PROJECT_ID')
        
        if not api_key or not project_id:
            return jsonify({
                'status': 'unhealthy',
                'error': 'Missing watsonx.ai credentials'
            }), 503
        
        return jsonify({
            'status': 'healthy',
            'service': 'pothole-analyzer',
            'configured': True
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503


@app.route('/analyze', methods=['POST'])
def analyze_video():
    """
    Analyze uploaded video for potholes.
    
    Expected: multipart/form-data with 'video' file
    Returns: JSON analysis report
    """
    try:
        # Check if video file is present
        if 'video' not in request.files:
            return jsonify({
                'error': 'No video file provided',
                'message': 'Please upload a video file with key "video"'
            }), 400
        
        file = request.files['video']
        
        if file.filename == '':
            return jsonify({
                'error': 'No file selected',
                'message': 'Please select a video file'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': 'Invalid file type',
                'message': f'Allowed types: {", ".join(ALLOWED_EXTENSIONS)}',
                'received': file.filename
            }), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(video_path)
        
        # Initialize analyzer
        video_processor, pothole_analyzer = initialize_analyzer()
        
        # Create output directory
        output_dir = os.path.join(app.config['OUTPUT_FOLDER'], Path(filename).stem)
        frames_dir = os.path.join(output_dir, 'frames')
        os.makedirs(frames_dir, exist_ok=True)
        
        # Extract frames
        extracted_frames = video_processor.extract_frames(video_path, frames_dir)
        
        # Analyze frames with parallel processing and fallback
        max_workers = min(int(os.getenv('MAX_WORKERS', '4')), 8)
        use_parallel = os.getenv('USE_PARALLEL', 'true').lower() == 'true'
        analyses = []
        
        if use_parallel and len(extracted_frames) > 1:
            print(f"Analyzing {len(extracted_frames)} frames using {max_workers} parallel workers...")
            
            try:
                # Use ThreadPoolExecutor with timeout protection
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all frame analysis tasks
                    future_to_frame = {
                        executor.submit(
                            pothole_analyzer.analyze_frame,
                            frame_path,
                            frame_number,
                            timestamp
                        ): (frame_path, frame_number, timestamp)
                        for frame_path, frame_number, timestamp in extracted_frames
                    }
                    
                    # Collect results with timeout (60 seconds per frame)
                    for future in as_completed(future_to_frame, timeout=60*len(extracted_frames)):
                        frame_info = future_to_frame[future]
                        try:
                            analysis = future.result(timeout=60)
                            analyses.append(analysis)
                            print(f"✓ Completed frame {frame_info[1]}/{len(extracted_frames)}")
                        except Exception as e:
                            print(f"✗ Error analyzing frame {frame_info[1]}: {str(e)}")
                            analyses.append({
                                'frame_path': frame_info[0],
                                'frame_number': frame_info[1],
                                'timestamp': frame_info[2],
                                'error': str(e),
                                'potholes_detected': False
                            })
                
                print(f"Parallel processing completed: {len(analyses)} frames analyzed")
                
            except Exception as e:
                print(f"Parallel processing failed: {str(e)}")
                print("Falling back to sequential processing...")
                analyses = []
                use_parallel = False
        
        # Fallback to sequential processing if parallel fails or disabled
        if not use_parallel or len(analyses) == 0:
            print(f"Analyzing {len(extracted_frames)} frames sequentially...")
            for i, (frame_path, frame_number, timestamp) in enumerate(extracted_frames, 1):
                try:
                    print(f"Processing frame {i}/{len(extracted_frames)}...")
                    analysis = pothole_analyzer.analyze_frame(
                        frame_path, frame_number, timestamp
                    )
                    analyses.append(analysis)
                    print(f"✓ Completed frame {i}/{len(extracted_frames)}")
                except Exception as e:
                    print(f"✗ Error analyzing frame {i}: {str(e)}")
                    analyses.append({
                        'frame_path': frame_path,
                        'frame_number': frame_number,
                        'timestamp': timestamp,
                        'error': str(e),
                        'potholes_detected': False
                    })
        
        # Sort analyses by frame number to maintain order
        analyses.sort(key=lambda x: x.get('frame_number', 0))
        print(f"Analysis complete: {len(analyses)} frames processed")
        
        # Generate report
        print("Generating maintenance report...")
        try:
            report = pothole_analyzer.generate_maintenance_report(analyses, video_path)
            print("Report generated successfully")
        except Exception as e:
            print(f"Error generating report: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        
        # Add video info
        print("Adding video info...")
        video_info = video_processor.get_video_info(video_path)
        report['video_info'] = video_info
        print("Video info added")
        
        # Clean up uploaded file
        print("Cleaning up files...")
        os.remove(video_path)
        print("Cleanup complete")
        
        # Return analysis
        print("Sending response...")
        import sys
        sys.stdout.flush()
        
        try:
            response_data = {
                'success': True,
                'filename': filename,
                'analysis': report
            }
            print(f"Response data size: {len(str(response_data))} characters")
            sys.stdout.flush()
            
            response = jsonify(response_data)
            print("Response created successfully")
            sys.stdout.flush()
            
            return response
        except Exception as e:
            print(f"Error creating response: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            raise
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error analyzing video: {error_trace}")
        return jsonify({
            'error': 'Analysis failed',
            'message': str(e),
            'trace': error_trace if app.debug else None
        }), 500


@app.route('/analyze-url', methods=['POST'])
def analyze_video_url():
    """
    Analyze video from URL.
    
    Expected JSON: {"video_url": "https://..."}
    Returns: JSON analysis report
    """
    try:
        data = request.get_json()
        
        if not data or 'video_url' not in data:
            return jsonify({
                'error': 'No video URL provided',
                'message': 'Please provide video_url in JSON body'
            }), 400
        
        video_url = data['video_url']
        
        # Download video (implement download logic)
        import requests
        response = requests.get(video_url, stream=True)
        
        if response.status_code != 200:
            return jsonify({
                'error': 'Failed to download video',
                'status_code': response.status_code
            }), 400
        
        # Save to temp file
        filename = secure_filename(video_url.split('/')[-1])
        if not allowed_file(filename):
            filename = 'video.mp4'
        
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(video_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Process similar to analyze_video
        video_processor, pothole_analyzer = initialize_analyzer()
        
        output_dir = os.path.join(app.config['OUTPUT_FOLDER'], Path(filename).stem)
        frames_dir = os.path.join(output_dir, 'frames')
        os.makedirs(frames_dir, exist_ok=True)
        
        extracted_frames = video_processor.extract_frames(video_path, frames_dir)
        
        # Analyze frames with parallel processing and fallback
        max_workers = min(int(os.getenv('MAX_WORKERS', '4')), 8)
        use_parallel = os.getenv('USE_PARALLEL', 'true').lower() == 'true'
        analyses = []
        
        if use_parallel and len(extracted_frames) > 1:
            print(f"Analyzing {len(extracted_frames)} frames using {max_workers} parallel workers...")
            
            try:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_frame = {
                        executor.submit(
                            pothole_analyzer.analyze_frame,
                            frame_path,
                            frame_number,
                            timestamp
                        ): (frame_path, frame_number, timestamp)
                        for frame_path, frame_number, timestamp in extracted_frames
                    }
                    
                    for future in as_completed(future_to_frame, timeout=60*len(extracted_frames)):
                        frame_info = future_to_frame[future]
                        try:
                            analysis = future.result(timeout=60)
                            analyses.append(analysis)
                            print(f"✓ Completed frame {frame_info[1]}/{len(extracted_frames)}")
                        except Exception as e:
                            print(f"✗ Error analyzing frame {frame_info[1]}: {str(e)}")
                            analyses.append({
                                'frame_path': frame_info[0],
                                'frame_number': frame_info[1],
                                'timestamp': frame_info[2],
                                'error': str(e),
                                'potholes_detected': False
                            })
                
                print(f"Parallel processing completed: {len(analyses)} frames analyzed")
                
            except Exception as e:
                print(f"Parallel processing failed: {str(e)}")
                print("Falling back to sequential processing...")
                analyses = []
                use_parallel = False
        
        if not use_parallel or len(analyses) == 0:
            print(f"Analyzing {len(extracted_frames)} frames sequentially...")
            for i, (frame_path, frame_number, timestamp) in enumerate(extracted_frames, 1):
                try:
                    print(f"Processing frame {i}/{len(extracted_frames)}...")
                    analysis = pothole_analyzer.analyze_frame(
                        frame_path, frame_number, timestamp
                    )
                    analyses.append(analysis)
                    print(f"✓ Completed frame {i}/{len(extracted_frames)}")
                except Exception as e:
                    print(f"✗ Error analyzing frame {i}: {str(e)}")
                    analyses.append({
                        'frame_path': frame_path,
                        'frame_number': frame_number,
                        'timestamp': timestamp,
                        'error': str(e),
                        'potholes_detected': False
                    })
        
        analyses.sort(key=lambda x: x.get('frame_number', 0))
        print(f"Analysis complete: {len(analyses)} frames processed")
        
        report = pothole_analyzer.generate_maintenance_report(analyses, video_path)
        video_info = video_processor.get_video_info(video_path)
        report['video_info'] = video_info
        
        # Clean up
        os.remove(video_path)
        
        return jsonify({
            'success': True,
            'video_url': video_url,
            'analysis': report
        })
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error analyzing video from URL: {error_trace}")
        return jsonify({
            'error': 'Analysis failed',
            'message': str(e),
            'trace': error_trace if app.debug else None
        }), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"Starting Pothole Video Analyzer API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)

# Made with Bob
