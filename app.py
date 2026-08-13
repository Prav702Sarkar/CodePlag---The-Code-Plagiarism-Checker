# app.py - Fixed version with better error handling
from dotenv import load_dotenv
load_dotenv()

import os
import sys
import gc
import logging
import time
from threading import Lock
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from config import Config

# Windows dev consoles default to cp1252 and crash on the emoji log prints.
# Force UTF-8 with lossy fallback so the app runs identically everywhere
# (Render/Linux already uses UTF-8).
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from utils.file_processing import allowed_file, extract_zip, get_file_language, is_text_file, is_github_supported_language
from utils.plagiarism_check import check_plagiarism
from utils.security import init_limiter, sanitize_filename, validate_file_content
from utils.web_check import check_web_sources

# Set up logging. DEBUG-level logs generate a lot of retained string data and
# slow the app down; keep them off in production (Render free = 512MB RAM).
log_level = logging.DEBUG if Config.DEBUG else logging.INFO
logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_object(Config)

# Initialize rate limiting
limiter = init_limiter(app)

# Only one heavy scan runs at a time. Concurrent scans are the fastest way to
# blow past the 512MB free-plan budget (each scan holds upload data, extracted
# blocks and search results in memory). Light requests still run on other threads.
scan_lock = Lock()


def get_worker_memory_mb():
    """Return the current process RSS in MB, or None if not measurable
    (e.g. on Windows dev machines). Used to refuse scans under memory pressure
    instead of letting the OOM killer SIGKILL the worker."""
    try:
        with open('/proc/self/status', 'r') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return None


def free_memory(full=False):
    """Release memory held by completed file processing so the next file or
    scan starts from a clean heap instead of carrying the previous scan's
    leftovers:
      - gc.collect() reclaims unreferenced cycles (AST trees, parsed HTML,
        BeautifulSoup documents, ...)
      - when a whole scan finishes (full=True), also purge expired on-disk
        result-cache entries so the 512MB free-plan disk stays small too.
    Logs the RSS before/after so the effect is visible in Render logs."""
    before = get_worker_memory_mb()
    gc.collect()
    if full:
        try:
            from utils.github_api import purge_expired_cache
            purge_expired_cache()
        except Exception:
            pass
    after = get_worker_memory_mb()
    if before is not None and after is not None:
        logger.info(f"Memory freed: RSS {before}MB -> {after}MB")
    return after

def process_single_file(file, filename):
    """Process a single file and return results"""
    try:
        logger.info(f"📄 Processing file: {filename}")
        print(f"\n{'='*60}")
        print(f"📄 PROCESSING: {filename}")
        print(f"{'='*60}")
        
        # Reset file stream position
        file.stream.seek(0)
        
        # Check if it's a text file
        if not is_text_file(file.stream):
            logger.debug(f"File {filename} is not a text file")
            return None, f'{filename} is not a text file'
        
        # Reset stream again before reading content (Latin-1 fallback for Windows-encoded files)
        file.stream.seek(0)
        raw_content = file.read()
        try:
            content = raw_content.decode('utf-8')
        except UnicodeDecodeError:
            content = raw_content.decode('latin-1')
        language = get_file_language(filename)
        
        logger.debug(f"File {filename}: Language detected: {language}, Content length: {len(content)}")
        
        if not language:
            return None, f'{filename} has unsupported file type'
        
        if not validate_file_content(content):
            return None, f'{filename} failed content validation'
        
        # Check if GitHub supports this language
        github_supported = is_github_supported_language(language)
        logger.debug(f"GitHub support for {language}: {github_supported}")
        print(f"\n🔍 Checking GitHub repositories...")
        
        if not github_supported:
            plagiarism_results = {'github': {"error": f"GitHub does not support code search for '{language}' files"}, 'web': []}
        else:
            plagiarism_results = check_plagiarism(content, language, filename)
        
        # Web results are already collected inside check_plagiarism; only run a
        # separate web check when the plagiarism module didn't provide one
        if not plagiarism_results.get('web'):
            print(f"🌐 Checking web sources...")
            web_results = check_web_sources(content, language)
            plagiarism_results['web'] = web_results
        
        # Calculate max similarities for display
        github_max_similarity = 0
        if 'error' not in plagiarism_results.get('github', {}) and plagiarism_results.get('github'):
            if isinstance(plagiarism_results['github'], list):
                similarities = [match.get('similarity', 0) for match in plagiarism_results['github'] if match.get('similarity')]
                github_max_similarity = max(similarities) if similarities else 0
        
        web_max_similarity = 0
        if plagiarism_results.get('web'):
            similarities = [match.get('similarity_score', match.get('similarity', 0)) for match in plagiarism_results['web'] if match.get('similarity_score') or match.get('similarity')]
            web_max_similarity = max(similarities) if similarities else 0
        
        logger.debug(f"File {filename} processed successfully. GitHub matches: {len(plagiarism_results.get('github', []))}, Web matches: {len(plagiarism_results.get('web', []))}")
        
        print(f"\n✅ Processing completed: {filename}")
        print(f"   • GitHub matches: {len(plagiarism_results.get('github', []))}")
        print(f"   • Web matches: {len(plagiarism_results.get('web', []))}")
        print(f"   • GitHub similarity: {github_max_similarity:.1f}%")
        print(f"   • Web similarity: {web_max_similarity:.1f}%")
        print(f"{'='*60}\n")
        
        return {
            'filename': filename,
            'language': language,
            'github': plagiarism_results.get('github', []),
            'web': plagiarism_results.get('web', []),
            'github_max_similarity': github_max_similarity,
            'web_max_similarity': web_max_similarity
        }, None
        
    except Exception as e:
        logger.error(f"Error processing {filename}: {str(e)}", exc_info=True)
        print(f"\n❌ ERROR processing {filename}: {str(e)}\n")
        return None, f"Error processing {filename}: {str(e)}"

