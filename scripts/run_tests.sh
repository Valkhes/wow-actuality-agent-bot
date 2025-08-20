#!/bin/bash
#
# Test runner script for WoW Actuality Bot
# Runs different types of tests with proper setup and teardown
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TESTS_DIR="./tests"
REPORTS_DIR="./test-reports"
LOGS_DIR="./logs"
COMPOSE_FILE="docker-compose.yml"

# Test types
UNIT_TESTS="unit"
INTEGRATION_TESTS="integration"
E2E_TESTS="e2e"
PERFORMANCE_TESTS="performance"
SECURITY_TESTS="security"
ALL_TESTS="unit or integration or e2e"

# Default test type
TEST_TYPE="unit"
COVERAGE=false
VERBOSE=false
SERVICES_REQUIRED=false
CLEANUP_AFTER=false

usage() {
    echo "Usage: $0 [OPTIONS] [TEST_TYPE]"
    echo ""
    echo "Test Types:"
    echo "  unit         Run unit tests only (default)"
    echo "  integration  Run integration tests (requires running services)"
    echo "  e2e          Run end-to-end tests (requires running services)"
    echo "  performance  Run performance tests"
    echo "  security     Run security tests"
    echo "  all          Run all tests"
    echo ""
    echo "Options:"
    echo "  -c, --coverage      Generate test coverage report"
    echo "  -v, --verbose       Verbose output"
    echo "  -s, --start-services Start services before testing"
    echo "  -k, --cleanup       Cleanup after tests"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 unit"
    echo "  $0 integration -s"
    echo "  $0 e2e --start-services --cleanup"
    echo "  $0 all -c -v"
}

log_message() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')] SUCCESS $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ERROR $1${NC}"
}

check_dependencies() {
    log_message "Checking test dependencies..."
    
    # Check if pytest is available
    if ! command -v pytest >/dev/null 2>&1; then
        log_error "pytest not found. Install test dependencies:"
        echo "  pip install -r tests/requirements.txt"
        exit 1
    fi
    
    # Check if docker-compose is available (for service tests)
    if [ "$SERVICES_REQUIRED" = true ]; then
        if ! command -v docker-compose >/dev/null 2>&1 && ! docker compose version >/dev/null 2>&1; then
            log_error "Docker Compose not found. Required for integration/e2e tests."
            exit 1
        fi
    fi
    
    log_success "Dependencies check passed"
}

setup_test_environment() {
    log_message "Setting up test environment..."
    
    # Create necessary directories
    mkdir -p "$REPORTS_DIR" "$LOGS_DIR"
    
    # Set test environment variables
    export ENVIRONMENT=testing
    export LOG_LEVEL=WARNING
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    
    # Load test environment if available
    if [ -f ".env.test" ]; then
        export $(grep -v '^#' .env.test | xargs)
        log_message "Loaded test environment from .env.test"
    elif [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
        log_message "Loaded environment from .env"
    fi
    
    log_success "Test environment setup complete"
}

start_services() {
    log_message "Starting services with Docker Compose..."
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "docker-compose.yml not found"
        exit 1
    fi
    
    # Start services in background
    if command -v docker-compose >/dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi
    
    $COMPOSE_CMD up -d
    
    # Wait for services to be ready
    log_message "Waiting for services to start..."
    sleep 30
    
    # Check service health
    log_message "Checking service health..."
    
    # Check API service
    for i in {1..12}; do  # 2 minutes max
        if curl -f -s "http://localhost:8000/health" >/dev/null 2>&1; then
            log_success "API service is ready"
            break
        fi
        if [ $i -eq 12 ]; then
            log_warning "API service not ready after 2 minutes"
        fi
        sleep 10
    done
    
    # Check ChromaDB
    for i in {1..12}; do
        if curl -f -s "http://localhost:8000/api/v1/heartbeat" >/dev/null 2>&1; then
            log_success "ChromaDB is ready"
            break
        fi
        if [ $i -eq 12 ]; then
            log_warning "ChromaDB not ready after 2 minutes"
        fi
        sleep 10
    done
    
    log_success "Services started"
}

stop_services() {
    log_message "Stopping services..."
    
    if command -v docker-compose >/dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi
    
    $COMPOSE_CMD down
    log_success "Services stopped"
}

run_tests() {
    local test_type=$1
    
    log_message "Running $test_type tests..."
    
    # Prepare pytest arguments
    PYTEST_ARGS=(
        "$TESTS_DIR"
        "--tb=short"
        "--durations=10"
        "--junitxml=$REPORTS_DIR/junit-$test_type.xml"
        "--html=$REPORTS_DIR/report-$test_type.html"
        "--self-contained-html"
    )
    
    # Add marker filter
    case $test_type in
        "unit")
            PYTEST_ARGS+=("-m" "not (integration or e2e or performance or security)")
            ;;
        "integration")
            PYTEST_ARGS+=("-m" "integration")
            ;;
        "e2e")
            PYTEST_ARGS+=("-m" "e2e")
            ;;
        "performance")
            PYTEST_ARGS+=("-m" "performance")
            ;;
        "security")
            PYTEST_ARGS+=("-m" "security")
            ;;
        "all")
            # Run all tests
            ;;
    esac
    
    # Add coverage if requested
    if [ "$COVERAGE" = true ]; then
        PYTEST_ARGS+=(
            "--cov=src"
            "--cov=discord-bot/src"
            "--cov=api-service/src"
            "--cov=crawler-service/src"
            "--cov-report=html:$REPORTS_DIR/coverage-$test_type"
            "--cov-report=term-missing"
        )
    fi
    
    # Add verbose if requested
    if [ "$VERBOSE" = true ]; then
        PYTEST_ARGS+=("-v" "-s")
    fi
    
    # Run pytest
    if pytest "${PYTEST_ARGS[@]}"; then
        log_success "$test_type tests passed"
        return 0
    else
        log_error "$test_type tests failed"
        return 1
    fi
}

