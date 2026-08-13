import requests
from bs4 import BeautifulSoup
import re
import random
import time
import urllib.parse
import logging
import difflib

# Attempt to import from config, but provide defaults if missing
try:
    from config import Config
except ImportError:
    class Config:
        MAX_WEB_PAGE_CHARS = 200 * 1024

# Attempt to import specific plagiarism helpers, but provide local fallbacks if missing
try:
    from .plagiarism_check import calculate_similarity, normalize_code
except ImportError:
    # FALLBACK 1: Basic Normalization
    def normalize_code(code, language='python'):
        """Remove comments and whitespace for comparison"""
        return re.sub(r'\s+', ' ', code).strip()

    # FALLBACK 2: Basic Similarity
    def calculate_similarity(text1, text2):
        """Standard SequenceMatcher"""
        return difflib.SequenceMatcher(None, text1, text2).ratio()

def calculate_code_similarity(code1, code2, language):
    """
    Enhanced similarity calculation that considers code structure
    Returns a weighted average of:
    - Text similarity (70%)
    - Structure similarity (30%)
    """
    # Text-based similarity
    text_sim = calculate_similarity(code1, code2)
    
    # Structure-based similarity (look for common patterns)
    structure_sim = 0
    try:
        # Extract code patterns
        if language == 'python':
            # Count common patterns
            patterns = [
                r'def\s+\w+',  # function definitions
                r'class\s+\w+',  # class definitions
                r'for\s+\w+\s+in',  # for loops
                r'if\s+\w+',  # if statements
                r'return\s+',  # return statements
                r'import\s+\w+',  # imports
                r'\w+\s*=\s*\w+',  # assignments
            ]
        else:
            # Generic patterns for other languages
            patterns = [
                r'function\s+\w+',
                r'class\s+\w+',
                r'for\s*\(',
                r'if\s*\(',
                r'return\s+',
                r'\w+\s*=\s*\w+',
            ]
        
        # Count pattern matches in both codes
        patterns1 = []
        patterns2 = []
        for pattern in patterns:
            patterns1.extend(re.findall(pattern, code1))
            patterns2.extend(re.findall(pattern, code2))
        
        # Calculate structure similarity based on common patterns
        if patterns1 and patterns2:
            common_patterns = set(patterns1) & set(patterns2)
            structure_sim = len(common_patterns) / max(len(set(patterns1)), len(set(patterns2)))
    except:
        structure_sim = 0
    
    # Weighted average: 70% text, 30% structure
    final_similarity = (text_sim * 0.7) + (structure_sim * 0.3)
    
    return final_similarity

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION & HEADERS
# =============================================================================

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
]

