import os
import time
import json
import hashlib
import logging
from github import Github, GithubException
from config import Config
from utils.file_processing import GITHUB_SUPPORTED_LANGUAGES
from threading import Lock

logger = logging.getLogger(__name__)

# Global variables for rate limiting and caching
github_lock = Lock()
last_api_call = 0
min_request_interval = 1.0  # Minimum time between requests in seconds
cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache')
os.makedirs(cache_dir, exist_ok=True)

# Cache the rate-limit check briefly so each search term doesn't cost extra API calls
_rate_limit_cache = {'timestamp': 0.0, 'ok': True, 'error': None}
RATE_LIMIT_CACHE_TTL = 20  # seconds

_cache_write_count = 0
CACHE_TTL = 3600  # 1 hour


def _purge_expired_cache():
    """Delete expired cache files so the on-disk cache can't grow unbounded on
    the small Render free disk (512MB). Uses file mtime - cache files are only
    ever written once, so mtime is a cheap, reliable proxy for age."""
    try:
        now = time.time()
        for name in os.listdir(cache_dir):
            if not name.endswith('.json'):
                continue
            path = os.path.join(cache_dir, name)
            try:
                if now - os.path.getmtime(path) > CACHE_TTL:
                    os.remove(path)
            except OSError:
                pass
    except OSError:
        pass


# Clean up stale cache entries from previous runs at startup
_purge_expired_cache()

def get_repo_license(repo):
    """Get the license of a repository"""
    try:
        license = repo.get_license()
        return license.license.spdx_id if license else "Unknown"
    except:
        return "Unknown"

def get_cache_key(query, language):
    """Generate a cache key from query and language"""
    key_str = f"{query}_{language}"
    return hashlib.md5(key_str.encode()).hexdigest()

def get_cached_result(cache_key):
    """Get a cached result if it exists and is still valid"""
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        # Check if cache is still valid (1 hour)
        if time.time() - cache_data['timestamp'] < CACHE_TTL:
            return cache_data['result']
        else:
            # Cache expired, delete the file
            os.remove(cache_file)
            return None
    except:
        return None

def cache_result(cache_key, result):
    """Cache a result"""
    global _cache_write_count
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")
    
    cache_data = {
        'timestamp': time.time(),
        'result': result
    }
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        # Sweep expired entries occasionally so the disk cache stays small
        _cache_write_count += 1
        if _cache_write_count % 100 == 0:
            _purge_expired_cache()
    except:
        pass  # Silently fail if caching doesn't work

def get_rate_limit_resources(rate_limit):
    """Get the resources object from a get_rate_limit() result.

    Compatible with PyGithub < 2.7 (get_rate_limit returns RateLimit directly)
    and PyGithub >= 2.7 (returns RateLimitOverview, which wraps RateLimit under
    the .resources attribute - see PyGithub PR #3205)."""
    resources = getattr(rate_limit, 'resources', None)
    return resources if resources is not None else rate_limit

def check_github_rate_limit():
    """Check GitHub rate limit status before making API calls (cached for RATE_LIMIT_CACHE_TTL)"""
    now = time.time()
    if now - _rate_limit_cache['timestamp'] < RATE_LIMIT_CACHE_TTL:
        return _rate_limit_cache['ok'], _rate_limit_cache['error']
    
    try:
        if not Config.GITHUB_API_KEY or Config.GITHUB_API_KEY == 'your-github-api-key-here':
            return False, "GitHub API key not configured"
        
        g = Github(Config.GITHUB_API_KEY)
        rate_limit = get_rate_limit_resources(g.get_rate_limit())
        search_remaining = rate_limit.search.remaining
        
        if search_remaining <= 0:
            reset_time = rate_limit.search.reset
            wait_minutes = (reset_time.timestamp() - time.time()) / 60
            _rate_limit_cache.update(timestamp=now, ok=False, error=f"GitHub search rate limit exceeded. Resets in {wait_minutes:.0f} minutes.")
            return False, _rate_limit_cache['error']
        elif search_remaining <= 2:
            _rate_limit_cache.update(timestamp=now, ok=False, error=f"GitHub search rate limit nearly exceeded ({search_remaining} remaining). Conserving quota.")
            return False, _rate_limit_cache['error']
        
        _rate_limit_cache.update(timestamp=now, ok=True, error=None)
        return True, None
        
    except GithubException as e:
        if e.status == 401:
            error = "GitHub API key is invalid or unauthorized (401 Bad credentials). Check GITHUB_API_KEY in .env."
        elif e.status in (403, 429):
            error = "GitHub search rate limit exceeded (403/429). Try again later."
        else:
            error = f"Unable to check GitHub rate limit: {e}"
        _rate_limit_cache.update(timestamp=now, ok=False, error=error)
        return False, error
    except Exception as e:
        error = f"Unable to check GitHub rate limit: {str(e)}"
        _rate_limit_cache.update(timestamp=now, ok=False, error=error)
        return False, error

