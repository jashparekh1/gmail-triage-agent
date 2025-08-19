# Gmail Triage Agent

An intelligent CLI tool that automatically classifies and prioritizes your unread Gmail messages using Google's Gemini AI.

## Features

- 🔍 **Smart Classification**: Automatically categorizes emails as urgent, non-urgent, or promotional
- 📅 **Date-based Filtering**: Process emails from specific dates or time periods
- 🤖 **AI-Powered**: Uses Google's Gemini AI for intelligent email classification
- 📊 **Rich Reporting**: Generate detailed markdown reports of your email triage
- 🎯 **Flexible Display**: Show specific categories or all emails with AI reasoning
- 📱 **Gmail API Integration**: Direct integration with Gmail for seamless email processing

## Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd gmail-triage-agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys
   ```

4. **Set up Gmail API credentials**
   - Follow [Gmail API setup guide](https://developers.google.com/gmail/api/quickstart/python)
   - Place `client_secret.json` in the project root
   - Run the tool once to authenticate and generate `.gmail_token.json`

## Configuration

Create a `.env` file with:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

## Usage

### Basic Triage
```bash
python -m src.triage.cli triage
```

### Advanced Options
```bash
# Triage emails from a specific date
python -m src.triage.cli triage --since 2024/01/15

# Limit the number of emails processed
python -m src.triage.cli triage --limit 100

# Show only urgent emails
python -m src.triage.cli triage --show urgent

# Show all emails with AI reasoning
python -m src.triage.cli triage --show all --justification

# Save a markdown report
python -m src.triage.cli triage --save
```

### Command Options

- `--since YYYY/MM/DD`: Process emails from this date (defaults to today)
- `--limit N`: Maximum number of unread emails to process (default: 50)
- `--show TYPE`: Display specific category: `urgent`, `non-urgent`, `promo`, or `all`
- `--justification`: Show AI reasoning for classifications
- `--save`: Generate and save a markdown report to `./reports/`

## Output

The tool provides:
- **Statistics**: Count of urgent, non-urgent, and promotional emails
- **Email List**: Sender, subject, snippet, and timestamp for each email
- **AI Reasoning**: Explanation of why each email was classified (with `--justification`)
- **Reports**: Optional markdown reports saved to `./reports/` directory

## Project Structure

```
gmail-triage-agent/
├── src/triage/
│   ├── cli.py          # Main CLI interface
│   ├── gmail_api.py    # Gmail API integration
│   ├── classify_llm.py # AI classification logic
│   └── render.py       # Report generation
├── requirements.txt     # Python dependencies
├── .env.example        # Environment variables template
└── README.md           # This file
```

## Requirements

- Python 3.8+
- Gmail API access
- Google Gemini API key
- Internet connection

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions, please open an issue on GitHub.
