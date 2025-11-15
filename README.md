# News Bias Analyzer

A Streamlit application for analyzing news bias using Valyu Search API and HolisticAI.

## Features

- 🔍 **Real-time News Search** - Search news from multiple sources using Valyu API
- 🤖 **AI-Powered Analysis** - Analyze articles using HolisticAI Claude 3.5
- 📊 **Bias Detection** - Calculate sentiment and detect potential bias
- 💡 **Smart Recommendations** - Get suggestions for balanced information
- 📰 **Multi-Source Support** - Compare coverage across different news sources

## Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone https://github.com/krishnanefx/TheGreatAgentHack.git
cd TheGreatAgentHack

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the project root (or use existing `config/.env`):

```bash
# Valyu Search API
VALYU_API_KEY=your_valyu_api_key

# HolisticAI Credentials
HOLISTIC_AI_TEAM_ID=your_team_id
HOLISTIC_AI_API_TOKEN=your_api_token
```

### 3. Run the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## How to Use

1. **Enter a Search Topic** - Type in any news topic (e.g., "climate change", "AI regulation")
2. **Select Sources** - Choose from predefined categories or add custom sources
3. **Analyze** - Click "Analyze News" to search and analyze articles
4. **Review Results** - View AI analysis, sentiment metrics, and article details

## Source Categories

- **All Sources** - Search across all available sources
- **Independent** - BBC, The Guardian, Reuters, Associated Press
- **Mainstream US** - CNN, Fox News, New York Times
- **State-Aligned** - China Daily, RT, Xinhua
- **Custom** - Add your own sources

## Project Structure

```
TheGreatAgentHack/
├── app.py                 # Main Streamlit application
├── tutorials/
│   └── holistic_ai_bedrock.py  # HolisticAI integration
├── config/
│   └── .env              # API keys
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Requirements

- Python 3.8+
- Streamlit
- LangChain + langchain-valyu
- HolisticAI access
- Valyu API access

## Troubleshooting

### "Import error"
```bash
pip install -r requirements.txt
```

### "API key not found"
- Ensure `.env` file exists in `config/` folder or project root
- Check that API keys are correctly formatted
- No quotes around keys in `.env`

### "Search failed"
- Verify Valyu API key is valid
- Check internet connection
- Try reducing number of results

## Contributing

See [contributing.md](contributing.md) for guidelines.

---

**Built for The Great Agent Hack 2025**  
*Powered by Valyu Search + HolisticAI*
