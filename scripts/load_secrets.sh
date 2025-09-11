#!/usr/bin/env bash
set -euo pipefail

fetch() { gcloud secrets versions access latest --secret="$1" 2>/dev/null || true; }

# Core secrets
export OPENAI_API_KEY="${OPENAI_API_KEY:-$(fetch OPENAI_API_KEY)}"
export ELEVENLABS_API_KEY="${ELEVENLABS_API_KEY:-$(fetch ELEVENLABS_API_KEY)}"
export ELEVENLABS_VOICE_ID="${ELEVENLABS_VOICE_ID:-wBXNqKUATyqu0RtYt25i}"

# YouTube (prefer refresh token for headless VM)
export YOUTUBE_REFRESH_TOKEN="${YOUTUBE_REFRESH_TOKEN:-$(fetch YOUTUBE_REFRESH_TOKEN)}"

# Slack
export SLACK_BOT_TOKEN="${SLACK_BOT_TOKEN:-$(fetch SLACK_BOT_TOKEN)}"
export SLACK_SIGNING_SECRET="${SLACK_SIGNING_SECRET:-$(fetch SLACK_SIGNING_SECRET)}"
export SLACK_CHANNEL_ID="${SLACK_CHANNEL_ID:-$(fetch SLACK_CHANNEL_ID)}"
export SLACK_APPROVER_USER="${SLACK_APPROVER_USER:-$(fetch SLACK_APPROVER_USER)}"

# Editors (optional)
export PICTORY_CLIENT_ID="${PICTORY_CLIENT_ID:-$(fetch PICTORY_CLIENT_ID)}"
export PICTORY_CLIENT_SECRET="${PICTORY_CLIENT_SECRET:-$(fetch PICTORY_CLIENT_SECRET)}"

# Prefect
export PREFECT_API_KEY="${PREFECT_API_KEY:-$(fetch PREFECT_API_KEY)}"

# App defaults
export APPROVAL_MODE="${APPROVAL_MODE:-manual}"
export TIMEZONE="${TIMEZONE:-America/Los_Angeles}"
export PUBLISH_HOUR_PT="${PUBLISH_HOUR_PT:-18}"
export YOUTUBE_UPLOAD="${YOUTUBE_UPLOAD:-true}"
