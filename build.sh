#!/usr/bin/env bash
# final_build.sh - Force reset database to resolve migration conflicts
set -o errexit

echo "🚀 Starting Render deployment build (force reset)..."

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
python manage.py collectstatic --no-input

# Force reset all migration tables in the database
echo "🔄 Force resetting database migration history..."

# Create a Python script to reset the database
cat << 'EOF' > reset_db.py
import os
import django
from django.conf import settings
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eatfast_backend.settings')
django.setup()

def reset_migration_tables():
    with connection.cursor() as cursor:
        try:
            # Drop the django_migrations table to start fresh
            cursor.execute("DROP TABLE IF EXISTS django_migrations CASCADE;")
            print("✓ Dropped django_migrations table")
            
            # Drop all Django auth/admin tables that might cause conflicts
            tables_to_drop = [
                'auth_permission',
                'auth_group', 
                'auth_group_permissions',
                'auth_user',
                'auth_user_groups',
                'auth_user_user_permissions',
                'django_admin_log',
                'django_content_type',
                'django_session'
            ]
            
            for table in tables_to_drop:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                    print(f"✓ Dropped {table} table")
                except Exception as e:
                    print(f"- Could not drop {table}: {e}")
            
            # Drop our backend tables if they exist
            backend_tables = [
                'backend_user',
                'backend_user_groups', 
                'backend_user_user_permissions',
                'backend_contactmessage',
                'backend_contactresponse',
                'backend_partnerapplication',
                'backend_partnerdocument',
                'backend_contactanalytics',
                'backend_partneranalytics'
            ]
            
            for table in backend_tables:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                    print(f"✓ Dropped {table} table")
                except Exception as e:
                    print(f"- Could not drop {table}: {e}")
                    
            print("✅ Database reset completed")
            
        except Exception as e:
            print(f"❌ Error resetting database: {e}")
            # Continue anyway - might be a fresh database

if __name__ == '__main__':
    reset_migration_tables()
EOF

# Run the database reset
echo "🗄️ Resetting database..."
python reset_db.py

# Remove the reset script
rm reset_db.py

# Remove any existing migration files
echo "📝 Removing existing migration files..."
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete 2>/dev/null || true
find . -path "*/migrations/*.pyc" -delete 2>/dev/null || true

# Create fresh migrations
echo "📝 Creating fresh migrations..."
python manage.py makemigrations backend

# Apply all migrations from scratch
echo "🗄️ Applying fresh migrations..."
python manage.py migrate

echo "✅ Build completed successfully!"