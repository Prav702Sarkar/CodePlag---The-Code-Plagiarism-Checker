"""
Utils package for the Advanced Plagiarism Checker.
This package contains modules for file processing, GitHub API integration,
plagiarism checking, and security utilities.
"""

# Import from the current package using relative imports
from .file_processing import (
    allowed_file,
    extract_zip,
    get_file_language,
    is_text_file,
    is_github_supported_language
)

from .github_api import (
    search_github_code,
    get_github_file_content,
    get_repo_license
)

from .plagiarism_check import (
    normalize_code,
    calculate_similarity,
    generate_code_fingerprint,
    check_plagiarism,
    check_web_for_plagiarism
)

from .security import (
    init_limiter,
    sanitize_filename,
    validate_file_content
)

from .web_check import (    
    check_web_sources
)

from .intelligent_extraction import (
    extract_core_code,
    IntelligentCodeExtractor
)

__all__ = [
    # File processing
    'allowed_file',
    'extract_zip',
    'get_file_language',
    'is_text_file',
    'is_github_supported_language',
    
    # GitHub API
    'search_github_code',
    'get_github_file_content',
    'get_repo_license',
    
    # Plagiarism check
    'normalize_code',
    'calculate_similarity',
    'generate_code_fingerprint',
    'check_plagiarism',
    'check_web_for_plagiarism',
    
    # Security
    'init_limiter',
    'sanitize_filename',
    'validate_file_content',
    
    # Web check
    'check_web_sources',
    
    # Intelligent extraction
    'extract_core_code',
    'IntelligentCodeExtractor'
]