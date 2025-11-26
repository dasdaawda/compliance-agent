#!/bin/bash
# AI-Compliance Agent - Setup Validation Script
# Validates that all hardening changes are in place

set -e

echo "=========================================="
echo "AI-Compliance Agent - Setup Validation"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (missing)"
        return 1
    fi
}

check_directory() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${RED}✗${NC} $1/ (missing)"
        return 1
    fi
}

ERRORS=0

# Check requirements files
echo "Checking requirements files..."
check_file "requirements.txt" || ((ERRORS++))
check_file "requirements.dev.txt" || ((ERRORS++))
echo ""

# Check Docker files
echo "Checking Docker configuration..."
check_file "Dockerfile" || ((ERRORS++))
check_file "docker-compose.yml" || ((ERRORS++))
check_file ".env.example" || ((ERRORS++))
check_file ".env.docker" || ((ERRORS++))
echo ""

# Check settings structure
echo "Checking Django settings structure..."
check_directory "backend/compliance_app/settings" || ((ERRORS++))
check_file "backend/compliance_app/settings/__init__.py" || ((ERRORS++))
check_file "backend/compliance_app/settings/base.py" || ((ERRORS++))
check_file "backend/compliance_app/settings/dev.py" || ((ERRORS++))
check_file "backend/compliance_app/settings/prod.py" || ((ERRORS++))
echo ""

# Check scripts
echo "Checking scripts..."
check_directory "scripts" || ((ERRORS++))
check_file "scripts/entrypoint.sh" || ((ERRORS++))
if [ -f "scripts/entrypoint.sh" ]; then
    if [ -x "scripts/entrypoint.sh" ]; then
        echo -e "${GREEN}✓${NC} scripts/entrypoint.sh is executable"
    else
        echo -e "${RED}✗${NC} scripts/entrypoint.sh is not executable"
        ((ERRORS++))
    fi
fi
echo ""

# Check documentation
echo "Checking documentation..."
check_file "README.md" || ((ERRORS++))
check_file "DEPLOYMENT.md" || ((ERRORS++))
check_file "CONFIGURATION.md" || ((ERRORS++))
check_file "DOCKER_QUICKSTART.md" || ((ERRORS++))
check_file "DEPLOYMENT_CHECKLIST.md" || ((ERRORS++))
check_file "HARDENING_SUMMARY.md" || ((ERRORS++))
echo ""

# Check Makefile
echo "Checking development tools..."
check_file "Makefile" || ((ERRORS++))
echo ""

# Verify requirements.txt has pinned versions
echo "Checking requirements.txt pinning..."
if grep -q "==" requirements.txt; then
    echo -e "${GREEN}✓${NC} requirements.txt has pinned versions"
else
    echo -e "${RED}✗${NC} requirements.txt missing pinned versions"
    ((ERRORS++))
fi

# Check for Django 5.0.6
if grep -q "Django==5.0.6" requirements.txt; then
    echo -e "${GREEN}✓${NC} Django 5.0.6 pinned"
else
    echo -e "${YELLOW}⚠${NC} Django version mismatch"
fi
echo ""

# Check Python syntax of settings files
echo "Checking Python syntax..."
for file in backend/compliance_app/settings/*.py; do
    if [ -f "$file" ]; then
        if python3 -m py_compile "$file" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} $(basename $file) syntax OK"
        else
            echo -e "${RED}✗${NC} $(basename $file) has syntax errors"
            ((ERRORS++))
        fi
    fi
done
echo ""

# Final summary
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo "Setup is ready for deployment."
    exit 0
else
    echo -e "${RED}✗ $ERRORS check(s) failed${NC}"
    echo "Please fix the issues above."
    exit 1
fi
