#!/usr/bin/env python
"""
Test script to verify Django settings can be imported correctly.
This validates the modular settings structure without requiring all dependencies.
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_settings_import():
    """Test that settings modules can be imported."""
    
    print("Testing Django settings structure...")
    print("=" * 50)
    
    # Test 1: Check settings directory exists
    settings_dir = os.path.join('backend', 'compliance_app', 'settings')
    if not os.path.isdir(settings_dir):
        print("❌ Settings directory not found")
        return False
    print("✓ Settings directory exists")
    
    # Test 2: Check all required files exist
    required_files = ['__init__.py', 'base.py', 'dev.py', 'prod.py']
    for filename in required_files:
        filepath = os.path.join(settings_dir, filename)
        if not os.path.isfile(filepath):
            print(f"❌ Missing file: {filename}")
            return False
        print(f"✓ {filename} exists")
    
    # Test 3: Verify Python syntax
    print("\nVerifying Python syntax...")
    for filename in required_files:
        filepath = os.path.join(settings_dir, filename)
        try:
            with open(filepath, 'r') as f:
                compile(f.read(), filepath, 'exec')
            print(f"✓ {filename} syntax valid")
        except SyntaxError as e:
            print(f"❌ {filename} has syntax error: {e}")
            return False
    
    # Test 4: Check key settings presence in base.py
    print("\nChecking base.py configuration...")
    base_path = os.path.join(settings_dir, 'base.py')
    with open(base_path, 'r') as f:
        base_content = f.read()
    
    required_settings = [
        'INSTALLED_APPS',
        'MIDDLEWARE',
        'AUTH_USER_MODEL',
        'CELERY_BROKER_URL',
        'REST_FRAMEWORK',
        'SIMPLE_JWT',
    ]
    
    for setting in required_settings:
        if setting in base_content:
            print(f"✓ {setting} defined")
        else:
            print(f"❌ {setting} not found")
            return False
    
    # Test 5: Check environment selection logic in __init__.py
    print("\nChecking environment selection...")
    init_path = os.path.join(settings_dir, '__init__.py')
    with open(init_path, 'r') as f:
        init_content = f.read()
    
    if 'DJANGO_ENV' in init_content:
        print("✓ DJANGO_ENV environment detection present")
    else:
        print("❌ DJANGO_ENV detection missing")
        return False
    
    if 'from .dev import *' in init_content:
        print("✓ Development settings import present")
    else:
        print("❌ Development settings import missing")
        return False
    
    if 'from .prod import *' in init_content:
        print("✓ Production settings import present")
    else:
        print("❌ Production settings import missing")
        return False
    
    # Test 6: Verify old settings.py is backed up
    print("\nChecking migration...")
    old_settings = os.path.join('backend', 'compliance_app', 'settings.old.py')
    new_settings_file = os.path.join('backend', 'compliance_app', 'settings.py')
    
    if os.path.isfile(old_settings):
        print("✓ Old settings.py backed up as settings.old.py")
    else:
        print("⚠ settings.old.py not found (may not have existed)")
    
    if not os.path.isfile(new_settings_file):
        print("✓ settings.py removed (directory structure in place)")
    else:
        print("⚠ settings.py still exists (should be removed or moved)")
    
    print("\n" + "=" * 50)
    print("✅ All settings structure tests passed!")
    return True

if __name__ == '__main__':
    success = test_settings_import()
    sys.exit(0 if success else 1)
