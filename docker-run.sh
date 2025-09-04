#!/bin/bash

# FluidKit Docker Management Script
# Usage: ./docker-run.sh [command]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${GREEN}[FluidKit]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[FluidKit]${NC} $1"
}

print_error() {
    echo -e "${RED}[FluidKit]${NC} $1"
}

# Function to build the Docker image
build_image() {
    print_status "Building FluidKit Docker image..."
    docker build -t fluidkit:latest .
    print_status "Build completed successfully!"
}

# Function to run production container
run_production() {
    print_status "Starting FluidKit in production mode..."
    docker-compose up -d
    print_status "FluidKit is running at http://localhost:8000"
    print_status "API documentation available at http://localhost:8000/docs"
}

# Function to run development container
run_development() {
    print_status "Starting FluidKit in development mode..."
    docker-compose -f docker-compose.dev.yml up
}

# Function to stop containers
stop_containers() {
    print_status "Stopping FluidKit containers..."
    docker-compose down
    docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
    print_status "Containers stopped successfully!"
}

# Function to show logs
show_logs() {
    print_status "Showing FluidKit logs..."
    docker-compose logs -f
}

# Function to run tests in container
run_tests() {
    print_status "Running tests in container..."
    docker run --rm -v "$(pwd)":/app fluidkit:latest python -m pytest tests/ -v
}

# Function to generate TypeScript clients
generate_clients() {
    print_status "Generating TypeScript clients..."
    docker run --rm -v "$(pwd)":/app -v "$(pwd)/.fluidkit:/app/.fluidkit" fluidkit:latest python test.py
    print_status "TypeScript clients generated in .fluidkit/ directory"
}

# Function to clean up Docker resources
cleanup() {
    print_status "Cleaning up Docker resources..."
    docker-compose down -v
    docker-compose -f docker-compose.dev.yml down -v 2>/dev/null || true
    docker system prune -f
    print_status "Cleanup completed!"
}

# Function to show help
show_help() {
    echo "FluidKit Docker Management Script"
    echo ""
    echo "Usage: ./docker-run.sh [command]"
    echo ""
    echo "Commands:"
    echo "  build       Build the Docker image"
    echo "  start       Start in production mode (detached)"
    echo "  dev         Start in development mode (with live reload)"
    echo "  stop        Stop all containers"
    echo "  logs        Show container logs"
    echo "  test        Run tests in container"
    echo "  generate    Generate TypeScript clients"
    echo "  cleanup     Clean up Docker resources"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./docker-run.sh build       # Build the image"
    echo "  ./docker-run.sh dev         # Start development server"
    echo "  ./docker-run.sh generate    # Generate TypeScript clients"
}

# Main command handler
case "${1:-help}" in
    build)
        build_image
        ;;
    start|prod|production)
        run_production
        ;;
    dev|development)
        run_development
        ;;
    stop)
        stop_containers
        ;;
    logs)
        show_logs
        ;;
    test|tests)
        run_tests
        ;;
    generate|gen)
        generate_clients
        ;;
    cleanup|clean)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
