#!/usr/bin/env python3
"""Test Slack with channel ID"""
import os, sys, subprocess
sys.path.insert(0, "/home/junaidqureshi/AIT")

# Load token
os.environ["SLACK_BOT_TOKEN"] = subprocess.check_output(
    ["gcloud", "secrets", "versions", "access", "latest", "--secret=SLACK_BOT_TOKEN"],
    stderr=subprocess.DEVNULL
).decode().strip()

from src.slack_approvals import SlackApprovalService
import uuid

print("Testing Slack with channel ID fix...")

# Temporarily update to use channel ID
slack = SlackApprovalService()
slack.channel = "C09FQQX8ZAM"  # Use channel ID directly

try:
    approval_id = slack.send_approval_request(
        content_type="video",
        title="TEST: Shotstack Pipeline Working!",
        preview_url="https://storage.googleapis.com/yta-main-assets/test.mp4",
        metadata={
            "Status": "✅ Shotstack rendering successful",
            "Render Time": "30 seconds",
            "Cost": "$0.002 (vs Pictory $0.50)",
            "Savings": "250x cheaper!",
            "Video": "8MB, 23 seconds"
        },
        approval_id=str(uuid.uuid4())
    )
    print(f"✅ Success! Approval request sent: {approval_id}")
    print("Check #ai-news-approvals channel in Slack")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

