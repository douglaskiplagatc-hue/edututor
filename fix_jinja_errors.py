#!/usr/bin/env python3
"""
Jinja2 Template Error Fixer
Scans all template files and fixes common syntax errors
"""

import os
import re
import sys
from pathlib import Path

class TemplateErrorFixer:
    def __init__(self):
        self.errors_found = []
        self.fixes_applied = []
        
    def scan_file(self, filepath):
        """Scan a single file for Jinja2 template errors"""
        with open(filepath, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            
        issues = []
        
        # Check for common Jinja2 errors
        for i, line in enumerate(lines, 1):
            issues.extend(self._check_line_errors(line, i, filepath))
            
        return issues, content
    
    def _check_line_errors(self, line, line_num, filepath):
        """Check a single line for template errors"""
        issues = []
        
        # Pattern 1: Missing closing braces {{ }}
        # Example: {{ variable  or {{ variable without }}
        missing_closing_braces = re.findall(r'\{\{.*?(?=\}\})', line)
        for match in missing_closing_braces:
            if '}}' not in line[match:match+2]:
                issues.append({
                    'type': 'missing_closing_brace',
                    'line': line_num,
                    'text': line.strip(),
                    'suggestion': line.replace('{{', '{{ ') + ' }}'
                })
        
        # Pattern 2: Missing closing tags {% %}
        # Example: {% if condition without endif
        unclosed_tags = re.findall(r'\{%\s*(if|for|block|macro|with)', line)
        for tag in unclosed_tags:
            issues.append({
                'type': 'unclosed_tag',
                'line': line_num,
                'text': line.strip(),
                'suggestion': f"Check that this {tag} has a matching 'end{tag}'"
            })
        
        # Pattern 3: Incorrect print statement syntax
        # Example: {{ "string" + variable }}
        string_concat_errors = re.findall(r'\{\{\s*".*?"\s*\+\s*[^}]+\}\}', line)
        for match in string_concat_errors:
            issues.append({
                'type': 'string_concat_error',
                'line': line_num,
                'text': match,
                'suggestion': match.replace('+', '~') if '+' in match else match
            })
        
        # Pattern 4: Missing quotes around strings
        # Example: {{ url_for(static, filename=style.css) }}
        unquoted_strings = re.findall(r'\b(filename|href|src|class)=([a-zA-Z0-9_.-]+)(?=[\s>}])', line)
        for attr, value in unquoted_strings:
            if not (value.startswith("'") or value.startswith('"')):
                issues.append({
                    'type': 'unquoted_string',
                    'line': line_num,
                    'text': f"{attr}={value}",
                    'suggestion': f'{attr}="{value}"'
                })
        
        # Pattern 5: Wrong filter syntax
        # Example: {{ variable|filter arg }} instead of {{ variable|filter(arg) }}
        wrong_filter_syntax = re.findall(r'\|\s*(\w+)\s+(\w+)', line)
        for filter_name, arg in wrong_filter_syntax:
            issues.append({
                'type': 'wrong_filter_syntax',
                'line': line_num,
                'text': f"|{filter_name} {arg}",
                'suggestion': f"|{filter_name}({arg})"
            })
        
        return issues
    
    def fix_file(self, filepath):
        """Apply fixes to a file"""
        with open(filepath, 'r') as f:
            original_content = f.read()
        
        content = original_content
        
        # Fix 1: Missing closing braces
        content = re.sub(r'(\{\{)([^}]+?)(?=\s*[\n<])', r'\1\2 }}', content)
        
        # Fix 2: Replace + with ~ for string concatenation
        content = re.sub(r'\{\{([^}]+?)\+\s*([^}]+?)\}\}', r'{{\1 ~ \2}}', content)
        
        # Fix 3: Add missing quotes to HTML attributes in Jinja
        content = re.sub(
            r'(\b(?:href|src|filename|class)\s*=\s*)([a-zA-Z0-9_.-]+)(?=[\s>}])',
            r'\1"\2"',
            content
        )
        
        # Fix 4: Fix filter syntax
        content = re.sub(
            r'(\|\s*)(\w+)\s+(\w+)(?=\s*\}\})',
            r'\1\2(\3)',
            content
        )
        
        # Fix 5: Fix missing endif/endfor/endblock
        lines = content.split('\n')
        fixed_lines = []
        stack = []
        
        for i, line in enumerate(lines):
            # Check for opening tags
            if re.search(r'\{%\s*(if|for|block|with)\b', line):
                tag_match = re.search(r'\{%\s*(if|for|block|with)\b', line)
                if tag_match:
                    stack.append(tag_match.group(1))
            
            # Check for closing tags
            elif re.search(r'\{%\s*end(if|for|block|with)\s*%\}', line):
                if stack:
                    stack.pop()
            
            # If we reach end of file with unclosed tags, add them
            if i == len(lines) - 1 and stack:
                for tag in reversed(stack):
                    fixed_lines.append(f'{{% end{tag} %}}')
            
            fixed_lines.append(line)
        
        fixed_content = '\n'.join(fixed_lines)
        
        if fixed_content != original_content:
            with open(filepath, 'w') as f:
                f.write(fixed_content)
            return True, fixed_content
        
        return False, original_content
    
    def find_template_files(self, directory):
        """Find all template files in the directory"""
        template_extensions = ['.html', '.jinja', '.jinja2', '.j2']
        template_files = []
        
        for root, dirs, files in os.walk(directory):
            # Skip virtual environments and hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', 'env', '__pycache__']]
            
            for file in files:
                if any(file.endswith(ext) for ext in template_extensions):
                    template_files.append(os.path.join(root, file))
        
        return template_files
    
    def find_python_files_with_templates(self, directory):
        """Find Python files that might contain template strings"""
        python_files = []
        
        for root, dirs, files in os.walk(directory):
            # Skip virtual environments and hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', 'env', '__pycache__']]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        return python_files
    
    def check_python_file_for_template_strings(self, filepath):
        """Check Python files for template strings that might have errors"""
        with open(filepath, 'r') as f:
            content = f.read()
        
        issues = []
        
        # Look for render_template calls with template strings
        render_template_patterns = [
            r'render_template_string\s*\(\s*["\'](.*?)["\']',
            r'render_template\s*\(\s*["\'](.*?)["\']',
            r'jinja2\.Template\s*\(\s*["\'](.*?)["\']',
        ]
        
        for pattern in render_template_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                # Check the template string for errors
                template_issues = self._check_line_errors(match, 1, filepath)
                for issue in template_issues:
                    issue['context'] = f"Template string in {os.path.basename(filepath)}"
                    issues.append(issue)
        
        return issues
    
    def run(self, directory='.'):
        """Main function to run the scanner"""
        print("=" * 80)
        print("JINJA2 TEMPLATE ERROR SCANNER & FIXER")
        print("=" * 80)
        
        # Scan template files
        print(f"\n🔍 Scanning template files in: {directory}")
        template_files = self.find_template_files(directory)
        
        if not template_files:
            print("No template files found!")
        else:
            print(f"Found {len(template_files)} template files")
            
            for template_file in template_files:
                print(f"\n📄 Checking: {template_file}")
                issues, content = self.scan_file(template_file)
                
                if issues:
                    print(f"   ❌ Found {len(issues)} issue(s):")
                    for issue in issues:
                        print(f"      Line {issue['line']}: {issue['type']}")
                        print(f"      Text: {issue['text'][:50]}...")
                        print(f"      Fix: {issue.get('suggestion', 'Manual check needed')}")
                        print()
                    
                    # Ask to fix
                    fix = input(f"Apply fixes to {template_file}? (y/n): ").lower()
                    if fix == 'y':
                        fixed, new_content = self.fix_file(template_file)
                        if fixed:
                            print(f"      ✅ Fixed {template_file}")
                            self.fixes_applied.append(template_file)
                else:
                    print(f"   ✅ No issues found")
        
        # Scan Python files for template strings
        print(f"\n🔍 Scanning Python files for template strings...")
        python_files = self.find_python_files_with_templates(directory)
        
        for python_file in python_files:
            issues = self.check_python_file_for_template_strings(python_file)
            if issues:
                print(f"\n📄 Issues in {python_file}:")
                for issue in issues:
                    print(f"   {issue['context']}: {issue['type']}")
                    print(f"   Suggestion: {issue.get('suggestion', 'Manual check needed')}")
        
        # Summary
        print("\n" + "=" * 80)
        print("SCAN COMPLETE")
        print("=" * 80)
        
        if self.fixes_applied:
            print(f"\n✅ Fixed {len(self.fixes_applied)} files:")
            for file in self.fixes_applied:
                print(f"   - {file}")
        else:
            print("\n✅ No fixes were applied (or no issues found)")
        
        return len(self.fixes_applied)

# Common Jinja2 Error Patterns and their fixes
COMMON_ERRORS_AND_FIXES = {
    "{{ variable }}": "Correct syntax for variable",
    "{{ variable|default('default') }}": "Correct filter syntax",
    "{% if condition %}": "Correct tag syntax",
    "{% for item in items %}": "Correct for loop syntax",
    "{{ url_for('static', filename='style.css') }}": "Correct url_for with quotes",
    "{{ 'Hello' ~ name }}": "String concatenation with ~",
}

def quick_fix_all(directory='.'):
    """Apply quick fixes to all template files without asking"""
    template_extensions = ['.html', '.jinja', '.jinja2', '.j2']
    
    for root, dirs, files in os.walk(directory):
        # Skip virtual environments
        dirs[:] = [d for d in dirs if d not in ['venv', 'env', '__pycache__', '.git']]
        
        for file in files:
            if any(file.endswith(ext) for ext in template_extensions):
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    content = f.read()
                
                # Apply common fixes
                original = content
                
                # Fix 1: Add missing closing braces
                content = re.sub(r'(\{\{)([^}]+?)(?=\s*[\n<])', r'\1\2 }}', content)
                
                # Fix 2: Fix string concatenation
                content = re.sub(r'\{\{([^}]+?)\+\s*([^}]+?)\}\}', r'{{\1 ~ \2}}', content)
                
                # Fix 3: Fix filter syntax
                content = re.sub(r'(\|\s*)(\w+)\s+(\w+)(?=\s*\}\})', r'\1\2(\3)', content)
                
                # Fix 4: Fix missing quotes in attributes
                content = re.sub(
                    r'(\b(?:href|src|filename|class|rel|type)\s*=\s*)([a-zA-Z0-9_.-]+)(?=[\s>}])',
                    r'\1"\2"',
                    content
                )
                
                # Fix 5: Fix missing endif/endfor
                lines = content.split('\n')
                fixed_lines = []
                tag_stack = []
                
                for line in lines:
                    # Check for opening tags
                    if_match = re.search(r'\{%\s*if\s+(.*?)\s*%\}', line)
                    for_match = re.search(r'\{%\s*for\s+(.*?)\s*%\}', line)
                    block_match = re.search(r'\{%\s*block\s+(.*?)\s*%\}', line)
                    
                    if if_match:
                        tag_stack.append('if')
                    elif for_match:
                        tag_stack.append('for')
                    elif block_match:
                        tag_stack.append('block')
                    
                    # Check for closing tags
                    endif_match = re.search(r'\{%\s*endif\s*%\}', line)
                    endfor_match = re.search(r'\{%\s*endfor\s*%\}', line)
                    endblock_match = re.search(r'\{%\s*endblock\s*%\}', line)
                    
                    if endif_match and 'if' in tag_stack:
                        tag_stack.remove('if')
                    elif endfor_match and 'for' in tag_stack:
                        tag_stack.remove('for')
                    elif endblock_match and 'block' in tag_stack:
                        tag_stack.remove('block')
                    
                    fixed_lines.append(line)
                
                # Add missing closing tags at the end
                for tag in reversed(tag_stack):
                    fixed_lines.append(f'{{% end{tag} %}}')
                
                fixed_content = '\n'.join(fixed_lines)
                
                if fixed_content != original:
                    with open(filepath, 'w') as f:
                        f.write(fixed_content)
                    print(f"✅ Fixed: {filepath}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix Jinja2 template errors')
    parser.add_argument('--dir', default='.', help='Directory to scan (default: current)')
    parser.add_argument('--quick', action='store_true', help='Apply quick fixes without asking')
    
    args = parser.parse_args()
    
    if args.quick:
        print("🚀 Applying quick fixes to all template files...")
        quick_fix_all(args.dir)
        print("\n✅ Quick fixes completed!")
    else:
        fixer = TemplateErrorFixer()
        fixer.run(args.dir)