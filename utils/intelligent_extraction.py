import ast
import re
import logging
from typing import List, Dict, Optional, Tuple

from config import Config

logger = logging.getLogger(__name__)

class IntelligentCodeExtractor:
    """
    Intelligent code extraction that focuses on algorithmic content
    by extracting only functions, classes, and core logic while skipping
    comments, imports, and boilerplate code.
    """
    
    def __init__(self):
        self.extracted_blocks = []
        
    def extract_core_code(self, code_content: str, language: str) -> Dict[str, any]:
        """
        Main extraction method that returns only the algorithmic core of code
        
        Args:
            code_content (str): The raw code content
            language (str): Programming language
            
        Returns:
            dict: Extracted core code blocks with metadata
        """
        try:
            logger.info(f"Starting intelligent code extraction for {language}")

            # AST parsing and regex extraction are super-linear in source size.
            # Cap what we extract from so a giant upload can't balloon memory
            # (real code files are almost always well under this limit).
            if len(code_content) > Config.EXTRACT_MAX_SOURCE_CHARS:
                logger.warning(f"Truncating {len(code_content)} chars of source to {Config.EXTRACT_MAX_SOURCE_CHARS} for extraction")
                code_content = code_content[:Config.EXTRACT_MAX_SOURCE_CHARS]

            if language == 'python':
                return self._extract_python_core(code_content)
            elif language in ['javascript', 'typescript']:
                return self._extract_js_core(code_content)
            elif language == 'java':
                return self._extract_java_core(code_content)
            elif language in ['c', 'cpp']:
                return self._extract_c_cpp_core(code_content)
            elif language == 'csharp':
                return self._extract_csharp_core(code_content)
            else:
                return self._extract_generic_core(code_content)
                
        except Exception as e:
            logger.error(f"Error in intelligent code extraction: {str(e)}")
            # Fallback to simple extraction
            return self._fallback_extraction(code_content, language)
    
    def _extract_python_core(self, code: str) -> Dict[str, any]:
        """Extract core Python code using AST parsing"""
        try:
            tree = ast.parse(code)
            core_blocks = []
            
            # Extract functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_code = ast.unparse(node)
                    core_blocks.append({
                        'type': 'function',
                        'name': node.name,
                        'code': func_code,
                        'line_start': node.lineno,
                        'complexity': self._calculate_complexity(func_code)
                    })
                
                elif isinstance(node, ast.ClassDef):
                    # Extract only methods from classes, not the entire class
                    class_methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_code = ast.unparse(item)
                            class_methods.append({
                                'type': 'method',
                                'name': f"{node.name}.{item.name}",
                                'code': method_code,
                                'line_start': item.lineno,
                                'complexity': self._calculate_complexity(method_code)
                            })
                    core_blocks.extend(class_methods)
                
                elif isinstance(node, (ast.For, ast.While, ast.If)) and node.lineno:
                    # Extract algorithmic constructs that are not inside functions
                    if self._is_top_level_logic(node, tree):
                        logic_code = ast.unparse(node)
                        core_blocks.append({
                            'type': 'logic',
                            'name': f"logic_block_{node.lineno}",
                            'code': logic_code,
                            'line_start': node.lineno,
                            'complexity': self._calculate_complexity(logic_code)
                        })
            
            return self._format_extraction_result(core_blocks, 'python')
            
        except Exception as e:
            logger.warning(f"AST parsing failed for Python code: {str(e)}")
            return self._extract_python_regex(code)
    
    def _extract_js_core(self, code: str) -> Dict[str, any]:
        """Extract core JavaScript/TypeScript code using regex patterns"""
        core_blocks = []
        
        # Remove comments first
        code_clean = self._remove_js_comments(code)
        
        # Extract function declarations
        func_pattern = r'function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}'
        for match in re.finditer(func_pattern, code_clean, re.MULTILINE | re.DOTALL):
            func_name = match.group(1)
            func_code = match.group(0)
            core_blocks.append({
                'type': 'function',
                'name': func_name,
                'code': func_code.strip(),
                'line_start': code[:match.start()].count('\n') + 1,
                'complexity': self._calculate_complexity(func_code)
            })
        
        # Extract arrow functions
        arrow_pattern = r'(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:\([^)]*\)|[a-zA-Z_$][a-zA-Z0-9_$]*)\s*=>\s*(?:\{[^}]*(?:\{[^}]*\}[^}]*)*\}|[^;,\n]+)'
        for match in re.finditer(arrow_pattern, code_clean, re.MULTILINE | re.DOTALL):
            func_name = match.group(1)
            func_code = match.group(0)
            core_blocks.append({
                'type': 'arrow_function',
                'name': func_name,
                'code': func_code.strip(),
                'line_start': code[:match.start()].count('\n') + 1,
                'complexity': self._calculate_complexity(func_code)
            })
        
        # Extract class methods
        class_pattern = r'class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*(?:extends\s+[a-zA-Z_$][a-zA-Z0-9_$]*)?\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        for match in re.finditer(class_pattern, code_clean, re.MULTILINE | re.DOTALL):
            class_name = match.group(1)
            class_body = match.group(2)
            
            # Extract methods from class body
            method_pattern = r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\([^)]*\)\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}'
            for method_match in re.finditer(method_pattern, class_body, re.MULTILINE | re.DOTALL):
                method_name = method_match.group(1)
                method_code = method_match.group(0)
                core_blocks.append({
                    'type': 'method',
                    'name': f"{class_name}.{method_name}",
                    'code': method_code.strip(),
                    'line_start': code[:match.start() + method_match.start()].count('\n') + 1,
                    'complexity': self._calculate_complexity(method_code)
                })
        
        return self._format_extraction_result(core_blocks, 'javascript')
    
    def _extract_java_core(self, code: str) -> Dict[str, any]:
        """Extract core Java code"""
        core_blocks = []
        
        # Remove comments
        code_clean = self._remove_java_comments(code)
        
        # Extract methods (public, private, protected, static)
        method_pattern = r'(?:public|private|protected)?\s*(?:static)?\s*(?:final)?\s*(?:[a-zA-Z_][a-zA-Z0-9_<>\[\]]*\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*(?:throws\s+[a-zA-Z0-9_,\s]+)?\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}'
        for match in re.finditer(method_pattern, code_clean, re.MULTILINE | re.DOTALL):
            method_name = match.group(1)
            # Skip constructors and common getters/setters
            if not self._is_java_boilerplate_method(method_name, match.group(0)):
                core_blocks.append({
                    'type': 'method',
                    'name': method_name,
                    'code': match.group(0).strip(),
                    'line_start': code[:match.start()].count('\n') + 1,
                    'complexity': self._calculate_complexity(match.group(0))
                })
        
        # Extract inner classes (non-boilerplate)
        class_pattern = r'(?:public|private|protected)?\s*(?:static)?\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:extends\s+[a-zA-Z_][a-zA-Z0-9_]*\s*)?(?:implements\s+[a-zA-Z0-9_,\s]+\s*)?\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
        for match in re.finditer(class_pattern, code_clean, re.MULTILINE | re.DOTALL):
            class_name = match.group(1)
            if not self._is_java_boilerplate_class(class_name):
                core_blocks.append({
                    'type': 'class',
                    'name': class_name,
                    'code': match.group(0).strip(),
                    'line_start': code[:match.start()].count('\n') + 1,
                    'complexity': self._calculate_complexity(match.group(0))
                })
        
        return self._format_extraction_result(core_blocks, 'java')
    
    def _extract_c_cpp_core(self, code: str) -> Dict[str, any]:
        """Extract core C/C++ code"""
        core_blocks = []
        
        # Remove comments
        code_clean = self._remove_c_comments(code)
        
        # Extract function definitions
        func_pattern = r'(?:static\s+)?(?:inline\s+)?(?:[a-zA-Z_][a-zA-Z0-9_]*\s+)*([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}'
        for match in re.finditer(func_pattern, code_clean, re.MULTILINE | re.DOTALL):
            func_name = match.group(1)
            # Skip main function and common boilerplate
            if func_name not in ['main', 'printf', 'scanf'] and not func_name.startswith('_'):
                core_blocks.append({
                    'type': 'function',
                    'name': func_name,
                    'code': match.group(0).strip(),
                    'line_start': code[:match.start()].count('\n') + 1,
                    'complexity': self._calculate_complexity(match.group(0))
                })
        
        # Extract class definitions (C++)
        class_pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?::\s*(?:public|private|protected)\s+[a-zA-Z_][a-zA-Z0-9_]*\s*)?\{[^}]*(?:\{[^}]*\}[^}]*)*\}'
        for match in re.finditer(class_pattern, code_clean, re.MULTILINE | re.DOTALL):
            class_name = match.group(1)
            core_blocks.append({
                'type': 'class',
                'name': class_name,
                'code': match.group(0).strip(),
                'line_start': code[:match.start()].count('\n') + 1,
                'complexity': self._calculate_complexity(match.group(0))
            })
        
        return self._format_extraction_result(core_blocks, 'cpp')
    
    def _extract_csharp_core(self, code: str) -> Dict[str, any]:
        """Extract core C# code"""
        core_blocks = []
        
        # Remove comments
        code_clean = self._remove_csharp_comments(code)
        
        # Extract method definitions
        method_pattern = r'(?:public|private|protected|internal)?\s*(?:static)?\s*(?:virtual|override)?\s*(?:[a-zA-Z_][a-zA-Z0-9_<>\[\]]*\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}'
        for match in re.finditer(method_pattern, code_clean, re.MULTILINE | re.DOTALL):
            method_name = match.group(1)
            if not self._is_csharp_boilerplate_method(method_name, match.group(0)):
                core_blocks.append({
                    'type': 'method',
                    'name': method_name,
                    'code': match.group(0).strip(),
                    'line_start': code[:match.start()].count('\n') + 1,
                    'complexity': self._calculate_complexity(match.group(0))
                })
        
        return self._format_extraction_result(core_blocks, 'csharp')
    
    def _extract_generic_core(self, code: str) -> Dict[str, any]:
        """Generic extraction for unsupported languages"""
        # Remove common comment patterns
        code_clean = re.sub(r'#.*?$', '', code, flags=re.MULTILINE)  # Shell-style comments
        code_clean = re.sub(r'//.*?$', '', code_clean, flags=re.MULTILINE)  # C-style comments
        code_clean = re.sub(r'/\*.*?\*/', '', code_clean, flags=re.DOTALL)  # Multi-line C-style
        
        # Split into logical blocks
        blocks = []
        lines = code_clean.split('\n')
        current_block = []
        
        for line in lines:
            line = line.strip()
            if line:
                current_block.append(line)
            elif current_block:
                if len(current_block) > 2:  # Only blocks with substantial content
                    block_code = '\n'.join(current_block)
                    blocks.append({
                        'type': 'code_block',
                        'name': f"block_{len(blocks)}",
                        'code': block_code,
                        'line_start': len(blocks) + 1,
                        'complexity': self._calculate_complexity(block_code)
                    })
                current_block = []
        
        return self._format_extraction_result(blocks, 'generic')
    
    def _extract_python_regex(self, code: str) -> Dict[str, any]:
        """Fallback Python extraction using regex"""
        core_blocks = []
        
        # Remove comments and docstrings
        code_clean = re.sub(r'#.*?$', '', code, flags=re.MULTILINE)
        code_clean = re.sub(r'""".*?"""', '', code_clean, flags=re.DOTALL)
        code_clean = re.sub(r"'''.*?'''", '', code_clean, flags=re.DOTALL)
        
        # Extract function definitions
        func_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\):[^def]*?(?=\ndef|\nclass|\Z)'
        for match in re.finditer(func_pattern, code_clean, re.MULTILINE | re.DOTALL):
            func_name = match.group(1)
            if func_name not in ['__init__', '__str__', '__repr__']:  # Skip boilerplate
                core_blocks.append({
                    'type': 'function',
                    'name': func_name,
                    'code': match.group(0).strip(),
                    'line_start': code[:match.start()].count('\n') + 1,
                    'complexity': self._calculate_complexity(match.group(0))
                })
        
        return self._format_extraction_result(core_blocks, 'python')
    
    # Helper methods
    def _remove_js_comments(self, code: str) -> str:
        """Remove JavaScript/TypeScript comments"""
        # Remove single-line comments
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        # Remove multi-line comments
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        return code
    
    def _remove_java_comments(self, code: str) -> str:
        """Remove Java comments"""
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        return code
    
    def _remove_c_comments(self, code: str) -> str:
        """Remove C/C++ comments"""
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        return code
    
    def _remove_csharp_comments(self, code: str) -> str:
        """Remove C# comments"""
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code = re.sub(r'///.*?$', '', code, flags=re.MULTILINE)  # XML docs
        return code
    
    def _calculate_complexity(self, code: str) -> int:
        """Simple complexity calculation based on control structures"""
        complexity = 1  # Base complexity
        
        # Count control structures
        complexity += len(re.findall(r'\bif\b', code, re.IGNORECASE))
        complexity += len(re.findall(r'\bfor\b', code, re.IGNORECASE))
        complexity += len(re.findall(r'\bwhile\b', code, re.IGNORECASE))
        complexity += len(re.findall(r'\bcatch\b', code, re.IGNORECASE))
        complexity += len(re.findall(r'\bswitch\b', code, re.IGNORECASE))
        
        return complexity
    
    def _is_top_level_logic(self, node, tree) -> bool:
        """Check if a node is top-level logic (not inside a function)"""
        # This is a simplified check - in practice, you'd walk up the AST
        return True  # For now, include all logic blocks
    
    def _is_java_boilerplate_method(self, method_name: str, code: str) -> bool:
        """Check if Java method is boilerplate (getter/setter/constructor)"""
        boilerplate_patterns = [
            r'get[A-Z]',  # getters
            r'set[A-Z]',  # setters
            r'toString',
            r'equals',
            r'hashCode'
        ]
        
        for pattern in boilerplate_patterns:
            if re.match(pattern, method_name):
                return True
        
        # Check if it's a simple getter/setter by code content
        if ('return' in code and len(code.split('\n')) < 5) or \
           ('this.' in code and '=' in code and len(code.split('\n')) < 5):
            return True
        
        return False
    
    def _is_java_boilerplate_class(self, class_name: str) -> bool:
        """Check if Java class is boilerplate"""
        boilerplate_names = ['Main', 'Test', 'Example', 'Demo']
        return class_name in boilerplate_names
    
    def _is_csharp_boilerplate_method(self, method_name: str, code: str) -> bool:
        """Check if C# method is boilerplate"""
        boilerplate_patterns = [
            r'get_[A-Z]',  # property getters
            r'set_[A-Z]',  # property setters
            r'ToString',
            r'Equals',
            r'GetHashCode'
        ]
        
        for pattern in boilerplate_patterns:
            if re.match(pattern, method_name):
                return True
        
        return False
    
    def _format_extraction_result(self, core_blocks: List[Dict], language: str) -> Dict[str, any]:
        """Format the extraction result"""
        # Sort blocks by complexity (most complex first)
        core_blocks.sort(key=lambda x: x.get('complexity', 0), reverse=True)

        # Bound memory: cap the number of blocks and the size of each block so
        # minified/obfuscated files can't produce huge retained blocks.
        core_blocks = core_blocks[:Config.MAX_EXTRACTED_BLOCKS]
        for block in core_blocks:
            if len(block['code']) > Config.MAX_EXTRACTED_BLOCK_CHARS:
                block['code'] = block['code'][:Config.MAX_EXTRACTED_BLOCK_CHARS]

        # Create summary
        total_blocks = len(core_blocks)
        total_lines = sum(block['code'].count('\n') + 1 for block in core_blocks)
        avg_complexity = sum(block.get('complexity', 0) for block in core_blocks) / max(total_blocks, 1)
        
        return {
            'language': language,
            'core_blocks': core_blocks,
            'summary': {
                'total_blocks': total_blocks,
                'total_core_lines': total_lines,
                'average_complexity': round(avg_complexity, 2),
                'block_types': list(set(block['type'] for block in core_blocks))
            },
            'extraction_success': True
        }
    
    def _fallback_extraction(self, code: str, language: str) -> Dict[str, any]:
        """Fallback when intelligent extraction fails"""
        logger.warning(f"Using fallback extraction for {language}")
        
        # Simple fallback: just remove comments and empty lines
        lines = code.split('\n')
        core_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Skip empty lines and common comment patterns
            if stripped and not stripped.startswith(('#', '//', '/*', '*', 'import ', 'from ', 'using ', '#include')):
                core_lines.append(line)
        
        fallback_code = '\n'.join(core_lines)

        # Bound the fallback block size too (same memory reason as above)
        if len(fallback_code) > Config.MAX_EXTRACTED_BLOCK_CHARS:
            fallback_code = fallback_code[:Config.MAX_EXTRACTED_BLOCK_CHARS]

        return {
            'language': language,
            'core_blocks': [{
                'type': 'fallback',
                'name': 'extracted_core',
                'code': fallback_code,
                'line_start': 1,
                'complexity': self._calculate_complexity(fallback_code)
            }],
            'summary': {
                'total_blocks': 1,
                'total_core_lines': len(core_lines),
                'average_complexity': self._calculate_complexity(fallback_code),
                'block_types': ['fallback']
            },
            'extraction_success': False,
            'fallback_used': True
        }

# Convenience function for easy integration
def extract_core_code(code_content: str, language: str) -> Dict[str, any]:
    """
    Extract core algorithmic content from code
    
    Args:
        code_content (str): Raw code content
        language (str): Programming language
    
    Returns:
        dict: Extracted core code with metadata
    """
    extractor = IntelligentCodeExtractor()
    return extractor.extract_core_code(code_content, language)