#!/bin/bash
# Script to setup database and run migrations

set -e

echo "=========================================="
echo "Database Setup Script"
echo "=========================================="

# Check if .env exists, if not create from example
if [ ! -f .env ]; then
    echo "Creating .env file from docker-compose defaults..."
    cat > .env << EOF
# Database Configuration
POSTGRES_DB=hue_portal
POSTGRES_USER=hue
POSTGRES_PASSWORD=huepass
POSTGRES_HOST=localhost
POSTGRES_PORT=5433

# Django Configuration
DJANGO_SECRET_KEY=change-me-in-production-use-secure-random-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=*

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS=true
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
EOF
    echo "✅ Created .env file"
else
    echo "✅ .env file already exists"
fi

# Start database container
echo ""
echo "Starting PostgreSQL container..."
docker compose up -d db || docker-compose up -d db

# Wait for database to be ready
echo "Waiting for database to be ready..."
sleep 5

# Enable extensions
echo ""
echo "Enabling PostgreSQL extensions..."
docker exec tryhardemnayproject-db-1 psql -U hue -d hue_portal -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" || echo "⚠️ pg_trgm extension"
docker exec tryhardemnayproject-db-1 psql -U hue -d hue_portal -c "CREATE EXTENSION IF NOT EXISTS unaccent;" || echo "⚠️ unaccent extension"

# Verify extensions
echo ""
echo "Verifying extensions..."
docker exec tryhardemnayproject-db-1 psql -U hue -d hue_portal -c "SELECT extname, extversion FROM pg_extension WHERE extname IN ('pg_trgm', 'unaccent');"

echo ""
echo "=========================================="
echo "Database setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Run migrations: cd backend/hue_portal && python manage.py migrate"
echo "2. Generate embeddings: python backend/scripts/generate_embeddings.py"
echo "3. Seed synonyms: python backend/scripts/seed_synonyms.py"

