// Global variables
let uploadedVideoFile = null;
let videoObjectURL = null;

// Global variables
let analysisData = null;

// DOM Elements
const uploadSection = document.getElementById('uploadSection');
const progressSection = document.getElementById('progressSection');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');
const uploadForm = document.getElementById('uploadForm');
const videoFileInput = document.getElementById('videoFile');
const fileNameSpan = document.getElementById('fileName');
const analyzeBtn = document.getElementById('analyzeBtn');

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
        // Show progress section
        showSection('progress');
        updateProgress(10, 'Uploading video...');

        // Create form data
        const formData = new FormData();
        formData.append('video', file);

        // Upload and analyze with timeout
        updateProgress(30, 'Extracting frames...');
        
        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minute timeout
        
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
            
            console.log('Response received, parsing JSON...');
            console.log('Response status:', response.status);
            console.log('Response headers:', [...response.headers.entries()]);
            
            const data = await response.json();
            console.log('JSON parsed successfully');
            console.log('Data:', data);
            
            if (data.success) {
                analysisData = data.analysis;
                updateProgress(100, 'Complete!');
                console.log('Calling displayResults...');
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

// Display results
function displayResults(analysis) {
    // Update summary cards
    document.getElementById('totalPotholes').textContent = analysis.total_potholes_detected || 0;
    document.getElementById('overallPriority').textContent = (analysis.overall_priority || 'N/A').toUpperCase();
    document.getElementById('framesAnalyzed').textContent = analysis.total_frames_analyzed || 0;
    
    const detectionRate = analysis.frames_with_potholes && analysis.total_frames_analyzed
        ? Math.round((analysis.frames_with_potholes / analysis.total_frames_analyzed) * 100)
        : 0;
    document.getElementById('detectionRate').textContent = `${detectionRate}%`;

    // Update priority card color
    const priorityCard = document.querySelector('.summary-card.priority');
    priorityCard.className = 'summary-card priority';
    const priority = (analysis.overall_priority || '').toLowerCase();
    if (priority === 'urgent' || priority === 'critical') {
        priorityCard.style.borderLeft = '4px solid #da1e28';
    } else if (priority === 'high') {
        priorityCard.style.borderLeft = '4px solid #f1c21b';
    } else if (priority === 'medium') {
        priorityCard.style.borderLeft = '4px solid #0f62fe';
    } else {
        priorityCard.style.borderLeft = '4px solid #24a148';
    }

    // Display severity breakdown
    displaySeverityBreakdown(analysis.severity_breakdown || {});

    // Display pothole list
    displayPotholeList(analysis.ranked_potholes || []);

    // Show results section
    showSection('results');
}

// Display severity breakdown
function displaySeverityBreakdown(severityBreakdown) {
    const severityBars = document.getElementById('severityBars');
    severityBars.innerHTML = '';

    const severities = ['critical', 'high', 'medium', 'low'];
    const total = Object.values(severityBreakdown).reduce((sum, val) => sum + val, 0);

    severities.forEach(severity => {
        const count = severityBreakdown[severity] || 0;
        const percentage = total > 0 ? (count / total) * 100 : 0;

        const barHTML = `
            <div class="severity-bar">
                <div class="severity-label">${severity.charAt(0).toUpperCase() + severity.slice(1)}</div>
                <div class="severity-progress">
                    <div class="severity-fill ${severity}" style="width: ${percentage}%">
                        ${count} (${Math.round(percentage)}%)
                    </div>
                </div>
            </div>
        `;
        severityBars.innerHTML += barHTML;
    });
}

// Display pothole list
function displayPotholeList(potholes) {
    const potholesList = document.getElementById('potholesList');
    potholesList.innerHTML = '';

    if (potholes.length === 0) {
        potholesList.innerHTML = '<p style="text-align: center; color: #525252;">No potholes detected in this video.</p>';
        return;
    }

    potholes.forEach((pothole, index) => {
        const cardHTML = `
            <div class="pothole-card">
                <div class="pothole-header">
                    <div class="pothole-title">
                        <i class="fas fa-map-marker-alt"></i>
                        Pothole #${index + 1}
                    </div>
                    <span class="severity-badge ${pothole.severity || 'low'}">
                        ${(pothole.severity || 'low').toUpperCase()}
                    </span>
                </div>
                <div class="pothole-details">
                    <div class="detail-item">
                        <span class="detail-label"><i class="fas fa-ruler"></i> Size</span>
                        <span class="detail-value">${pothole.estimated_size || 'N/A'}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label"><i class="fas fa-map-pin"></i> Location</span>
                        <span class="detail-value">${pothole.location || 'N/A'}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label"><i class="fas fa-arrows-alt-v"></i> Depth</span>
                        <span class="detail-value">${pothole.depth_assessment || 'N/A'}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label"><i class="fas fa-clock"></i> Timestamp</span>
                        <span class="detail-value">${formatTimestamp(pothole.frame_info?.timestamp)}</span>
                    </div>
                </div>
                ${pothole.description ? `
                    <div class="pothole-description">
                        <strong><i class="fas fa-info-circle"></i> Description:</strong><br>
                        ${pothole.description}
                    </div>
                ` : ''}
            </div>
        `;
        potholesList.innerHTML += cardHTML;
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
    
    // Clean up video player
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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    showSection('upload');
});

// Made with Bob

// Setup video player with pothole markers
function setupVideoPlayer(potholes) {
    if (!uploadedVideoFile) return;

    const videoPlayer = document.getElementById('videoPlayer');
    const videoSource = document.getElementById('videoSource');
    const timelineMarkers = document.getElementById('timelineMarkers');
    const currentDetection = document.getElementById('currentDetection');
    const detectionInfo = document.getElementById('detectionInfo');

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
            const timestamp = pothole.frame_info?.timestamp || 0;
            const position = (timestamp / duration) * 100;

            const marker = document.createElement('div');
            marker.className = `timeline-marker ${pothole.severity || 'low'}`;
            marker.style.left = `${position}%`;
            marker.dataset.time = formatTimestamp(timestamp);
            marker.dataset.index = index;
            marker.title = `${pothole.severity?.toUpperCase()} - ${formatTimestamp(timestamp)}`;

            // Click marker to jump to that time
            marker.addEventListener('click', () => {
                videoPlayer.currentTime = timestamp;
                videoPlayer.play();
            });

            timelineMarkers.appendChild(marker);
        });
    });

    // Show detection alert when video reaches pothole timestamp
    videoPlayer.addEventListener('timeupdate', () => {
        const currentTime = videoPlayer.currentTime;
        let detectionShown = false;

        potholes.forEach((pothole) => {
            const timestamp = pothole.frame_info?.timestamp || 0;
            // Show alert if within 1 second of pothole
            if (Math.abs(currentTime - timestamp) < 1) {
                detectionInfo.textContent = `${pothole.severity?.toUpperCase()} severity at ${pothole.location || 'unknown location'}`;
                currentDetection.style.display = 'block';
                detectionShown = true;
            }
        });

        if (!detectionShown) {
            currentDetection.style.display = 'none';
        }
    });
}
