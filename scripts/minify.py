#!/usr/bin/env python3
"""
Simple minification script for CSS and JavaScript files.
Removes comments and unnecessary whitespace for production deployment.
"""

import re
import os
import sys

def minify_css(content):
    """Minify CSS by removing comments and unnecessary whitespace."""
    # Remove CSS comments /* */
    content = re.sub(r'/\*[\s\S]*?\*/', '', content)

    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in content.split('\n')]
    content = ' '.join(lines)

    # Remove whitespace around special characters
    content = re.sub(r'\s*([{};:,>+~])\s*', r'\1', content)

    # Remove whitespace before/after braces
    content = re.sub(r'\s*\{\s*', '{', content)
    content = re.sub(r'\s*\}\s*', '}', content)

    # Collapse multiple spaces
    content = re.sub(r'\s+', ' ', content)

    # Remove space after colons in properties (but keep space in selectors)
    content = re.sub(r':\s+', ':', content)

    # Remove trailing semicolons before closing braces
    content = re.sub(r';}', '}', content)

    return content.strip()


def minify_js(content):
    """Minify JavaScript by removing comments and collapsing whitespace."""
    # Remove single-line comments (but not URLs with //)
    # Be careful not to remove // inside strings
    lines = content.split('\n')
    result_lines = []

    in_multiline_comment = False

    for line in lines:
        # Handle multi-line comments
        if in_multiline_comment:
            if '*/' in line:
                line = line[line.index('*/') + 2:]
                in_multiline_comment = False
            else:
                continue

        # Remove /* */ comments on single line
        line = re.sub(r'/\*.*?\*/', '', line)

        # Check for start of multi-line comment
        if '/*' in line:
            line = line[:line.index('/*')]
            in_multiline_comment = True

        # Remove single-line comments (careful with strings and URLs)
        # Simple approach: remove // comments only if not inside a string
        # This is imperfect but works for most cases
        if '//' in line:
            # Find // that's not inside a string
            in_string = False
            string_char = None
            new_line = []
            i = 0
            while i < len(line):
                char = line[i]
                if not in_string:
                    if char in '"\'`':
                        in_string = True
                        string_char = char
                        new_line.append(char)
                    elif char == '/' and i + 1 < len(line) and line[i + 1] == '/':
                        # Found comment, stop here
                        break
                    else:
                        new_line.append(char)
                else:
                    new_line.append(char)
                    if char == string_char and (i == 0 or line[i-1] != '\\'):
                        in_string = False
                i += 1
            line = ''.join(new_line)

        line = line.rstrip()
        if line:
            result_lines.append(line)

    content = '\n'.join(result_lines)

    # Collapse multiple newlines to single
    content = re.sub(r'\n\s*\n', '\n', content)

    # Remove leading whitespace from lines (preserving string contents)
    # This is a simplified approach
    lines = content.split('\n')
    content = '\n'.join(line.strip() for line in lines if line.strip())

    return content


def minify_file(input_path, output_path=None):
    """Minify a file based on its extension."""
    if output_path is None:
        name, ext = os.path.splitext(input_path)
        output_path = f"{name}.min{ext}"

    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_size = len(content)

    if input_path.endswith('.css'):
        minified = minify_css(content)
    elif input_path.endswith('.js'):
        minified = minify_js(content)
    else:
        print(f"Unknown file type: {input_path}")
        return None

    minified_size = len(minified)
    reduction = (1 - minified_size / original_size) * 100

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(minified)

    print(f"{os.path.basename(input_path)}: {original_size:,} → {minified_size:,} bytes ({reduction:.1f}% reduction)")
    return output_path


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.join(script_dir, '..')

    print("Minifying assets for production...\n")

    # Minify CSS
    css_path = os.path.join(root_dir, 'styles.css')
    css_min_path = os.path.join(root_dir, 'styles.min.css')
    minify_file(css_path, css_min_path)

    # Minify JS
    js_path = os.path.join(root_dir, 'script.js')
    js_min_path = os.path.join(root_dir, 'script.min.js')
    minify_file(js_path, js_min_path)

    print("\nMinified files created. To use in production:")
    print("  - Replace styles.css with styles.min.css")
    print("  - Replace script.js with script.min.js")


if __name__ == '__main__':
    main()
