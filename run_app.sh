#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Check if MongoDB is running
if ! docker ps | grep -q mongodb-hwid; then
    echo "Starting MongoDB..."
    docker start mongodb-hwid
    sleep 3
fi

# Run the application
echo "Starting HWID Authentication System..."
echo "Access at: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
