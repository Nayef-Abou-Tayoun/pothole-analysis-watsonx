// Global variables
let uploadedVideoFile = null;
let videoObjectURL = null;
// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

let analysisData = null;

// DOM Elements
const uploadSection = document.getElementById('uploadSection');
const progressSection = document.getElementById('progressSection');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');
const uploadForm = document.getElementById('uploadForm');
const videoFileInput = document.getElementById('videoFile');
const fileNameSpan = document.getElementById('fileName');

// File input change handler
videoFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        uploadedVideoFile = file;
        fileNameSpan.textContent = file.name;
        fileNameSpan.style.color = '#0f62fe';
    } else {
        uploadedVideoFile = null;
        fileNameSpan.textContent = 'Choose Video File';
        fileNameSpan.style.color = '';
    }
});

// Form submission handler
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const file = videoFileInput.files[0];
    if (!file) {
        showError('Please select a video file');
        return;
    }

    // Validate file size (500MB max)
    const maxSize = 500 * 1024 * 1024;
    if (file.size > maxSize) {
        showError('File size exceeds 500MB limit');
        return;
    }

    await analyzeVideo(file);
});

// Analyze video function
async function analyzeVideo(file) {
    try {
        showSection('progress');
        updateProgress(10, 'Uploading video...');

        const formData = new FormData();
        formData.append('video', file);

        updateProgress(30, 'Extracting frames...');
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 600000);
        
        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Analysis failed');
            }

            updateProgress(90, 'Processing results...');
            const data = await response.json();
            
            if (data.success) {
                analysisData = data.analysis;
                updateProgress(100, 'Complete!');
                setTimeout(() => displayResults(data.analysis), 500);
            } else {
                throw new Error(data.error || 'Analysis failed');
            }
        } catch (fetchError) {
            clearTimeout(timeoutId);
            if (fetchError.name === 'AbortError') {
                throw new Error('Request timeout - analysis took too long');
            }
            throw fetchError;
        }

    } catch (error) {
        console.error('Analysis error:', error);
        showError(error.message || 'An error occurred during analysis');
    }
}

// Update progress
function updateProgress(percent, text) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    progressFill.style.width = `${percent}%`;
    progressText.textContent = text;
}

// Display results - SIMPLIFIED VERSION
function displayResults(analysis) {
    // Get all frames
    const allFrames = analysis.detailed_analyses || [];
    
    // Setup video player with markers for frames with potholes
    const framesWithPotholes = allFrames.filter(f => f.potholes_detected);
    setupVideoPlayer(framesWithPotholes);
    
    // Display summary
    const summaryText = document.getElementById('summaryText');
    summaryText.textContent = analysis.summary || 'Analysis complete.';
    
    // Display ALL frames with AI analysis
    displayAllFrames(allFrames);
    
    // Show Maximo section if potholes detected
    const maximoSection = document.getElementById('maximoSection');
    if (framesWithPotholes.length > 0) {
        maximoSection.style.display = 'block';
        // Reset Maximo section to show button
        document.getElementById('maximoStatus').style.display = 'block';
        document.getElementById('maximoResult').style.display = 'none';
    } else {
        maximoSection.style.display = 'none';
    }
    
    // Show results section
    showSection('results');
}

// Display ALL frames with AI analysis text
function displayAllFrames(frames) {
    const framesGrid = document.getElementById('framesGrid');
    framesGrid.innerHTML = '';

    if (!frames || frames.length === 0) {
        framesGrid.innerHTML = '<p style="text-align: center; color: #525252; grid-column: 1/-1;">No frames analyzed.</p>';
        return;
    }

    frames.forEach((frame, index) => {
        if (frame.frame_url) {
            const frameCard = document.createElement('div');
            frameCard.className = 'frame-card';
            
            // Get AI response text
            const aiResponse = frame.raw_response || frame.analysis_text || 'No analysis available';
            
            // Determine if pothole detected for styling
            const hasPothole = frame.potholes_detected || false;
            const severity = frame.severity || (hasPothole ? 'medium' : 'none');
            const severityLabel = hasPothole ? (severity.toUpperCase()) : 'CLEAR';
            
            frameCard.innerHTML = `
                <div class="frame-header">
                    <span class="severity-badge ${severity}">${severityLabel}</span>
                    <span class="frame-time">Frame ${frame.frame_number} - ${formatTimestamp(frame.timestamp)}</span>
                </div>
                <div class="ai-response">${escapeHtml(aiResponse)}</div>
                <img src="${frame.frame_url}" alt="Frame ${index + 1}"
                     onerror="this.parentElement.style.display='none'">
            `;
            
            // Click to jump to this time in video
            frameCard.addEventListener('click', () => {
                const videoPlayer = document.getElementById('videoPlayer');
                videoPlayer.currentTime = pothole.timestamp || 0;
                videoPlayer.play();
                videoPlayer.scrollIntoView({ behavior: 'smooth', block: 'center' });
            });
            
            framesGrid.appendChild(frameCard);
        }
    });
}