def search_github_code(query, language=None, max_results=10):
    """Search for code on GitHub using the API with improved rate limiting and error handling"""
    global last_api_call
    
    # Check if GitHub API key is configured
    if not Config.GITHUB_API_KEY or Config.GITHUB_API_KEY == 'your-github-api-key-here':
        return {"error": "GitHub API key not configured. Please add your GitHub API key to the .env file."}
    
    # Check rate limit FIRST before doing anything else
    rate_ok, rate_error = check_github_rate_limit()
    if not rate_ok:
        return {"error": f"GitHub search blocked: {rate_error}"}
    
    # Check if language is supported by GitHub
    if language and language not in GITHUB_SUPPORTED_LANGUAGES:
        return {"error": f"GitHub does not support code search for '{language}' files"}
    
    # Generate cache key
    cache_key = get_cache_key(query, language or '')
    cached_result = get_cached_result(cache_key)
    
    if cached_result is not None:
        logger.debug(f"Using cached GitHub result for query: {query[:30]}...")
        return cached_result
    
    try:
        # Use lock to ensure thread-safe API calls
        with github_lock:
            # Rate limiting: ensure minimum time between requests
            current_time = time.time()
            elapsed = current_time - last_api_call
            if elapsed < min_request_interval:
                time.sleep(min_request_interval - elapsed)
            
            g = Github(Config.GITHUB_API_KEY)
            
            # Build search query with better error handling
            safe_query = str(query)[:100].strip()  # Ensure string and limit length
            if not safe_query:
                return {"error": "Empty search query provided"}
                
            search_query = f'"{safe_query}"'
            if language:
                search_query += f' language:{language}'
            
            logger.debug(f"GitHub search query: {search_query}")
            
            # Perform the search with timeout
            try:
                results = g.search_code(search_query, sort='indexed', order='desc')
            except Exception as search_error:
                error_msg = f"GitHub search failed: {str(search_error)}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            matches = []
            count = 0
            
            try:
                for content_file in results:
                    if count >= max_results:
                        break
                        
                    try:
                        # Get file content safely
                        repo = content_file.repository
                        
                        # Try to decode content with fallback
                        try:
                            file_content = content_file.decoded_content.decode('utf-8')
                        except UnicodeDecodeError:
                            # Try with error handling for non-UTF8 files
                            file_content = content_file.decoded_content.decode('utf-8', errors='ignore')
                        except Exception as decode_error:
                            logger.debug(f"Failed to decode file content: {decode_error}")
                            continue
                        
                        # Cap stored content: keeps per-request memory and on-disk
                        # cache files small on the 512MB free plan. 64KB is far more
                        # than enough for the core-block extraction used for matching.
                        if len(file_content) > Config.GITHUB_RESULT_CONTENT_LIMIT:
                            file_content = file_content[:Config.GITHUB_RESULT_CONTENT_LIMIT]
                        
                        # Build result with all required fields
                        match = {
                            'repository': repo.full_name,
                            'file_path': content_file.path,
                            'url': content_file.html_url,
                            'content': file_content,
                            'license': get_repo_license(repo)
                        }
                        
                        matches.append(match)
                        count += 1
                        
                        logger.debug(f"Added GitHub match {count}: {repo.full_name}/{content_file.path}")
                        
                    except GithubException as e:
                        if e.status == 403 or e.status == 429:
                            error_msg = f"GitHub API rate limit exceeded during result processing: {e}"
                            logger.warning(error_msg)
                            return {"error": error_msg}
                        # Skip this result and continue with others
                        logger.debug(f"Skipping GitHub result due to error: {e}")
                        continue
                    except Exception as e:
                        # Skip this result and continue with others
                        logger.debug(f"Skipping GitHub result due to unexpected error: {e}")
                        continue
                        
            except Exception as iteration_error:
                logger.error(f"Error iterating GitHub search results: {iteration_error}")
                # Return what we have so far
                pass
            
            last_api_call = time.time()
            
            # Always cache the result (even if empty)
            cache_result(cache_key, matches)
            
            logger.info(f"GitHub search completed: {len(matches)} matches found for query '{safe_query}'")
            return matches
            
    except GithubException as e:
        error_msg = f"GitHub API error: {e}"
        if e.status == 403 or e.status == 429:
            error_msg = f"GitHub API rate limit exceeded: {e}"
        elif e.status == 422:
            error_msg = "GitHub API error: Invalid search query or parameters"
        
        logger.error(error_msg)
        return {"error": error_msg}
        
    except Exception as e:
        error_msg = f"Unexpected GitHub API error: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

def get_github_file_content(repo_owner, repo_name, file_path):
    """Get the content of a specific file from GitHub"""
    # Check if GitHub API key is configured
    if not Config.GITHUB_API_KEY or Config.GITHUB_API_KEY == 'your-github-api-key-here':
        return {"error": "GitHub API key not configured"}
    
    try:
        g = Github(Config.GITHUB_API_KEY)
        print(f"Rate limit: {g.get_rate_limit()}")
        repo = g.get_repo(f"{repo_owner}/{repo_name}")
        file_content = repo.get_contents(file_path).decoded_content.decode('utf-8')
        return file_content
    except GithubException as e:
        return {"error": f"GitHub API error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}