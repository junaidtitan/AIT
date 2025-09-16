#!/bin/bash
#
# Artifact Cleanup Script
# Run this periodically via cron to clean up old pipeline artifacts
#

cd /home/junaidqureshi/AIT

echo "========================================="
echo "Pipeline Artifact Cleanup"
echo "Time: $(date)"
echo "========================================="

# Load configuration if exists
if [ -f "cleanup_config.json" ]; then
    echo "Using cleanup_config.json configuration"
    python3 src/utils/artifact_cleanup.py --load-config cleanup_config.json
else
    echo "Using default moderate strategy"
    python3 src/utils/artifact_cleanup.py --strategy moderate
fi

echo "========================================="
echo "Cleanup completed"
echo "========================================="