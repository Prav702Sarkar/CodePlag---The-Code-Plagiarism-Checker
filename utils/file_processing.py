import os
import zipfile
from werkzeug.utils import secure_filename
from config import Config
import logging

logger = logging.getLogger(__name__)

# GitHub supported languages
GITHUB_SUPPORTED_LANGUAGES = ['python', 'javascript', 'java', 'c', 'cpp', 'csharp', 'ruby', 
                             'php', 'go', 'rust', 'swift', 'kotlin', 'typescript', 'html', 'css',
                             'scala', 'shell', 'r', 'perl', 'haskell', 'lua']

def allowed_file(filename):
    """Check if the uploaded file is allowed"""
    if not filename or '.' not in filename:
        logger.debug(f"File {filename} has no extension")
        return False
    
    # Get the extension properly
    try:
        ext = '.' + filename.rsplit('.', 1)[1].lower()
    except IndexError:
        logger.debug(f"File {filename} has invalid extension format")
        return False
    
    logger.debug(f"Checking file: {filename}, Extension: {ext}")
    
    # Allow zip files
    if ext == '.zip':
        logger.debug(f"File {filename} is a ZIP file - allowed")
        return True
    
    # Check if extension is in any of the supported language extensions
    for language, extensions in Config.LANGUAGE_EXTENSIONS.items():
        if ext in extensions:
            logger.debug(f"File {filename} is supported ({language})")
            return True
    
    logger.debug(f"File {filename} has unsupported extension: {ext}")
    logger.debug(f"Supported extensions: {[ext for exts in Config.LANGUAGE_EXTENSIONS.values() for ext in exts]}")
    return False

def extract_zip(file_stream):
    """Extract zip file and return dictionary of file contents.

    Memory-safe for the Render free plan (512MB RAM): the uncompressed size of
    every file, the total uncompressed size, and the file count are all bounded
    so a hostile or oversized archive can't balloon process memory.
    """
    extracted_files = {}
    total_size = 0
    
    try:
        with zipfile.ZipFile(file_stream, 'r') as z:
            for file_info in z.infolist():
                if not file_info.is_dir():
                    filename = file_info.filename
                    # Skip hidden files and directories
                    if not os.path.basename(filename).startswith('.'):
                        # Per-file size cap (matches the single-file upload limit)
                        if file_info.file_size > Config.ZIP_MAX_FILE_SIZE:
                            logger.debug(f"Skipped oversized file in ZIP: {filename} ({file_info.file_size} bytes)")
                            continue
                        # Total uncompressed size cap - stops zip-bomb style expansion
                        if total_size + file_info.file_size > Config.ZIP_MAX_TOTAL_SIZE:
                            logger.warning(f"ZIP total uncompressed size limit ({Config.ZIP_MAX_TOTAL_SIZE} bytes) reached; stopping extraction")
                            break
                        # File count cap
                        if len(extracted_files) >= Config.ZIP_MAX_FILES:
                            logger.warning(f"ZIP contains more than {Config.ZIP_MAX_FILES} files; stopping extraction")
                            break
                        with z.open(file_info) as f:
                            content = f.read()
                            # Try to decode as text, skip binary files
                            try:
                                content_str = content.decode('utf-8')
                                extracted_files[filename] = content_str
                                total_size += len(content_str)
                                logger.debug(f"Extracted file: {filename}, Size: {len(content_str)}")
                            except UnicodeDecodeError:
                                # Skip binary files
                                logger.debug(f"Skipped binary file: {filename}")
                                continue
    except zipfile.BadZipFile:
        logger.error("Invalid ZIP file")
        return None
    except Exception as e:
        logger.error(f"Error extracting ZIP: {str(e)}")
        return None
    
    logger.debug(f"Extracted {len(extracted_files)} files from ZIP")
    return extracted_files

def get_file_language(filename):
    """Determine programming language from file extension"""
    if not filename or '.' not in filename:
        logger.debug(f"File {filename} has no extension for language detection")
        return None
        
    try:
        file_ext = os.path.splitext(filename)[1].lower()
    except IndexError:
        logger.debug(f"File {filename} has invalid extension for language detection")
        return None
    
    logger.debug(f"Detecting language for {filename}, Extension: {file_ext}")
    
    # Map file extensions to languages
    for language, extensions in Config.LANGUAGE_EXTENSIONS.items():
        if file_ext in extensions:
            logger.debug(f"Detected language: {language} for {filename}")
            return language
    
    logger.debug(f"No language detected for {filename} with extension {file_ext}")
    return None

def is_text_file(file_stream):
    """
    Check if a file is likely a text file by attempting to decode it as UTF-8.
    """
    try:
        # Save current position
        original_position = file_stream.tell()
        
        # Read the first 1024 bytes
        sample = file_stream.read(1024)
        file_stream.seek(original_position)  # Reset stream position
        
        # Try to decode as UTF-8, falling back to Latin-1 for Windows-encoded files
        try:
            sample.decode('utf-8')
        except UnicodeDecodeError:
            sample.decode('latin-1')  # Windows-1252 / Latin-1 files are still text
        logger.debug("File is text (UTF-8/Latin-1 decodable)")
        return True
    except Exception as e:
        logger.debug(f"Error checking if file is text: {str(e)}")
        return False

def is_github_supported_language(language):
    """Check if a language is supported by GitHub code search"""
    supported = language in GITHUB_SUPPORTED_LANGUAGES
    logger.debug(f"Language {language} GitHub supported: {supported}")
    return supported