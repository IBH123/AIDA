# 🍅 AIDA - Adaptive Intelligent Day Assistant

**Your JARVIS-style AI assistant that turns natural conversation into an optimized day plan.**

AIDA v0.2 introduces an intelligent conversational interface inspired by JARVIS from Iron Man. Simply tell AIDA about your day in natural language, and it will create a structured, time-blocked schedule with built-in Pomodoro cycles and breaks. No more JSON files or complex input formats—just talk to AIDA like you would a personal assistant.

## ✨ Features (v0.2)

### 🤖 JARVIS-Style Conversational Assistant
- **Natural Language Planning**: Tell AIDA your tasks and meetings conversationally
- **Intelligent Extraction**: Automatically understands priorities, time estimates, and scheduling preferences
- **Smart Follow-ups**: Asks clarifying questions to optimize your schedule
- **Professional Personality**: Witty, sophisticated, and goal-oriented like a trusted aide

### 📋 Smart Planning & Execution
- **Real-time Planning**: Plans from current time with tomorrow overflow suggestions
- **Realistic Scheduling**: Respects fixed meetings with buffers and handles task segmentation
- **Built-in Timer**: Run your plan with a console-based Pomodoro timer
- **Local Privacy**: All conversations and data stay on your machine
- **Dual Interface**: Conversational assistant and traditional CLI commands

## 🚀 Quick Start

### Installation & Setup

```bash
# Clone repository
git clone https://github.com/IBH123/AIDA.git
cd AIDA

# Set up virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set up OpenAI API key for conversational features
echo "OPENAI_API_KEY=your_api_key_here" > .env
echo "AIDA_LLM_MODEL=gpt-4o-mini" >> .env
```

### Quick Start - Talk to AIDA!

1. **🗣️ Conversational Planning (NEW!)**:
   ```bash
   python run_aida.py assistant
   # Or: aida assistant
   ```
   ```
   AIDA: Good morning! I'm AIDA, ready to help you plan your day efficiently.
         What are your priorities today?
   
   You: I need to work on the WFIP3 paper and I have a team meeting at 2pm
   AIDA: Excellent. The WFIP3 paper sounds important. How much time do you estimate?
   You: About 3 hours, and yes 10 minutes buffer for the meeting please
   AIDA: Perfect. Any other tasks or commitments I should know about?
   You: That's all for now
   AIDA: Understood. Let me generate your optimized schedule...
   ```

2. **📋 Traditional Planning**:
   ```bash
   python run_aida.py plan examples/today.json
   ```

3. **⏰ Run with Timer**:
   ```bash
   python run_aida.py run examples/today.json
   ```

## 📋 How It Works

### 🗣️ Conversational Mode (v0.2)
1. **Natural Conversation**: Tell AIDA about your tasks, meetings, and priorities in plain English
2. **Smart Extraction**: AIDA understands time estimates, deadlines, and task complexity automatically
3. **Intelligent Planning**: Segments tasks into Pomodoro cycles and optimizes around your schedule
4. **Real-time Execution**: Start your timer immediately and follow your optimized plan

### 📊 Traditional Mode
1. **JSON Input**: Provide structured tasks and events via JSON files
2. **Planning**: AIDA segments tasks into Pomodoro cycles and packs them around your events
3. **Scheduling**: Creates time blocks with proper breaks (5min regular, 15min every 4th cycle)
4. **Execution**: Run the timer to follow your plan with console notifications

### Example Input

```json
{
  "preferences": {
    "workday_start": "2025-08-25T09:00:00-07:00",
    "workday_end": "2025-08-25T17:30:00-07:00",
    "pomodoro_min": 25
  },
  "tasks": [
    {
      "title": "Review paper draft",
      "estimate_min": 60,
      "priority": 4,
      "requires_deep_work": true
    }
  ],
  "events": [
    {
      "start": "2025-08-25T11:00:00-07:00",
      "end": "2025-08-25T12:00:00-07:00",
      "title": "Team meeting"
    }
  ]
}
```

## 🛠️ Commands

### 🤖 Conversational Commands (NEW!)

- `python run_aida.py assistant` - Start JARVIS-style conversation  
- `aida assistant` - Alternative entry point for conversational planning

### 📊 Traditional CLI Commands

