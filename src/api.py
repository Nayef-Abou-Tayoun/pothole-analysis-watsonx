"""
Flask API for pothole video analysis - designed for IBM Code Engine deployment.
"""
import os
import json
import tempfile
import shutil
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


def cleanup_old_files(directory, keep_current=None):
    """Clean up old files and directories, optionally keeping current one."""
    try:
        if os.path.exists(directory):
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if keep_current and item == keep_current:
                    continue
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    print(f"Warning: Could not delete {item_path}: {e}")
    except Exception as e:
        print(f"Warning: Cleanup failed for {directory}: {e}")


def generate_summary_report(report):
    """Generate a detailed 3+ line summary focusing on specific pothole characteristics."""
    total_frames = report.get('total_frames_analyzed', 0)
    
    # Get all frame analyses
    analyses = report.get('detailed_analyses', [])
    
    # Collect detailed pothole information
    pothole_details = []
    road_markings_clear = True
    traffic_conditions = []
    has_street_lights = False
    num_lanes = None
    weather_condition = None
    side_features = set()  # Use set to avoid duplicates
    
    for analysis in analyses:
        raw_text = analysis.get('raw_response', '').lower()
        frame_num = analysis.get('frame_number', 0)
        
        # Extract pothole details if found
        if 'pothole' in raw_text:
            detail = {'frame': frame_num, 'raw_text': raw_text}
            
            # Determine size and estimate in cm
            if 'large' in raw_text:
                detail['size'] = 'large'
                detail['size_cm'] = '50-80 cm'
                detail['severity'] = 'medium'
            elif 'medium' in raw_text:
                detail['size'] = 'medium'
                detail['size_cm'] = '20-50 cm'
                detail['severity'] = 'medium'
            elif 'small' in raw_text:
                detail['size'] = 'small'
                detail['size_cm'] = '10-20 cm'
                detail['severity'] = 'low'
            else:
                detail['size'] = 'medium'
                detail['size_cm'] = '20-50 cm'
                detail['severity'] = 'medium'
            
            # Determine location (left/center/right)
            if 'left' in raw_text:
                detail['position'] = 'left'
            elif 'right' in raw_text:
                detail['position'] = 'right'
            elif 'center' in raw_text or 'middle' in raw_text:
                detail['position'] = 'center'
            elif 'barrier' in raw_text:
                detail['position'] = 'barrier area'
            else:
                detail['position'] = 'center'
            
            # Determine lane if mentioned
            if 'lane 1' in raw_text or 'first lane' in raw_text:
                detail['lane'] = 'lane 1'
            elif 'lane 2' in raw_text or 'second lane' in raw_text:
                detail['lane'] = 'lane 2'
            else:
                detail['lane'] = 'main lane'
            
            pothole_details.append(detail)
        
        # Check road markings
        if 'marking' in raw_text:
            if 'faded' in raw_text or 'unclear' in raw_text or 'worn' in raw_text:
                road_markings_clear = False
        
        # Check traffic conditions
        if 'traffic' in raw_text:
            if 'heavy' in raw_text:
                traffic_conditions.append('heavy')
            elif 'light' in raw_text:
                traffic_conditions.append('light')
            elif 'moderate' in raw_text:
                traffic_conditions.append('moderate')
        
        # Check for street lights
        if 'light' in raw_text or 'street light' in raw_text or 'lamp' in raw_text or 'lighting' in raw_text:
            has_street_lights = True
        
        # Detect number of lanes - AI counts them from the image
        # Look for explicit lane counts
        if '4 lane' in raw_text or 'four lane' in raw_text:
            num_lanes = 4
        elif '3 lane' in raw_text or 'three lane' in raw_text:
            num_lanes = 3
        elif '2 lane' in raw_text or 'two lane' in raw_text:
            num_lanes = 2
        elif '1 lane' in raw_text or 'one lane' in raw_text or 'single lane' in raw_text:
            num_lanes = 1
        
        # Detect weather conditions
        if 'snow' in raw_text or 'snowy' in raw_text or 'snowing' in raw_text:
            weather_condition = 'snow'
        elif 'rain' in raw_text or 'rainy' in raw_text or 'raining' in raw_text or 'wet' in raw_text:
            weather_condition = 'rain'
        elif 'fog' in raw_text or 'foggy' in raw_text:
            weather_condition = 'fog'
        elif 'sunny' in raw_text or 'clear' in raw_text or 'bright' in raw_text:
            weather_condition = 'clear'
        elif 'cloudy' in raw_text or 'overcast' in raw_text:
            weather_condition = 'cloudy'
        
        # Detect side features - track counts to find most prominent
        if 'concrete barrier' in raw_text or 'traffic barrier' in raw_text or 'barrier' in raw_text:
            side_features.add('concrete traffic barriers')
        
        # Detect pedestrian areas
        if ('pedestrian' in raw_text or 'sidewalk' in raw_text or 'footpath' in raw_text or
            'pavement' in raw_text or 'walkway' in raw_text):
            side_features.add('pedestrian pavement')
        
        if 'cycle' in raw_text or 'bike lane' in raw_text or 'bicycle lane' in raw_text:
            side_features.add('cycle lane')
        
        if 'open side' in raw_text or 'open' in raw_text:
            side_features.add('open side')
    
    # Build summary
    if not pothole_details:
        line1 = f"Analysis Summary: Analyzed {total_frames} frames. No potholes detected in the road segment."
        line2 = f"Road markings are {'clear and visible' if road_markings_clear else 'faded or unclear'}. Overall traffic conditions appear normal with well-maintained road surface."
        line3 = f"Street lights are {'present' if has_street_lights else 'not visible in the analyzed frames'}."
        summary = f"{line1}\n{line2}\n{line3}"
    else:
        # Focus on the most significant pothole (largest or first found)
        primary_pothole = pothole_details[0]
        for p in pothole_details:
            if p['size'] == 'large':
                primary_pothole = p
                break
        
        # Determine overall traffic
        if traffic_conditions:
            traffic_desc = max(set(traffic_conditions), key=traffic_conditions.count)
        else:
            traffic_desc = 'moderate'
        
        # Build detailed summary with lanes, sides, and weather
        line1 = f"Analysis Summary: Pothole detected {primary_pothole['size']} size (estimated {primary_pothole['size_cm']}), located on the {primary_pothole['position']} side of {primary_pothole['lane']}. Severity is {primary_pothole['severity']}."
        
        # Line 2: Road markings, lanes, sides, traffic, and weather
        line2_parts = [f"Road markings are {'clear and visible' if road_markings_clear else 'faded or unclear'}."]
        
        if num_lanes:
            line2_parts.append(f"It is a {num_lanes} lane street.")
        
        # Show only the most prominent side feature (first one found is usually most visible)
        if side_features:
            # Priority order: barriers > pedestrian > cycle > open
            if 'concrete traffic barriers' in side_features:
                prominent_feature = 'concrete traffic barriers'
            elif 'pedestrian pavement' in side_features:
                prominent_feature = 'pedestrian pavement'
            elif 'cycle lane' in side_features:
                prominent_feature = 'cycle lane'
            else:
                prominent_feature = 'open side'
            line2_parts.append(f"Sides have {prominent_feature}.")
        
        line2_parts.append(f"Overall traffic conditions: {traffic_desc}.")
        
        if weather_condition:
            line2_parts.append(f"Weather condition: {weather_condition}.")
        
        line2 = " ".join(line2_parts)
        
        # Line 3: Street lights
        if has_street_lights:
            line3 = "There are street lights so pothole expected to be visible during night."
        else:
            line3 = "No street lights visible, pothole may not be easily visible during night."
        
        summary = f"{line1}\n{line2}\n{line3}"
    
    return summary


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


