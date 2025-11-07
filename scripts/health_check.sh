#!/bin/bash
# Health check script for all services in the radio stream infrastructure
# Usage: ./scripts/health_check.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "  24/7 Radio Stream - Health Check"
echo "============================================"
echo ""

check_service() {
    local service_name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Checking $service_name... "
    
    if response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null); then
        if [ "$response" -eq "$expected_status" ]; then
            echo -e "${GREEN}✓ OK${NC} (HTTP $response)"
            return 0
        else
            echo -e "${YELLOW}⚠ WARNING${NC} (HTTP $response, expected $expected_status)"
            return 1
        fi
    else
        echo -e "${RED}✗ FAILED${NC} (Connection refused)"
        return 1
    fi
}

check_docker_service() {
    local service_name=$1
    echo -n "Checking Docker container $service_name... "
    
    if docker ps --filter "name=$service_name" --filter "status=running" | grep -q "$service_name"; then
        echo -e "${GREEN}✓ RUNNING${NC}"
        return 0
    else
        echo -e "${RED}✗ NOT RUNNING${NC}"
        return 1
    fi
}

check_port() {
    local service_name=$1
    local host=$2
    local port=$3
    
    echo -n "Checking $service_name port $port... "
    
    if nc -z -w5 "$host" "$port" 2>/dev/null; then
        echo -e "${GREEN}✓ OPEN${NC}"
        return 0
    else
        echo -e "${RED}✗ CLOSED${NC}"
        return 1
    fi
}

# Track overall health
all_healthy=true

# Check Docker containers
echo "=== Docker Containers ==="
check_docker_service "radio_nginx_rtmp" || all_healthy=false
check_docker_service "radio_metadata_watcher" || all_healthy=false
check_docker_service "radio_postgres" || all_healthy=false
check_docker_service "radio_prometheus" || all_healthy=false
echo ""

# Check HTTP endpoints
echo "=== HTTP Health Endpoints ==="
check_service "nginx-rtmp" "http://localhost:8080/health" 200 || all_healthy=false
check_service "metadata-watcher" "http://localhost:9000/health" 200 || all_healthy=false
check_service "prometheus" "http://localhost:9090/-/healthy" 200 || all_healthy=false
echo ""

# Check ports
echo "=== Network Ports ==="
check_port "RTMP" "localhost" "1935" || all_healthy=false
check_port "nginx-rtmp HTTP" "localhost" "8080" || all_healthy=false
check_port "metadata-watcher" "localhost" "9000" || all_healthy=false
check_port "prometheus" "localhost" "9090" || all_healthy=false
check_port "postgres" "localhost" "5432" || all_healthy=false
echo ""

# Check database connectivity
echo "=== Database ==="
echo -n "Checking PostgreSQL connectivity... "
if docker exec radio_postgres pg_isready -U radio >/dev/null 2>&1; then
    echo -e "${GREEN}✓ READY${NC}"
else
    echo -e "${RED}✗ NOT READY${NC}"
    all_healthy=false
fi
echo ""

# Summary
echo "============================================"
if [ "$all_healthy" = true ]; then
    echo -e "${GREEN}✓ All services are healthy${NC}"
    exit 0
else
    echo -e "${RED}✗ Some services have issues${NC}"
    echo ""
    echo "Troubleshooting tips:"
    echo "  1. Check logs: docker-compose logs -f [service-name]"
    echo "  2. Restart services: docker-compose restart"
    echo "  3. Check .env file configuration"
    echo "  4. Verify network connectivity"
    exit 1
fi




