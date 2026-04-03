"""
Main application for pothole video analysis using watsonx.ai.
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm

from video_processor import VideoProcessor
from pothole_analyzer import PotholeAnalyzer


class PotholeVideoAnalyzer:
    """Main application class for video analysis."""
    
    def __init__(self):
        """Initialize the analyzer with configuration."""
        # Load environment variables
        load_dotenv('config/.env')
        
        # Get configuration
        self.api_key = os.getenv('WATSONX_API_KEY')
        self.project_id = os.getenv('WATSONX_PROJECT_ID')
        self.url = os.getenv('WATSONX_URL', 'https://us-south.ml.cloud.ibm.com')
        self.model_id = os.getenv('VISION_MODEL_ID', 'meta-llama/llama-3-2-90b-vision-instruct')
        self.frame_rate = int(os.getenv('FRAME_EXTRACTION_RATE', '1'))
        self.output_dir = os.getenv('OUTPUT_DIR', 'output')
        
        # Validate configuration
        if not self.api_key or not self.project_id:
            raise ValueError(
                "Missing required configuration. Please set WATSONX_API_KEY and "
                "WATSONX_PROJECT_ID in config/.env file"
            )
        
        # Initialize components
        self.video_processor = VideoProcessor(frame_rate=self.frame_rate)
        self.pothole_analyzer = PotholeAnalyzer(
            api_key=self.api_key,
            project_id=self.project_id,
            url=self.url,
            model_id=self.model_id
        )
        
        print("✓ Pothole Video Analyzer initialized")
        print(f"  - Model: {self.model_id}")
        print(f"  - Frame extraction rate: {self.frame_rate} fps")
    
    def analyze_video(self, video_path: str) -> dict:
        """
        Analyze a video file for potholes.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Analysis report dictionary
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        print(f"\n{'='*60}")
        print(f"Analyzing video: {os.path.basename(video_path)}")
        print(f"{'='*60}\n")
        
        # Create output directory for this video
        video_name = Path(video_path).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_dir = os.path.join(self.output_dir, f"{video_name}_{timestamp}")
        frames_dir = os.path.join(analysis_dir, "frames")
        
        Path(analysis_dir).mkdir(parents=True, exist_ok=True)
        
        # Step 1: Extract frames
        print("Step 1: Extracting frames from video...")
        video_info = self.video_processor.get_video_info(video_path)
        print(f"Video info: {video_info['width']}x{video_info['height']}, "
              f"{video_info['fps']:.2f} fps, {video_info['duration']:.2f}s")
        
        extracted_frames = self.video_processor.extract_frames(video_path, frames_dir)
        print(f"✓ Extracted {len(extracted_frames)} frames\n")
        
        # Step 2: Analyze each frame
        print("Step 2: Analyzing frames for potholes...")
        analyses = []
        
        for frame_path, frame_number, timestamp in tqdm(extracted_frames, desc="Analyzing frames"):
            analysis = self.pothole_analyzer.analyze_frame(
                frame_path, frame_number, timestamp
            )
            analyses.append(analysis)
        
        print(f"✓ Analyzed {len(analyses)} frames\n")
        
        # Step 3: Generate report
        print("Step 3: Generating maintenance report...")
        report = self.pothole_analyzer.generate_maintenance_report(analyses, video_path)
        
        # Add video info to report
        report['video_info'] = video_info
        report['analysis_timestamp'] = timestamp
        report['analysis_directory'] = analysis_dir
        
        # Save report
        report_path = os.path.join(analysis_dir, "pothole_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✓ Report saved to: {report_path}\n")
        
        # Generate summary report
        self._generate_summary_report(report, analysis_dir)
        
        return report
    
    def _generate_summary_report(self, report: dict, output_dir: str):
        """
        Generate a human-readable summary report.
        
        Args:
            report: Analysis report dictionary
            output_dir: Output directory path
        """
        summary_path = os.path.join(output_dir, "SUMMARY.txt")
        
        with open(summary_path, 'w') as f:
            f.write("="*70 + "\n")
            f.write("POTHOLE DETECTION AND ANALYSIS REPORT\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Video File: {report['video_file']}\n")
            f.write(f"Analysis Date: {report['analysis_timestamp']}\n")
            f.write(f"Total Frames Analyzed: {report['total_frames_analyzed']}\n")
            f.write(f"Frames with Potholes: {report['frames_with_potholes']}\n\n")
            
            f.write("-"*70 + "\n")
            f.write("SUMMARY\n")
            f.write("-"*70 + "\n")
            f.write(f"Total Potholes Detected: {report['total_potholes_detected']}\n")
            f.write(f"Overall Priority: {report['overall_priority'].upper()}\n\n")
            
            f.write("Severity Breakdown:\n")
            for severity, count in report['severity_breakdown'].items():
                if count > 0:
                    f.write(f"  - {severity.capitalize()}: {count}\n")
            
            f.write("\n" + "-"*70 + "\n")
            f.write("DETAILED POTHOLE INFORMATION (Ranked by Severity)\n")
            f.write("-"*70 + "\n\n")
            
            for idx, pothole in enumerate(report['ranked_potholes'], 1):
                f.write(f"Pothole #{idx}\n")
                f.write(f"  Severity: {pothole.get('severity', 'N/A').upper()}\n")
                f.write(f"  Location: {pothole.get('location', 'N/A')}\n")
                f.write(f"  Size: {pothole.get('estimated_size', 'N/A')}\n")
                f.write(f"  Depth: {pothole.get('depth_assessment', 'N/A')}\n")
                f.write(f"  Video Timestamp: {pothole['frame_info']['timestamp']:.2f}s\n")
                f.write(f"  Frame: {pothole['frame_info']['frame_number']}\n")
                f.write(f"  Description: {pothole.get('description', 'N/A')}\n")
                f.write("\n")
            
            f.write("-"*70 + "\n")
            f.write("MAINTENANCE RECOMMENDATIONS\n")
            f.write("-"*70 + "\n")
            
            if report['overall_priority'] == 'urgent':
                f.write("⚠️  URGENT ACTION REQUIRED\n")
                f.write("Critical potholes detected that require immediate attention.\n")
            elif report['overall_priority'] == 'high':
                f.write("⚠️  HIGH PRIORITY\n")
                f.write("Significant potholes detected. Schedule repairs soon.\n")
            elif report['overall_priority'] == 'medium':
                f.write("Medium priority repairs needed.\n")
            else:
                f.write("Low priority. Monitor and schedule routine maintenance.\n")
        
        print(f"✓ Summary report saved to: {summary_path}")
        
        # Print summary to console
        print(f"\n{'='*60}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*60}")
        print(f"Total Potholes Detected: {report['total_potholes_detected']}")
        print(f"Overall Priority: {report['overall_priority'].upper()}")
        print(f"\nSeverity Breakdown:")
        for severity, count in report['severity_breakdown'].items():
            if count > 0:
                print(f"  - {severity.capitalize()}: {count}")
        print(f"\nFull report available at: {output_dir}")
        print(f"{'='*60}\n")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_video>")
        print("\nExample:")
        print("  python main.py ../samples/road_video.mp4")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    try:
        analyzer = PotholeVideoAnalyzer()
        report = analyzer.analyze_video(video_path)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

# Made with Bob
