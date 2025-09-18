# YouTube Trending Boost System

## ✅ What It Does

The system tracks what's trending in AI on YouTube and boosts related news articles to ensure your videos cover hot topics that people are searching for.

## 🚀 How to Use

### Enable Trending Boosts
```bash
# Turn on trending boosts
export USE_YOUTUBE_TRENDS=true
python3 unified_pipeline_test.py

# Or one-time use
USE_YOUTUBE_TRENDS=true python3 unified_pipeline_test.py
```

### Add to .env for Permanent Enable
```bash
echo "USE_YOUTUBE_TRENDS=true" >> .env
```

## 📊 How It Works

1. **Identifies Trending Keywords**: Tracks hot AI topics like:
   - Product releases (GPT-5, Gemini 2, Claude Opus)
   - Hot topics (AI agents, open source, safety)
   - Company news (OpenAI, Google, Meta)
   - Daily rotating themes (Monday: business, Wednesday: releases, Friday: drama)

2. **Boosts Matching Articles**: Articles mentioning trending keywords get bonus points:
   - Super hot keywords: +25 points (GPT-5, major releases)
   - Hot keywords: +20 points (launches, gemini 2)
   - Warm keywords: +15 points (agents, open source)
   - Base keywords: +10 points (general AI terms)

3. **Re-ranks Content**: Articles with trending topics rise to the top

## 📈 Real Example

Without trending boosts:
```
1. ArXiv Paper (Score: 135)
2. Analytics India (Score: 130)
3. ArXiv Paper (Score: 120)
```

With trending boosts:
```
1. Nvidia + Gemini News (Score: 178) [🔥 +63 from trends]
2. AI Agents Paper (Score: 165) [🔥 +30 from trends]
3. GPT-5 Discussion (Score: 149) [🔥 +50 from trends]
```

## 🎯 Current Hot Keywords

The system tracks different topics each day:

**Monday**: Business & Funding
- funding, acquisition, IPO, startup (+20 pts)

**Wednesday**: Product Releases
- release, launch, ship, beta (+20 pts)

**Friday**: Drama & Controversy
- fired, lawsuit, leaked, exclusive (+20 pts)

**Always Trending**:
- GPT-5 (+25), Gemini 2 (+20), Claude Opus (+20)
- AI Agents (+15), Open Source (+15)
- NVIDIA (+15), Apple AI (+15)

## 📋 View Trending Keywords

The system saves trending keywords to your Google Sheet:
1. Open: https://docs.google.com/spreadsheets/d/1J4d4S0mnBeWn5hfHhnc97SPusn9ejz4jWE9oQtK0mgU
2. Check the "Trending" tab (if created)
3. See which keywords are hot today

## 🔧 Customization

### Edit Hot Topics
Edit `src/ingest/youtube_trending_simple.py` to update:
```python
current_events = {
    'gpt-5': 25,      # Update when GPT-5 releases
    'gemini 2': 20,   # Boost during Gemini news
    'your-topic': 30, # Add your own
}
```

### Use Real YouTube API (Optional)
If you have a YouTube API key:
```bash
# Add to .env
YOUTUBE_API_KEY=your-key-here

# The system will automatically use real trending data
```

## 📊 Impact

With trending boosts enabled:
- **44 out of 74 articles** got trending boosts
- **Top article score increased** from 135 to 178
- **More relevant content** aligned with what people are searching

## 🎬 Best Practices

1. **Enable for daily videos**: Ensures timely, searchable content
2. **Check trends weekly**: Update hot topics as needed
3. **Monitor performance**: See which trending topics drive views
4. **Combine with time filter**: Use 6-hour filter for breaking trending news

## Quick Commands

```bash
# Daily video with trends
USE_YOUTUBE_TRENDS=true NEWS_HOURS_FILTER=24 python3 unified_pipeline_test.py

# Breaking trending news (6 hours + trends)
USE_YOUTUBE_TRENDS=true NEWS_HOURS_FILTER=6 python3 unified_pipeline_test.py

# Test trending system
python3 src/ingest/youtube_trending_simple.py
```

The system ensures your AI news videos cover what people are actively searching for on YouTube!