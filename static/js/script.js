// CodePlag - Modern JavaScript for Advanced Plagiarism Checker

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all functionality
    initDragAndDrop();
    initFileInput();
    initFormSubmission();
    initSmoothScrolling();
    initAnimations();
    initNotifications();
    initTooltips();
    
    console.log('⚡ CodePlag initialized with cyberpunk theme');
    
    // Initialize How It Works section scrolling
    initHowItWorks();
});

function initHowItWorks() {
    // Fix for How It Works navigation
    const howItWorksLinks = document.querySelectorAll('a[href="#how-it-works"]');
    howItWorksLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.getElementById('how-it-works');
            if (target) {
                window.scrollTo({
                    top: target.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });
    });
}

function initDragAndDrop() {
    const uploadArea = document.querySelector('.upload-area');
    const fileInput = document.querySelector('input[type="file"]');
    
    if (!uploadArea || !fileInput) return;
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
        document.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // Highlight drop area when file is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        uploadArea.classList.add('highlight');
        uploadArea.style.transform = 'translateY(-5px)';
        uploadArea.style.boxShadow = '0 10px 30px rgba(0, 245, 255, 0.2)';
    }
    
    function unhighlight() {
        uploadArea.classList.remove('highlight');
        uploadArea.style.transform = '';
        uploadArea.style.boxShadow = '';
    }
    
    // Handle dropped files
    uploadArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length) {
            fileInput.files = files;
            updateFileList(files);
            showLargeFileWarning(files);
            
            // Add success animation
            uploadArea.classList.add('glow-animation');
            setTimeout(() => {
                uploadArea.classList.remove('glow-animation');
            }, 2000);
            
            showNotification(`${files.length} file${files.length !== 1 ? 's' : ''} uploaded successfully`, 'success');
        }
    }
}

function initFileInput() {
    const fileInput = document.querySelector('input[type="file"]');
    
    if (!fileInput) return;
    
    fileInput.addEventListener('change', function() {
        updateFileList(this.files);
        showLargeFileWarning(this.files);
        
        // Add visual feedback
        if (this.files.length > 0) {
            showNotification(`${this.files.length} file${this.files.length !== 1 ? 's' : ''} selected`, 'success');
        }
    });
}

function updateFileList(files) {
    const fileList = document.getElementById('file-list');
    
    // Create file list element if it doesn't exist
    if (!fileList) {
        const uploadArea = document.querySelector('.upload-area');
        const newFileList = document.createElement('div');
        newFileList.id = 'file-list';
        newFileList.className = 'mt-3';
        uploadArea.parentNode.insertBefore(newFileList, uploadArea.nextSibling);
    }
    
    // Clear previous list
    fileList.innerHTML = '';
    
    // Add files to list
    if (files.length === 0) {
        fileList.innerHTML = `
            <div class="text-center py-4" style="color: #C6D3E1;">
                <i class="bi bi-cloud-upload-fill fs-1 mb-3" style="color: #00F5FF;"></i>
                <p class="mb-0">Drag & drop files or click to browse</p>
            </div>
        `;
        
        // Keep Scan disabled until at least one file is selected
        const submitBtn = document.getElementById('submit-btn');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.title = '';
        }
        return;
    }
    
    const list = document.createElement('div');
    list.className = 'list-group list-group-flush';
    
    let totalSize = 0;
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        totalSize += file.size;
        
        const listItem = document.createElement('div');
        listItem.className = 'list-group-item d-flex justify-content-between align-items-center';
        listItem.style.background = 'transparent';
        listItem.style.borderColor = 'rgba(0, 245, 255, 0.1)';
        listItem.dataset.index = i;
        
        const leftSection = document.createElement('div');
        leftSection.className = 'd-flex align-items-center';
        
        const fileIcon = document.createElement('i');
        fileIcon.className = 'bi bi-file-code me-3';
        fileIcon.style.color = '#00F5FF';
        fileIcon.style.fontSize = '1.2rem';
        
        const fileInfo = document.createElement('div');
        
        const fileName = document.createElement('div');
        fileName.style.color = '#C6D3E1';
        fileName.style.fontWeight = '500';
        fileName.textContent = file.name.length > 30 ? file.name.substring(0, 30) + '...' : file.name;
        
        const fileMeta = document.createElement('small');
        fileMeta.style.color = '#8899A6';
        fileMeta.textContent = formatFileSize(file.size);
        
        fileInfo.appendChild(fileName);
        fileInfo.appendChild(fileMeta);
        
        leftSection.appendChild(fileIcon);
        leftSection.appendChild(fileInfo);
        
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-sm btn-outline-danger';
        removeBtn.innerHTML = '<i class="bi bi-x"></i>';
        removeBtn.onclick = function() {
            removeFile(i);
        };
        
        listItem.appendChild(leftSection);
        listItem.appendChild(removeBtn);
        list.appendChild(listItem);
    }
    
    // Add total summary
    const summaryItem = document.createElement('div');
    summaryItem.className = 'list-group-item text-center';
    summaryItem.style.background = 'transparent';
    summaryItem.style.borderColor = 'rgba(0, 245, 255, 0.1)';
    summaryItem.style.color = '#00F5FF';
    summaryItem.style.fontWeight = '600';
    summaryItem.innerHTML = `
        <i class="bi bi-folder-check me-2"></i>
        ${files.length} file${files.length !== 1 ? 's' : ''} • ${formatFileSize(totalSize)}
    `;
    
    list.appendChild(summaryItem);
    fileList.appendChild(list);
    
    // Block scanning while oversized files are selected
    const submitBtn = document.getElementById('submit-btn');
    if (submitBtn) {
        const hasLargeFiles = getLargeFiles(files).length > 0;
        submitBtn.disabled = hasLargeFiles;
        submitBtn.title = hasLargeFiles ? 'Remove files over 3MB to enable scanning' : '';
    }
}

