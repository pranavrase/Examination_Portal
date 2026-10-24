import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def detect_function_pattern(source_code: str) -> Optional[str]:
    """
    Detect if student code uses function-based pattern (e.g., def solution(...))
    and does NOT already read from stdin.
    Returns the function name if wrapping is needed, None otherwise.
    """
    # First check if code already reads from stdin (standard pattern)
    stdin_patterns = [
        r'sys\.stdin\.read',
        r'input\s*\(\s*\)',
        r'scanner\.',
        r'Scanner\s',
        r'cin\s*>>',
        r'getline\s*\(',
        r'readFileSync\s*\(',
    ]
    
    for pattern in stdin_patterns:
        if re.search(pattern, source_code, re.IGNORECASE):
            logger.info("Code already reads from stdin, no wrapping needed")
            return None
    
    # Look for common function patterns that need wrapping
    patterns = [
        r'def\s+solution\s*\(',
        r'def\s+solve\s*\(',
        r'def\s+main\s*\(',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, source_code)
        if match:
            func_name = match.group(0).replace('def ', '').replace('(', '').strip()
            logger.info(f"Detected function-based code with function: {func_name} - wrapping needed")
            return func_name
    
    return None


def wrap_function_code(source_code: str, func_name: str, test_input: str) -> str:
    """
    Wrap function-based student code to read input from stdin and call the function.
    
    For example, if student code is:
        def solution(s):
            return s == s[::-1]
        print(solution("madam"))
    
    The wrapper will transform it to:
        [original student code]
        import sys
        input_data = sys.stdin.read().strip()
        print(solution(input_data))
    """
    # Remove any existing hardcoded print/call statements at the end
    lines = source_code.split('\n')
    wrapped_lines = []
    
    # Keep the function definition part
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip lines that look like hardcoded test calls
        if re.match(r'print\s*\(\s*\w+\s*\(', stripped):
            logger.debug(f"Skipping hardcoded test call: {stripped}")
            continue
        
        wrapped_lines.append(line)
    
    wrapped_code = '\n'.join(wrapped_lines)
    
    # Add wrapper to read from stdin and call function
    # For Python, we need to handle the input appropriately
    wrapper = f"""
import sys

# Read input from stdin
input_data = sys.stdin.read().strip()

# Try to evaluate the input if it looks like a literal
try:
    # Remove quotes if present
    if (input_data.startswith('"') and input_data.endswith('"')) or (input_data.startswith("'") and input_data.endswith("'")):
        input_data = input_data[1:-1]
except:
    pass

# Call the detected function with the input
result = {func_name}(input_data)
print(result)
"""
    
    final_code = wrapped_code + wrapper
    logger.info(f"Wrapped function code for function: {func_name}")
    return final_code


def prepare_code_for_execution(source_code: str, stdin: str) -> Tuple[str, bool]:
    """
    Prepare student code for execution by detecting and wrapping function-based patterns.
    
    Returns:
        Tuple of (prepared_code, was_wrapped)
    """
    func_name = detect_function_pattern(source_code)
    
    if func_name:
        # Function-based code detected - wrap it
        logger.info(f"Function-based code detected, wrapping for function: {func_name}")
        wrapped_code = wrap_function_code(source_code, func_name, stdin)
        return wrapped_code, True
    else:
        # Standard stdin/stdout code - use as-is
        logger.info("Standard stdin/stdout code detected, using as-is")
        return source_code, False


def sanitize_input_for_eval(input_str: str) -> str:
    """
    Sanitize input string for safe evaluation in function calls.
    For strings, add quotes if needed.
    """
    input_str = input_str.strip()
    
    # If input looks like a string literal (has quotes), use as-is
    if (input_str.startswith('"') and input_str.endswith('"')) or \
       (input_str.startswith("'") and input_str.endswith("'")):
        return input_str[1:-1]  # Remove quotes for processing
    
    # If input is numeric, return as-is
    try:
        int(input_str)
        return input_str
    except ValueError:
        pass
    
    try:
        float(input_str)
        return input_str
    except ValueError:
        pass
    
    # Otherwise treat as string
    return input_str