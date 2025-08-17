# ⚡ MatOllama — Fast, Clean Terminal Workflows for Local LLMs

MatOllama is a polished command-line interface (CLI) for running and managing local large language models (LLMs) via Ollama. It emphasizes speed, clarity, and ergonomics with adaptive layouts, responsive streaming chat, and robust control features.

---

## ✨ Features

- **Clean Terminal UX**: Rich panels, tables, and spinners.
- **Streamlined Model Management**: Commands for listing, pulling, running, copying, creating, pushing, and removing models.
- **Adaptive Design**: Table widths adjust dynamically based on terminal size and content.
- **Responsive Chat**: Streamed output with first-token responsiveness.
- **Intelligent Outputs**: Handles "thinking" models, dims intermediate steps, and presents clean final answers.
- **Session Management**: Save/load sessions with timestamps and CLI version metadata.
- **Safe and Controlled Operations**: Graceful handling of Ctrl+C, confirmations for destructive actions, and robust error management.
- **Verbose Debugging**: Output detailed API fields in debug mode (`-v/--verbose`).
- **Version Panel**: Displays CLI and Ollama versions for easy troubleshooting.

---

## 📦 Installation

### Requirements:

- **Python**: Version 3.9 or higher.
- **Ollama**: Installed and running locally (default: `http://localhost:11434`). [Download Ollama](https://ollama.com/download).
- **Python Packages**: `requests`, `rich`.

### Steps to Install:

1. Clone the repository:
   ```bash
   git clone https://github.com/maternion/MatOllama.git
   cd MatOllama
   ```

2. Run MatOllama:
   ```bash
   python3 MatOllama.py
   ```

3. (Optional) Make the script executable:
   ```bash
   chmod +x MatOllama.py
   ./MatOllama.py
   ```

---

## 🚀 Quick Start

1. **Start Ollama**:
   ```bash
   ollama serve
   ```

2. **Launch MatOllama and list models**:
   ```bash
   ./MatOllama.py
   ```

3. **Pull a Model**:
   ```bash
   pull llama3
   ```

4. **Run a Model**:
   ```bash
   run llama3.1
   # or by index:
   run 2
   ```

5. **Enter Chat Mode**:
   - After running a model, type your messages directly.
   - Use `exit` to leave chat mode, `stop` to halt generation, or `unload` to free resources.

---

## 🧰 CLI Commands

- **`list`**: Show available models (index, name, digest, size, modified).
- **`pull`**: Download a model from the registry.
- **`run`**: Start chat or one-shot prompt.
  - Example: `run llama3 "Write a poem."`
- **`show`**: Display model metadata.
- **`rm`**: Remove a local model (requires confirmation).
- **`copy`**: Duplicate a model under a new name.
- **`create`**: Create a model from a Modelfile (interactive or file-based input).
- **`push`**: Upload a model to the registry (requires login).
- **`ps`**: List currently running models (with expiry info).
- **`version`**: Show CLI and Ollama versions with recent changes.
- **`unload`**: Unload the active model and clear its state.
- **`stop`**: Halt the current generation process.
- **`temp`**: Show or set the temperature (0.0–2.0).
- **`system`**: Set or clear the system prompt.
- **`history`**: Display the conversation history.
- **`clear`**: Clear history (requires confirmation).
- **`save`**: Save the session to `~/.ollama_cli/session_*.json`.
- **`load`**: Load a session from a file.
- **`help`**: Show help information.
- **`exit | quit`**: Exit the application (prompts to save if history exists).

---

## 🧪 Examples

- **Run by Index with Immediate Prompt**:
  ```bash
  run 2 "Write a haiku about monsoons."
  ```

- **Enable Verbose Debugging**:
  ```bash
  run llama3 --verbose
  ```

- **Create a Model Interactively**:
  ```bash
  create my-model
  # Paste Modelfile lines, end with 'END'
  ```

- **Save and Load Sessions**:
  ```bash
  save
  load session_20250101_120000.json
  ```

---

## 🎛️ UX Details

- **Adaptive Design**: Adjusts table widths based on terminal dimensions and content.
- **Humanized Information**: Displays file sizes in MB/GB and readable timestamps.
- **Progress Feedback**: Detailed updates during operations (pull, create, push).
- **Graceful Signal Handling**: Ctrl+C stops active generation, with hints for `exit`.

---

## ⚙️ Configuration

- **Host**: Use `--host` (default: `http://localhost:11434`).
- **Timeout**: Set `--timeout` in seconds (default: 300).
- **Temperature**: Adjust with `temp [0.0–2.0]`.
- **System Prompt**: Configure using `system "You are a helpful assistant."`.

---

## 🆘 Troubleshooting

- **"Cannot connect to Ollama"**:
  - Ensure `ollama serve` is running and `--host` is correct.

- **"Model not found locally"**:
  - Use `pull` or accept the prompt to download the model.

- **Terminal Layout Issues**:
  - Resize the terminal to recalculate table widths dynamically.

- **Stuck Generation**:
  - Use `stop` or Ctrl+C, then `unload` if needed.

---

## 🙏 Acknowledgements

Built to provide smooth local LLM workflows with Ollama, leveraging `requests` and `rich` for a clean and responsive terminal experience.

---- Verbose mode (-v/--verbose) for debug fields from the API
- Version panel shows both CLI and Ollama versions

## 📦 Install
Requirements:
- Python 3.9+
- Install Ollama - https://ollama.com/download
- Ollama running locally (default: http://localhost:11434)
- Python packages: requests, rich

Clone and run directly:
```bash
git clone 
cd 
python3 MatOllama.py
```

(Optional) Make executable:
```bash
chmod +x MatOllama.py
./MatOllama.py
```

## 🚀 Quick start
1) Start Ollama:
```bash
ollama serve
```

2) Launch MatOllama and list models:
```bash
./MatOllama.py
list # happens by default
```

