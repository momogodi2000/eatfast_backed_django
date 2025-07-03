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

# Handle migrations with potential conflicts
echo "🔄 Handling migrations..."

# Check if this is a fresh database or has existing migrations
if python manage.py showmigrations --plan | grep -q "admin.*\[X\]"; then
    echo "📝 Existing migrations detected - fixing migration history..."
    
    # Fix migration dependency issues
    echo "⚡ Fake-applying core Django migrations..."
    python manage.py migrate admin 0001 --fake 2>/dev/null || true
    python manage.py migrate auth 0001 --fake 2>/dev/null || true
    python manage.py migrate contenttypes 0001 --fake 2>/dev/null || true
    python manage.py migrate sessions 0001 --fake 2>/dev/null || true
    
    # Apply our backend migrations with fake-initial
    echo "🗄️ Applying backend migrations with fake-initial..."
    python manage.py migrate backend --fake-initial
    
    # Apply all remaining migrations
    echo "🔄 Applying remaining migrations..."
    python manage.py migrate
else
    echo "🆕 Fresh database detected - creating migrations..."
    python manage.py makemigrations --verbosity 2
    
    echo "🗄️ Applying all migrations..."
    python manage.py migrate --verbosity 2
fi

echo "✅ Build completed successfully!"