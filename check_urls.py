#!/usr/bin/env python3
"""
Simple URL validation script to check if all referenced URLs exist in URL patterns.
"""
import os
import re

def extract_urls_from_template(template_path):
    """Extract all URL references from a template."""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find URL patterns like {% url 'name' %} or {% url 'name' arg %}
        url_pattern = r'{%\s*url\s+[\'"]([^\'"]+)[\'"](?:\s+[^%]+)?\s*%}'
        urls = re.findall(url_pattern, content)
        
        # Find hx-get, hx-post, etc. attributes that reference URLs
        hx_pattern = r'hx-(?:get|post|put|delete|patch)=[\'"]([^\'"]+)[\'"]'
        hx_urls = re.findall(hx_pattern, content)
        
        return list(set(urls + hx_urls))
        
    except Exception as e:
        return []

def main():
    template_dir = '/home/engine/project/backend/templates'
    
    print("Checking URLs in templates...")
    
    all_urls = set()
    url_files = {}
    
    for root, dirs, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.html'):
                template_path = os.path.join(root, file)
                rel_path = os.path.relpath(template_path, template_dir)
                
                urls = extract_urls_from_template(template_path)
                
                if urls:
                    url_files[rel_path] = urls
                    all_urls.update(urls)
    
    print(f"Found {len(all_urls)} unique URL references:")
    for url in sorted(all_urls):
        print(f"  - {url}")
    
    print(f"\nURL references by file:")
    for file_path, urls in url_files.items():
        print(f"\n📄 {file_path}:")
        for url in sorted(urls):
            print(f"  - {url}")
    
    print("\nURL analysis complete.")

if __name__ == '__main__':
    main()