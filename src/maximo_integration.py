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
        reported_by: str = "POTHOLE_ANALYZER",
        assetnum: str = "GARDINER_EXPRESSWAY"
    ) -> Optional[Dict]:
        """
        Create a service request in Maximo Manage
        
        Args:
            description: Short description of the issue
            location: Location where the issue was found
            priority: Priority level (1=High, 2=Medium, 3=Low)
            details: Detailed description with analysis results
            reported_by: Who reported the issue
            assetnum: Asset number in Maximo (default: GARDINER_EXPRESSWAY)
            
        Returns:
            Dict with SR details if successful, None otherwise
        """
        if not self.enabled:
            logger.error("Maximo integration not enabled. Check credentials.")
            return None
        
        try:
            # Prepare service request payload per IBM documentation
            # Location field completely removed - causes validation error BMXAA2661E
            payload = {
                "reportedby": reported_by,
                "description": description,
                "description_longdescription": details,
                "assetnum": assetnum,
                "SITEID": "BEDFORD",  # Default site
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
    description = "A pothole detected"
    
    # Create detailed description with comprehensive pothole information
    details = f"""{summary}

Location: {location}
Detection Method: AI Video Analysis (watsonx.ai)
Priority: {'High' if priority == 1 else 'Medium' if priority == 2 else 'Low'}

=== Description of Service/Summary ===
Potholes form when water seeps into cracks in the road, freezes, and expands, causing the pavement to break apart. They are especially common in spring due to repeated freeze‑thaw cycles. Residents can help keep roads safe by reporting potholes to 311 for timely repair.

=== Potholes Road Surface Damage Criteria ===
Pothole size thresholds vary depending on the road classification, helping crews determine when repairs are required and how to prioritize work for safety and efficiency. The required minimum measurements for pothole repair on each road type are:

• Expressways: over 600 cm² in surface area and 8 cm deep
• Arterial Roads: over 800 cm² in surface area and 8 cm deep
• Collector and Local Roads: over 1,000 cm² in surface area and 8 cm deep

=== What Causes Potholes ===
Potholes are created when water penetrates the top layer of asphalt through cracks in the road. After the moisture freezes and expands, sections of the pavement are forced up. The weight of vehicles going over this section of road breaks the pavement and the asphalt is forced out. Potholes are more frequent in the spring, after the freeze/thaw action following winter.

=== Steps to Fix a Pothole ===
To combat the problem, the City of Toronto's Transportation Division has a number of work crews that are assigned to the job of fixing potholes and similar road defects as close to year-round as the weather permits.

• Crews place asphalt and rake it into the pothole.
• The asphalt is tamped down and smoothed out until the road surface is improved.
• During winter months potholes are temporarily patched with cold mix asphalt to make the road safe.
• More permanent repairs are performed with hot asphalt when warmer conditions prevail.

=== How to Report a Pothole Road Damage Request ===
To report potholes on City of Toronto roads, bike lanes or expressways, please submit a service request online at: toronto.ca/311 by selecting the "Roads, Sidewalks, Bicycle & Traffic Safety" Service Request category or call 311.

City of Toronto Expressways include:
• Don Valley Parkway (DVP) - south of the 401
• Highway 27 - north from Highway 401 west of Martin Grove Rd., to Steeles Ave.
• Gardiner Expressway
• Hwy 2a (Kingston Rd.)
• Allen Expressway
• Black Creek Dr.

If you wish to report potholes on a Provincial Highway or ramp, such as the 400, 401, 403, 404, 409, 410, 427, or QEW, visit Potholes - provincial highways.

=== What Happens When a Request is Created ===
• The City will review your request and assess the pothole.
• Repairs are prioritized based on road type and safety risk.
• If you signed up for updates, we'll notify you when work begins.

=== Expected Timelines for Repair ===
The Estimated Resolution Timeframe is an average time for pothole repairs across all road classifications. The timelines below outline the expected repair periods for each road type, all of which meet or exceed provincial maintenance standards. Highly frequented roads are attended to more quickly:

• Emergency Repair: Within 24 hours (for major roadways where the pothole is large and poses risk to vehicles or pedestrians)
• City Expressways (over 40,000 vehicles per day, e.g., DVP, Allen): 4 days
• Arterial Roads (over 8,000 vehicles per day, e.g. Yonge St.): 4 days
• Collector Road (2,500 to 8,000 vehicles per day, e.g., John St.): 14 days
• Local Street (Less than 2,500 vehicles per day, e.g., Mercer St.): 21 days
• Public Laneways: 21 days

If a pothole requires more extensive work, crews will complete a temporary repair within the timelines listed above, followed by a permanent repair at a later date.

=== Additional Information and Facts on Potholes in the City of Toronto ===
• The City has a comprehensive pothole repair program to maintain safe and reliable roadways for all users.
• Toronto is a big city with a huge network of roads, bikeways and surface transit options, and the City is committed to keeping our road network safe for all residents and visitors.
• Potholes are created when water penetrates the top layer of asphalt through cracks in the road. After the moisture freezes and expands, sections of the pavement are forced up and the weight of vehicles going over this section of road breaks the pavement, creating a pothole.
• A winter with more freeze-thaw cycles also increases the number of potholes on city streets.
• Pothole repair crews also handle other road maintenance activities such as snow clearing and removal, street sweeping and other maintenance and roadway safety work.
• The public is asked to be safe by respecting work zones and giving crews space while they make repairs."""
    
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
