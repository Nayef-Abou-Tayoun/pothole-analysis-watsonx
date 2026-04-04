"""
Pothole detection and analysis module using IBM watsonx.ai.
"""
import os
import base64
from typing import Dict, List, Optional
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai import Credentials
import json


class PotholeAnalyzer:
    """Analyzes images for potholes using watsonx.ai vision models."""
    
    def __init__(self, api_key: str, project_id: str, url: str, model_id: str):
        """
        Initialize PotholeAnalyzer with watsonx.ai credentials.
        
        Args:
            api_key: IBM Cloud API key
            project_id: watsonx.ai project ID
            url: watsonx.ai service URL
            model_id: Vision model ID to use
        """
        self.credentials = Credentials(
            api_key=api_key,
            url=url
        )
        self.project_id = project_id
        self.model_id = model_id
        
        # Initialize model
        self.model = ModelInference(
            model_id=self.model_id,
            credentials=self.credentials,
            project_id=self.project_id,
            params={
                GenParams.MAX_NEW_TOKENS: 500,
                GenParams.TEMPERATURE: 0.3,
                GenParams.TOP_P: 0.9,
            }
        )
    
    def encode_image(self, image_path: str) -> str:
        """
        Encode image to base64 string.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image string
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def analyze_frame(self, frame_path: str, frame_number: int, timestamp: float) -> Dict:
        """
        Analyze a single frame for potholes.
        
        Args:
            frame_path: Path to frame image
            frame_number: Frame number in video
            timestamp: Timestamp in video (seconds)
            
        Returns:
            Dictionary containing analysis results
        """
        # Encode image
        image_base64 = self.encode_image(frame_path)
        
        # Simple and effective prompt - based on successful test
        prompt = """Any issue with the road?

Provide a detailed assessment in JSON format:

{
  "potholes_detected": true/false,
  "count": number of defects found,
  "potholes": [
    {
      "id": 1,
      "severity": "low/medium/high/critical",
      "estimated_size": "description (e.g., 'small - 10-20cm', 'medium - 20-40cm', 'large - 40cm+')",
      "location": "precise location (e.g., 'right side of lane', 'center', 'left side')",
      "depth_assessment": "shallow/moderate/deep",
      "type": "pothole/crack/depression/surface damage",
      "description": "detailed description for maintenance team"
    }
  ],
  "road_condition": "overall assessment",
  "maintenance_priority": "low/medium/high/urgent"
}"""

        try:
            # Generate analysis using vision model
            response = self.model.generate_text(
                prompt=prompt,
                guardrails=False
            )
            
            # Parse response
            analysis = self._parse_analysis(response, frame_path, frame_number, timestamp)
            return analysis
            
        except Exception as e:
            print(f"Error analyzing frame {frame_number}: {str(e)}")
            return {
                'frame_path': frame_path,
                'frame_number': frame_number,
                'timestamp': timestamp,
                'error': str(e),
                'potholes_detected': False
            }
    
    def _parse_analysis(self, response: str, frame_path: str, 
                       frame_number: int, timestamp: float) -> Dict:
        """
        Parse the model response and structure the results.
        
        Args:
            response: Raw model response
            frame_path: Path to analyzed frame
            frame_number: Frame number
            timestamp: Video timestamp
            
        Returns:
            Structured analysis dictionary
        """
        result = {
            'frame_path': frame_path,
            'frame_number': frame_number,
            'timestamp': timestamp,
            'raw_response': response
        }
        
        try:
            # Try to extract JSON from response
            # Look for JSON block in the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)
                result.update(parsed)
            else:
                # If no JSON found, create structured response from text
                result['potholes_detected'] = 'pothole' in response.lower()
                result['analysis_text'] = response
                
        except json.JSONDecodeError:
            # Fallback: analyze text response
            result['potholes_detected'] = 'pothole' in response.lower()
            result['analysis_text'] = response
        
        return result
    
    def rank_by_severity(self, analyses: List[Dict]) -> List[Dict]:
        """
        Rank detected potholes by severity.
        
        Args:
            analyses: List of frame analysis results
            
        Returns:
            Sorted list of potholes by severity
        """
        severity_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        all_potholes = []
        
        for analysis in analyses:
            if analysis.get('potholes_detected') and 'potholes' in analysis:
                for pothole in analysis['potholes']:
                    pothole['frame_info'] = {
                        'frame_number': analysis['frame_number'],
                        'timestamp': analysis['timestamp'],
                        'frame_path': analysis['frame_path']
                    }
                    all_potholes.append(pothole)
        
        # Sort by severity
        all_potholes.sort(
            key=lambda x: severity_order.get(x.get('severity', 'low'), 0),
            reverse=True
        )
        
        return all_potholes
    
    def generate_maintenance_report(self, analyses: List[Dict], 
                                   video_path: str) -> Dict:
        """
        Generate comprehensive maintenance report.
        
        Args:
            analyses: List of all frame analyses
            video_path: Path to analyzed video
            
        Returns:
            Comprehensive maintenance report
        """
        ranked_potholes = self.rank_by_severity(analyses)
        
        # Count by severity
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for pothole in ranked_potholes:
            severity = pothole.get('severity', 'low')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Determine overall priority
        if severity_counts['critical'] > 0:
            overall_priority = 'urgent'
        elif severity_counts['high'] > 0:
            overall_priority = 'high'
        elif severity_counts['medium'] > 0:
            overall_priority = 'medium'
        else:
            overall_priority = 'low'
        
        report = {
            'video_file': os.path.basename(video_path),
            'total_frames_analyzed': len(analyses),
            'frames_with_potholes': sum(1 for a in analyses if a.get('potholes_detected')),
            'total_potholes_detected': len(ranked_potholes),
            'severity_breakdown': severity_counts,
            'overall_priority': overall_priority,
            'ranked_potholes': ranked_potholes,
            'detailed_analyses': analyses
        }
        
        return report

# Made with Bob
