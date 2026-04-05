"""
Maximo Manage Integration Module
Handles service request creation in IBM Maximo Manage
"""

import os
import requests
import json
import base64
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class MaximoClient:
    """Client for IBM Maximo Manage REST API"""
    
    def __init__(self):
        self.base_url = os.getenv('MAXIMO_URL', '').rstrip('/')
        self.api_key = os.getenv('MAXIMO_API_KEY', '')
        
        if not self.base_url or not self.api_key:
            logger.warning("Maximo credentials not configured. Service request creation will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            # Use service request endpoint (mxapisr) per IBM documentation
            self.api_url = f"{self.base_url}/maximo/api/os/mxapisr"
            logger.info(f"Maximo integration enabled: {self.base_url}")
            logger.info(f"Using API endpoint: {self.api_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Maximo API requests"""
        # Note: API key is passed in URL, not header, per IBM documentation
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def create_service_request(
        self,
        description: str,
        location: str,
        priority: int = 2,
        details: str = "",
        reported_by: str = "POTHOLE_ANALYZER"
    ) -> Optional[Dict]:
        """
        Create a service request in Maximo Manage
        
        Args:
            description: Short description of the issue
            location: Location where the issue was found
            priority: Priority level (1=High, 2=Medium, 3=Low)
            details: Detailed description with analysis results
            reported_by: Who reported the issue
            
        Returns:
            Dict with SR details if successful, None otherwise
        """
        if not self.enabled:
            logger.error("Maximo integration not enabled. Check credentials.")
            return None
        
        try:
            # Prepare service request payload per IBM documentation
            payload = {
                "reportedby": reported_by,
                "description": description,
                "SITEID": "BEDFORD",  # Default site
                "location": location if location != "Unknown Location" else "REPAIR",
                "affectedpersonid": reported_by
            }
            
            # Add API key to URL per IBM documentation
            create_url = f"{self.api_url}?lean=1&apikey={self.api_key}"
            
            logger.info(f"Creating work order in Maximo: {description}")
            logger.info(f"Maximo API URL: {create_url}")
            logger.info(f"Payload: {json.dumps(payload, indent=2)}")
            
            # Make API request
            response = requests.post(
                create_url,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response body: {response.text[:500]}")
            
            if response.status_code in [200, 201]:
                # Try to get ticketid from response body
                ticketid = None
                
                if response.text and 'application/json' in response.headers.get('Content-Type', ''):
                    try:
                        body = response.json()
                        ticketid = body.get('ticketid')
                    except json.JSONDecodeError:
                        pass
                
                # Fallback: Use Location header to get the created service request
                if not ticketid:
                    sr_href = response.headers.get('Location')
                    if sr_href:
                        lean_href = f"{sr_href}?lean=1&apikey={self.api_key}"
                        get_resp = requests.get(
                            lean_href,
                            headers=self._get_headers(),
                            timeout=20
                        )
                        if get_resp.status_code == 200:
                            data = get_resp.json()
                            ticketid = data.get('ticketid')
                
                if ticketid:
                    logger.info(f"Service request created successfully: {ticketid}")
                    return {
                        'success': True,
                        'ticket_id': ticketid,
                        'href': response.headers.get('Location', ''),
                        'message': f"Service request {ticketid} created successfully"
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Could not retrieve ticket ID',
                        'message': 'Service request created but ticket ID could not be resolved'
                    }
            else:
                logger.error(f"Failed to create SR. Status: {response.status_code}, Response: {response.text}")
                
                # Check for authorization error
                if response.status_code == 400 and 'BMXAA9301E' in response.text:
                    return {
                        'success': False,
                        'error': 'Authorization Error',
                        'message': 'The API key does not have permission to create service requests in Maximo. Please ensure the API key is associated with a user that has MXSR object permissions.'
                    }
                
                return {
                    'success': False,
                    'error': f"Maximo API error: {response.status_code}",
                    'message': f"Status {response.status_code}: {response.text[:200]}"
                }
                
        except requests.exceptions.Timeout:
            logger.error("Maximo API request timed out")
            return {
                'success': False,
                'error': 'Request timeout',
                'message': 'Connection to Maximo timed out'
            }
        except Exception as e:
            logger.error(f"Error creating service request: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to create service request: {str(e)}'
            }
    
    def attach_file_to_sr(
        self,
        ticket_id: str,
        file_path: str,
        description: str = "Pothole Analysis"
    ) -> bool:
        """
        Attach a file to an existing service request
        
        Args:
            ticket_id: The service request ticket ID
            file_path: Path to the file to attach
            description: Description of the attachment
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Read file and encode as base64
            with open(file_path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode('utf-8')
            
            file_name = os.path.basename(file_path)
            
            # Maximo doclinks endpoint
            doclinks_url = f"{self.base_url}/maximo/oslc/os/mxsr/{ticket_id}/doclinks"
            
            payload = {
                "document": file_name,
                "description": description,
                "urltype": "FILE",
                "upload": True,
                "docinfoid": None,
                "document_data": file_data
            }
            
            response = requests.post(
                doclinks_url,
                headers=self._get_headers(),
                json=payload,
                timeout=60
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"File attached to SR {ticket_id}: {file_name}")
                return True
            else:
                logger.error(f"Failed to attach file. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error attaching file: {str(e)}")
            return False


def create_sr_from_analysis(
    summary: str,
    pothole_count: int,
    location: str = "Unknown Location",
    video_path: Optional[str] = None,
    frame_paths: Optional[List[str]] = None
) -> Optional[Dict]:
    """
    Create a service request from pothole analysis results
    
    Args:
        summary: Analysis summary text
        pothole_count: Number of potholes detected
        location: Location where video was taken
        video_path: Path to analyzed video (optional)
        frame_paths: List of paths to pothole frame images (optional)
        
    Returns:
        Dict with SR creation result
    """
    client = MaximoClient()
    
    if not client.enabled:
        return {
            'success': False,
            'error': 'Maximo integration not configured',
            'message': 'Please configure MAXIMO_URL and MAXIMO_API_KEY environment variables'
        }
    
    # Determine priority based on pothole count
    if pothole_count >= 5:
        priority = 1  # High
    elif pothole_count >= 2:
        priority = 2  # Medium
    else:
        priority = 3  # Low
    
    # Create description
    description = f"Road Maintenance Required - {pothole_count} Pothole(s) Detected"
    
    # Create detailed description
    details = f"""AUTOMATED POTHOLE DETECTION REPORT

{summary}

Location: {location}
Detection Method: AI Video Analysis (watsonx.ai)
Priority: {'High' if priority == 1 else 'Medium' if priority == 2 else 'Low'}

This service request was automatically generated by the Pothole Video Analyzer.
Please review attached images and video for detailed assessment.
"""
    
    # Create service request
    result = client.create_service_request(
        description=description,
        location=location,
        priority=priority,
        details=details
    )
    
    if result and result.get('success'):
        ticket_id = result.get('ticket_id')
        
        # Attach video if provided
        if video_path and os.path.exists(video_path):
            logger.info(f"Attaching video to SR {ticket_id}")
            client.attach_file_to_sr(ticket_id, video_path, "Analyzed Video")
        
        # Attach frame images if provided
        if frame_paths:
            for i, frame_path in enumerate(frame_paths[:5], 1):  # Limit to 5 images
                if os.path.exists(frame_path):
                    logger.info(f"Attaching frame {i} to SR {ticket_id}")
                    client.attach_file_to_sr(
                        ticket_id,
                        frame_path,
                        f"Pothole Detection Frame {i}"
                    )
    
    return result

# Made with Bob