3) Pull a model:
```bash
pull llama3
```

4) Run a model (by name or number from list):
```bash
run llama3.1
# or
run 2
```

5) Chat mode:
- After `run`, type messages; use `exit` to leave chat mode.
- Use `stop` to halt generation, `unload` to free the model.

## 🧰 CLI commands
- list — List available models with index, name, digest, size, modified
- pull  — Download a model from registry
- run  ["prompt"] [--verbose|-v] — Start chat or one‑shot prompt
- show  — Show model metadata
- rm  — Delete a local model (with confirmation)
- copy   — Copy a model under a new name
- create  [Modelfile] — Create from a Modelfile (file or interactive input)
- push  — Push to registry (must be logged in)
- ps — Show currently running models (with expiry)
- version — Show CLI and Ollama versions + recent changes
- unload — Unload current model and clear state
- stop — Stop current generation
- temp [value] — Show/set temperature (0.0–2.0)
- system [prompt] — Set/clear system prompt
- history — Show conversation history
- clear — Clear history (with confirm)
- save [file] — Save session to ~/.ollama_cli/session_*.json
- load  — Load session from file
- help — Show help
- exit | quit — Exit (prompt to save if history exists)

## 🧪 Examples
- Run by index with immediate prompt:
```bash
run 2 "Write a haiku about monsoons."
```

- Enable verbose debug (extra API fields in dim yellow):
```bash
run llama3 --verbose
```

- Create a model interactively:
```bash
create my-model
# paste Modelfile lines, end with 'END'
```

- Save and load sessions:
```bash
save
load session_20250101_120000.json
```

## 🎛️ UX details
- Adaptive width: Calculates optimal table width for model list based on terminal size and longest model name.
- Humanized info: Shows MB/GB sizes and readable timestamps.
- Progress feedback: Detailed status for pull/create/push (manifest, download, verify, cleanup).
- Thinking models: Streams internal content dimmed, then reveals the final answer clearly.
- Signal handling: Ctrl+C gracefully stops active generation; otherwise hints to use `exit`.

## ⚙️ Configuration
- Host: `--host` (default http://localhost:11434)
- Timeout: `--timeout` in seconds (default 300)
- Temperature: `temp [0.0–2.0]`
- System prompt: `system "You are a helpful assistant."`

## 🆘 Troubleshooting
- “Cannot connect to Ollama”
  - Ensure `ollama serve` is running and `--host` is correct.
- “Model not found locally”
  - Use `pull` or accept prompt to pull when running by name.
- Terminal layout issues
  - Resize the terminal; the table width recalculates dynamically.
- Stuck generation
  - Use `stop` or Ctrl+C; then `unload` if needed.

## 🙏 Acknowledgements
Built for smooth local LLM workflows with Ollama, using requests and rich for a clean terminal experience.
