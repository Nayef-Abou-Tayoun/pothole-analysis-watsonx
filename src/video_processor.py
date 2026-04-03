"""
Video processing module for extracting frames from video files.
"""
import cv2
import os
from typing import List, Tuple
import numpy as np
from pathlib import Path


class VideoProcessor:
    """Handles video frame extraction and preprocessing."""
    
    def __init__(self, frame_rate: int = 1):
        """
        Initialize VideoProcessor.
        
        Args:
            frame_rate: Number of frames to extract per second
        """
        self.frame_rate = frame_rate
        
    def extract_frames(self, video_path: str, output_dir: str) -> List[Tuple[str, int, float]]:
        """
        Extract frames from video at specified frame rate.
        
        Args:
            video_path: Path to input video file
            output_dir: Directory to save extracted frames
            
        Returns:
            List of tuples containing (frame_path, frame_number, timestamp)
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        print(f"Video properties:")
        print(f"  - FPS: {fps}")
        print(f"  - Total frames: {total_frames}")
        print(f"  - Duration: {duration:.2f} seconds")
        
        # Calculate frame interval
        frame_interval = int(fps / self.frame_rate)
        
        extracted_frames = []
        frame_count = 0
        saved_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Extract frame at specified interval
            if frame_count % frame_interval == 0:
                timestamp = frame_count / fps
                frame_filename = f"frame_{saved_count:04d}_t{timestamp:.2f}s.jpg"
                frame_path = os.path.join(output_dir, frame_filename)
                
                # Save frame
                cv2.imwrite(frame_path, frame)
                extracted_frames.append((frame_path, frame_count, timestamp))
                saved_count += 1
            
            frame_count += 1
        
        cap.release()
        print(f"Extracted {saved_count} frames from video")
        
        return extracted_frames
    
    def get_video_info(self, video_path: str) -> dict:
        """
        Get video metadata.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary containing video metadata
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        info = {
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'total_frames': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'duration': cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
        }
        
        cap.release()
        return info
    
    @staticmethod
    def resize_frame(frame: np.ndarray, max_size: int = 1024) -> np.ndarray:
        """
        Resize frame while maintaining aspect ratio.
        
        Args:
            frame: Input frame
            max_size: Maximum dimension size
            
        Returns:
            Resized frame
        """
        height, width = frame.shape[:2]
        
        if max(height, width) <= max_size:
            return frame
        
        if height > width:
            new_height = max_size
            new_width = int(width * (max_size / height))
        else:
            new_width = max_size
            new_height = int(height * (max_size / width))
        
        return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

# Made with Bob