def get_random_headers():
    """Get random headers to look like a real browser"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

# =============================================================================
# SEARCH ENGINE LOGIC
# =============================================================================

def search_duckduckgo(query, max_results=2):
    """Search DuckDuckGo HTML (No API key required)"""
    results = []
    try:
        # Use HTML version which is easier to scrape
        url = "https://html.duckduckgo.com/html/"
        params = {'q': query}
        
        headers = get_random_headers()
        # Add a referrer to look legitimate
        headers['Referer'] = 'https://duckduckgo.com/'
        
        response = requests.post(url, data=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Parse Results
        for result in soup.find_all('div', class_='result')[:max_results]:
            title_tag = result.find('a', class_='result__a')
            snippet_tag = result.find('a', class_='result__snippet')
            
            if title_tag:
                link = title_tag['href']
                # Skip ads or internal DDG links
                if 'duckduckgo.com' in link:
                    continue
                    
                results.append({
                    'title': title_tag.get_text(strip=True),
                    'url': link,
                    'snippet': snippet_tag.get_text(strip=True) if snippet_tag else "",
                    'source': 'DuckDuckGo'
                })
    except Exception as e:
        logger.warning(f"DuckDuckGo search error: {e}")
    
    return results

def search_bing(query, max_results=2):
    """Search Bing HTML (Backup engine)"""
    results = []
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.bing.com/search?q={encoded_query}"
        
        headers = get_random_headers()
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Bing selectors change often, these are the most common recent ones
        items = soup.find_all('li', class_='b_algo')
        
        for item in items[:max_results]:
            h2 = item.find('h2')
            if h2 and h2.find('a'):
                link = h2.find('a')['href']
                title = h2.get_text(strip=True)
                
                # Try to find snippet
                caption = item.find('p')
                snippet = caption.get_text(strip=True) if caption else "No snippet available"
                
                results.append({
                    'title': title,
                    'url': link,
                    'snippet': snippet,
                    'source': 'Bing'
                })
    except Exception as e:
        logger.warning(f"Bing search error: {e}")
        
    return results

def search_code_repos(query, max_results=2):
    """Quick check on StackOverflow via search"""
    results = []
    try:
        encoded_query = urllib.parse.quote(query + " site:stackoverflow.com")
        # We reuse DuckDuckGo to search specifically for SO results
        so_results = search_duckduckgo(query + " site:stackoverflow.com", max_results)
        
        for res in so_results:
            res['source'] = 'StackOverflow' # Rename source for clarity
            results.append(res)
            
    except Exception as e:
        logger.debug(f"Repo search error: {e}")
    return results

# =============================================================================
# EXTRACTION & ANALYSIS
# =============================================================================

def extract_code_from_url(url, timeout=8):
    """Visit the URL and scrape the content with improved code extraction"""
    try:
        # Filter out huge files or irrelevant domains
        if any(x in url.lower() for x in ['.pdf', '.zip', 'youtube.com', 'facebook.com']):
            return None
            
        response = requests.get(url, headers=get_random_headers(), timeout=timeout)
        if response.status_code != 200:
            return None

        # Cap the amount of HTML that gets parsed. BeautifulSoup builds a parse
        # tree that is many times the size of the raw text, so parsing a huge
        # page can spike memory past the 512MB free-plan budget.
        raw_html = response.content[:Config.MAX_WEB_PAGE_CHARS]
        soup = BeautifulSoup(raw_html, 'html.parser')
        
        # Remove non-content elements first
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
            tag.decompose()
        
        code_blocks = []
        
        # Priority 1: <pre><code> combinations (highest quality)
        for pre in soup.find_all('pre'):
            code_tag = pre.find('code')
            if code_tag:
                text = code_tag.get_text().strip()
                if len(text) > 30:
                    code_blocks.append(text)
            elif len(pre.get_text().strip()) > 30:
                code_blocks.append(pre.get_text().strip())
        
        # Priority 2: Standalone <code> tags with substantial content
        if len(code_blocks) < 3:
            for code in soup.find_all('code'):
                text = code.get_text().strip()
                if len(text) > 30 and text not in [cb for cb in code_blocks]:
                    code_blocks.append(text)
        
        # Priority 3: Divs with code-related classes
        if len(code_blocks) < 3:
            for div in soup.find_all('div', class_=re.compile(r'code|highlight|snippet|example|program|source', re.I)):
                text = div.get_text().strip()
                if len(text) > 30:
                    code_blocks.append(text)
        
        # Priority 4: Look for code patterns (contains typical code syntax)
        if len(code_blocks) < 2:
            for tag in soup.find_all(['div', 'section', 'article']):
                text = tag.get_text().strip()
                # Check if it looks like code (has parentheses, brackets, semicolons, etc.)
                if len(text) > 50 and len(text) < 3000:
                    code_indicators = sum([
                        text.count('('), text.count(')'), text.count('{'), 
                        text.count('}'), text.count('['), text.count(']'),
                        text.count('def '), text.count('function '), text.count('class ')
                    ])
                    if code_indicators > 10:
                        code_blocks.append(text)
                
        if code_blocks:
            # Combine code blocks, prioritizing longer ones
            code_blocks.sort(key=len, reverse=True)
            return "\n\n".join(code_blocks[:8])  # Return top 8 blocks
            
        # Fallback: Get main text from main content area
        main_content = soup.find(['main', 'article', 'div'], class_=re.compile(r'content|main|body', re.I))
        if main_content:
            return main_content.get_text()[:5000]
        
        return soup.get_text()[:5000]
        
    except Exception as e:
        logger.debug(f"Extraction failed for {url}: {e}")
        return None

def create_search_queries(code, language):
    """
    Improved Strategy: Create better search queries with language context
    """
    lines = code.split('\n')
    candidates = []
    
    # Filter for meaningful lines
    for line in lines:
        line = line.strip()
        # Ignore comments, imports, and very short lines
        if len(line) > 20 and not line.startswith(('#', '//', 'import', 'from', 'include', 'using', 'package')):
            # Prioritize lines with function/class definitions or unique logic
            if any(keyword in line for keyword in ['def ', 'function ', 'class ', '=', 'return', 'if ', 'for ', 'while ']):
                candidates.append(line)
            elif len(line) > 30:
                candidates.append(line)
            
    # Sort by length and uniqueness (longer lines are usually more unique)
    candidates.sort(key=len, reverse=True)
    
    # Take top 3-4 unique lines
    unique_queries = candidates[:4]
    
    # Add language to queries for better search results
    search_queries = []
    for query in unique_queries:
        # Add language keyword to improve relevance
        search_queries.append(f"{query} {language}")
    
    # If no complex lines found, use basic approach
    if not search_queries:
        meaningful_lines = [line.strip() for line in lines if len(line.strip()) > 15][:3]
        search_queries = [f"{line} {language}" for line in meaningful_lines]
        
    return search_queries

def web_scraping_search(code, language, max_results=5):
    """
    Coordinator function with improved matching:
    1. Generates better queries with language context
    2. Searches Engines
    3. Extracts code-focused content
    4. Calculates similarity and reports every match above a low floor
    """
    normalized_input = normalize_code(code, language)
    queries = create_search_queries(code, language)
    
    logger.info(f"Generated {len(queries)} queries for web check")
    
    final_matches = []
    seen_urls = set()
    
    # Low, honest reporting floor: any computed similarity above this is kept and
    # shown on the results page with its real percentage. The old adaptive
    # thresholds (10%/12%/15%) silently dropped matches like 11.49% that were
    # visible in the logs, making the UI show 0% despite real fetched results.
    MATCH_FLOOR = 0.08
    logger.debug(f"Using similarity floor: {MATCH_FLOOR * 100}% - all matches above this are reported")
    
    for query in queries:
        # Search all engines
        search_hits = []
        search_hits.extend(search_duckduckgo(query))
        time.sleep(1) # Polite delay
        
        if not search_hits:
            search_hits.extend(search_bing(query))
        
        for hit in search_hits:
            url = hit['url']
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # Extract content with improved code extraction
            extracted_content = extract_code_from_url(url)
            
            if extracted_content:
                extracted_norm = normalize_code(extracted_content, language)
                
                # Use enhanced similarity calculation
                similarity = calculate_code_similarity(normalized_input, extracted_norm, language)
                
                logger.debug(f"URL: {url[:50]}... - Similarity: {similarity * 100:.2f}%")
                
                # Keep every match above the low floor so the real percentage is
                # shown on the results page instead of being silently dropped
                if similarity > MATCH_FLOOR:
                    hit['similarity_score'] = similarity  # Store as decimal (0-1.0) to match GitHub format
                    hit['matched_content'] = extracted_content[:300] + "..."
                    final_matches.append(hit)
                    logger.info(f"✓ Match found: {similarity * 100:.2f}% - {url}")
            
            if len(final_matches) >= max_results:
                break
        
        if len(final_matches) >= max_results:
            break
    
    # Sort by highest similarity
    final_matches.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
    return final_matches

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def check_web_sources(code, language, max_results=5):
    """
    Main function called by app.py
    """
    return web_scraping_search(code, language, max_results)