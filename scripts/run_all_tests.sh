#!/bin/bash
#
# Run all tests for the 24/7 FFmpeg YouTube Radio Stream project
# 
# This script runs:
# - Unit tests (fast)
# - Integration tests (requires Docker)
# - Load tests (optional, with Locust)
# - Failover tests (requires Docker)
# - Coverage report generation
#
# Usage:
#   ./scripts/run_all_tests.sh [options]
#
# Options:
#   --unit-only       Run only unit tests
#   --integration     Run unit + integration tests
#   --all             Run all tests including slow tests (default)
#   --coverage        Generate coverage report
#   --html            Generate HTML coverage report
#   --docker-start    Start Docker test environment
#   --docker-stop     Stop Docker test environment
#   --skip-docker     Skip tests that require Docker
#   --load-test       Run load tests with Locust
#   --help            Show this help message

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Default options
RUN_UNIT=true
RUN_INTEGRATION=false
RUN_SLOW=false
RUN_COVERAGE=false
HTML_COVERAGE=false
DOCKER_START=false
DOCKER_STOP=false
SKIP_DOCKER=false
RUN_LOAD_TEST=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit-only)
            RUN_UNIT=true
            RUN_INTEGRATION=false
            RUN_SLOW=false
            ;;
        --integration)
            RUN_UNIT=true
            RUN_INTEGRATION=true
            RUN_SLOW=false
            ;;
        --all)
            RUN_UNIT=true
            RUN_INTEGRATION=true
            RUN_SLOW=true
            ;;
        --coverage)
            RUN_COVERAGE=true
            ;;
        --html)
            RUN_COVERAGE=true
            HTML_COVERAGE=true
            ;;
        --docker-start)
            DOCKER_START=true
            ;;
        --docker-stop)
            DOCKER_STOP=true
            ;;
        --skip-docker)
            SKIP_DOCKER=true
            ;;
        --load-test)
            RUN_LOAD_TEST=true
            ;;
        --help)
            grep '^#' "$0" | grep -v '#!/bin/bash' | sed 's/^# //'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
    shift
done

# Functions
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if virtual environment is activated
check_venv() {
    if [[ -z "$VIRTUAL_ENV" ]]; then
        print_warning "Virtual environment not activated"
        if [[ -d "venv" ]]; then
            print_info "Activating virtual environment..."
            source venv/bin/activate
        else
            print_error "Virtual environment not found. Please run: python3 -m venv venv"
            exit 1
        fi
    fi
    print_success "Virtual environment active: $VIRTUAL_ENV"
}

# Check if dependencies are installed
check_dependencies() {
    print_info "Checking dependencies..."
    
    if ! python -c "import pytest" 2>/dev/null; then
        print_warning "pytest not found. Installing dependencies..."
        pip install -r requirements-dev.txt
    fi
    
    print_success "Dependencies installed"
}

# Start Docker test environment
start_docker() {
    print_header "Starting Docker Test Environment"
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "docker-compose not found"
        exit 1
    fi
    
    print_info "Starting Docker services..."
    docker-compose -f docker-compose.test.yml up -d
    
    print_info "Waiting for services to be healthy..."
    sleep 10
    
    print_success "Docker services started"
}

# Stop Docker test environment
stop_docker() {
    print_header "Stopping Docker Test Environment"
    
    print_info "Stopping Docker services..."
    docker-compose -f docker-compose.test.yml down -v
    
    print_success "Docker services stopped"
}

# Run unit tests
run_unit_tests() {
    print_header "Running Unit Tests"
    
    local pytest_args="-v --tb=short"
    
    if [[ "$RUN_COVERAGE" == "true" ]]; then
        pytest_args="$pytest_args --cov=. --cov-report=term-missing"
        
        if [[ "$HTML_COVERAGE" == "true" ]]; then
            pytest_args="$pytest_args --cov-report=html"
        fi
    fi
    
    if [[ "$SKIP_DOCKER" == "true" ]]; then
        pytest_args="$pytest_args -m 'not requires_docker'"
    fi
    
    # Run unit tests
    if pytest tests/unit/ $pytest_args; then
        print_success "Unit tests passed"
        return 0
    else
        print_error "Unit tests failed"
        return 1
    fi
}

