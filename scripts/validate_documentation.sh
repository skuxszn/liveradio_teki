#!/bin/bash

# Documentation Validation Script
# Validates that all required documentation files exist and are properly formatted

set -e

echo "=========================================="
echo "Documentation Validation Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Function to check if file exists
check_file_exists() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $description exists: $file"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description missing: $file"
        ((FAILED++))
        return 1
    fi
}

# Function to check file size (should not be empty)
check_file_not_empty() {
    local file=$1
    local description=$2
    
    if [ ! -f "$file" ]; then
        return 1
    fi
    
    if [ -s "$file" ]; then
        echo -e "${GREEN}✓${NC} $description is not empty: $file"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description is empty: $file"
        ((FAILED++))
        return 1
    fi
}

# Function to check for valid Markdown
check_markdown_syntax() {
    local file=$1
    local description=$2
    
    if [ ! -f "$file" ]; then
        return 1
    fi
    
    # Basic check: file should have at least one heading
    if grep -q '^#' "$file"; then
        echo -e "${GREEN}✓${NC} $description has valid Markdown headings"
        ((PASSED++))
        return 0
    else
        echo -e "${YELLOW}⚠${NC} $description may not have proper Markdown structure"
        ((WARNINGS++))
        return 1
    fi
}

# Function to check for broken internal links
check_internal_links() {
    local file=$1
    local description=$2
    
    if [ ! -f "$file" ]; then
        return 1
    fi
    
    # Extract Markdown links and check if referenced files exist
    local broken_links=0
    
    # Find all [text](./path) or [text](path.md) style links
    grep -oP '\[.*?\]\(\./.*?\)' "$file" 2>/dev/null | while read -r link; do
        # Extract the path
        path=$(echo "$link" | sed 's/.*(\.\///' | sed 's/).*//')
        
        # Check if file exists (relative to project root)
        if [ ! -f "$path" ] && [ ! -d "$path" ]; then
            echo -e "${YELLOW}⚠${NC} Broken link in $file: $path"
            ((broken_links++))
        fi
    done
    
    if [ $broken_links -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $description: No broken internal links found"
        ((PASSED++))
        return 0
    else
        echo -e "${YELLOW}⚠${NC} $description: $broken_links potential broken links"
        ((WARNINGS++))
        return 1
    fi
}

echo "Checking required documentation files..."
echo ""

# Check primary documentation files
echo "--- Primary Documentation ---"
check_file_exists "docs/DEPLOYMENT.md" "Deployment Guide"
check_file_not_empty "docs/DEPLOYMENT.md" "Deployment Guide"
check_markdown_syntax "docs/DEPLOYMENT.md" "Deployment Guide"

check_file_exists "docs/CONFIGURATION.md" "Configuration Reference"
check_file_not_empty "docs/CONFIGURATION.md" "Configuration Reference"
check_markdown_syntax "docs/CONFIGURATION.md" "Configuration Reference"

check_file_exists "docs/TROUBLESHOOTING.md" "Troubleshooting Guide"
check_file_not_empty "docs/TROUBLESHOOTING.md" "Troubleshooting Guide"
check_markdown_syntax "docs/TROUBLESHOOTING.md" "Troubleshooting Guide"

check_file_exists "docs/API.md" "API Documentation"
check_file_not_empty "docs/API.md" "API Documentation"
check_markdown_syntax "docs/API.md" "API Documentation"

check_file_exists "docs/ARCHITECTURE.md" "Architecture Documentation"
check_file_not_empty "docs/ARCHITECTURE.md" "Architecture Documentation"
check_markdown_syntax "docs/ARCHITECTURE.md" "Architecture Documentation"

check_file_exists "docs/FAQ.md" "FAQ"
check_file_not_empty "docs/FAQ.md" "FAQ"
check_markdown_syntax "docs/FAQ.md" "FAQ"

echo ""
echo "--- Specialized Documentation ---"
check_file_exists "docs/FFMPEG_TUNING.md" "FFmpeg Tuning Guide"
check_file_exists "docs/ASSET_PREPARATION.md" "Asset Preparation Guide"
check_file_exists "docs/MONITORING.md" "Monitoring Guide"
check_file_exists "docs/SECURITY.md" "Security Guide"
check_file_exists "docs/ADVANCED_TRANSITIONS.md" "Advanced Transitions Guide"

echo ""
echo "--- Meta Documentation ---"
check_file_exists "README.md" "Main README"
check_file_exists "SHARD_12_README.md" "SHARD-12 README"
check_file_exists "SHARD_12_COMPLETION_REPORT.md" "SHARD-12 Completion Report"

echo ""
echo "--- Configuration Files ---"
check_file_exists "env.example" "Environment Example"
check_file_exists "docker-compose.yml" "Docker Compose"

echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All required documentation is present!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some required documentation is missing.${NC}"
    exit 1
fi



