import os
import re
from werkzeug.utils import secure_filename
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging

logger = logging.getLogger(__name__)

def init_limiter(app):
    """Initialize rate limiting for the application"""
    return Limiter(
        get_remote_address,
        app=app,
        default_limits=[app.config.get('RATELIMIT_DEFAULT', "200 per day, 50 per hour")],
        storage_uri="memory://",
    )

def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal attacks"""
    # Remove directory path
    filename = secure_filename(os.path.basename(filename))
    
    # Remove potentially dangerous characters but keep parentheses and spaces for C++ files
    filename = re.sub(r'[^\w\.\-\s\(\)]', '_', filename)
    
    logger.debug(f"Sanitized filename: {filename}")
    return filename

def validate_file_content(content):
    """Validate file content - the app never executes uploaded code, so keep only
    structural sanity checks. Patterns like eval()/system()/subprocess are legitimate
    in real source code; rejecting them caused false negatives."""
    # Check for extremely long lines (potential attack)
    lines = content.split('\n')
    if any(len(line) > 100000 for line in lines):
        logger.warning("File content validation failed: very long line detected")
        return False
    
    # Check file size (sanity check)
    if len(content) > 16 * 1024 * 1024:  # 16MB max
        logger.warning("File content validation failed: file too large")
        return False
    
    # Informational only - do NOT reject on these patterns
    suspicious_patterns = [
        r'__import__\s*\(',  # Python-specific
        r'eval\s*\(',        # JavaScript/Python
        r'exec\s*\(',        # Python
        r'system\s*\(',      # Common in C++ and PHP
        r'os\.popen',        # Python-specific
        r'subprocess\.call'  # Python-specific
    ]
    for pattern in suspicious_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            logger.debug(f"File content contains pattern '{pattern}' (informational only, not blocking)")
    
    logger.debug("File content validation passed")
    return True