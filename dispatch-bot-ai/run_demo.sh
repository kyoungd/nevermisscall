#!/bin/bash
# Never Missed Call AI - Demo Console Runner
# This script sets up the environment and runs the interactive demo

echo "🔧 Never Missed Call AI - Production Demo"
echo "=========================================="  
echo "⚠️  This demo uses REAL APIs and may incur costs"

# Check if we're in the right directory
if [ ! -d "src/dispatch_bot" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    echo "   cd /home/young/Desktop/Code/nvermisscall/nmc-ai"
    echo "   ./run_demo.sh"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "   Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check for API keys
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY environment variable not set"
    echo "   Export your OpenAI API key:"
    echo "   export OPENAI_API_KEY='your_openai_api_key_here'"
    exit 1
fi

if [ -z "$GOOGLE_MAPS_API_KEY" ]; then
    echo "❌ Error: GOOGLE_MAPS_API_KEY environment variable not set"
    echo "   Export your Google Maps API key:"
    echo "   export GOOGLE_MAPS_API_KEY='your_google_maps_api_key_here'"
    exit 1
fi

echo "🔑 API Keys Found:"
echo "   ✅ OpenAI API Key: ${OPENAI_API_KEY:0:8}..."
echo "   ✅ Google Maps API Key: ${GOOGLE_MAPS_API_KEY:0:8}..."
echo ""

echo "🚀 Starting production demo console..."
echo "   This will make real API calls to OpenAI GPT-4o and Google Maps"
echo "   Press Ctrl+C to exit at any time"
echo "   Type 'quit' to exit normally"
echo "   Type 'reset' to start a new conversation"
echo ""

# Run the demo with proper Python path
PYTHONPATH=src ./venv/bin/python demo_console.py