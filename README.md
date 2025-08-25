# 🍅 AIDA - Adaptive Intelligent Day Assistant

**Turn a brief morning check-in into a realistic day plan and run it with a Pomodoro timer.**

AIDA helps you transform your daily goals and meetings into a structured, time-blocked schedule with built-in Pomodoro cycles and breaks. No more guessing how to fit everything in—just provide your tasks and fixed events, and AIDA creates an executable plan for your day.

## ✨ Features (v0.1)

- **Smart Planning**: Converts tasks and events into chronological Pomodoro blocks
- **Realistic Scheduling**: Respects fixed meetings with buffers and handles task segmentation
- **Built-in Timer**: Run your plan with a console-based Pomodoro timer
- **Flexible Formats**: JSON input/output, ICS calendar export
- **Local Privacy**: All data stays on your machine
- **Dual Interface**: CLI commands and REST API

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd aida

# Install with development dependencies
make install-dev

# Or just the package
pip install -e .
```

### Basic Usage

1. **Plan your day**:
   ```bash
   aida plan examples/today.json
   ```

2. **Run with timer**:
   ```bash
   aida run examples/today.json
   ```

3. **Export to calendar**:
   ```bash
   aida plan examples/today.json --ics my-plan.ics
   ```

4. **Start API server**:
   ```bash
   make run-api
   # API docs at http://localhost:8000/docs
   ```

## 📋 How It Works

1. **Input**: Provide tasks (with estimates/priorities) and fixed events
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

### CLI Commands

- `aida plan <file>` - Generate and display day plan  
- `aida run <file>` - Generate plan and start timer
- `aida timer <plan-file>` - Run timer on existing plan
- `aida config --show` - Show current preferences
- `aida version` - Show version info

### API Endpoints

- `POST /v1/plan` - Generate day plan
- `GET /v1/plan/ics` - Export plan as ICS
- `POST /v1/timer/start` - Start timer
- `GET /v1/timer/status` - Get timer status
- `GET /v1/summary/today` - Get session summary

## 🏗️ Development

### Project Structure

```
aida/
├── aida/
│   ├── models.py      # Pydantic data models
│   ├── planner.py     # Core planning algorithm
│   ├── timer.py       # Pomodoro timer implementation
│   ├── cli.py         # CLI interface
│   ├── api.py         # FastAPI application
│   ├── storage.py     # Local data persistence
│   └── ics.py         # Calendar export
├── examples/
│   └── today.json     # Sample plan request
├── tests/             # Test suite
└── pyproject.toml     # Package configuration
```

### Development Commands

```bash
make install-dev    # Install with dev dependencies
make format         # Format code with black/ruff
make lint          # Run linting
make typecheck     # Run mypy type checking
make test          # Run test suite
make run-api       # Start development API server
```

### Testing

```bash
# Run all tests
make test

# Test specific functionality
pytest tests/test_planner.py -v

# Test with coverage
pytest --cov=aida tests/
```

## ⚙️ Configuration

AIDA stores preferences and logs in `~/.aida/`:

- `prefs.json` - User preferences (work hours, break durations)
- `logs/` - Daily session logs in JSONL format
- `aida.db` - Optional SQLite database

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

- **v0.1** (Current): CLI + API + Basic timer ✅
- **v0.2**: ICS export + Configurable buffers + Lunch detection
- **v0.3**: Web UI + MCP tool integration + Advanced scheduling
- **v0.4**: Email integration + Multi-day planning

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run `make format lint typecheck test`
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details.

## 🙋‍♂️ Support

- Check [examples/today.json](examples/today.json) for input format
- API documentation at `/docs` when running server
- File issues on GitHub for bugs/features

---

**Made with ❤️ for focused productivity**