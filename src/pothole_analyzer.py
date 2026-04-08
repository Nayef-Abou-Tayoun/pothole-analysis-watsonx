"""
Pothole detection and analysis module using IBM watsonx.ai.
"""
import os
import base64
from typing import Dict, List
import json
import requests


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
        self.api_key = api_key
        self.project_id = project_id
        self.model_id = model_id
        self.url = url
        
        # Get access token for API calls
        self.access_token = self._get_access_token()
    
    def _get_access_token(self) -> str:
        """Get IBM Cloud IAM access token."""
        token_url = "https://iam.cloud.ibm.com/identity/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": self.api_key
        }
        
        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code != 200:
            raise Exception(f"Failed to get access token: {response.text}")
        
        return response.json()["access_token"]
    
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
        Analyze a single frame for potholes using chat API with vision.
        
        Args:
            frame_path: Path to frame image
            frame_number: Frame number in video
            timestamp: Timestamp in video (seconds)
            
        Returns:
            Dictionary containing analysis results
        """
        # Encode image to base64
        image_base64 = self.encode_image(frame_path)
        
        # Prepare chat API request
        url = f"{self.url}/ml/v1/text/chat?version=2023-05-29"
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        # Enhanced prompt with Toronto pothole criteria and context
        prompt_text = """You are analyzing road conditions for the City of Toronto's pothole repair program on an EXPRESSWAY (default: Gardiner Expressway).

IMPORTANT: Only include Toronto repair information that is RELEVANT to what you observe in the image.

POTHOLE SIZE CRITERIA (City of Toronto Standards):
• Expressways: Repair required if over 600 cm² surface area and 8 cm deep
• Arterial Roads: Repair required if over 800 cm² surface area and 8 cm deep
• Collector/Local Roads: Repair required if over 1,000 cm² surface area and 8 cm deep

REPAIR PRIORITY FOR EXPRESSWAYS:
• Emergency (24 hours): Large potholes posing immediate risk to vehicles or pedestrians
• High Priority (4 days): Standard expressway repairs (over 40,000 vehicles/day)

CONTEXT TO USE WHEN RELEVANT:
• If you see cracks or water damage: Mention that potholes form when water seeps into cracks, freezes, and expands
• If weather appears wet/icy/snowy: Note that freeze-thaw cycles increase pothole formation
• If pothole detected: State whether it meets expressway repair criteria (600 cm² and 8 cm deep)
• If pothole is large/dangerous: Mention Emergency repair timeline (24 hours)
• If pothole is moderate: Mention High Priority timeline (4 days for expressways)

EXPRESSWAY CHARACTERISTICS TO VERIFY:
• Multiple lanes (typically 2-4 lanes per direction)
• High traffic volume (over 40,000 vehicles/day)
• Concrete traffic barriers on sides

Now analyze this expressway road image and provide:
1) POTHOLE DETECTION: If found, estimate size in cm² and depth in cm, exact location (which lane, left/center/right). State if it meets expressway repair criteria (600 cm² and 8 cm deep). If you see cracks or water damage, briefly mention the freeze-thaw cause.

2) ROAD CLASSIFICATION: Confirm expressway characteristics (lanes, barriers). If pothole detected, state the applicable repair timeline based on severity.

3) SIDE FEATURES: Describe what's on the sides (concrete barriers, pedestrian pavement, cycle lane, or open).

4) REPAIR RECOMMENDATION: Overall road condition, safety concerns, recommended priority (Emergency/High/Medium/Low). Only mention relevant Toronto repair information based on what you observe."""

        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                    ]
                }
            ],
            "project_id": self.project_id,
            "model_id": self.model_id,
            "frequency_penalty": 0,
            "max_tokens": 2000,
            "presence_penalty": 0,
            "temperature": 0,
            "top_p": 1
        }
        
        try:
            # Call chat API with image
            response = requests.post(url, headers=headers, json=body, timeout=60)
            
            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code} - {response.text}")
            
            data = response.json()
            
            # Extract response text from chat completion
            response_text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            # Parse response
            analysis = self._parse_analysis(response_text, frame_path, frame_number, timestamp)
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
