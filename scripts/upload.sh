#!/bin/bash

# Upload script for llm-warehouse package

set -e

if [ "$1" == "--test" ]; then
    echo "🧪 Uploading to TestPyPI..."
    twine upload --repository testpypi dist/*
    echo "✅ Uploaded to TestPyPI!"
    echo "📦 Test installation: pip install --index-url https://test.pypi.org/simple/ llm-warehouse"
elif [ "$1" == "--prod" ]; then
    echo "🚀 Uploading to PyPI..."
    twine upload dist/*
    echo "✅ Uploaded to PyPI!"
    echo "📦 Install with: pip install llm-warehouse"
else
    echo "Usage: $0 [--test|--prod]"
    echo "  --test: Upload to TestPyPI"
    echo "  --prod: Upload to production PyPI"
    exit 1
fi
