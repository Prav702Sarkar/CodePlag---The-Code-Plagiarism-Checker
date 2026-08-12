import ast
import re
import hashlib
import logging
from difflib import SequenceMatcher
from config import Config
from utils.intelligent_extraction import extract_core_code

logger = logging.getLogger(__name__)

# Any GitHub match above this floor is reported with its real similarity %.
# The old hard 30% drop made genuine matches (e.g. 11.49%) invisible on the
# results page even though the backend computed them.
GITHUB_MATCH_FLOOR = 0.08

def normalize_code(code, language):
    """Normalize code by removing comments, whitespace, and standardizing identifiers"""
    try:
        if language == 'python':
            return normalize_python_code(code)
        elif language in ['javascript', 'java', 'c', 'cpp', 'csharp']:
            return normalize_curly_brace_code(code)
        else:
            # Generic normalization for other languages
            # Remove comments
            code = re.sub(r'//.*?$|/\*.*?\*/', '', code, flags=re.MULTILINE|re.DOTALL)
            # Remove extra whitespace
            code = re.sub(r'\s+', ' ', code)
            return code.strip()
    except Exception as e:
        # If normalization fails, return the original code
        return code

def normalize_python_code(code):
    """Normalize Python code by removing comments and extra whitespace while preserving structure"""
    try:
        # Remove comments but keep code structure
        # Remove single-line comments
        lines = code.split('\n')
        cleaned_lines = []
        for line in lines:
            # Remove inline comments but keep the code part
            if '#' in line:
                # Find the # that's not in a string
                in_string = False
                quote_char = None
                for i, char in enumerate(line):
                    if char in ['"', "'"] and (i == 0 or line[i-1] != '\\'):
                        if not in_string:
                            in_string = True
                            quote_char = char
                        elif char == quote_char:
                            in_string = False
                            quote_char = None
                    elif char == '#' and not in_string:
                        line = line[:i].rstrip()
                        break
            cleaned_lines.append(line)
        
        code = '\n'.join(cleaned_lines)
        
        # Remove docstrings but preserve function/class names
        code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
        code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
        
        # Normalize whitespace but keep structure
        code = re.sub(r'[ \t]+', ' ', code)  # Multiple spaces/tabs to single space
        code = re.sub(r'\n\s*\n', '\n', code)  # Multiple newlines to single
        
        return code.strip()
    except Exception as e:
        # Fallback: just remove comments
        lines = [line.split('#')[0].rstrip() for line in code.split('\n')]
        return '\n'.join(lines).strip()

def normalize_curly_brace_code(code):
    """Normalize code for languages with C-style syntax while preserving meaningful structure"""
    # Remove single-line comments
    code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
    # Remove multi-line comments
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    # Normalize whitespace but keep structure
    code = re.sub(r'[ \t]+', ' ', code)  # Multiple spaces/tabs to single space
    code = re.sub(r'\n\s*\n', '\n', code)  # Multiple newlines to single
    return code.strip()

def calculate_similarity(text1, text2):
    """Calculate similarity between two texts using SequenceMatcher"""
    if not text1 or not text2:
        return 0
    return SequenceMatcher(None, text1, text2).ratio()

def generate_code_fingerprint(code, language):
    """Generate a fingerprint for the code to compare against other code snippets"""
    normalized = normalize_code(code, language)
    return hashlib.sha256(normalized.encode()).hexdigest()