// Setup video player with pothole markers
function setupVideoPlayer(potholes) {
    if (!uploadedVideoFile) return;

    const videoPlayer = document.getElementById('videoPlayer');
    const videoSource = document.getElementById('videoSource');
    const timelineMarkers = document.getElementById('timelineMarkers');

    // Clean up previous video URL
    if (videoObjectURL) {
        URL.revokeObjectURL(videoObjectURL);
    }

    // Create object URL for uploaded video
    videoObjectURL = URL.createObjectURL(uploadedVideoFile);
    videoSource.src = videoObjectURL;
    videoPlayer.load();

    // Clear existing markers
    timelineMarkers.innerHTML = '';

    // Get video duration and create markers
    videoPlayer.addEventListener('loadedmetadata', () => {
        const duration = videoPlayer.duration;

        // Create timeline markers for each pothole
        potholes.forEach((pothole, index) => {
            const timestamp = pothole.timestamp || 0;
            const position = (timestamp / duration) * 100;

            const marker = document.createElement('div');
            marker.className = `timeline-marker ${pothole.severity || 'low'}`;
            marker.style.left = `${position}%`;
            marker.title = `${pothole.severity?.toUpperCase()} - ${formatTimestamp(timestamp)}`;

            // Click marker to jump to that time
            marker.addEventListener('click', () => {
                videoPlayer.currentTime = timestamp;
                videoPlayer.play();
            });

            timelineMarkers.appendChild(marker);
        });
    });
}

// Format timestamp
function formatTimestamp(seconds) {
    if (!seconds && seconds !== 0) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Show section
function showSection(section) {
    uploadSection.style.display = 'none';
    progressSection.style.display = 'none';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'none';

    switch(section) {
        case 'upload':
            uploadSection.style.display = 'block';
            break;
        case 'progress':
            progressSection.style.display = 'block';
            break;
        case 'results':
            resultsSection.style.display = 'block';
            break;
        case 'error':
            errorSection.style.display = 'block';
            break;
    }
}

// Show error
function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    showSection('error');
}

// Reset analysis
function resetAnalysis() {
    uploadForm.reset();
    fileNameSpan.textContent = 'Choose Video File';
    fileNameSpan.style.color = '';
    analysisData = null;
    uploadedVideoFile = null;
    
    const videoPlayer = document.getElementById('videoPlayer');
    if (videoPlayer) {
        videoPlayer.pause();
        videoPlayer.src = '';
    }
    
    if (videoObjectURL) {
        URL.revokeObjectURL(videoObjectURL);
        videoObjectURL = null;
    }
    
    showSection('upload');
}

// Download report
function downloadReport() {
    if (!analysisData) return;

    const dataStr = JSON.stringify(analysisData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `pothole-analysis-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Create service request in Maximo
async function createServiceRequest() {
    if (!analysisData) {
        alert('No analysis data available');
        return;
    }
    
    const createSRBtn = document.getElementById('createSRBtn');
    const originalText = createSRBtn.innerHTML;
    
    try {
        // Disable button and show loading
        createSRBtn.disabled = true;
        createSRBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating Service Request...';
        
        // Count potholes
        const potholeCount = (analysisData.detailed_analyses || []).filter(f => f.potholes_detected).length;
        
        // Prepare request data
        const requestData = {
            summary: analysisData.summary || 'Pothole detected',
            pothole_count: potholeCount,
            location: 'Road Location', // You can add a location input field if needed
            video_filename: uploadedVideoFile ? uploadedVideoFile.name : ''
        };
        
        // Call API
        const response = await fetch('/create-service-request', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Hide button, show success message
            document.getElementById('maximoStatus').style.display = 'none';
            document.getElementById('maximoResult').style.display = 'block';
            document.getElementById('ticketId').textContent = result.ticket_id;
            
            // Set up link
            const maximoLink = document.getElementById('maximoLink');
            if (result.link) {
                maximoLink.href = result.link;
                maximoLink.style.display = 'inline-block';
            } else {
                maximoLink.style.display = 'none';
            }
        } else {
            throw new Error(result.message || 'Failed to create service request');
        }
        
    } catch (error) {
        console.error('Error creating service request:', error);
        alert('Failed to create service request: ' + error.message);
        
        // Re-enable button
        createSRBtn.disabled = false;
        createSRBtn.innerHTML = originalText;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    showSection('upload');
});

// Made with Bob
