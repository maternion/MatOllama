# MatOllama — Fast, clean terminal workflows for local LLMs

MatOllama is a polished command-line interface for running and managing local LLMs via Ollama. It emphasizes speed, clarity, and ergonomics, with adaptive layouts, responsive streaming chat, and safe controls suited for daily use.

## Features

- Clean terminal UX with rich panels, tables, and spinners
- Streamlined model ops: list, pull, run, show, copy, create, push, remove
- Adaptive table width based on terminal size and model names
- Streaming chat with first‑token responsiveness
- “Thinking” model support: parses …, dims chain‑of‑thought, shows final answer cleanly
- Session tools: save/load with timestamps and CLI version metadata
- Safety and control: graceful Ctrl+C, stop/unload, confirmations for destructive actions
- Verbose mode (-v/--verbose) for debug fields from the API
- Version panel shows both CLI and Ollama versions

## Install

- Requirements:
  - Python 3.9+
  - Ollama running locally (default: http://localhost:11434)
  - Python packages: requests, rich

Clone and run directly:
```bash
git clone 
cd 
python3 matollama.py
```

(Optional) Make executable:
```bash
chmod +x matollama.py
./matollama.py
```

## Quick start

1) Start Ollama:
```bash
ollama serve
```

2) Launch MatOllama and list models:
```bash
./matollama.py
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

## CLI commands

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

## Examples

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

## UX details

- Adaptive width: Calculates optimal table width for model list based on terminal size and longest model name.
- Humanized info: Shows MB/GB sizes and readable timestamps.
- Progress feedback: Detailed status for pull/create/push (manifest, download, verify, cleanup).
- Thinking models: Streams internal  content dimmed, then reveals the final answer clearly.
- Signal handling: Ctrl+C gracefully stops active generation; otherwise hints to use `exit`.

## Configuration

- Host: `--host` (default http://localhost:11434)
- Timeout: `--timeout` in seconds (default 300)
- Temperature: `temp [0.0–2.0]`
- System prompt: `system "You are a helpful assistant."`

## Versioning

- Semantic Versioning (SemVer): MAJOR.MINOR.PATCH
- Current CLI: 1.0.4
  - Fixes:
    - Variable name error in main loop
    - Improved “Starting…” message handling
    - Removed redundant “select” command
    - Stability improvements

## Troubleshooting

- “Cannot connect to Ollama”
  - Ensure `ollama serve` is running and `--host` is correct.
- “Model not found locally”
  - Use `pull ` or accept prompt to pull when running by name.
- Terminal layout issues
  - Resize the terminal; the table width recalculates dynamically.
- Stuck generation
  - Use `stop` or Ctrl+C; then `unload` if needed.

## Acknowledgements

Built for smooth local LLM workflows with Ollama, using requests and rich for a clean terminal experience.
