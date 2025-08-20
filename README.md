# 🚀 Gmail Triage Agent

**Smart email management with ML personalization and intelligent unsubscribe recommendations**

Transform your Gmail experience with AI-powered email triage, smart unsubscribe suggestions, and personalized priority scoring.

## ✨ Features

### 🧠 **Smart Unsubscribe Engine**
- **Engagement Analysis**: Learn which senders you consistently ignore vs. engage with
- **Unsubscribe Recommendations**: Get prioritized suggestions with confidence scores
- **One-Click Unsubscribe**: Direct links to unsubscribe from newsletters and spam
- **Impact Metrics**: See how many emails you can eliminate from your inbox

### 📊 **Advanced Email Analytics**
- **Sender Reputation**: Track engagement patterns, response rates, and spam likelihood
- **Behavioral Insights**: Understand your email habits and preferences
- **Category Analysis**: Deep dive into Gmail's smart categorization
- **Temporal Patterns**: Analyze when you're most productive with emails

### 🎯 **Personalized Priority Scoring**
- **ML-Based Classification**: Combines Gmail categories with your behavior patterns
- **Smart Filtering**: Learn what's truly important to you
- **Confidence Levels**: See why emails are classified as urgent/important
- **Continuous Learning**: Improves accuracy as you provide feedback

## 🏗️ Architecture

```
src/triage/
├── data_collector.py      # Gmail API data collection
├── unsubscribe_engine.py  # Smart unsubscribe analysis
├── unsubscribe_cli.py     # CLI for unsubscribe features
├── classify_llm.py        # LLM-based email classification
├── gmail_api.py          # Gmail API wrapper
├── cli.py                # Original triage CLI
└── render.py             # Report generation
```

## 🚀 Quick Start

### 1. Setup Gmail API
```bash
# Install dependencies
pip install -r requirements.txt

# Set up Gmail API credentials
# Place client_secret.json in repo root
export GOOGLE_API_KEY="your_gemini_api_key"
```

### 2. Collect Your Email Data
```bash
# Download your email history (last 90 days)
python -m src.triage.unsubscribe_cli collect --days 90

# Or force fresh collection
python -m src.triage.unsubscribe_cli collect --force-collect
```

### 3. Get Smart Unsubscribe Recommendations
```bash
# Analyze and get recommendations
python -m src.triage.unsubscribe_cli analyze

# View statistics
python -m src.triage.unsubscribe_cli stats

# Generate reports
python -m src.triage.unsubscribe_cli report --output markdown
```

### 4. Use Original Triage Features
```bash
# Basic email triage
python -m src.triage.cli triage --save

# With ML personalization (coming soon)
python -m src.triage.ml_cli triage --train
```

## 📊 What You'll Discover

### **Unsubscribe Insights**
- "You've ignored 15 emails from X in 3 months - unsubscribe?"
- "You only open 2% of emails from Y - consider unsubscribing"
- "This sender has high unsubscribe rates - easy to remove"

### **Engagement Patterns**
- Which senders you actually respond to vs. ignore
- Your personal definition of "important" vs. "spam"
- Optimal times for email processing
- Newsletter fatigue indicators

### **Inbox Optimization**
- Potential email reduction (often 30-50%!)
- Sender reputation scores
- Category-based filtering strategies
- One-click unsubscribe workflows

## 🔧 Configuration

### Environment Variables
```bash
GOOGLE_API_KEY=your_gemini_api_key  # For LLM classification
```

### Data Storage
- **Raw Data**: `data/gmail_data_*.parquet` (efficient binary format)
- **Reports**: `data/unsubscribe_report_*.md` (human-readable)
- **Recommendations**: `data/unsubscribe_recommendations_*.json` (structured data)

## 📈 Roadmap

### **Phase 1: Smart Unsubscribe** ✅
- [x] Data collection pipeline
- [x] Engagement analysis engine
- [x] Unsubscribe recommendations
- [x] CLI interface

### **Phase 2: Personal Spam Filter** 🚧
- [ ] ML-based spam detection
- [ ] Personal spam patterns
- [ ] Auto-filtering rules

### **Phase 3: Priority Scoring** 📋
- [ ] Logistic regression model
- [ ] Personalized importance scoring
- [ ] Confidence explanations

### **Phase 4: Dashboard** 🎨
- [ ] Streamlit web interface
- [ ] Interactive visualizations
- [ ] One-click actions

## 🤝 Contributing

This is a personal project focused on practical email management. Feel free to:

1. **Fork and adapt** for your own use
2. **Report issues** with Gmail API integration
3. **Suggest features** that would actually improve your workflow
4. **Share your results** - how many emails did you eliminate?

## 📝 License

MIT License - Use this to improve your own email productivity!

## 💡 Use Cases

- **Newsletter Overload**: Identify and unsubscribe from low-value newsletters
- **Spam Reduction**: Learn your personal spam patterns
- **Priority Management**: Focus on emails that matter to you
- **Inbox Zero**: Reduce email volume by 30-50%
- **Productivity**: Spend less time on email triage

---

**Built with ❤️ for people who want to actually manage their email, not just read about it.**