def extract_meaningful_search_terms(code, language):
    """Extract meaningful terms from code for search queries"""
    search_terms = []
    
    # Extract function names
    if language == 'python':
        # Find function definitions
        func_matches = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
        search_terms.extend(func_matches)
        
        # Find class names
        class_matches = re.findall(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
        search_terms.extend(class_matches)
        
        # Find imports
        import_matches = re.findall(r'(?:from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+)?import\s+([a-zA-Z_][a-zA-Z0-9_.,\s]*)', code)
        for match in import_matches:
            if match[0]:  # from ... import
                search_terms.append(match[0])
            search_terms.extend([m.strip() for m in match[1].split(',') if m.strip()])
        
        # Find method calls and variable names
        method_calls = re.findall(r'(\w+)\.(\w+)\s*\(', code)
        for obj, method in method_calls:
            if len(obj) > 2 and len(method) > 2:
                search_terms.extend([obj, method])
        
        # Find variable assignments
        var_assignments = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=', code)
        search_terms.extend([var for var in var_assignments if len(var) > 2])
        
        # Find string literals with meaningful content
        string_matches = re.findall(r'[\'"]([a-zA-Z_][a-zA-Z0-9_\s]{3,20})[\'"]', code)
        for string in string_matches:
            # Extract meaningful words from strings
            words = re.findall(r'\b[a-zA-Z]{4,}\b', string)
            search_terms.extend(words)
    
    elif language in ['javascript', 'typescript']:
        # Find function declarations
        func_matches = re.findall(r'function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', code)
        search_terms.extend(func_matches)
        
        # Find class names
        class_matches = re.findall(r'class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', code)
        search_terms.extend(class_matches)
        
        # Find arrow functions (covers JSX/TSX components like `const Foo = () => ...`)
        arrow_matches = re.findall(r'(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:\([^)]*\)|[a-zA-Z_$][a-zA-Z0-9_$]*)\s*=>', code)
        search_terms.extend(arrow_matches)
        
        # Find method calls
        method_calls = re.findall(r'(\w+)\.(\w+)\s*\(', code)
        for obj, method in method_calls:
            if len(obj) > 2 and len(method) > 2:
                search_terms.extend([obj, method])
    
    elif language == 'java':
        # Find class names  
        class_matches = re.findall(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
        search_terms.extend(class_matches)
        
        # Find method names
        method_matches = re.findall(r'(?:public|private|protected)?\s*(?:static)?\s*(?:\w+\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', code)
        search_terms.extend(method_matches)
        
        # Find method calls
        method_calls = re.findall(r'(\w+)\.(\w+)\s*\(', code)
        for obj, method in method_calls:
            if len(obj) > 2 and len(method) > 2:
                search_terms.extend([obj, method])
    
    else:
        # Generic extraction for C/C++/C#/Go/Rust/Swift/Kotlin/Java-alternatives, Ruby, PHP,
        # Scala, Shell, R, Perl, Haskell, Lua, HTML and CSS - covers every supported format
        func_patterns = [
            r'\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)',                            # JS/PHP/Lua
            r'\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)',                                  # Ruby/Scala
            r'\bfunc\s+(?:\([^)]*\)\s+)?([a-zA-Z_][a-zA-Z0-9_]*)',              # Go/Swift
            r'\bfn\s+([a-zA-Z_][a-zA-Z0-9_]*)',                                   # Rust
            r'\bfun\s+([a-zA-Z_][a-zA-Z0-9_]*)',                                  # Kotlin
            r'\bsub\s+([a-zA-Z_][a-zA-Z0-9_]*)',                                  # Perl
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*<-\s*function',                          # R
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*::\s*[a-zA-Z_]',                          # Haskell
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\)\s*\{',                            # Shell
            r'\b(?:int|void|char|bool|double|float|long|unsigned|string|auto|size_t|const|var|let)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{',  # C/C++/C#/Go
            r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)',                                # Many languages
            r'\bstruct\s+([a-zA-Z_][a-zA-Z0-9_]*)',                               # C/C++/Go/Rust/Swift
            r'\binterface\s+([a-zA-Z_][a-zA-Z0-9_]*)',                            # Go/C#
        ]
        for pattern in func_patterns:
            search_terms.extend([m for m in re.findall(pattern, code) if m])
        
        # Method calls (generic)
        method_calls = re.findall(r'(\w+)\.(\w+)\s*\(', code)
        for obj, method in method_calls:
            if len(obj) > 2 and len(method) > 2:
                search_terms.extend([obj, method])
    
    # Remove duplicates and common words
    common_words = {
        'main', 'test', 'init', 'get', 'set', 'var', 'function', 'class', 'def', 'return',
        'true', 'false', 'null', 'none', 'this', 'self', 'super', 'len', 'str', 'int', 'list',
        'dict', 'args', 'kwargs', 'name', 'value', 'data', 'item', 'result', 'error', 'message'
    }
    search_terms = [term for term in set(search_terms) if term not in common_words and len(term) > 2]
    
    return search_terms[:5]  # Return top 5 terms

def check_plagiarism(content, language, filename=None):
    """Check for plagiarism using intelligent code extraction"""
    from utils.github_api import search_github_code
    
    try:
        logger.info(f"Starting intelligent plagiarism check for {language} code")
        
        # Step 1: Extract core algorithmic content (skip comments, imports, boilerplate)
        extraction_result = extract_core_code(content, language)
        
        if not extraction_result['extraction_success']:
            logger.warning("Intelligent extraction failed, using fallback method")
            return check_plagiarism_fallback(content, language, filename)
        
        core_blocks = extraction_result['core_blocks']
        logger.info(f"Extracted {len(core_blocks)} core code blocks for analysis")
        
        github_matches = []
        first_github_error = None
        github_search_count = 0
        github_stop = False
        MAX_GITHUB_SEARCHES = 4  # Respect GitHub's code-search API limit (10/min)
        processed_blocks = 0
        
        # Step 2: Check each core block for plagiarism
        for block in core_blocks:
            if processed_blocks >= 5 or github_stop:  # Limit blocks and GitHub searches
                break
                
            block_code = block['code']
            block_name = block['name']
            
            logger.debug(f"Analyzing core block: {block_name} (type: {block['type']})")
            
            # Extract search terms from this specific block
            search_terms = extract_meaningful_search_terms(block_code, language)
            
            # Normalize block code for comparison
            normalized_block = normalize_code(block_code, language)
            
            # Search GitHub for this specific block
            if search_terms:
                for term in search_terms[:2]:  # Top 2 terms per block
                    if github_search_count >= MAX_GITHUB_SEARCHES:
                        github_stop = True
                        break
                    github_search_count += 1
                    try:
                        github_results = search_github_code(term, language, max_results=3)
                        
                        if isinstance(github_results, dict) and 'error' in github_results:
                            error_msg = github_results['error']
                            logger.warning(f"GitHub search error for {term}: {error_msg}")
                            if first_github_error is None:
                                first_github_error = error_msg
                            
                            # Stop on rate limits or auth problems instead of wasting quota
                            if ("rate limit" in error_msg.lower() or "401" in error_msg
                                    or "invalid" in error_msg.lower() or "unauthorized" in error_msg.lower()):
                                logger.warning("GitHub search unavailable, stopping further GitHub searches for this request")
                                github_stop = True
                                break
                            continue
                        
                        # Compare with found results
                        for result in github_results:
                            try:
                                if 'content' in result:
                                    # Extract core code from the GitHub result too
                                    result_extraction = extract_core_code(result['content'], language)
                                    
                                    # Find the best matching block in the result
                                    best_similarity = 0
                                    best_match_block = None
                                    
                                    for result_block in result_extraction['core_blocks']:
                                        result_normalized = normalize_code(result_block['code'], language)
                                        similarity = calculate_similarity(normalized_block, result_normalized)
                                        
                                        if similarity > best_similarity:
                                            best_similarity = similarity
                                            best_match_block = result_block
                                    
                                    # Report every match above the floor so the
                                    # real percentage shows on the results page
                                    if best_similarity >= GITHUB_MATCH_FLOOR:
                                        result['similarity'] = round(best_similarity, 3)
                                        result['similarity_percentage'] = f"{best_similarity*100:.1f}%"
                                        result['matched_block'] = {
                                            'original_block': block_name,
                                            'matched_block': best_match_block['name'] if best_match_block else 'unknown',
                                            'block_type': block['type']
                                        }
                                        github_matches.append(result)
                                        logger.info(f"Found {best_similarity*100:.1f}% similarity between {block_name} and {result.get('repository', 'unknown')}")
                                        
                            except Exception as e:
                                logger.warning(f"Error processing GitHub result: {str(e)}")
                                continue
                                
                    except Exception as e:
                        logger.warning(f"Error searching GitHub for term {term}: {str(e)}")
                        continue
            
            processed_blocks += 1
        
        # Step 3: Remove duplicates and sort by similarity
        seen_urls = set()
        unique_matches = []
        for match in github_matches:
            url = match.get('url', '')
            if url not in seen_urls:
                seen_urls.add(url)
                unique_matches.append(match)
        
        # Sort by similarity score (highest first)
        unique_matches.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        
        # Surface GitHub errors on the results page instead of silently showing 0%
        if not unique_matches and first_github_error:
            github_results_out = {"error": f"GitHub search unavailable: {first_github_error}"}
        else:
            github_results_out = unique_matches[:10]  # Top 10 matches
        
        # Step 4: Web search using core blocks (not full content)
        from utils.web_check import check_web_sources
        
        # Create a condensed version of core code for web search
        core_code_summary = create_core_code_summary(core_blocks[:3])  # Top 3 blocks
        web_results = check_web_sources(core_code_summary, language)
        
        logger.info(f"Intelligent plagiarism check completed: {len(unique_matches)} GitHub matches, {len(web_results)} web matches from {len(core_blocks)} core blocks")
        
        return {
            'github': github_results_out,
            'web': web_results,
            'extraction_info': {
                'total_blocks_analyzed': len(core_blocks),
                'blocks_processed': processed_blocks,
                'extraction_successful': True,
                'core_lines': extraction_result['summary']['total_core_lines']
            }
        }
        
    except Exception as e:
        logger.error(f"Error in intelligent plagiarism check: {str(e)}")
        # Fallback to original method
        return check_plagiarism_fallback(content, language, filename)

def create_core_code_summary(core_blocks):
    """Create a condensed summary of core code blocks for web search"""
    if not core_blocks:
        return ""
    
    summary_parts = []
    for block in core_blocks:
        # Extract key lines from each block
        lines = block['code'].split('\n')
        key_lines = [line.strip() for line in lines if line.strip() and 
                    not line.strip().startswith(('*', '//', '#', 'import', 'from', 'using'))]
        
        if key_lines:
            # Take first few lines of algorithmic content
            summary_parts.extend(key_lines[:3])
    
    return '\n'.join(summary_parts[:10])  # Max 10 lines total

def check_plagiarism_fallback(content, language, filename=None):
    """Fallback plagiarism check method (original implementation)"""
    logger.info(f"Using fallback plagiarism check for {language} code")
    
    try:
        # Normalize the code for comparison
        normalized_code = normalize_code(content, language)
        
        # Extract meaningful search terms instead of using normalized code
        search_terms = extract_meaningful_search_terms(content, language)
        
        github_matches = []
        first_github_error = None
        github_search_count = 0
        MAX_GITHUB_SEARCHES = 4  # Respect GitHub's code-search API limit (10/min)
        
        # If we have specific search terms, use them
        if search_terms:
            for term in search_terms:
                if github_search_count >= MAX_GITHUB_SEARCHES:
                    break
                github_search_count += 1
                logger.debug(f"Searching GitHub for term: {term}")
                from utils.github_api import search_github_code
                github_results = search_github_code(term, language, max_results=5)
                
                if isinstance(github_results, dict) and 'error' in github_results:
                    error_msg = github_results['error']
                    logger.warning(f"GitHub search error: {error_msg}")
                    if first_github_error is None:
                        first_github_error = error_msg
                    
                    # Stop on rate limits or auth problems
                    if ("rate limit" in error_msg.lower() or "401" in error_msg
                            or "invalid" in error_msg.lower() or "unauthorized" in error_msg.lower()):
                        logger.warning("GitHub search unavailable in fallback check, stopping GitHub searches")
                        break
                    continue
                
                # Calculate similarity for each result
                for result in github_results:
                    try:
                        if 'content' in result:
                            result_normalized = normalize_code(result['content'], language)
                            similarity = calculate_similarity(normalized_code, result_normalized)
                            
                            # Report every match above the floor so the real
                            # percentage shows on the results page
                            if similarity >= GITHUB_MATCH_FLOOR:
                                result['similarity'] = round(similarity, 3)
                                result['similarity_percentage'] = f"{similarity*100:.1f}%"
                                github_matches.append(result)
                                logger.info(f"Found match with {similarity*100:.1f}% similarity")
                    except Exception as e:
                        logger.warning(f"Error processing GitHub result: {str(e)}")
                        continue
        
        # Remove duplicates and sort by similarity
        seen_urls = set()
        unique_matches = []
        for match in github_matches:
            url = match.get('url', '')
            if url not in seen_urls:
                seen_urls.add(url)
                unique_matches.append(match)
        
        # Sort by similarity score (highest first)
        unique_matches.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        
        # Surface GitHub errors on the results page instead of silently showing 0%
        if not unique_matches and first_github_error:
            github_results_out = {"error": f"GitHub search unavailable: {first_github_error}"}
        else:
            github_results_out = unique_matches[:10]
        
        # For web results, use the web_check module
        from utils.web_check import check_web_sources
        web_results = check_web_sources(content, language)
        
        logger.info(f"Fallback plagiarism check completed: {len(unique_matches)} GitHub matches, {len(web_results)} web matches")
        
        return {
            'github': github_results_out,
            'web': web_results,
            'extraction_info': {
                'extraction_successful': False,
                'fallback_used': True
            }
        }
        
    except Exception as e:
        logger.error(f"Error in fallback plagiarism check: {str(e)}")
        return {'github': {"error": f"Plagiarism check error: {str(e)}"}, 'web': []}

def check_web_for_plagiarism(code, language):
    """Check web sources for similar code (placeholder implementation)"""
    # This would typically use a search engine API or custom web scraping
    # For this example, we'll return mock data
    return [
        {
            'source': 'Stack Overflow',
            'url': 'https://stackoverflow.com/questions/1234567',
            'similarity': 0.75,
            'snippet': 'Similar code snippet found on Stack Overflow...'
        }
    ]