- `python run_aida.py plan <file>` - Generate and display day plan  
- `python run_aida.py run <file>` - Generate plan and start timer
- `python run_aida.py timer <plan-file>` - Run timer on existing plan
- `aida config --show` - Show current preferences
- `aida version` - Show version info

### 🌐 API Endpoints (Coming in v0.3)

- `POST /v1/plan` - Generate day plan
- `GET /v1/plan/ics` - Export plan as ICS
- `POST /v1/timer/start` - Start timer
- `GET /v1/timer/status` - Get timer status
- `GET /v1/summary/today` - Get session summary

## 🏗️ Development

### Project Structure

```
AIDA/
├── aida/
│   ├── models.py      # Pydantic data models (enhanced for v0.2)
│   ├── planner.py     # Core planning algorithm
│   ├── timer.py       # Pomodoro timer implementation
│   ├── assistant.py   # 🆕 JARVIS-style conversational AI
│   ├── cli.py         # CLI interface (enhanced for assistant)
│   ├── api.py         # FastAPI application (coming v0.3)
│   ├── storage.py     # Local data persistence
│   └── ics.py         # Calendar export
├── examples/
│   └── today.json     # Sample plan request
├── tests/             # Test suite
├── run_aida.py        # 🆕 Main launcher script
├── aida.bat           # 🆕 Windows batch launcher
├── requirements.txt   # 🆕 Python dependencies
└── .env.example       # 🆕 Environment variables template
```

### Development Commands

```bash
# Set up development environment
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Test the assistant
python run_aida.py assistant

# Test traditional planning
python run_aida.py plan examples/today.json

# Run tests
pytest tests/ -v

# Format code
black aida/
ruff check aida/
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Test specific functionality
pytest tests/test_planner.py -v
pytest tests/test_models.py -v

# Test with coverage
pytest --cov=aida tests/
```

## ⚙️ Configuration

### Environment Variables (v0.2)
Create a `.env` file in the project root:

```bash
# Required for conversational features
OPENAI_API_KEY=your_openai_api_key_here
AIDA_LLM_MODEL=gpt-4o-mini  # Recommended for cost efficiency

# Optional - customize JARVIS personality
AIDA_ASSISTANT_PERSONALITY=professional  # professional, friendly, witty
```

### Data Storage
AIDA stores preferences and logs in `~/.aida/`:

- `prefs.json` - User preferences (work hours, break durations)
- `logs/` - Daily session logs in JSONL format
- `plans/` - 🆕 Generated conversation plans (auto-saved)
- `conversations/` - 🆕 Chat history (optional)

## 📊 Algorithm Details

**Task Scoring**: `5×priority + urgency + energy_match`
- Priority: 1-5 user rating
- Urgency: Days until deadline (max 10 points)  
- Energy match: +2 for deep work in morning hours

**Interval Management**: 
- Adds 5-minute buffers around fixed events
- Segments tasks into 25-minute Pomodoro cycles
- Greedy packing: highest-scoring tasks first

## 🔄 Roadmap

- **v0.1**: CLI + Basic timer ✅
- **v0.1.1**: Real-time planning + Tomorrow overflow suggestions ✅
- **v0.2**: 🆕 **JARVIS-style conversational assistant with LLM integration** ✅
- **v0.3**: FastAPI service + ICS export + Configurable buffers
- **v0.4**: Web UI + MCP tool integration + Advanced scheduling  
- **v0.5**: Email integration + Multi-day planning + Calendar sync

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run `black aida/` and `ruff check aida/`
5. Test with `pytest tests/ -v`
6. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details.

## 🙋‍♂️ Support

- Start with `python run_aida.py assistant` for conversational planning
- Check [examples/today.json](examples/today.json) for traditional input format
- File issues on GitHub for bugs/features
- See [aida_planning.md](aida_planning.md) for detailed technical documentation

## 💰 Cost Information (v0.2)

AIDA uses OpenAI's API for conversational features:
- **Daily usage**: ~6,000-15,000 tokens (3-5 planning sessions)
- **Cost**: ~$0.01-0.03/day with gpt-4o-mini
- **Privacy**: All conversations happen via API, no data stored by OpenAI

---

**Made with ❤️ for focused productivity • Now with AI-powered conversation! 🤖**