// Global variables
let uploadedVideoFile = null;
let videoObjectURL = null;
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
    // Setup video player first
    setupVideoPlayer(analysis.ranked_potholes || []);
    
    // Display summary
    const summaryText = document.getElementById('summaryText');
    summaryText.textContent = analysis.summary || 'Analysis complete.';
    
    // Display only frames with potholes
    displayPotholeFrames(analysis.ranked_potholes || []);
    
    // Show results section
    showSection('results');
}

// Display pothole frames in a grid
function displayPotholeFrames(potholes) {
    const framesGrid = document.getElementById('framesGrid');
    framesGrid.innerHTML = '';

    if (potholes.length === 0) {
        framesGrid.innerHTML = '<p style="text-align: center; color: #525252; grid-column: 1/-1;">No potholes detected in this video.</p>';
        return;
    }

    potholes.forEach((pothole, index) => {
        if (pothole.frame_url) {
            const frameCard = document.createElement('div');
            frameCard.className = 'frame-card';
            frameCard.innerHTML = `
                <img src="${pothole.frame_url}" alt="Pothole ${index + 1}" 
                     onerror="this.parentElement.style.display='none'">
                <div class="frame-info">
                    <span class="severity-badge ${pothole.severity || 'low'}">${(pothole.severity || 'low').toUpperCase()}</span>
                    <span class="frame-time">${formatTimestamp(pothole.timestamp)}</span>
                </div>
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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    showSection('upload');
});

// Made with Bob
