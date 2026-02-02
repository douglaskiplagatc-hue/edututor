#!/usr/bin/env python3
"""
Enhanced Jinja2 Template Fixer
Handles specific error patterns and provides manual fixes
"""

import os
import re
import shutil
from datetime import datetime

class EnhancedJinjaFixer:
    def __init__(self):
        self.backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.fixed_files = []
        self.unfixable_errors = []
        
    def backup_file(self, filepath):
        """Create backup of original file"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        rel_path = os.path.relpath(filepath)
        backup_path = os.path.join(self.backup_dir, rel_path)
        
        # Create parent directories in backup
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(filepath, backup_path)
        return backup_path

    def fix_string_concatenation(self, content):
        """Fix string concatenation errors (most common)"""
        patterns = [
            # Pattern: {{ "string" + variable }}
            (r'\{\{\s*"([^"]+)"\s*\+\s*([^}]+)\}\}', r'{{ "\1" ~ \2 }}'),
            (r"\{\{\s*'([^']+)'\s*\+\s*([^}]+)\}\}", r"{{ '\1' ~ \2 }}"),
            
            # Pattern: {{ variable + "string" }}
            (r'\{\{\s*([^}]+?)\s*\+\s*"([^"]+)"\s*\}\}', r'{{ \1 ~ "\2" }}'),
            (r"\{\{\s*([^}]+?)\s*\+\s*'([^']+)'\s*\}\}", r"{{ \1 ~ '\2' }}"),
            
            # Pattern: {{ "string1" + "string2" }} (just remove +)
            (r'\{\{\s*"([^"]+)"\s*\+\s*"([^"]+)"\s*\}\}', r'{{ "\1\2" }}'),
            (r"\{\{\s*'([^']+)'\s*\+\s*'([^']+)'\s*\}\}", r"{{ '\1\2' }}"),
            
            # Pattern: multiple concatenations
            (r'(\{\{[^}]+\})\s*\+\s*(\{\{[^}]+\}\})', r'\1 ~ \2'),
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        return content

    def fix_missing_braces(self, content):
        """Fix missing closing braces"""
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Count opening and closing braces
            open_braces = line.count('{{')
            close_braces = line.count('}}')
            
            if open_braces > close_braces:
                # Add missing closing braces
                missing = open_braces - close_braces
                line = line + ' }}' * missing
            
            # Also check for {% %}
            open_tags = line.count('{%')
            close_tags = line.count('%}')
            
            if open_tags > close_tags:
                line = line + ' %}'
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

    def fix_url_for_syntax(self, content):
        """Fix url_for syntax errors"""
        # Fix missing quotes in filename parameter
        content = re.sub(
            r'url_for\(\s*[\'"][^"\']*[\'"]\s*,\s*filename\s*=\s*([a-zA-Z0-9_.-]+)(?=[\s,)])',
            r"url_for('\1', filename='\2'",
            content
        )
        
        # Fix missing quotes in endpoint
        content = re.sub(
            r'url_for\(\s*([a-zA-Z0-9_.-]+)(?:\s*,\s*filename\s*=)',
            r"url_for('\1', filename=",
            content
        )
        
        return content

    def fix_filter_syntax(self, content):
        """Fix filter syntax errors"""
        # Fix: |filter arg to |filter(arg)
        content = re.sub(
            r'\|\s*(\w+)\s+(\w+)(?=\s*\}\})',
            r'|\1(\2)',
            content
        )
        
        # Fix: |filter(arg1, arg2) to |filter(arg1, arg2)
        content = re.sub(
            r'\|\s*(\w+)\(\s*([^),]+)\s*,\s*([^)]+)\s*\)',
            r'|\1(\2, \3)',
            content
        )
        
        return content

    def fix_complex_expressions(self, content):
        """Fix complex expressions with operators"""
        # Fix arithmetic operations that should be in parentheses
        patterns = [
            # Fix: {{ a + b * c }} -> {{ (a + b * c) }}
            (r'\{\{\s*([a-zA-Z_][\w\.]*\s*[+\-*/]\s*[^}]+)\}\}', r'{{ (\1) }}'),
            
            # Fix comparisons: {{ a > b }} is OK, but {{ a > b and c }} needs parens
            (r'\{\{\s*([^}]*?\b(?:and|or|not)\b[^}]*)\}\}', r'{{ (\1) }}'),
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        return content

    def fix_html_in_jinja(self, content):
        """Fix HTML attributes inside Jinja expressions"""
        # Fix: {{ <tag attr=value> }} -> {{ '<tag attr="value">' }}
        content = re.sub(
            r'\{\{\s*<([a-zA-Z][a-zA-Z0-9]*)\s+([^>]+)>\s*\}\}',
            r'{{ \'<\1 \2>\' }}',
            content
        )
        
        # Fix missing quotes in HTML attributes
        content = re.sub(
            r'(\b(?:class|id|name|type|value|placeholder)\s*=\s*)([a-zA-Z0-9_-]+)(?=[\s>])',
            r'\1"\2"',
            content
        )
        
        return content

    def fix_block_structure(self, content):
        """Fix block/if/for structure issues"""
        lines = content.split('\n')
        fixed_lines = []
        block_stack = []
        
        for i, line in enumerate(lines):
            # Check for block starts
            block_match = re.search(r'\{%\s*(block|if|for|macro|with|set)\s+([^%]+)\s*%\}', line)
            if block_match:
                block_type = block_match.group(1)
                block_stack.append((block_type, i))
            
            # Check for block ends
            end_match = re.search(r'\{%\s*end(block|if|for|macro|with|set)\s*%\}', line)
            if end_match:
                if block_stack:
                    block_stack.pop()
            
            # If we have mismatched blocks at end of file
            if i == len(lines) - 1 and block_stack:
                for block_type, _ in reversed(block_stack):
                    fixed_lines.append(f'{{% end{block_type} %}}')
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

    def fix_specific_error(self, error_type, line_content):
        """Apply specific fixes based on error type"""
        fixes = {
            'string_concat': lambda x: x.replace('+', '~'),
            'missing_brace': lambda x: x + ' }}' if '{{' in x and '}}' not in x else x,
            'unquoted_string': lambda x: re.sub(r'(\w+)\s*=\s*(\w+)', r'\1="\2"', x),
            'wrong_filter': lambda x: re.sub(r'\|(\w+)\s+(\w+)', r'|\1(\2)', x),
            'url_for_quotes': lambda x: re.sub(r'filename=(\w+)', r"filename='\1'", x),
        }
        
        if error_type in fixes:
            return fixes[error_type](line_content)
        return line_content

    def analyze_and_fix_file(self, filepath, auto_fix=True):
        """Analyze file and apply fixes"""
        print(f"\n📁 Analyzing: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Create backup
        backup_path = self.backup_file(filepath)
        print(f"   📦 Backup created: {backup_path}")
        
        # Apply all fixes
        content = original_content
        
        fixes_applied = []
        
        # Apply fixes in sequence
        original_len = len(content)
        
        content = self.fix_string_concatenation(content)
        if len(content) != original_len:
            fixes_applied.append("String concatenation")
        
        content = self.fix_missing_braces(content)
        if len(content) != original_len:
            fixes_applied.append("Missing braces")
        
        content = self.fix_url_for_syntax(content)
        if len(content) != original_len:
            fixes_applied.append("URL syntax")
        
        content = self.fix_filter_syntax(content)
        if len(content) != original_len:
            fixes_applied.append("Filter syntax")
        
        content = self.fix_complex_expressions(content)
        if len(content) != original_len:
            fixes_applied.append("Complex expressions")
        
        content = self.fix_html_in_jinja(content)
        if len(content) != original_len:
            fixes_applied.append("HTML in Jinja")
        
        content = self.fix_block_structure(content)
        if len(content) != original_len:
            fixes_applied.append("Block structure")
        
        # Check if content changed
        if content != original_content:
            if auto_fix:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.fixed_files.append((filepath, fixes_applied))
                print(f"   ✅ Fixed: {', '.join(fixes_applied)}")
            else:
                print(f"   🔧 Would fix: {', '.join(fixes_applied)}")
                print(f"   Use --apply to actually fix")
        else:
            print(f"   ✓ No auto-fixes available for this file")
            
            # Show lines that might need manual fixes
            self.find_unfixable_patterns(filepath, original_content)
        
        return content

    def find_unfixable_patterns(self, filepath, content):
        """Find patterns that need manual fixing"""
        lines = content.split('\n')
        problematic_lines = []
        
        for i, line in enumerate(lines, 1):
            # Complex nested expressions
            if re.search(r'\{\{.*\{.*\}.*\}\}', line):
                problematic_lines.append((i, line, "Nested Jinja expressions need manual review"))
            
            # Multiple statements in one tag
            if re.search(r'\{%.*;.*%\}', line):
                problematic_lines.append((i, line, "Multiple statements in one tag - split them"))
            
            # Jinja in JavaScript/JSON
            if re.search(r'<script.*>\s*\{%', line, re.DOTALL):
                problematic_lines.append((i, line, "Jinja in script tags needs escaping"))
            
            # Complex string operations
            if line.count('"') > 4 or line.count("'") > 4:
                if '{{' in line and '}}' in line:
                    problematic_lines.append((i, line, "Complex string operations need review"))
        
        if problematic_lines:
            print(f"   ⚠️  Lines needing manual attention:")
            for line_num, line_text, issue in problematic_lines:
                print(f"      Line {line_num}: {issue}")
                print(f"      Code: {line_text[:60]}...")

    def scan_directory(self, directory, auto_fix=False):
        """Scan directory and fix templates"""
        template_extensions = ['.html', '.jinja', '.jinja2', '.j2']
        
        for root, dirs, files in os.walk(directory):
            # Skip virtual environments
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', 'env', '__pycache__', 'backup']]
            
            for file in files:
                if any(file.endswith(ext) for ext in template_extensions):
                    filepath = os.path.join(root, file)
                    self.analyze_and_fix_file(filepath, auto_fix)
        
        self.print_summary()

    def print_summary(self):
        """Print summary of fixes"""
        print("\n" + "="*80)
        print("FIXING SUMMARY")
        print("="*80)
        
        if self.fixed_files:
            print(f"\n✅ Successfully fixed {len(self.fixed_files)} files:")
            for filepath, fixes in self.fixed_files:
                print(f"   {filepath}")
                print(f"      Applied: {', '.join(fixes)}")
        else:
            print("\n⚠️  No files were automatically fixed.")
            print("   Some errors require manual fixing. See suggestions above.")
        
        if os.path.exists(self.backup_dir):
            print(f"\n📦 Backups saved in: {self.backup_dir}")
            print("   You can restore originals if needed.")

def manual_fixes_guide():
    """Print manual fixes guide for common unfixable errors"""
    print("\n" + "="*80)
    print("MANUAL FIXES GUIDE")
    print("="*80)
    
    guide = """
    COMMON UNFIXABLE ERRORS AND MANUAL FIXES:

    1. NESTED EXPRESSIONS:
       ❌ Wrong: {{ {{ variable }} }}
       ✅ Fixed: {{ variable }}

    2. JINJA IN JAVASCRIPT:
       ❌ Wrong: <script>var x = {{ value }};</script>
       ✅ Fixed: <script>var x = {{ value|tojson|safe }};</script>

    3. MULTIPLE STATEMENTS:
       ❌ Wrong: {% if a %}Text{% else %}Other{% endif %} {{ var }}
       ✅ Fixed: {% if a %}Text{% else %}Other{% endif %}\n{{ var }}

    4. COMPLEX FILTER CHAINS:
       ❌ Wrong: {{ var|filter1|filter2 arg }}
       ✅ Fixed: {{ var|filter1|filter2(arg) }}

    5. CONDITIONAL ATTRIBUTES:
       ❌ Wrong: <div {% if condition %}class="active"{% endif %}>
       ✅ Fixed: <div{% if condition %} class="active"{% endif %}>

    6. LINE CONTINUATIONS:
       ❌ Wrong: {{ very_long_variable_name +
                  another_variable }}
       ✅ Fixed: {{ (very_long_variable_name +
                  another_variable) }}

    7. MIXED CONTENT:
       ❌ Wrong: <p>Hello {{ name }}, welcome to {{ site }}!</p>
       ✅ Fixed: <p>Hello {{ name }}, welcome to {{ site }}!</p>
       Note: This is actually correct. The fixer might flag it unnecessarily.

    TIPS:
    - Use Jinja2's |safe filter for HTML content
    - Use |tojson for JavaScript variables
    - Break complex expressions into multiple lines
    - Use parentheses for complex operations
    - Test with a Jinja2 validator after fixing
    """
    print(guide)

def interactive_fixer():
    """Interactive fixer with step-by-step guidance"""
    print("🔧 INTERACTIVE JINJA2 FIXER")
    print("-" * 40)
    
    filepath = input("Enter template file path: ").strip()
    
    if not os.path.exists(filepath):
        print("❌ File not found!")
        return
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        if '{{' in line or '{%' in line:
            print(f"\nLine {i}: {line[:80]}...")
            
            # Check for common errors
            if '+' in line and '{{' in line:
                fix = input(f"  Found '+' in Jinja expression. Replace with '~'? (y/n): ")
                if fix.lower() == 'y':
                    lines[i-1] = line.replace('+', '~')
                    print(f"  ✅ Fixed line {i}")
            
            if 'url_for' in line and 'filename=' in line:
                if not re.search(r"filename=['\"]", line):
                    fix = input(f"  Missing quotes in url_for filename. Add quotes? (y/n): ")
                    if fix.lower() == 'y':
                        lines[i-1] = re.sub(r'filename=(\w+)', r"filename='\1'", line)
                        print(f"  ✅ Fixed line {i}")
    
    # Save changes
    save = input(f"\nSave changes to {filepath}? (y/n): ")
    if save.lower() == 'y':
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
        print(f"✅ File saved!")
    else:
        print("❌ Changes discarded.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Jinja2 Template Fixer')
    parser.add_argument('--dir', default='.', help='Directory to scan')
    parser.add_argument('--apply', action='store_true', help='Apply fixes (otherwise dry run)')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    parser.add_argument('--guide', action='store_true', help='Show manual fixes guide')
    
    args = parser.parse_args()
    
    if args.guide:
        manual_fixes_guide()
    elif args.interactive:
        interactive_fixer()
    else:
        fixer = EnhancedJinjaFixer()
        fixer.scan_directory(args.dir, auto_fix=args.apply)
        
        if not args.apply:
            print("\n💡 Run with --apply to actually fix the files")
            print("💡 Run with --guide for manual fixing instructions")