#!/bin/bash
# Validate configuration before starting services
# Usage: ./scripts/validate_config.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "============================================"
echo "  Configuration Validation"
echo "============================================"
echo ""

errors=0
warnings=0

check_file_exists() {
    local file=$1
    local description=$2
    
    echo -n "Checking $description... "
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ Found${NC}"
        return 0
    else
        echo -e "${RED}✗ Missing${NC}"
        errors=$((errors + 1))
        return 1
    fi
}

check_env_var() {
    local var_name=$1
    local is_required=${2:-true}
    
    if [ -z "${!var_name}" ]; then
        if [ "$is_required" = true ]; then
            echo -e "${RED}✗ Required variable $var_name is not set${NC}"
            errors=$((errors + 1))
        else
            echo -e "${YELLOW}⚠ Optional variable $var_name is not set${NC}"
            warnings=$((warnings + 1))
        fi
        return 1
    else
        echo -e "${GREEN}✓ $var_name is set${NC}"
        return 0
    fi
}

# Check required files
echo "=== Required Files ==="
check_file_exists "docker-compose.yml" "docker-compose.yml"
check_file_exists "nginx-rtmp/nginx.conf" "nginx-rtmp configuration"
check_file_exists "nginx-rtmp/Dockerfile" "nginx-rtmp Dockerfile"
echo ""

# Check for .env file
echo "=== Environment Configuration ==="
if [ ! -f ".env" ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    echo "  Please copy env.example to .env and configure it:"
    echo "  cp env.example .env"
    errors=$((errors + 1))
else
    echo -e "${GREEN}✓ .env file found${NC}"
    
    # Load .env
    export $(grep -v '^#' .env | xargs)
    
    echo ""
    echo "=== Critical Variables ==="
    check_env_var "YOUTUBE_STREAM_KEY" true
    check_env_var "POSTGRES_PASSWORD" true
    
    echo ""
    echo "=== Important Variables ==="
    check_env_var "AZURACAST_URL" false
    check_env_var "AZURACAST_API_KEY" false
    check_env_var "DISCORD_WEBHOOK_URL" false
fi
echo ""

# Check Docker
echo "=== Docker Environment ==="
echo -n "Checking Docker... "
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Installed${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    errors=$((errors + 1))
fi

echo -n "Checking Docker Compose... "
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    echo -e "${GREEN}✓ Installed${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    errors=$((errors + 1))
fi
echo ""

# Check directories
echo "=== Required Directories ==="
echo -n "Checking /srv/loops directory... "
if [ -d "/srv/loops" ]; then
    echo -e "${GREEN}✓ Exists${NC}"
else
    echo -e "${YELLOW}⚠ Does not exist${NC}"
    echo "  You may need to create it: sudo mkdir -p /srv/loops"
    warnings=$((warnings + 1))
fi

echo -n "Checking /var/log/radio directory... "
if [ -d "/var/log/radio" ]; then
    echo -e "${GREEN}✓ Exists${NC}"
else
    echo -e "${YELLOW}⚠ Does not exist${NC}"
    echo "  You may need to create it: sudo mkdir -p /var/log/radio"
    warnings=$((warnings + 1))
fi
echo ""

# Validate docker-compose.yml
echo "=== Docker Compose Validation ==="
echo -n "Validating docker-compose.yml syntax... "
if docker-compose config > /dev/null 2>&1 || docker compose config > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Valid${NC}"
else
    echo -e "${RED}✗ Invalid syntax${NC}"
    errors=$((errors + 1))
fi
echo ""

# Summary
echo "============================================"
if [ $errors -eq 0 ]; then
    echo -e "${GREEN}✓ Configuration is valid${NC}"
    if [ $warnings -gt 0 ]; then
        echo -e "${YELLOW}  ($warnings warnings)${NC}"
    fi
    echo ""
    echo "You can now start the services:"
    echo "  docker-compose up -d"
    exit 0
else
    echo -e "${RED}✗ Configuration has $errors error(s)${NC}"
    if [ $warnings -gt 0 ]; then
        echo -e "${YELLOW}  and $warnings warning(s)${NC}"
    fi
    echo ""
    echo "Please fix the errors before starting services."
    exit 1
fi




