#!/bin/bash
DATE=$(date +%Y-%m-%d_%H-%M)
tar -czf "/root/reclaw-backups/reclaw-$DATE.tar.gz" \
  --exclude='__pycache__' \
  --exclude='*.log' \
  /root/ReClaw-2.0
echo "Backup created: reclaw-$DATE.tar.gz"
