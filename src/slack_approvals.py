"""
Slack Approvals Service for AI News Channel
Sends draft videos/scripts to Slack for human review before publishing
"""
import os
import json
import time
import hashlib
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import requests

class SlackApprovalService:
    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.channel = os.getenv("SLACK_APPROVAL_CHANNEL", "#approvals")
        self.approval_timeout = int(os.getenv("SLACK_APPROVAL_TIMEOUT", "3600"))  # 1 hour default
        
        if not self.webhook_url and not self.bot_token:
            raise ValueError("Either SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN must be set")
    
    def send_approval_request(self, 
                             content_type: str,
                             title: str,
                             preview_url: str,
                             metadata: Dict,
                             approval_id: Optional[str] = None) -> str:
        """
        Send approval request to Slack
        
        Args:
            content_type: 'video', 'script', or 'thumbnail'
            title: Content title
            preview_url: URL to preview content
            metadata: Additional metadata (duration, word count, etc)
            approval_id: Unique ID for tracking (auto-generated if not provided)
        
        Returns:
            Approval ID for tracking
        """
        if not approval_id:
            # Generate unique approval ID
            timestamp = datetime.now().isoformat()
            content = f"{content_type}-{title}-{timestamp}"
            approval_id = hashlib.md5(content.encode()).hexdigest()[:12]
        
        # Build Slack message
        message = self._build_approval_message(
            approval_id, content_type, title, preview_url, metadata
        )
        
        # Send via webhook or API
        if self.webhook_url:
            self._send_via_webhook(message)
        else:
            self._send_via_api(message)
        
        return approval_id
    
    def _build_approval_message(self, approval_id: str, content_type: str,
                               title: str, preview_url: str, 
                               metadata: Dict) -> Dict:
        """Build rich Slack message with approval buttons"""
        
        # Format metadata
        metadata_text = "\n".join([f"• *{k}*: {v}" for k, v in metadata.items()])
        
        # Emoji based on content type
        emoji = {
            "video": "🎬",
            "script": "📝",
            "thumbnail": "🖼️"
        }.get(content_type, "📄")
        
        return {
            "text": f"{emoji} Approval Request: {title}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} {content_type.upper()} Approval Required"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Title:* {title}\n*Type:* {content_type}\n*ID:* `{approval_id}`"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Details:*\n{metadata_text}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"<{preview_url}|🔗 Preview Content>"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "actions",
                    "block_id": f"approval_{approval_id}",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✅ Approve"
                            },
                            "style": "primary",
                            "action_id": f"approve_{approval_id}",
                            "value": approval_id
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "❌ Reject"
                            },
                            "style": "danger",
                            "action_id": f"reject_{approval_id}",
                            "value": approval_id
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✏️ Request Changes"
                            },
                            "action_id": f"changes_{approval_id}",
                            "value": approval_id
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"⏱️ Expires <t:{int(time.time() + self.approval_timeout)}:R>"
                        }
                    ]
                }
            ]
        }
    
    def _send_via_webhook(self, message: Dict):
        """Send message via webhook URL"""
        response = requests.post(self.webhook_url, json=message)
        response.raise_for_status()
    
    def _send_via_api(self, message: Dict):
        """Send message via Slack API"""
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "channel": self.channel,
            **message
        }
        
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        result = response.json()
        if not result.get("ok"):
            raise Exception(f"Slack API error: {result.get('error')}")
    
    def wait_for_approval(self, approval_id: str, 
                         poll_interval: int = 30) -> Tuple[str, Optional[str]]:
        """
        Wait for approval decision
        
        Args:
            approval_id: The approval ID to wait for
            poll_interval: How often to check (seconds)
        
        Returns:
            Tuple of (status, feedback)
            status: 'approved', 'rejected', 'changes_requested', or 'timeout'
            feedback: Optional feedback message
        """
        # In production, this would check a database or cache
        # where the Slack webhook handler stores responses
        
        start_time = time.time()
        approval_file = f"/tmp/slack_approval_{approval_id}.json"
        
        while time.time() - start_time < self.approval_timeout:
            if os.path.exists(approval_file):
                with open(approval_file, 'r') as f:
                    result = json.load(f)
                os.remove(approval_file)  # Clean up
                return result["status"], result.get("feedback")
            
            time.sleep(poll_interval)
        
        return "timeout", None
    
    def send_publish_notification(self, title: str, url: str, 
                                 platform: str, stats: Dict):
        """Send notification after successful publish"""
        
        stats_text = " | ".join([f"{k}: {v}" for k, v in stats.items()])
        
        message = {
            "text": f"✅ Published: {title}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🎉 Content Published Successfully!"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Title:* {title}\n*Platform:* {platform}\n*URL:* <{url}|View Published Content>"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"📊 {stats_text}"
                        }
                    ]
                }
            ]
        }
        
        if self.webhook_url:
            self._send_via_webhook(message)
        else:
            self._send_via_api(message)

# Webhook handler (for receiving Slack interactions)
class SlackWebhookHandler:
    """
    Handle incoming webhooks from Slack interactions
    This would typically run as a separate service
    """
    
    def handle_interaction(self, payload: Dict):
        """Process Slack interaction payload"""
        
        # Extract action details
        action = payload.get("actions", [{}])[0]
        action_id = action.get("action_id", "")
        approval_id = action.get("value", "")
        user = payload.get("user", {}).get("username", "unknown")
        
        # Determine status from action
        if action_id.startswith("approve_"):
            status = "approved"
        elif action_id.startswith("reject_"):
            status = "rejected"
        elif action_id.startswith("changes_"):
            status = "changes_requested"
        else:
            return
        
        # Store result for polling
        result = {
            "status": status,
            "user": user,
            "timestamp": datetime.now().isoformat(),
            "feedback": None  # Could prompt for feedback in modal
        }
        
        # Save to temp file (in production, use database)
        approval_file = f"/tmp/slack_approval_{approval_id}.json"
        with open(approval_file, 'w') as f:
            json.dump(result, f)
        
        # Update message to show decision
        self._update_message(payload, status, user)
    
    def _update_message(self, payload: Dict, status: str, user: str):
        """Update original message to show decision"""
        
        status_emoji = {
            "approved": "✅",
            "rejected": "❌",
            "changes_requested": "✏️"
        }.get(status, "❓")
        
        # Add status block to original message
        blocks = payload.get("message", {}).get("blocks", [])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{status_emoji} *Decision:* {status.replace('_', ' ').title()} by @{user}"
            }
        })
        
        # Remove action buttons
        blocks = [b for b in blocks if b.get("type") != "actions"]
        
        return {
            "replace_original": True,
            "blocks": blocks
        }

# Example usage
if __name__ == "__main__":
    # Initialize service
    service = SlackApprovalService()
    
    # Send approval request for a video
    approval_id = service.send_approval_request(
        content_type="video",
        title="Today in AI - November 15, 2024",
        preview_url="https://storage.googleapis.com/preview/video.mp4",
        metadata={
            "Duration": "5:32",
            "File Size": "125 MB",
            "Resolution": "1920x1080",
            "Script Words": "832"
        }
    )
    
    print(f"Approval request sent: {approval_id}")
    
    # Wait for approval
    status, feedback = service.wait_for_approval(approval_id)
    print(f"Approval status: {status}")
    
    if status == "approved":
        # Publish and notify
        service.send_publish_notification(
            title="Today in AI - November 15, 2024",
            url="https://youtube.com/watch?v=abc123",
            platform="YouTube",
            stats={
                "Views": "0",
                "Duration": "5:32",
                "Published": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        )