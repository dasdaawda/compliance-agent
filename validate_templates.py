#!/usr/bin/env python3
"""
Simple template validation script to check Django templates for basic syntax errors.
"""
import os
import re

def validate_template_syntax(template_path):
    """Check basic Django template syntax."""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        errors = []
        
        # Check for unmatched template tags
        open_tags = re.findall(r'{%\s*([^%]+)\s*%}', content)
        close_tags = re.findall(r'{%\s*end([^%]+)\s*%}', content)
        
        # Check for unmatched blocks
        blocks = re.findall(r'{%\s*block\s+(\w+)', content)
        endblocks = re.findall(r'{%\s*endblock', content)
        
        if len(blocks) != len(endblocks):
            errors.append(f"Mismatched block/endblock tags: {len(blocks)} blocks, {len(endblocks)} endblocks")
        
        # Check for unmatched extends
        extends = re.findall(r'{%\s*extends\s+[^%]+%}', content)
        if len(extends) > 1:
            errors.append("Multiple extends tags found")
        
        # Check for basic syntax issues
        if '{{ ' in content and ' }}' not in content:
            errors.append("Found unclosed variable tags")
        
        return errors
        
    except Exception as e:
        return [f"Error reading file: {e}"]

def main():
    template_dir = '/home/engine/project/backend/templates'
    
    print("Validating Django templates...")
    
    for root, dirs, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.html'):
                template_path = os.path.join(root, file)
                rel_path = os.path.relpath(template_path, template_dir)
                
                errors = validate_template_syntax(template_path)
                
                if errors:
                    print(f"❌ {rel_path}:")
                    for error in errors:
                        print(f"   - {error}")
                else:
                    print(f"✅ {rel_path}")
    
    print("\nTemplate validation complete.")

if __name__ == '__main__':
    main()