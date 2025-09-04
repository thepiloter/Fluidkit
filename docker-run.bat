@echo off
REM FluidKit Docker Management Script for Windows
REM Usage: docker-run.bat [command]

setlocal EnableDelayedExpansion

REM Function to print colored output (simplified for Windows)
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "NC=[0m"

if "%1"=="build" goto build
if "%1"=="start" goto start
if "%1"=="prod" goto start
if "%1"=="production" goto start
if "%1"=="dev" goto dev
if "%1"=="development" goto dev
if "%1"=="stop" goto stop
if "%1"=="logs" goto logs
if "%1"=="test" goto test
if "%1"=="tests" goto test
if "%1"=="generate" goto generate
if "%1"=="gen" goto generate
if "%1"=="cleanup" goto cleanup
if "%1"=="clean" goto cleanup
if "%1"=="help" goto help
if "%1"=="--help" goto help
if "%1"=="-h" goto help
if "%1"=="" goto help
goto unknown

:build
echo %GREEN%[FluidKit]%NC% Building FluidKit Docker image...
docker build -t fluidkit:latest .
if errorlevel 1 (
    echo %RED%[FluidKit]%NC% Build failed!
    exit /b 1
)
echo %GREEN%[FluidKit]%NC% Build completed successfully!
goto end

:start
echo %GREEN%[FluidKit]%NC% Starting FluidKit in production mode...
docker-compose up -d
if errorlevel 1 (
    echo %RED%[FluidKit]%NC% Failed to start production containers!
    exit /b 1
)
echo %GREEN%[FluidKit]%NC% FluidKit is running at http://localhost:8000
echo %GREEN%[FluidKit]%NC% API documentation available at http://localhost:8000/docs
goto end

:dev
echo %GREEN%[FluidKit]%NC% Starting FluidKit in development mode...
docker-compose -f docker-compose.dev.yml up
goto end

:stop
echo %GREEN%[FluidKit]%NC% Stopping FluidKit containers...
docker-compose down
docker-compose -f docker-compose.dev.yml down 2>nul
echo %GREEN%[FluidKit]%NC% Containers stopped successfully!
goto end

:logs
echo %GREEN%[FluidKit]%NC% Showing FluidKit logs...
docker-compose logs -f
goto end

:test
echo %GREEN%[FluidKit]%NC% Running tests in container...
docker run --rm -v "%cd%":/app fluidkit:latest python -m pytest tests/ -v
goto end

:generate
echo %GREEN%[FluidKit]%NC% Generating TypeScript clients...
docker run --rm -v "%cd%":/app -v "%cd%\.fluidkit":/app/.fluidkit fluidkit:latest python test.py
echo %GREEN%[FluidKit]%NC% TypeScript clients generated in .fluidkit\ directory
goto end

:cleanup
echo %GREEN%[FluidKit]%NC% Cleaning up Docker resources...
docker-compose down -v
docker-compose -f docker-compose.dev.yml down -v 2>nul
docker system prune -f
echo %GREEN%[FluidKit]%NC% Cleanup completed!
goto end

:help
echo FluidKit Docker Management Script
echo.
echo Usage: docker-run.bat [command]
echo.
echo Commands:
echo   build       Build the Docker image
echo   start       Start in production mode (detached)
echo   dev         Start in development mode (with live reload)
echo   stop        Stop all containers
echo   logs        Show container logs
echo   test        Run tests in container
echo   generate    Generate TypeScript clients
echo   cleanup     Clean up Docker resources
echo   help        Show this help message
echo.
echo Examples:
echo   docker-run.bat build       # Build the image
echo   docker-run.bat dev         # Start development server
echo   docker-run.bat generate    # Generate TypeScript clients
goto end

:unknown
echo %RED%[FluidKit]%NC% Unknown command: %1
goto help

:end
endlocal
