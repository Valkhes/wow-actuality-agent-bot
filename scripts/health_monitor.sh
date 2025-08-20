#!/bin/bash
#
# Health monitoring script for WoW Actuality Bot services
# Checks all Docker services and reports their health status
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICES=("wow-postgres" "wow-chromadb" "wow-langfuse" "wow-litellm-gateway" "wow-api-service" "wow-discord-bot" "wow-crawler-service")
COMPOSE_FILE="docker-compose.yml"
LOG_FILE="./logs/health_monitor.log"

# Ensure logs directory exists
mkdir -p ./logs

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo -e "$1"
}

check_docker_compose() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_message "${RED}ERROR: $COMPOSE_FILE not found${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose >/dev/null 2>&1; then
        if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
            log_message "${RED}ERROR: Docker Compose not found${NC}"
            exit 1
        fi
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
}

check_service_health() {
    local service_name=$1
    local container_name=$2
    
    # Check if container is running
    if ! docker ps --format "table {{.Names}}" | grep -q "^$container_name$"; then
        log_message "${RED}FAIL $service_name: Container not running${NC}"
        return 1
    fi
    
    # Check container health if health check is configured
    local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "no-healthcheck")
    
    if [ "$health_status" = "healthy" ]; then
        log_message "${GREEN}OK $service_name: Healthy${NC}"
        return 0
    elif [ "$health_status" = "unhealthy" ]; then
        log_message "${RED}FAIL $service_name: Unhealthy${NC}"
        return 1
    elif [ "$health_status" = "starting" ]; then
        log_message "${YELLOW}WAIT $service_name: Starting${NC}"
        return 2
    elif [ "$health_status" = "no-healthcheck" ]; then
        # No health check configured, just check if running
        log_message "${BLUE}INFO $service_name: Running (no health check)${NC}"
        return 0
    else
        log_message "${YELLOW}WARN $service_name: Unknown status ($health_status)${NC}"
        return 2
    fi
}

check_service_endpoints() {
    log_message "${BLUE}Checking service endpoints...${NC}"
    
    # Check API service
    if curl -f -s "http://localhost:8000/health" >/dev/null 2>&1; then
        log_message "${GREEN}OK API Service endpoint: Accessible${NC}"
    else
        log_message "${RED}FAIL API Service endpoint: Not accessible${NC}"
    fi
    
    # Check Langfuse
    if curl -f -s "http://localhost:3000/api/public/health" >/dev/null 2>&1; then
        log_message "${GREEN}OK Langfuse endpoint: Accessible${NC}"
    else
        log_message "${RED}FAIL Langfuse endpoint: Not accessible${NC}"
    fi
    
    # Check LiteLLM Gateway
    if curl -f -s "http://localhost:4000/health" >/dev/null 2>&1; then
        log_message "${GREEN}OK LiteLLM Gateway endpoint: Accessible${NC}"
    else
        log_message "${RED}FAIL LiteLLM Gateway endpoint: Not accessible${NC}"
    fi
    
    # Check ChromaDB
    if curl -f -s "http://localhost:8000/api/v1/heartbeat" >/dev/null 2>&1; then
        log_message "${GREEN}OK ChromaDB endpoint: Accessible${NC}"
    else
        log_message "${RED}FAIL ChromaDB endpoint: Not accessible${NC}"
    fi
    
    # Check Crawler service
    if curl -f -s "http://localhost:8002/health" >/dev/null 2>&1; then
        log_message "${GREEN}OK Crawler Service endpoint: Accessible${NC}"
    else
        log_message "${RED}FAIL Crawler Service endpoint: Not accessible${NC}"
    fi
}

check_resource_usage() {
    log_message "${BLUE}Checking resource usage...${NC}"
    
    for service in "${SERVICES[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "^$service$"; then
            local stats=$(docker stats "$service" --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" | tail -n 1)
            log_message "${BLUE}STATS $stats${NC}"
        fi
    done
}

generate_health_report() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local report_file="./reports/health_report_$(date '+%Y%m%d_%H%M%S').json"
    
    mkdir -p ./reports
    
    cat > "$report_file" <<EOF
{
  "timestamp": "$timestamp",
  "health_check": {
    "overall_status": "unknown",
    "services": {
EOF

    local overall_healthy=true
    local first_service=true
    
    for i, service in "${SERVICES[@]}"; do
        if [ "$first_service" = false ]; then
            echo "," >> "$report_file"
        fi
        first_service=false
        
        if docker ps --format "table {{.Names}}" | grep -q "^$service$"; then
            local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$service" 2>/dev/null || echo "no-healthcheck")
            local running="true"
            
            if [ "$health_status" = "unhealthy" ]; then
                overall_healthy=false
            fi
        else
            local health_status="not-running"
            local running="false"
            overall_healthy=false
        fi
        
        cat >> "$report_file" <<EOF
      "$service": {
        "running": $running,
        "health_status": "$health_status"
      }
EOF
    done
    
    cat >> "$report_file" <<EOF
    }
  },
  "overall_healthy": $overall_healthy,
  "report_file": "$report_file"
}
EOF

    log_message "${BLUE}Health report generated: $report_file${NC}"
}

show_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -c, --check          Check service health (default)"
    echo "  -e, --endpoints      Check service endpoints"
    echo "  -r, --resources      Check resource usage"
    echo "  -a, --all           Check everything"
    echo "  -w, --watch         Watch mode (continuous monitoring)"
    echo "  --report            Generate health report"
    echo "  -h, --help          Show this help message"
}

main() {
    local action="check"
    local watch_mode=false
    local generate_report=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--check)
                action="check"
                shift
                ;;
            -e|--endpoints)
                action="endpoints"
                shift
                ;;
            -r|--resources)
                action="resources"
                shift
                ;;
            -a|--all)
                action="all"
                shift
                ;;
            -w|--watch)
                watch_mode=true
                shift
                ;;
            --report)
                generate_report=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    check_docker_compose
    
    log_message "${BLUE}=== WoW Actuality Bot Health Monitor ===${NC}"
    log_message "${BLUE}Started at: $(date)${NC}"
    
    do_health_check() {
        case $action in
            "check")
                log_message "${BLUE}Checking service health...${NC}"
                local healthy_count=0
                local total_count=${#SERVICES[@]}
                
                for service in "${SERVICES[@]}"; do
                    if check_service_health "$service" "$service"; then
                        ((healthy_count++))
                    fi
                done
                
                log_message "${BLUE}Health Summary: $healthy_count/$total_count services healthy${NC}"
                ;;
            "endpoints")
                check_service_endpoints
                ;;
            "resources")
                check_resource_usage
                ;;
            "all")
                log_message "${BLUE}Checking service health...${NC}"
                for service in "${SERVICES[@]}"; do
                    check_service_health "$service" "$service"
                done
                echo ""
                check_service_endpoints
                echo ""
                check_resource_usage
                ;;
        esac
        
        if [ "$generate_report" = true ]; then
            generate_health_report
        fi
    }
    
    if [ "$watch_mode" = true ]; then
        log_message "${BLUE}Watch mode enabled (press Ctrl+C to stop)${NC}"
        while true; do
            clear
            do_health_check
            sleep 30
        done
    else
        do_health_check
    fi
    
    log_message "${BLUE}Health check completed at: $(date)${NC}"
}

# Run main function with all arguments
main "$@"