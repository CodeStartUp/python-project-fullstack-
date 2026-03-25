#!/bin/bash

echo "Stopping application..."
pkill -f uvicorn || true
echo "Application stopped"

read -p "Do you want to stop MongoDB container? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker stop mongodb-hwid
    echo "MongoDB stopped"
fi