def process_zip_file(file, filename):
    """Process a zip file and return results for all contained files"""
    try:
        logger.info(f"📦 Processing ZIP file: {filename}")
        print(f"\n{'='*60}")
        print(f"📦 EXTRACTING ZIP: {filename}")
        print(f"{'='*60}")
        
        extracted_files = extract_zip(file.stream)
        
        if not extracted_files:
            print(f"❌ No supported files found in ZIP\n")
            return None, 'Invalid zip file or no supported files found'
        
        print(f"✅ Extracted {len(extracted_files)} file(s)\n")
        results = {}
        processed_count = 0
        skipped_files = []
        
        for extracted_name, content in extracted_files.items():
            language = get_file_language(extracted_name)
            if language and validate_file_content(content):
                file_result, error = process_file_content(content, language, extracted_name)
                if file_result:
                    results[file_result['filename']] = file_result
                    processed_count += 1
            else:
                skipped_files.append(extracted_name)
            # Release per-file memory (AST trees, parsed web pages, ...) so a
            # large archive doesn't accumulate leftovers across all its files
            free_memory()
        
        # Surface skipped files instead of silently dropping them
        if not results and skipped_files:
            skipped_preview = ', '.join(f"'{f}'" for f in skipped_files[:8])
            if len(skipped_files) > 8:
                skipped_preview += '...'
            return None, 'No supported code files were processed. Skipped: ' + skipped_preview
        if skipped_files:
            logger.warning(f"Skipped {len(skipped_files)} unsupported/binary file(s) inside {filename}: {skipped_files[:10]}")
        
        logger.debug(f"ZIP file processing completed: {processed_count} files processed")
        print(f"\n✅ ZIP processing completed: {processed_count} file(s) processed")
        print(f"{'='*60}\n")
        return results, None
        
    except Exception as e:
        logger.error(f"Error processing zip file {filename}: {str(e)}", exc_info=True)
        print(f"\n❌ ERROR processing ZIP {filename}: {str(e)}\n")
        return None, f'Error processing zip file: {str(e)}'

def process_file_content(content, language, filename):
    """Process file content for plagiarism checking"""
    try:
        logger.debug(f"Processing file content: {filename}, Language: {language}")
        
        plagiarism_results = check_plagiarism(content, language, filename)
        
        # Debug the structure of results
        logger.debug(f"Plagiarism results keys: {list(plagiarism_results.keys()) if isinstance(plagiarism_results, dict) else 'Not a dict'}")
        
        # Handle new plagiarism check structure
        github_matches = []
        web_matches = []
        
        # The new structure returns matches in 'github' and 'web' keys
        if plagiarism_results.get('github'):
            github_matches = plagiarism_results['github']
            logger.debug(f"GitHub matches found: {len(github_matches) if isinstance(github_matches, list) else 'Not a list'}")
        
        if plagiarism_results.get('web'):
            web_matches = plagiarism_results['web']
            logger.debug(f"Web matches found: {len(web_matches) if isinstance(web_matches, list) else 'Not a list'}")
        
        # Calculate max similarities for display
        github_max_similarity = 0
        if isinstance(github_matches, list) and github_matches:
            similarities = []
            for match in github_matches:
                if isinstance(match, dict):
                    sim = match.get('similarity', 0)
                    if sim and sim > 0:
                        similarities.append(sim)
            github_max_similarity = max(similarities) if similarities else 0
            logger.debug(f"GitHub max similarity: {github_max_similarity}")
        
        web_max_similarity = 0
        if isinstance(web_matches, list) and web_matches:
            similarities = []
            for match in web_matches:
                if isinstance(match, dict):
                    # Try both similarity_score and similarity fields
                    sim = match.get('similarity_score', match.get('similarity', 0))
                    if sim and sim > 0:
                        similarities.append(sim)
            web_max_similarity = max(similarities) if similarities else 0
            logger.debug(f"Web max similarity: {web_max_similarity}")
        
        result = {
            'filename': filename,
            'language': language,
            'github': github_matches,
            'web': web_matches,
            'github_max_similarity': github_max_similarity,
            'web_max_similarity': web_max_similarity
        }
        
        logger.debug(f"Final result: GitHub={len(result['github'])} matches, Web={len(result['web'])} matches, Max similarities: GitHub={result['github_max_similarity']}, Web={result['web_max_similarity']}")
        
        return result, None
        
    except Exception as e:
        logger.error(f"Error processing file content {filename}: {str(e)}", exc_info=True)
        return None, f'Error processing {filename}: {str(e)}'