function removeFile(index) {
    const fileInput = document.querySelector('input[type="file"]');
    const files = Array.from(fileInput.files);
    
    // Remove the file at the specified index
    const removedFile = files.splice(index, 1)[0];
    
    // Create a new FileList object
    const dataTransfer = new DataTransfer();
    files.forEach(file => dataTransfer.items.add(file));
    
    // Update the file input
    fileInput.files = dataTransfer.files;
    
    // Update the file list display
    updateFileList(fileInput.files);
    
    // Show notification
    showNotification(`Removed: ${removedFile.name}`, 'info');
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Large file warning threshold - files above 3MB take a long time to process
const LARGE_FILE_WARNING_LIMIT = 3 * 1024 * 1024; // 3MB

function getLargeFiles(files) {
    return Array.from(files).filter(file => file.size > LARGE_FILE_WARNING_LIMIT);
}

function showLargeFileWarning(files) {
    const largeFiles = getLargeFiles(files);
    if (largeFiles.length === 0) return;
    
    const names = largeFiles.map(file => `"${file.name}"`).join(', ');
    const message = `${names} exceed${largeFiles.length === 1 ? 's' : ''} the 3MB limit. ` +
                    `Files larger than 3MB take hours to process, so scanning is blocked. ` +
                    `Please split ${largeFiles.length === 1 ? 'it' : 'them'} into smaller parts ` +
                    `(each under 3MB) and upload ${largeFiles.length === 1 ? 'it' : 'them'} as a ZIP file.`;
    
    showNotification(message, 'warning', 12000, true);
}

function initFormSubmission() {
    const form = document.querySelector('form');
    
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        console.log('[CodePlag] Form submission started');
        console.log('[CodePlag] Backend URL:', window.location.origin + '/check');
        
        // Show loading indicator
        showLoadingIndicator();
        
        // Validate files before submitting
        const fileInput = document.querySelector('input[type="file"]');
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            console.warn('[CodePlag] No files selected');
            e.preventDefault();
            hideLoadingIndicator();
            showNotification('Please select at least one file to upload.', 'warning');
            return;
        }
        
        console.log('[CodePlag] Files to upload:', fileInput.files.length);
        for (let i = 0; i < fileInput.files.length; i++) {
            console.log(`  - ${fileInput.files[i].name} (${(fileInput.files[i].size / 1024).toFixed(2)} KB)`);
        }
        
        // Block files larger than 3MB - they take hours to process
        if (getLargeFiles(fileInput.files).length > 0) {
            e.preventDefault();
            hideLoadingIndicator();
            showLargeFileWarning(fileInput.files);
            return;
        }
        
        // Check file types
        // Must stay in sync with Config.LANGUAGE_EXTENSIONS (server truth)
        const supportedExtensions = ['.py', '.pyw', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.h',
                                     '.cpp', '.cc', '.cxx', '.hpp', '.hh', '.cs', '.rb', '.php', '.go',
                                     '.rs', '.swift', '.kt', '.html', '.htm', '.css', '.scala', '.sh',
                                     '.bash', '.r', '.pl', '.pm', '.hs', '.lua', '.zip'];
        
        for (let i = 0; i < fileInput.files.length; i++) {
            const fileName = fileInput.files[i].name.toLowerCase();
            const isSupported = supportedExtensions.some(ext => fileName.endsWith(ext));
            
            if (!isSupported) {
                e.preventDefault();
                hideLoadingIndicator();
                showNotification(
                    `File "${fileName}" has an unsupported extension. Please upload code files or ZIP archives.`,
                    'warning'
                );
                return;
            }
        }
        
        // Show CodePlag loading animation
        const loadingHTML = `
            <div id="codeplag-loading" style="
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(10, 15, 20, 0.95);
                backdrop-filter: blur(10px);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                z-index: 9999;
            ">
                <div class="codeplag-spinner" style="
                    position: relative;
                    width: 100px;
                    height: 100px;
                    margin-bottom: 30px;
                ">
                    <div class="spinner-border text-primary" style="width: 4rem; height: 4rem;" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
                
                <h3 style="color: #00F5FF; margin-bottom: 15px;">
                    <i class="bi bi-robot"></i> CodePlag Analysis
                </h3>
                
                <p style="color: #C6D3E1; margin-bottom: 25px;">
                    Scanning with <strong>99.5% accuracy</strong> against 200M+ repositories
                </p>
                
                <div class="progress" style="width: 300px; background: rgba(0, 245, 255, 0.1); height: 8px;">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         style="background: linear-gradient(135deg, #00F5FF 0%, #00BCD4 100%); width: 45%;">
                    </div>
                </div>
                
                <div class="loading-stats mt-4" style="color: #8899A6; font-size: 0.9rem;">
                    <i class="bi bi-github"></i> GitHub API • <i class="bi bi-globe"></i> Web Search
                </div>
            </div>
        `;
        
        // Add loading overlay
        document.body.insertAdjacentHTML('beforeend', loadingHTML);
        
        // Add spinner animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes codeplag-spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .codeplag-spinner::before {
                content: '';
                position: absolute;
                top: -10px;
                left: -10px;
                right: -10px;
                bottom: -10px;
                border: 2px solid transparent;
                border-top: 2px solid #00F5FF;
                border-radius: 50%;
                animation: codeplag-spin 1s linear infinite;
            }
            
            .codeplag-spinner::after {
                content: '';
                position: absolute;
                top: -20px;
                left: -20px;
                right: -20px;
                bottom: -20px;
                border: 2px solid transparent;
                border-top: 2px solid #FF008A;
                border-radius: 50%;
                animation: codeplag-spin 1.5s linear infinite reverse;
            }
        `;
        document.head.appendChild(style);
        
        // Set flag to allow navigation to results page
        isFormSubmitting = true;
        console.log('[CodePlag] Form validated successfully, submitting to backend...');
    });
}

function showLoadingIndicator() {
    const submitButton = document.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            Processing...
        `;
        submitButton.classList.add('loading');
    }
}

