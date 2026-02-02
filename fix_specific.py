#!/usr/bin/env python3
"""
Quick fixes for specific Jinja2 error patterns
"""

import os
import re
import sys

def fix_all_in_directory(directory):
    """Apply all possible fixes to directory"""
    fixes = [
        ("String concatenation", r'\{\{([^}]+)"([^"]+)"\s*\+\s*([^}]+)\}\}', r'{{\1"\2" ~ \3}}'),
        ("Missing quotes in url_for", r'url_for\([^)]*filename=([a-zA-Z0-9_.-]+)[^)]*\)', r"url_for('static', filename='\1')"),
        ("Wrong filter syntax", r'\|\s*(\w+)\s+(\w+)(?=\s*\}\})', r'|\1(\2)'),
        ("Unclosed print statements", r'(\{\{[^}]+?)(?=\s*[\n<])', r'\1 }}'),
        ("HTML attributes without quotes", r'(\b(?:class|id|name|for|type|value|placeholder)\s*=\s*)([a-zA-Z0-9_-]+)(?=[\s>])', r'\1"\2"'),
    ]
    
    for root, dirs, files in os.walk(directory):
        if 'venv' in root or 'env' in root:
            continue
            
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                
                with open(filepath, 'r') as f:
                    content = f.read()
                
                original = content
                
                for fix_name, pattern, replacement in fixes:
                    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                    if new_content != content:
                        print(f"✅ Applied {fix_name} to {filepath}")
                        content = new_content
                
                if content != original:
                    with open(filepath, 'w') as f:
                        f.write(content)
                    print(f"📝 Updated: {filepath}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = '.'
    
    print(f"🔧 Applying quick fixes to {directory}...")
    fix_all_in_directory(directory)
    print("✅ Done!")