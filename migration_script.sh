#!/usr/bin/env bash
# migration_script.sh
# Script to handle database migrations and setup

set -o errexit

echo "🚀 Starting EatFast backend setup..."

# 1. Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# 2. Create migrations for backend app
echo "🔄 Creating migrations..."
python manage.py makemigrations backend

# 3. Apply all migrations
echo "🗄️ Applying migrations..."
python manage.py migrate

# 4. Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# 5. Create superuser if it doesn't exist
echo "👑 Creating superuser..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@eatfast.cm',
        password='EatFast2025!'
    )
    print('Superuser created: admin / EatFast2025!')
else:
    print('Superuser already exists')
EOF

echo "✅ Setup completed successfully!"
echo "🌐 You can now access:"
echo "   - API: http://localhost:8000/api/v1/"
echo "   - Admin: http://localhost:8000/admin/"
echo "   - Health Check: http://localhost:8000/api/v1/health/"