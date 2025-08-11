#!/bin/bash

# Port Forward Management Script for Transcripts v2
# Manages all port forwards needed for local development

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="/tmp/transcripts-port-forwards"

# Create PID directory
mkdir -p "$PID_DIR"

# Port forward configurations
declare -A FORWARDS=(
    ["registry"]="infrastructure:svc/docker-registry:30500:5000"
    ["argocd"]="argocd:svc/argocd-server:30080:80"
    ["argo-workflows"]="argo-workflows:svc/argo-server:30746:2746"
    ["minio"]="infrastructure:svc/minio:30900:9001"
    ["minio-api"]="infrastructure:svc/minio:30901:9000"
    ["gateway"]="endpoints:svc/gateway:30800:8000"
)

usage() {
    echo "Usage: $0 [start|stop|restart|status] [service_name]"
    echo ""
    echo "Services:"
    for service in "${!FORWARDS[@]}"; do
        echo "  $service"
    done
    echo ""
    echo "Examples:"
    echo "  $0 start                # Start all port forwards"
    echo "  $0 start registry       # Start only registry port forward"
    echo "  $0 stop                 # Stop all port forwards"
    echo "  $0 status               # Show status of all port forwards"
    echo "  $0 restart              # Restart all port forwards"
}

start_forward() {
    local service="$1"
    local config="${FORWARDS[$service]}"
    
    if [ -z "$config" ]; then
        echo "❌ Unknown service: $service"
        return 1
    fi
    
    local namespace port_config
    IFS=':' read -r namespace svc port_config <<< "$config"
    IFS=':' read -r local_port remote_port <<< "$port_config"
    
    local pid_file="$PID_DIR/$service.pid"
    
    # Check if already running
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "✅ $service port forward already running (PID: $pid)"
            return 0
        else
            rm -f "$pid_file"
        fi
    fi
    
    echo "🔗 Starting port forward for $service: localhost:$local_port -> $namespace/$svc:$remote_port"
    
    # Start port forward in background
    kubectl port-forward -n "$namespace" "$svc" "$local_port:$remote_port" &
    local new_pid=$!
    
    # Save PID
    echo "$new_pid" > "$pid_file"
    
    # Give it a moment to start
    sleep 1
    
    # Verify it's running
    if kill -0 "$new_pid" 2>/dev/null; then
        echo "✅ $service port forward started (PID: $new_pid)"
    else
        echo "❌ Failed to start $service port forward"
        rm -f "$pid_file"
        return 1
    fi
}

stop_forward() {
    local service="$1"
    local pid_file="$PID_DIR/$service.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            echo "🛑 Stopped $service port forward (PID: $pid)"
        fi
        rm -f "$pid_file"
    else
        echo "ℹ️  $service port forward not running"
    fi
}

status_forward() {
    local service="$1"
    local config="${FORWARDS[$service]}"
    local pid_file="$PID_DIR/$service.pid"
    
    local namespace port_config
    IFS=':' read -r namespace svc port_config <<< "$config"
    IFS=':' read -r local_port remote_port <<< "$port_config"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "✅ $service: localhost:$local_port -> $namespace/$svc:$remote_port (PID: $pid)"
            return 0
        else
            echo "❌ $service: localhost:$local_port -> $namespace/$svc:$remote_port (DEAD)"
            rm -f "$pid_file"
            return 1
        fi
    else
        echo "⚪ $service: localhost:$local_port -> $namespace/$svc:$remote_port (NOT RUNNING)"
        return 1
    fi
}

cleanup() {
    echo "🧹 Cleaning up port forwards..."
    for service in "${!FORWARDS[@]}"; do
        stop_forward "$service"
    done
    # Also kill any kubectl port-forward processes
    pkill -f "kubectl port-forward" 2>/dev/null || true
}

# Trap cleanup on script exit
trap cleanup EXIT

case "${1:-start}" in
    start)
        if [ -n "$2" ]; then
            start_forward "$2"
        else
            echo "🚀 Starting all port forwards..."
            for service in "${!FORWARDS[@]}"; do
                start_forward "$service" || true
            done
            echo ""
            echo "📋 Port Forward Summary:"
            for service in "${!FORWARDS[@]}"; do
                status_forward "$service" || true
            done
        fi
        ;;
    stop)
        if [ -n "$2" ]; then
            stop_forward "$2"
        else
            echo "🛑 Stopping all port forwards..."
            for service in "${!FORWARDS[@]}"; do
                stop_forward "$service"
            done
        fi
        ;;
    restart)
        if [ -n "$2" ]; then
            stop_forward "$2"
            sleep 1
            start_forward "$2"
        else
            echo "🔄 Restarting all port forwards..."
            for service in "${!FORWARDS[@]}"; do
                stop_forward "$service"
            done
            sleep 2
            for service in "${!FORWARDS[@]}"; do
                start_forward "$service" || true
            done
        fi
        ;;
    status)
        echo "📊 Port Forward Status:"
        local all_running=true
        for service in "${!FORWARDS[@]}"; do
            status_forward "$service" || all_running=false
        done
        if [ "$all_running" = true ]; then
            echo ""
            echo "✅ All port forwards are running!"
        else
            echo ""
            echo "⚠️  Some port forwards are not running"
        fi
        ;;
    cleanup)
        cleanup
        ;;
    *)
        usage
        exit 1
        ;;
esac

# Don't run cleanup trap if we're starting port forwards
if [ "${1:-start}" = "start" ]; then
    trap - EXIT
    echo ""
    echo "🎯 Port forwards are running in the background"
    echo "   Use '$0 status' to check status"
    echo "   Use '$0 stop' to stop all"
    echo "   Use '$0 cleanup' for emergency cleanup"
fi