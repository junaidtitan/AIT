# Google Sheets Service Account Setup

## ⚠️ Service Account Key Needs Recreation

The service account key file was lost during the git restore. Follow these steps to recreate it:

## 📋 Prerequisites

1. Google Cloud Project with Sheets API enabled
2. Service account with appropriate permissions
3. Access to the Google Sheet: `1J4d4S0mnBeWn5hfHhnc97SPusn9ejz4jWE9oQtK0mgU`

## 🔧 Step-by-Step Setup

### 1. Create Service Account Key

```bash
# List your service accounts
gcloud iam service-accounts list

# Create a new key for your service account
# Replace SERVICE_ACCOUNT_EMAIL with your actual service account email
gcloud iam service-accounts keys create \
    /home/junaidqureshi/AIT/sheets_service_account.json \
    --iam-account=SERVICE_ACCOUNT_EMAIL
```

### 2. Alternative: Create via Console

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to IAM & Admin → Service Accounts
3. Find your service account (or create new one)
4. Click on the service account
5. Go to "Keys" tab
6. Add Key → Create new key → JSON
7. Save as `/home/junaidqureshi/AIT/sheets_service_account.json`

### 3. Share the Google Sheet

1. Open the sheet: https://docs.google.com/spreadsheets/d/1J4d4S0mnBeWn5hfHhnc97SPusn9ejz4jWE9oQtK0mgU
2. Click "Share" button
3. Add the service account email (found in the JSON key file)
4. Give "Editor" permissions
5. Click "Send"

### 4. Required Sheet Structure

The Google Sheet should have these tabs:

#### Sources Tab
| Column | Field | Example |
|--------|-------|---------|
| A | Name | OpenAI Blog |
| B | URL | https://openai.com/blog/rss.xml |
| D | Category | company |
| F | Priority | 10 |
| G | Enabled | Yes |

#### Companies Tab
| Column | Field | Example |
|--------|-------|---------|
| A | Company | OpenAI |
| B | Aliases | openai, open ai |
| C | Products | gpt, chatgpt, dall-e |

#### Scoring Tab
| Column | Field | Example |
|--------|-------|---------|
| A | Metric | news_freshness_1h |
| B | Weight | 40 |

#### Article Log Tab (auto-created)
Used for logging top articles back to the sheet.

#### Trending Tab (optional)
Created when YouTube trending is enabled.

## 🧪 Test the Setup

```bash
# Test the connection
python3 -c "
from src.ingest.simple_sheets_manager import SimpleSheetsManager
import asyncio

async def test():
    manager = SimpleSheetsManager()
    sources = manager.get_sources()
    print(f'✅ Connected! Found {len(sources)} sources')

asyncio.run(test())
"
```

## 🚨 Troubleshooting

### "Request had insufficient authentication scopes"
- The service account needs the Sheets API scope
- Recreate the key if needed

### "Permission denied"
- Make sure the sheet is shared with the service account email
- Check that the service account has Editor permissions

### Using Default Credentials Instead
If you can't create a service account key, the system will try to use Application Default Credentials:

```bash
# Authenticate with your Google account
gcloud auth application-default login

# Make sure you have access to the sheet with your account
```

## 📝 Notes

- The service account email typically looks like: `name@project-id.iam.gserviceaccount.com`
- The JSON key file contains sensitive credentials - never commit it to git
- The system will fall back to hardcoded sources if Sheets access fails
- Sheet ID: `1J4d4S0mnBeWn5hfHhnc97SPusn9ejz4jWE9oQtK0mgU`