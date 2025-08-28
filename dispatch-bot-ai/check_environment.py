#!/usr/bin/env python3
"""
Environment Configuration Checker for Never Missed Call AI

This script validates that your environment is properly configured for Phase 1.
Run this before starting development to ensure all required API keys are set.
"""

import sys
from pathlib import Path

# Add src directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dispatch_bot.config.phase1_settings import validate_environment


def main():
    """Check environment configuration and display results."""
    print("🔍 Never Missed Call AI - Environment Configuration Check")
    print("=" * 60)
    
    validation = validate_environment()
    
    # Display environment info
    env_info = validation.get("environment", {})
    print(f"📱 App: {env_info.get('app_name', 'Unknown')}")
    print(f"🔢 Version: {env_info.get('version', 'Unknown')}")
    print(f"🐛 Debug Mode: {env_info.get('debug', 'Unknown')}")
    print(f"📝 Log Level: {env_info.get('log_level', 'Unknown')}")
    print()
    
    # Check API keys status
    print("🔑 API Keys Status:")
    print("-" * 20)
    
    if validation["valid"]:
        print("✅ All required API keys are configured!")
        print("   - Google Maps API Key: ✅ Set")
        print("   - OpenAI API Key: ✅ Set")
    else:
        print("❌ Missing required API keys:")
        for key in validation["missing_keys"]:
            print(f"   - {key}: ❌ Not set")
        
        print("\n💡 Instructions:")
        for warning in validation["warnings"]:
            print(f"   {warning}")
        
        print(f"\n📝 To fix this:")
        print(f"   1. Edit the .env file in your project root")
        print(f"   2. Add your API keys:")
        for key in validation["missing_keys"]:
            print(f"      {key}=your_actual_api_key_here")
        print(f"   3. Save the file and run this check again")
    
    print()
    print("📁 Configuration Files:")
    print("-" * 25)
    
    project_root = Path(__file__).parent
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    
    print(f"   .env file: {'✅ Found' if env_file.exists() else '❌ Missing'}")
    print(f"   .env.example: {'✅ Found' if env_example.exists() else '❌ Missing'}")
    
    if not env_file.exists():
        print(f"\n   📝 To create .env file:")
        print(f"      cp .env.example .env")
    
    print()
    
    if validation["valid"]:
        print("🎉 Environment is ready for Phase 1 development!")
        return 0
    else:
        print("⚠️  Please configure missing API keys before continuing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())