function hideLoadingIndicator() {
    const submitButton = document.querySelector('button[type="submit"]');
    if (submitButton) {
        const fileInput = document.querySelector('input[type="file"]');
        const noFiles = !fileInput || !fileInput.files || fileInput.files.length === 0;
        const hasLargeFiles = fileInput && getLargeFiles(fileInput.files).length > 0;
        submitButton.disabled = noFiles || hasLargeFiles;
        submitButton.innerHTML = '<i class="bi bi-search"></i> Check for Plagiarism';
        submitButton.classList.remove('loading');
    }
    
    // Remove loading overlay if exists
    const loadingOverlay = document.getElementById('codeplag-loading');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
}

function initSmoothScrolling() {
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href === '#' || href === '#!') return;
            
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                window.scrollTo({
                    top: target.offsetTop - 80,
                    behavior: 'smooth'
                });
                
                // Add active class to navbar links
                document.querySelectorAll('.nav-link').forEach(link => {
                    link.classList.remove('active');
                });
                this.classList.add('active');
            }
        });
    });
}

function initAnimations() {
    // Intersection Observer for scroll animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);
    
    // Observe elements for animation
    document.querySelectorAll('.card, .feature-icon, .stats-counter, .result-card, .how-it-works-step').forEach(el => {
        observer.observe(el);
    });
    
    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .animate-in {
            animation: fadeInUp 0.6s ease-out forwards;
        }
        
        @keyframes pulse-glow {
            0%, 100% {
                box-shadow: 0 0 5px rgba(0, 245, 255, 0.5);
            }
            50% {
                box-shadow: 0 0 20px rgba(0, 245, 255, 0.8);
            }
        }
        
        .glow-animation {
            animation: pulse-glow 2s infinite;
        }
        
        @keyframes border-glow {
            0%, 100% {
                opacity: 0.5;
            }
            50% {
                opacity: 1;
            }
        }
        
        .upload-area.highlight::before {
            animation: border-glow 2s linear infinite;
        }
    `;
    document.head.appendChild(style);
}

function initNotifications() {
    // Create notification container
    const notificationContainer = document.createElement('div');
    notificationContainer.id = 'notification-container';
    notificationContainer.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        gap: 10px;
    `;
    document.body.appendChild(notificationContainer);
    
    // Global notification function
    window.showNotification = function(message, type = 'info', duration = 5000, attention = false) {
        const notification = document.createElement('div');
        notification.className = 'notification';
        
        const colors = {
            'info': { bg: 'rgba(0, 245, 255, 0.9)', text: '#0A0F14', icon: 'ℹ️' },
            'success': { bg: 'rgba(61, 255, 106, 0.9)', text: '#0A0F14', icon: '✅' },
            'warning': { bg: 'rgba(255, 0, 138, 0.9)', text: '#FFFFFF', icon: '⚠️' },
            'error': { bg: 'rgba(255, 0, 138, 0.9)', text: '#FFFFFF', icon: '❌' }
        };
        
        const color = colors[type] || colors.info;
        
        notification.style.cssText = `
            background: ${color.bg};
            color: ${color.text};
            padding: 15px 20px;
            border-radius: 8px;
            backdrop-filter: blur(10px);
            border-left: 4px solid ${color.text};
            min-width: 300px;
            max-width: 400px;
            animation: slideIn 0.3s ease-out;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        `;
        
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.2rem;">${color.icon}</span>
                <span style="font-weight: 500;">${message}</span>
            </div>
            <button type="button" class="btn-close" onclick="this.parentElement.remove()" 
                    style="filter: invert(${type === 'warning' || type === 'error' ? '1' : '0'});">
            </button>
        `;
        
        // Attention-grabbing styling for important warnings (e.g. large file size)
        if (attention) {
            notification.style.animation = 'attentionIn 0.6s ease-out';
            notification.style.border = '2px solid rgba(255, 0, 138, 0.9)';
            notification.style.boxShadow = '0 0 25px rgba(255, 0, 138, 0.5)';
        }
        
        notificationContainer.appendChild(notification);
        
        // Auto-remove after duration
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.animation = 'slideOut 0.3s ease-out';
                setTimeout(() => notification.remove(), 300);
            }
        }, duration);
        
        // Add animation styles
        const animationStyle = document.createElement('style');
        if (!document.querySelector('#notification-animations')) {
            animationStyle.id = 'notification-animations';
            animationStyle.textContent = `
                @keyframes slideIn {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                
                @keyframes slideOut {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                }
                
                @keyframes attentionIn {
                    from {
                        transform: translateX(100%) scale(0.8);
                        opacity: 0;
                    }
                    60% {
                        transform: translateX(-8px) scale(1.05);
                        opacity: 1;
                    }
                    80% {
                        transform: translateX(4px) scale(1);
                    }
                    to {
                        transform: translateX(0) scale(1);
                        opacity: 1;
                    }
                }
            `;
            document.head.appendChild(animationStyle);
        }
    };
}

function initTooltips() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// File validation helper
function validateFile(file) {
    const maxSize = LARGE_FILE_WARNING_LIMIT; // 3MB - larger files take hours to process
    const supportedTypes = [
        'text/x-python', 'application/javascript', 'text/x-java', 'text/x-c++src',
        'text/x-c', 'text/x-csharp', 'application/x-php', 'application/x-ruby',
        'text/x-go', 'text/x-rust', 'text/x-swift', 'text/x-kotlin',
        'application/typescript', 'text/html', 'text/css', 'application/zip',
        'application/x-zip-compressed'
    ];
    
    if (file.size > maxSize) {
        return { valid: false, reason: 'File size exceeds 3MB limit. Please split the file into smaller parts and upload as a ZIP.' };
    }
    
    if (!supportedTypes.includes(file.type) && !file.name.match(/\.(py|js|java|cpp|c|cs|php|rb|go|rs|swift|kt|ts|html|css|zip)$/i)) {
        return { valid: false, reason: 'Unsupported file type' };
    }
    
    return { valid: true };
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + U to focus file upload
    if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
        e.preventDefault();
        const fileInput = document.querySelector('input[type="file"]');
        if (fileInput) {
            fileInput.click();
        }
    }
    
    // Escape to close notifications
    if (e.key === 'Escape') {
        const notifications = document.querySelectorAll('.notification');
        notifications.forEach(notification => notification.remove());
    }
});

// Add global error handling
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    showNotification('An unexpected error occurred. Please try again.', 'error');
});

// Track if form is being submitted normally
let isFormSubmitting = false;

// Add beforeunload handler for form submission
window.addEventListener('beforeunload', function(e) {
    const submitButton = document.querySelector('button[type="submit"]');
    // Only show warning if processing AND not submitting the form normally
    if (submitButton && submitButton.classList.contains('loading') && !isFormSubmitting) {
        e.preventDefault();
        e.returnValue = 'Your plagiarism check is still processing. Are you sure you want to leave?';
        return e.returnValue;
    }
});

// Export functions for global use
window.CodePlag = {
    showNotification: window.showNotification,
    formatFileSize,
    validateFile
};

// Helper function for file list updates (for modal use)
window.updateFileList = updateFileList;