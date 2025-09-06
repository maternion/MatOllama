# ⚡ MatOllama — Enhanced CLI for Local LLM Management

**MatOllama** is a powerful, feature-rich command-line interface for managing and interacting with local large language models through Ollama. Built for developers, researchers, and AI enthusiasts who demand speed, clarity, and robust functionality in their terminal workflows.

<div align="center">

Professional terminal UX -  Context-aware switching -  Session persistence

</div>

***

## ✨ Key Features

### 🎯 **Professional Terminal Experience**
- **Rich UI Components**: Beautiful tables, panels, progress bars, and color-coded output
- **Adaptive Layouts**: Dynamic table widths that adjust to terminal size and content length
- **Real-time Feedback**: Streaming chat responses with first-token responsiveness
- **Intelligent Display**: Handles "thinking" models with dimmed reasoning steps

### 🔄 **Advanced Model Management**
- **Context-Aware Switching**: Seamlessly switch between models while preserving conversation history
- **Comprehensive Operations**: Pull, run, copy, rename, create, push, and remove models with confirmation prompts
- **Smart Selection**: Interactive model picker with arrow key navigation
- **Resource Control**: Unload models, monitor running processes, and manage GPU/CPU usage

### 💾 **Session & Data Management**
- **Persistent Sessions**: Save/load conversations with metadata and version tracking
- **Export Capabilities**: Export chats in JSON (for datasets) or text formats
- **Organized Storage**: Automatic directory structure (Sessions/, Exports/, config.json)
- **Theme Persistence**: Customizable color themes that survive restarts

### 🛡️ **Robust Error Handling**
- **Graceful Interruption**: Ctrl+C handling with context-aware responses
- **Input Blocking**: Prevents commands during long operations (model copying/renaming)
- **Confirmation Dialogs**: Safety prompts for destructive actions
- **Detailed Debugging**: Verbose mode for API inspection and troubleshooting

***

## 📦 Installation

