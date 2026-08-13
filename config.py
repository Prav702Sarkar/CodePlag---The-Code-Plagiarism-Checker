import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max request size (hard ceiling)
    MAX_UPLOAD_SIZE = 3 * 1024 * 1024  # 3MB - files larger than this take hours to process
    
    # GitHub API settings
    GITHUB_API_KEY = os.environ.get('GITHUB_API_KEY')
    
    # Web Scraping Settings
    # ===========================================
    
    # Rate limiting settings
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    
    # Web scraping similarity threshold
    WEB_SIMILARITY_THRESHOLD = 0.3  # Minimum similarity to report
    
    # Supported languages and their extensions - CORRECTED
    LANGUAGE_EXTENSIONS = {
        'python': ['.py', '.pyw'],
        'javascript': ['.js', '.jsx'],
        'typescript': ['.ts', '.tsx'],
        'java': ['.java'],
        'c': ['.c', '.h'],
        'cpp': ['.cpp', '.cc', '.cxx', '.hpp', '.hh', '.h'],  # FIXED: Added .cpp support
        'csharp': ['.cs'],
        'ruby': ['.rb'],
        'php': ['.php'],
        'go': ['.go'],
        'rust': ['.rs'],
        'swift': ['.swift'],
        'kotlin': ['.kt'],
        'html': ['.html', '.htm'],
        'css': ['.css'],
        'scala': ['.scala'],
        'shell': ['.sh', '.bash'],
        'r': ['.r'],
        'perl': ['.pl', '.pm'],
        'haskell': ['.hs'],
        'lua': ['.lua']
    }
    
    # Similarity threshold for reporting (lowered for better detection)
    SIMILARITY_THRESHOLD = 0.3
    
    # Memory bounds for the Render free plan (512MB RAM). Keep peak request
    # memory bounded no matter how large the uploaded archive or matched files are.
    GITHUB_RESULT_CONTENT_LIMIT = 64 * 1024  # 64KB - cap stored file content per GitHub match
    ZIP_MAX_FILES = 100  # max files extracted from a single ZIP
    ZIP_MAX_TOTAL_SIZE = 30 * 1024 * 1024  # 30MB - max total uncompressed size per ZIP
    ZIP_MAX_FILE_SIZE = 3 * 1024 * 1024  # 3MB - matches the single-file upload limit

    # Debug settings
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'