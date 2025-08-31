#!/bin/bash
# PayMCP Quick Test Script
# Runs basic validation and unit tests

echo "🚀 PayMCP Quick Test Starting..."
echo "================================"

# Setup environment
echo "📋 Setting up environment..."
python scripts/setup_test_env.py

if [ $? -eq 0 ]; then
    echo "✅ Environment setup completed"
else
    echo "❌ Environment setup failed"
    exit 1
fi

echo ""
echo "🧪 Running unit tests..."
python scripts/test_all_providers.py --unit-only --verbose

echo ""
echo "🎉 Quick test completed!"