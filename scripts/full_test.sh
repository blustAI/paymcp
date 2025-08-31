#!/bin/bash
# PayMCP Full Test Suite Script
# Runs comprehensive testing including performance benchmarks

echo "🧪 PayMCP Full Test Suite Starting..."
echo "====================================="

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
echo "🔍 Running comprehensive tests..."
python scripts/test_all_providers.py --verbose --performance

echo ""
echo "📊 Test suite completed!"
echo ""
echo "💡 Next steps:"
echo "  • Review any failed tests above"
echo "  • Check credentials for missing providers"
echo "  • Run integration tests with: python scripts/test_all_providers.py --integration"