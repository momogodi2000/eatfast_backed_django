#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting Render deployment build..."

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p staticfiles
mkdir -p media
mkdir -p logs

# Collect static files
echo "🎨 Collecting static files..."
python manage.py collectstatic --no-input --verbosity 2

# Make migrations
echo "🔄 Creating migrations..."
python manage.py makemigrations --verbosity 2

# Apply migrations
echo "🗄️ Applying migrations..."
python manage.py migrate --verbosity 2

echo "✅ Build completed successfully!"