@app.route('/frames/<path:filename>')
def serve_frame(filename):
    """Serve frame images."""
    try:
        # Security: ensure the path is within OUTPUT_FOLDER
        safe_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if not os.path.abspath(safe_path).startswith(os.path.abspath(app.config['OUTPUT_FOLDER'])):
            return jsonify({'error': 'Invalid path'}), 403
        
        if os.path.exists(safe_path):
            return send_file(safe_path, mimetype='image/jpeg')
        else:
            return jsonify({'error': 'Frame not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
        
        # Clean up old uploads and outputs before processing new file
        cleanup_old_files(app.config['UPLOAD_FOLDER'])
        cleanup_old_files(app.config['OUTPUT_FOLDER'])
        
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
        
        # Generate summary report
        print("Generating summary report...")
        summary = generate_summary_report(report)
        report['summary'] = summary
        print("Summary report generated")
        
        # Clean up uploaded video file only (keep frames for display)
        print("Cleaning up video file...")
        os.remove(video_path)
        print("Cleanup complete (frames preserved for display)")
        
        # Return analysis
        print("Sending response...")
        import sys
        sys.stdout.flush()
        
        try:
            # Filter analyses to show only frames with medium severity potholes
            video_stem = Path(filename).stem
            filtered_analyses = []
            
            for analysis in analyses:
                raw_text = analysis.get('raw_response', '').lower()
                
                # Check if frame has a pothole with medium severity
                has_medium_pothole = False
                if 'pothole' in raw_text:
                    # Check for medium or large size (both are medium severity)
                    if 'medium' in raw_text or 'large' in raw_text:
                        has_medium_pothole = True
                
                # Only include frames with medium severity potholes
                if has_medium_pothole:
                    # Add frame URL if frame exists
                    if 'frame_path' in analysis:
                        frame_filename = os.path.basename(analysis['frame_path'])
                        analysis['frame_url'] = f'/frames/{video_stem}/frames/{frame_filename}'
                    filtered_analyses.append(analysis)
            
            # Update report with filtered analyses
            report['detailed_analyses'] = filtered_analyses
            
            response_data = {
                'success': True,
                'filename': filename,
                'analysis': report
            }
            print(f"Response data size: {len(str(response_data))} characters")
            sys.stdout.flush()
            
            print("Response created successfully, returning...")
            sys.stdout.flush()
            
            # Use jsonify which properly handles Flask response
            response = jsonify(response_data)
            
            # Force immediate flush
            sys.stdout.flush()
            sys.stderr.flush()
            
            print(f"Returning response")
            sys.stdout.flush()
            
            return response
        except Exception as e:
            print(f"Error creating response: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            raise
        finally:
            print("Response function completed")
            sys.stdout.flush()
        
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
