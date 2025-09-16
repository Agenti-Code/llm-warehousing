#!/bin/bash

# Build script for llm-warehouse package

set -e

echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info/

echo "📦 Building package..."
python -m build

echo "✅ Build complete! Files:"
ls -la dist/

echo ""
echo "📋 Next steps:"
echo "1. Test the package: pip install dist/llm_warehouse-*.whl"
echo "2. Upload to TestPyPI: twine upload --repository testpypi dist/*"
echo "3. Test from TestPyPI: pip install --index-url https://test.pypi.org/simple/ llm-warehouse"
echo "4. Upload to PyPI: twine upload dist/*"
