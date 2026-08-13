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
    ZIP_MAX_FILES = 25  # max files extracted/processed from a single ZIP
    ZIP_MAX_TOTAL_SIZE = 30 * 1024 * 1024  # 30MB - max total uncompressed size per ZIP
    ZIP_MAX_FILE_SIZE = 3 * 1024 * 1024  # 3MB - matches the single-file upload limit
    MAX_FILES_PER_REQUEST = 10  # max files accepted in a single upload request
    MAX_WEB_PAGE_CHARS = 200 * 1024  # 200KB - only this much of a scraped page is parsed
    MAX_EXTRACTED_BLOCKS = 25  # max core blocks kept per file
    MAX_EXTRACTED_BLOCK_CHARS = 16 * 1024  # 16KB - cap the size of any single extracted block
    EXTRACT_MAX_SOURCE_CHARS = 250 * 1024  # 250KB - cap the source fed to code extraction
    SIMILARITY_MAX_INPUT_CHARS = 64 * 1024  # 64KB - cap strings fed to SequenceMatcher
    MAX_WORKER_MEMORY_MB = 400  # reject new scans above this RSS to avoid OOM kills

    # Debug settings
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'