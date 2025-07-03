#!/usr/bin/env bash
# fix_migrations.sh
# Script to fix migration history issues

set -o errexit

echo "🔧 Fixing Django migration history issues..."

# Option 1: Reset all migrations and start fresh
echo "📝 Resetting migration history..."

# Fake-apply Django's built-in migrations first
echo "⚡ Fake-applying Django admin migrations..."
python manage.py migrate admin 0001 --fake

echo "⚡ Fake-applying Django auth migrations..."
python manage.py migrate auth 0001 --fake

echo "⚡ Fake-applying Django contenttypes migrations..."
python manage.py migrate contenttypes 0001 --fake

echo "⚡ Fake-applying Django sessions migrations..."
python manage.py migrate sessions 0001 --fake

# Now apply our backend migrations
echo "🗄️ Applying backend migrations..."
python manage.py migrate backend 0001 --fake-initial

# Apply remaining migrations normally
echo "🔄 Applying all remaining migrations..."
python manage.py migrate

echo "✅ Migration fix completed!"