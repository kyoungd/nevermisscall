#!/usr/bin/env python3
"""Development server runner for as-call-service."""

import os
import sys
import subprocess
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def run_dev_server():
    """Run development server with auto-reload."""
    print("🚀 Starting as-call-service development server...")
    print("📍 Service will be available at http://localhost:3104")
    print("📖 API docs will be available at http://localhost:3104/docs")
    print("🔄 Auto-reload is enabled - changes will restart the server")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Set development environment variables
    os.environ.setdefault("DEBUG", "true")
    os.environ.setdefault("LOG_LEVEL", "DEBUG")
    os.environ.setdefault("HOST", "0.0.0.0")
    os.environ.setdefault("PORT", "3104")
    
    # Run with uvicorn
    cmd = [
        "python", "-m", "uvicorn",
        "as_call_service.main:app",
        "--host", "0.0.0.0",
        "--port", "3104",
        "--reload",
        "--log-level", "debug",
        "--app-dir", "src",
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Development server stopped!")


def run_production_server():
    """Run production server."""
    print("🏭 Starting as-call-service production server...")
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Set production environment variables
    os.environ.setdefault("DEBUG", "false")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("HOST", "0.0.0.0")
    os.environ.setdefault("PORT", "3104")
    
    # Run with uvicorn
    cmd = [
        "python", "-m", "uvicorn",
        "as_call_service.main:app",
        "--host", "0.0.0.0",
        "--port", "3104",
        "--workers", "4",
        "--log-level", "info",
        "--app-dir", "src",
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Production server stopped!")


def check_dependencies():
    """Check if all required dependencies are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "asyncpg",
        "httpx",
        "pytest",
        "python-jose",
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("💡 Install with: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All dependencies are installed!")
        return True


def setup_environment():
    """Setup development environment."""
    print("⚙️  Setting up development environment...")
    
    project_dir = Path(__file__).parent
    env_file = project_dir / ".env"
    env_example = project_dir / ".env.example"
    
    # Copy .env.example to .env if it doesn't exist
    if not env_file.exists() and env_example.exists():
        print("📋 Copying .env.example to .env...")
        env_file.write_text(env_example.read_text())
        print("✅ .env file created!")
        print("💡 Please update .env with your actual configuration values")
    elif env_file.exists():
        print("✅ .env file already exists")
    else:
        print("⚠️  No .env.example file found")
    
    # Create logs directory
    logs_dir = project_dir / "logs"
    if not logs_dir.exists():
        logs_dir.mkdir()
        print("✅ Created logs directory")
    
    print("✅ Development environment setup complete!")


def run_quick_test():
    """Run a quick smoke test."""
    print("🧪 Running quick smoke test...")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/unit/test_validation_service.py::TestValidationService::test_validate_phone_number_valid_formats",
        "-v"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, cwd=Path(__file__).parent)
        print("✅ Quick test passed!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Quick test failed!")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Development tools for as-call-service")
    parser.add_argument(
        "action",
        nargs="?",
        choices=["dev", "prod", "setup", "check", "test"],
        default="dev",
        help="Action to perform"
    )
    
    args = parser.parse_args()
    
    if args.action == "dev":
        if check_dependencies():
            run_dev_server()
        else:
            sys.exit(1)
    elif args.action == "prod":
        if check_dependencies():
            run_production_server()
        else:
            sys.exit(1)
    elif args.action == "setup":
        setup_environment()
    elif args.action == "check":
        success = check_dependencies()
        sys.exit(0 if success else 1)
    elif args.action == "test":
        success = run_quick_test()
        sys.exit(0 if success else 1)
    else:
        print("Unknown action. Use --help for available options.")