# Run integration tests
run_integration_tests() {
    print_header "Running Integration Tests"
    
    local pytest_args="-v --tb=short -m integration"
    
    if [[ "$SKIP_DOCKER" == "true" ]]; then
        pytest_args="$pytest_args and not requires_docker"
    fi
    
    if [[ "$RUN_SLOW" == "false" ]]; then
        pytest_args="$pytest_args and not slow"
    fi
    
    if pytest tests/integration/ $pytest_args; then
        print_success "Integration tests passed"
        return 0
    else
        print_error "Integration tests failed"
        return 1
    fi
}

# Run failover tests
run_failover_tests() {
    print_header "Running Failover Tests"
    
    local pytest_args="-v --tb=short"
    
    if [[ "$SKIP_DOCKER" == "true" ]]; then
        pytest_args="$pytest_args -m 'not requires_docker'"
    fi
    
    if [[ "$RUN_SLOW" == "false" ]]; then
        pytest_args="$pytest_args -m 'not slow'"
    fi
    
    if pytest tests/failover/ $pytest_args; then
        print_success "Failover tests passed"
        return 0
    else
        print_error "Failover tests failed"
        return 1
    fi
}

# Run load tests
run_load_tests() {
    print_header "Running Load Tests"
    
    if ! command -v locust &> /dev/null; then
        print_warning "Locust not found. Skipping load tests."
        print_info "Install with: pip install locust"
        return 0
    fi
    
    print_info "Starting Locust load test (10 users, 2 min)..."
    
    locust -f tests/load/locustfile.py \
        --host=http://localhost:9001 \
        --users 10 \
        --spawn-rate 2 \
        --run-time 2m \
        --headless \
        --only-summary
    
    print_success "Load tests completed"
}

# Generate coverage report
show_coverage_report() {
    if [[ "$RUN_COVERAGE" == "true" ]]; then
        print_header "Coverage Report"
        
        if [[ "$HTML_COVERAGE" == "true" ]]; then
            print_success "HTML coverage report generated: htmlcov/index.html"
            
            if command -v xdg-open &> /dev/null; then
                print_info "Opening coverage report in browser..."
                xdg-open htmlcov/index.html &
            fi
        fi
    fi
}

# Main execution
main() {
    print_header "24/7 FFmpeg YouTube Radio Stream - Test Suite"
    
    # Check environment
    check_venv
    check_dependencies
    
    # Docker management
    if [[ "$DOCKER_START" == "true" ]]; then
        start_docker
    fi
    
    # Track test results
    FAILED_TESTS=()
    
    # Run tests
    if [[ "$RUN_UNIT" == "true" ]]; then
        if ! run_unit_tests; then
            FAILED_TESTS+=("unit")
        fi
    fi
    
    if [[ "$RUN_INTEGRATION" == "true" ]]; then
        if ! run_integration_tests; then
            FAILED_TESTS+=("integration")
        fi
    fi
    
    if [[ "$RUN_SLOW" == "true" ]]; then
        if ! run_failover_tests; then
            FAILED_TESTS+=("failover")
        fi
    fi
    
    if [[ "$RUN_LOAD_TEST" == "true" ]]; then
        run_load_tests
    fi
    
    # Show coverage
    show_coverage_report
    
    # Docker cleanup
    if [[ "$DOCKER_STOP" == "true" ]]; then
        stop_docker
    fi
    
    # Final summary
    print_header "Test Summary"
    
    if [[ ${#FAILED_TESTS[@]} -eq 0 ]]; then
        print_success "All tests passed! ✓"
        exit 0
    else
        print_error "Some tests failed:"
        for test in "${FAILED_TESTS[@]}"; do
            print_error "  - $test tests"
        done
        exit 1
    fi
}

# Run main function
main "$@"