def get_upload_size(file):
    """Get the byte size of an uploaded file without consuming its stream"""
    try:
        file.stream.seek(0, os.SEEK_END)
        size = file.stream.tell()
        file.stream.seek(0)
        return size
    except Exception:
        return int(getattr(file, 'content_length', 0) or 0)

@app.route('/')
def index():
    return render_template('index.html', languages=list(Config.LANGUAGE_EXTENSIONS.keys()))

@app.route('/check', methods=['POST'])
@limiter.limit("10 per minute")
def check_plagiarism_route():
    """Handle plagiarism check requests"""
    # Serialize scans - see scan_lock comment above
    if not scan_lock.acquire(blocking=False):
        logger.warning("Rejected /check - another scan is already running")
        flash('Another scan is already running. Please wait a moment and try again.')
        return redirect(url_for('index'))
    try:
        logger.info("="*60)
        logger.info("NEW PLAGIARISM CHECK REQUEST RECEIVED")
        logger.info("="*60)
        
        # Check if files were uploaded
        if 'files' not in request.files:
            logger.warning("No files in request")
            flash('No files uploaded')
            return redirect(url_for('index'))
        
        files = request.files.getlist('files')
        logger.info(f"Received {len(files)} file(s)")
        
        if not files or all(file.filename == '' for file in files):
            logger.warning("All files have empty filenames")
            flash('No files selected')
            return redirect(url_for('index'))

        # Bound how many files one request may process - each one holds
        # extracted blocks and search results in memory until the scan ends
        if len(files) > Config.MAX_FILES_PER_REQUEST:
            logger.warning(f"Upload blocked - {len(files)} files exceeds the {Config.MAX_FILES_PER_REQUEST}-file limit")
            flash(f'Too many files. Please upload at most {Config.MAX_FILES_PER_REQUEST} files at a time.')
            return redirect(url_for('index'))

        # Refuse to start a scan when the worker is already under memory
        # pressure, instead of letting the OOM killer SIGKILL us mid-request
        current_mb = get_worker_memory_mb()
        if current_mb is not None and current_mb > Config.MAX_WORKER_MEMORY_MB:
            logger.warning(f"Rejected /check - worker RSS {current_mb}MB exceeds {Config.MAX_WORKER_MEMORY_MB}MB")
            flash('The server is under heavy load right now. Please wait a moment and try again.')
            return redirect(url_for('index'))
        
        # Block files larger than 3MB - they take hours to process
        large_files = []
        for file in files:
            if file.filename == '':
                continue
            if get_upload_size(file) > Config.MAX_UPLOAD_SIZE:
                large_files.append(file.filename)
        
        if large_files:
            names = ', '.join(large_files)
            logger.warning(f"Upload blocked - files over 3MB: {names}")
            flash(
                f'{names} exceed the 3MB limit. Files larger than 3MB can take hours to process, '
                'so processing was blocked. Please split them into smaller parts (each under 3MB) '
                'and upload them as a ZIP file.'
            )
            return redirect(url_for('index'))
        
        results = {}
        error_messages = []
        processed_files = 0
        
        logger.debug(f"Starting plagiarism check for {len(files)} files")
        
        for i, file in enumerate(files):
            if file.filename == '':
                continue
            
            logger.info(f"[{i+1}/{len(files)}] Processing: {file.filename}")
            
            if file and allowed_file(file.filename):
                filename = sanitize_filename(file.filename)
                logger.debug(f"File allowed: {filename}")
                
                if filename.lower().endswith('.zip'):
                    result, error = process_zip_file(file, filename)
                else:
                    result, error = process_single_file(file, filename)
                
                if error:
                    error_messages.append(error)
                    logger.debug(f"Error processing {filename}: {error}")
                elif result:
                    if 'filename' in result:  # Single file result
                        results[result['filename']] = result
                        processed_files += 1
                    else:  # Zip file result (multiple files)
                        results.update(result)
                        processed_files += len(result)
            else:
                error_msg = f"File type not supported: {file.filename}"
                error_messages.append(error_msg)
                logger.debug(error_msg)
            
            # Free this file's memory before starting the next one so each
            # scan starts clean and a multi-file request stays low-RSS
            free_memory()
        
        # Add error messages to flash
        for error in error_messages:
            flash(error)
        
        logger.info(f"Processing completed. Files processed: {processed_files}, Results: {len(results)}")
        logger.info("="*60)
        
        if not results:
            logger.warning("No results to display")
            flash('No supported code files were processed. Please check file types.')
            return render_template('results.html', results={})
        
        # Calculate overall statistics
        github_max_similarity = 0
        web_max_similarity = 0
        total_matches = 0
        
        for file_data in results.values():
            if file_data.get('github_max_similarity', 0) > github_max_similarity:
                github_max_similarity = file_data.get('github_max_similarity', 0)
            if file_data.get('web_max_similarity', 0) > web_max_similarity:
                web_max_similarity = file_data.get('web_max_similarity', 0)
            
            if isinstance(file_data.get('github'), list):
                total_matches += len(file_data['github'])
            if isinstance(file_data.get('web'), list):
                total_matches += len(file_data['web'])
        
        max_overall_similarity = max(github_max_similarity, web_max_similarity)
        
        logger.debug(f"Final results: {len(results)} files processed, {total_matches} matches found")
        
        return render_template('results.html', 
                             results=results,
                             github_max_similarity=github_max_similarity,
                             web_max_similarity=web_max_similarity,
                             total_matches=total_matches,
                             max_overall_similarity=max_overall_similarity)
    
    except Exception as e:
        logger.error(f"Error during plagiarism check: {str(e)}", exc_info=True)
        flash('An error occurred during the plagiarism check. Please try again.')
        return redirect(url_for('index'))
    finally:
        # Full cleanup after the scan: GC + purge expired on-disk cache
        # entries so the next scan starts fresh
        free_memory(full=True)
        scan_lock.release()

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('error.html', 
                         error_title="Page Not Found", 
                         error_message="The page you are looking for does not exist."), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return render_template('error.html', 
                         error_title="Internal Server Error", 
                         error_message="An internal error occurred. Please try again later."), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors"""
    flash('File too large. Maximum allowed size is 16MB.')
    return redirect(url_for('index'))

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0',
        'supported_languages': list(Config.LANGUAGE_EXTENSIONS.keys())
    })

@app.route('/api-status')
def api_status():
    """Check API rate limit status"""
    try:
        from github import Github
        
        # Check GitHub API status
        if Config.GITHUB_API_KEY and Config.GITHUB_API_KEY != 'your-github-api-key-here':
            from utils.github_api import get_rate_limit_resources
            g = Github(Config.GITHUB_API_KEY)
            rate_limit = get_rate_limit_resources(g.get_rate_limit())
            
            github_status = {
                'search_remaining': rate_limit.search.remaining,
                'search_limit': rate_limit.search.limit,
                'core_remaining': rate_limit.core.remaining,
                'core_limit': rate_limit.core.limit,
                'search_reset': rate_limit.search.reset.isoformat(),
                'core_reset': rate_limit.core.reset.isoformat()
            }
        else:
            github_status = {'error': 'GitHub API not configured'}
        
        # Detection methods status
        detection_methods = {
            'github_api': bool(Config.GITHUB_API_KEY),
            'web_scraping': True,
            'search_engines': ['DuckDuckGo', 'Bing'],
            'code_sites': ['Stack Overflow', 'CodePen']
        }
        
        return jsonify({
            'timestamp': time.time(),
            'github_api': github_status,
            'detection_methods': detection_methods,
            'app_rate_limits': {
                'default': Config.RATELIMIT_DEFAULT,
                'check_endpoint': '10 per minute'
            }
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Error checking API status: {str(e)}'
        }), 500

if __name__ == '__main__':
    logger.info("Starting Advanced Plagiarism Checker")
    logger.info(f"Supported languages: {list(Config.LANGUAGE_EXTENSIONS.keys())}")
    logger.info(f"Supported extensions: {[ext for exts in Config.LANGUAGE_EXTENSIONS.values() for ext in exts]}")
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=os.environ.get('DEBUG', 'False').lower() == 'true', host='0.0.0.0', port=port)