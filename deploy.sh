#!/bin/bash

# LLM Warehouse Python Package Deployment Script
# This script builds, versions, and publishes the package to PyPI

set -e  # Exit on any error

echo "🐍 Starting LLM Warehouse Python Package Deployment"
echo "==================================================="

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: pyproject.toml not found. Make sure you're in the llm-warehouse-package directory."
    exit 1
fi

# Check if required tools are installed
echo "🔍 Checking required tools..."

if ! command -v python3 > /dev/null 2>&1; then
    echo "❌ Error: python3 not found. Please install Python 3.9+."
    exit 1
fi

if ! python3 -c "import build" > /dev/null 2>&1; then
    echo "⚠️  'build' package not found. Installing..."
    pip install build
fi

if ! python3 -c "import twine" > /dev/null 2>&1; then
    echo "⚠️  'twine' package not found. Installing..."
    pip install twine
fi

echo "✅ Required tools verified"

# Check PyPI authentication
echo "🔍 Checking PyPI authentication..."
if [ ! -f "$HOME/.pypirc" ] && [ -z "$TWINE_USERNAME" ] && [ -z "$TWINE_PASSWORD" ]; then
    echo "⚠️  PyPI credentials not found."
    echo "💡 You can configure them by:"
    echo "   1. Creating ~/.pypirc file, or"
    echo "   2. Setting TWINE_USERNAME and TWINE_PASSWORD environment variables, or" 
    echo "   3. You'll be prompted during upload"
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/
rm -rf build/
rm -rf *.egg-info/

# Run tests if available
echo "🧪 Running tests..."
if [ -f "pytest.ini" ] || [ -f "setup.cfg" ] || [ -d "tests/" ]; then
    if command -v pytest > /dev/null 2>&1; then
        echo "Running pytest..."
        pytest || echo "⚠️  Some tests failed, but continuing..."
    elif python3 -m pytest --version > /dev/null 2>&1; then
        echo "Running python -m pytest..."
        python3 -m pytest || echo "⚠️  Some tests failed, but continuing..."
    else
        echo "⚠️  pytest not found, skipping tests"
    fi
else
    echo "⚠️  No test configuration found, skipping tests"
fi

# Get current version from pyproject.toml
current_version=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])" 2>/dev/null || \
                 python3 -c "import tomli; print(tomli.load(open('pyproject.toml', 'rb'))['project']['version'])" 2>/dev/null || \
                 grep -E '^version\s*=' pyproject.toml | sed 's/.*"\(.*\)".*/\1/')

echo ""
echo "📝 Current version: $current_version"
echo ""
echo "What type of version bump would you like?"
echo "1) patch (0.1.1 -> 0.1.2) - bug fixes"
echo "2) minor (0.1.1 -> 0.2.0) - new features" 
echo "3) major (0.1.1 -> 1.0.0) - breaking changes"
echo "4) custom - enter specific version"
echo "5) skip version bump"
echo ""
read -p "Enter choice (1-5) [default: 1]: " version_choice

case $version_choice in
    2)
        # Minor bump: 0.1.1 -> 0.2.0
        IFS='.' read -ra ADDR <<< "$current_version"
        new_version="${ADDR[0]}.$((${ADDR[1]} + 1)).0"
        ;;
    3)
        # Major bump: 0.1.1 -> 1.0.0  
        IFS='.' read -ra ADDR <<< "$current_version"
        new_version="$((${ADDR[0]} + 1)).0.0"
        ;;
    4)
        # Custom version
        read -p "Enter new version: " new_version
        if [ -z "$new_version" ]; then
            echo "❌ No version provided"
            exit 1
        fi
        ;;
    5)
        # Skip version bump
        new_version="$current_version"
        ;;
    *)
        # Patch bump: 0.1.1 -> 0.1.2 (default)
        IFS='.' read -ra ADDR <<< "$current_version"
        new_version="${ADDR[0]}.${ADDR[1]}.$((${ADDR[2]} + 1))"
        ;;
esac

# Check git status
echo "🔍 Checking git status..."
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  Git working directory is not clean"
    echo "📋 Uncommitted changes:"
    git status --porcelain
    echo ""
    read -p "Do you want to commit these changes first? (y/N): " commit_changes
    
    if [[ $commit_changes =~ ^[Yy]$ ]]; then
        echo "📝 Committing changes..."
        git add .
        read -p "Enter commit message: " commit_message
        if [ -z "$commit_message" ]; then
            commit_message="Update package for deployment"
        fi
        git commit -m "$commit_message"
        echo "✅ Changes committed"
    else
        echo "⚠️  Proceeding with uncommitted changes"
    fi
else
    echo "✅ Git working directory is clean"
fi

# Update version in pyproject.toml if changed
if [ "$new_version" != "$current_version" ]; then
    echo "📈 Updating version from $current_version to $new_version..."
    
    # Update version in pyproject.toml
    if command -v sed > /dev/null 2>&1; then
        # Use sed to update version
        sed -i.bak "s/version = \"$current_version\"/version = \"$new_version\"/" pyproject.toml
        rm pyproject.toml.bak
    else
        echo "❌ sed not found. Please manually update version in pyproject.toml"
        exit 1
    fi
    
    echo "✅ Version updated to: $new_version"
    
    # Commit version change if git is clean
    if git diff-index --quiet HEAD -- pyproject.toml; then
        echo "⚠️  No version change detected in git"
    else
        git add pyproject.toml
        git commit -m "Bump version to $new_version"
        echo "✅ Version change committed"
    fi
else
    echo "⏭️  Skipping version bump"
fi

# Build the package
echo "🔨 Building Python package..."
python3 -m build

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Build successful"

# Show what will be published
echo ""
echo "📦 Package contents:"
ls -la dist/
echo ""
echo "📋 Package info:"
python3 -m twine check dist/*

# Confirmation
echo ""
echo "🚨 Ready to publish to PyPI!"
echo "Package: llm-warehouse"
echo "Version: $new_version"
echo "Files: $(ls dist/)"
echo ""
read -p "Do you want to continue with publishing? (y/N): " confirm

if [[ $confirm =~ ^[Yy]$ ]]; then
    echo "🚀 Publishing to PyPI..."
    
    # Upload to PyPI
    python3 -m twine upload dist/*
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "🎉 SUCCESS! Package published successfully!"
        echo "✅ Package: llm-warehouse@$new_version"
        echo "🌐 PyPI URL: https://pypi.org/project/llm-warehouse/"
        echo "📥 Install with: pip install llm-warehouse"
        echo ""
        echo "🔗 Useful commands:"
        echo "   pip show llm-warehouse"
        echo "   pip install llm-warehouse==$new_version"
        echo ""
        
        # Create and push git tag for the version
        if [ "$new_version" != "$current_version" ]; then
            echo "🏷️  Creating git tag v$new_version..."
            git tag "v$new_version"
            echo "✅ Git tag v$new_version created"
            
            echo "📤 Pushing git changes and tags..."
            git push origin HEAD
            git push origin "v$new_version"
            echo "✅ Git changes and tags pushed to remote"
        fi
    else
        echo "❌ Publishing failed!"
        exit 1
    fi
else
    echo "❌ Publishing cancelled by user"
    exit 1
fi

echo "🏁 Deployment complete!"