cleanup() {
    log_message "Cleaning up test artifacts..."
    
    # Remove temporary files
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # Clean up test logs older than 7 days
    find "$LOGS_DIR" -name "test_*.log" -mtime +7 -delete 2>/dev/null || true
    
    log_success "Cleanup complete"
}

generate_summary() {
    log_message "Generating test summary..."
    
    echo ""
    echo "==============================================="
    echo "           TEST EXECUTION SUMMARY"
    echo "==============================================="
    echo "Test Type: $TEST_TYPE"
    echo "Coverage: $COVERAGE"
    echo "Reports Directory: $REPORTS_DIR"
    
    if [ -f "$REPORTS_DIR/junit-$TEST_TYPE.xml" ]; then
        # Extract test counts from JUnit XML (basic parsing)
        if command -v xmllint >/dev/null 2>&1; then
            TESTS_RUN=$(xmllint --xpath "//testsuite/@tests" "$REPORTS_DIR/junit-$TEST_TYPE.xml" 2>/dev/null | cut -d'"' -f2)
            TESTS_FAILED=$(xmllint --xpath "//testsuite/@failures" "$REPORTS_DIR/junit-$TEST_TYPE.xml" 2>/dev/null | cut -d'"' -f2)
            TESTS_ERRORS=$(xmllint --xpath "//testsuite/@errors" "$REPORTS_DIR/junit-$TEST_TYPE.xml" 2>/dev/null | cut -d'"' -f2)
            
            echo "Tests Run: ${TESTS_RUN:-N/A}"
            echo "Failures: ${TESTS_FAILED:-N/A}"
            echo "Errors: ${TESTS_ERRORS:-N/A}"
        fi
    fi
    
    echo ""
    echo "Reports available:"
    echo "  HTML Report: $REPORTS_DIR/report-$TEST_TYPE.html"
    echo "  JUnit XML: $REPORTS_DIR/junit-$TEST_TYPE.xml"
    
    if [ "$COVERAGE" = true ]; then
        echo "  Coverage Report: $REPORTS_DIR/coverage-$TEST_TYPE/index.html"
    fi
    
    echo "==============================================="
}

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--coverage)
                COVERAGE=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -s|--start-services)
                SERVICES_REQUIRED=true
                shift
                ;;
            -k|--cleanup)
                CLEANUP_AFTER=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            unit|integration|e2e|performance|security|all)
                TEST_TYPE=$1
                if [[ "$TEST_TYPE" == "integration" || "$TEST_TYPE" == "e2e" || "$TEST_TYPE" == "all" ]]; then
                    SERVICES_REQUIRED=true
                fi
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Main execution
    log_message "Starting test execution for: $TEST_TYPE"
    
    # Trap cleanup on exit
    if [ "$CLEANUP_AFTER" = true ]; then
        trap cleanup EXIT
    fi
    
    # Setup
    check_dependencies
    setup_test_environment
    
    # Start services if needed
    if [ "$SERVICES_REQUIRED" = true ]; then
        start_services
        # Trap service cleanup
        trap 'stop_services; if [ "$CLEANUP_AFTER" = true ]; then cleanup; fi' EXIT
    fi
    
    # Run tests
    if run_tests "$TEST_TYPE"; then
        TEST_RESULT=0
    else
        TEST_RESULT=1
    fi
    
    # Generate summary
    generate_summary
    
    # Stop services if started
    if [ "$SERVICES_REQUIRED" = true ]; then
        stop_services
    fi
    
    # Final cleanup if requested
    if [ "$CLEANUP_AFTER" = true ]; then
        cleanup
    fi
    
    # Exit with test result
    if [ $TEST_RESULT -eq 0 ]; then
        log_success "All tests completed successfully!"
    else
        log_error "Some tests failed. Check reports for details."
    fi
    
    exit $TEST_RESULT
}

main "$@"