### Prerequisites
- **Python 3.9+** (Check with `python3 --version`)
- **Ollama** installed and running ([Download Ollama](https://ollama.com/download))

### Quick Install

1. **Clone the repository**:
   ```bash
   git clone https://github.com/maternion/MatOllama.git
   cd MatOllama
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run MatOllama**:
   ```bash
   python3 MatOllama.py
   ```

4. **Optional: Make executable**:
   ```bash
   chmod +x MatOllama.py
   ./MatOllama.py
   ```

### Dependencies (`requirements.txt`)
```txt
requests==2.31.0
rich==13.7.1
prompt-toolkit==3.0.43
inquirer==3.2.4
```

***

## 🚀 Quick Start

### 1. **Launch Ollama Server**
```bash
ollama serve
```

### 2. **Start MatOllama**
```bash
./MatOllama.py
```

### 3. **Pull and Run Your First Model**
```bash
# Pull a model
pull llama3.1

# Run by name or index
run llama3.1
# or
run 1

# One-shot prompt
run llama3.1 "Explain quantum computing in simple terms"
```

### 4. **Interactive Chat**
Once a model is loaded:
- Type messages directly
- Use `/switch 2` to change models while preserving context
- Use `/exit` to leave chat mode
- Use `stop` or Ctrl+C to halt generation

***

## 🧰 Command Reference

### Core Model Operations
| Command | Description | Examples |
|---------|-------------|----------|
| `list` | Display all models with index, name, size, and modified date | `list` |
| `select` | Interactive model picker with arrow keys | `select` |
| `pull <model>` | Download model from Ollama registry | `pull codellama:7b` |
| `run <model\|#> [prompt]` | Start chat session or execute single prompt | `run 2`, `run llama3 "Hello"` |
| `show <model>` | Display detailed model information | `show llama3.1` |

### Model Management
| Command | Description | Examples |
|---------|-------------|----------|
| `rm <model\|#>` | Remove model (with confirmation) | `rm 3`, `rm old-model` |
| `copy <src> <dest>` | Duplicate model with new name | `copy llama3 my-llama` |
| `rename <old> <new>` | Rename model (copy + delete original) | `rename 1 better-name` |
| `create <name> [file]` | Create custom model from Modelfile | `create my-bot ./Modelfile` |
| `push <model\|#>` | Upload model to registry (requires auth) | `push my-model` |

### System & Control
| Command | Description | Examples |
|---------|-------------|----------|
| `ps` | Show currently running models with resource usage | `ps` |
| `unload [model\|#]` | Free model from memory | `unload`, `unload 2` |
| `stop` | Halt active generation | `stop` |
| `version` | Display CLI and Ollama version info | `version` |

### Session & Configuration
| Command | Description | Examples |
|---------|-------------|----------|
| `save [filename]` | Save current session to Sessions/ | `save`, `save my-session` |
| `load <filename>` | Load session from Sessions/ | `load session_20250101.json` |
| `export [format] [file]` | Export conversation to Exports/ | `export json`, `export text chat.txt` |
| `theme [color]` | Set persistent theme color | `theme blue`, `theme` |
| `temp [0.0-2.0]` | Show/set temperature (persistent) | `temp 0.8`, `temp` |
| `system [prompt]` | Set system prompt for current session | `system "You are a helpful coding assistant"` |

### Chat & History
| Command | Description | Examples |
|---------|-------------|----------|
| `history` | Display conversation with timestamps | `history` |
| `clear` | Clear conversation history (with confirmation) | `clear` |
| `help` | Show comprehensive command help | `help` |
| `exit` \| `quit` | Exit application (prompts to save) | `exit` |

***

## 💬 In-Chat Commands

When in chat mode (after running a model):

| Command | Description | Examples |
|---------|-------------|----------|
| `/switch <model\|#>` | **Switch models preserving context** | `/switch 2`, `/switch gpt-4o` |
| `/set verbose <true\|false>` | Toggle detailed API debugging | `/set verbose true` |
| `/set think <true\|false>` | Toggle thinking mode for reasoning models | `/set think false` |
| `/exit` | Exit chat mode, return to command mode | `/exit` |
| `/help` | Show in-chat help | `/help` |

***

## 🎨 Advanced Features

### Context-Aware Model Switching
```bash
# Start conversation with one model
run llama3.1
> "Let's discuss machine learning basics"

# Switch to specialized model while keeping context
/switch codellama
# Conversation history is preserved and transferred
```

### Persistent Themes & Settings
```bash
# Set theme (survives restarts)
theme magenta

# Configure temperature (persistent)
temp 0.9

# Settings stored in config.json
```

### Batch Operations & Automation
```bash
# Rename models efficiently
rename 1 production-model
rename 2 dev-model

# Export conversations in different formats
export json training-data.json
export text readable-chat.txt
```

### Session Management Workflow
```bash
# Save current work
save important-research

# Load previous session
load important-research.json
# Restores: model, history, settings, theme

# Export for sharing
export text research-summary.txt
```

***

## ⚙️ Configuration

### Command Line Options
```bash
./MatOllama.py --help

Options:
  --host TEXT          Ollama server URL (default: http://localhost:11434)
  --timeout FLOAT      Request timeout in seconds (default: 300.0)
  --version           Show version and exit
```

### Configuration Files
MatOllama creates organized directories:
```
MatOllama/
├── MatOllama.py          # Main script
├── requirements.txt      # Dependencies
├── config.json          # Persistent settings
├── Sessions/            # Saved chat sessions
├── Exports/             # Exported conversations
└── .ollama_history      # Command history
```

### Environment Variables
```bash
# Custom Ollama host
export OLLAMA_HOST=http://192.168.1.100:11434

# Run with custom settings
./MatOllama.py --host $OLLAMA_HOST --timeout 600
```

***

## 🎯 Usage Examples

### Research Workflow
```bash
# Pull research-focused model
pull deepseek-coder:33b

# Start research session
run deepseek-coder:33b

# Chat about complex topics, then switch for different perspective
/switch llama3.1:70b

# Save valuable conversation
save research-session-$(date +%Y%m%d)

# Export for sharing
export text research-summary.txt
```

### Development Workflow
```bash
# Interactive model selection
select
# Use arrow keys to choose

# Quick code generation
run codellama "Write a Python function for binary search"

# Switch to general model for documentation
/switch llama3.1 
"Now write documentation for that function"

# Export as training data
export json code-examples.json
```

### Model Management
```bash
# List all models with clear formatting
list

# Clean up old models
rm old-model-v1
rm 3  # Remove by index

# Create production copies
copy experimental-model production-v1
rename development-model staging-v2

# Monitor system resources
ps
```

***

## 🔧 Troubleshooting

### Connection Issues
```bash
# Check Ollama server status
curl http://localhost:11434/api/version

# Test with custom host
./MatOllama.py --host http://localhost:11434

# Verify Ollama is running
ollama serve
```

### Performance Issues
```bash
# Check running models
ps

# Unload unused models
unload old-model

# Monitor during operations
run llama3 --verbose
```

### Display Problems
```bash
# Terminal too narrow?
# Resize terminal - tables auto-adjust

# Color issues?
theme cyan  # Try different theme

# Text corruption?
clear  # Clear terminal buffer
```

### Model Issues
```bash
# Model not found?
pull missing-model

# Corrupted model?
rm problematic-model
pull problematic-model  # Re-download

# Out of memory?
unload  # Free current model
ps      # Check what's running
```

***

## 🎯 Tips & Best Practices

### Performance
- Use `unload` between different models to free memory
- Monitor with `ps` to track resource usage
- Set appropriate `temp` values (0.7 default, 0.3 for factual, 1.2 for creative)

### Workflow
- Use `select` for visual model picking
- Save important sessions before switching models
- Export conversations regularly for backup
- Use `/switch` to compare model responses on same topic

### Organization
- Use descriptive names when saving sessions
- Export training conversations as JSON
- Keep Sessions/ organized by date or topic
- Regular cleanup of old exports and models

***

## 🙏 Acknowledgments

Built with love for the Ollama community. MatOllama leverages:
- **[Ollama](https://ollama.com)** - The foundation for local LLM serving
- **[Rich](https://github.com/Textualize/rich)** - Beautiful terminal formatting
- **[prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/)** - Enhanced input handling
- **[inquirer](https://github.com/magmax/python-inquirer)** - Interactive selections

<div align="center">

**MatOllama v1.1.0** - Professional CLI for Local LLMs

[⭐ Star this repo](https://github.com/maternion/MatOllama) if MatOllama enhances your AI workflow!

</div>
