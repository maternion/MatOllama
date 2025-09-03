#!/usr/bin/env python3
"""
Ollama CLI
Version: 1.0.4
"""
import argparse
import json
import os
import sys
import signal
import readline
import time
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import Generator, List, Dict, Optional
import requests
from requests.exceptions import RequestException
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.text import Text
from rich import box
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# CLI Version following Semantic Versioning (SemVer)
# MAJOR.MINOR.PATCH
# MAJOR: Breaking changes, major overhauls
# MINOR: New features, backward-compatible
# PATCH: Bug fixes, small improvements
CLI_VERSION = "1.0.4"

console = Console(highlight=False)

@dataclass
class ChatMsg:
    role: str
    content: str
    ts: datetime = field(default_factory=datetime.now)



class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434", timeout: float = 300.0):
        self.host = host.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, **kw):
        url = f"{self.host}{path}"
        kw.pop("timeout", None)
        try:
            r = requests.request(method, url, timeout=self.timeout, **kw)
            r.raise_for_status()
            return r
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Request timed out after {self.timeout} seconds.")
        except RequestException as e:
            raise RuntimeError(f"Network error: {e}") from e

    def list_models(self) -> List[Dict]:
        try:
            response = self._request("GET", "/api/tags")
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            console.print(f"[red]Error fetching models: {e}[/red]")
            return []

    def pull_model(self, name: str) -> bool:
        try:
            console.print(f"[cyan]Pulling {name}...[/cyan]")
            r = self._request("POST", "/api/pull", json={"name": name}, stream=True)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TextColumn("•"),
                TextColumn("{task.fields[status]}", style="cyan"),
                console=console,
                transient=False
            ) as progress:
                task = progress.add_task(f"Pulling {name}", status="Starting...")
                
                completed = False
                for line in r.iter_lines():
                    if not line:
                        continue
                        
                    try:
                        data = json.loads(line.decode("utf-8"))
                        
                        # Update progress with current status
                        status = data.get('status', 'Unknown')
                        
                        # Handle different status types with better descriptions
                        if status == 'pulling manifest':
                            progress.update(task, status="📋 Pulling manifest...")
                        elif status == 'downloading':
                            # Show download progress if available
                            if 'completed' in data and 'total' in data:
                                completed_bytes = data['completed']
                                total_bytes = data['total']
                                percent = (completed_bytes / total_bytes) * 100 if total_bytes > 0 else 0
                                completed_mb = completed_bytes / (1024*1024)
                                total_mb = total_bytes / (1024*1024)
                                progress.update(task, status=f"⬇️ {completed_mb:.1f}/{total_mb:.1f}MB ({percent:.1f}%)")
                            else:
                                progress.update(task, status="⬇️ Downloading...")
                        elif status == 'verifying sha256 digest':
                            progress.update(task, status="🔍 Verifying...")
                        elif status == 'writing manifest':
                            progress.update(task, status="📝 Writing manifest...")
                        elif status == 'removing any unused layers':
                            progress.update(task, status="🧹 Cleaning up...")
                        elif status == 'success':
                            progress.update(task, status="✅ Complete!")
                            completed = True
                            time.sleep(0.5)  # Brief pause to show completion
                            break
                        elif 'error' in data:
                            error_msg = data.get('error', 'Unknown error')
                            progress.update(task, status=f"❌ Error: {error_msg}")
                            console.print(f"[red]Pull failed: {error_msg}[/red]")
                            return False
                        else:
                            progress.update(task, status=status)
                            
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        console.print(f"[yellow]Progress parse error: {e}[/yellow]")
                        continue
                        
                return completed
                
        except Exception as e:
            console.print(f"[red]Error pulling {name}: {e}[/red]")
            return False

    def delete_model(self, name: str) -> bool:
        try:
            self._request("DELETE", "/api/delete", json={"name": name})
            return True
        except Exception as e:
            console.print(f"[red]Error deleting {name}: {e}[/red]")
            return False

    def copy_model(self, source: str, destination: str) -> bool:
        try:
            self._request("POST", "/api/copy", json={"source": source, "destination": destination})
            return True
        except Exception as e:
            console.print(f"[red]Error copying {source} to {destination}: {e}[/red]")
            return False

    def create_model(self, name: str, modelfile: str) -> bool:
        try:
            console.print(f"[cyan]Creating {name}...[/cyan]")
            r = self._request("POST", "/api/create", json={"name": name, "modelfile": modelfile}, stream=True)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TextColumn("•"),
                TextColumn("{task.fields[status]}", style="cyan"),
                console=console,
                transient=False
            ) as progress:
                task = progress.add_task(f"Creating {name}", status="Starting...")
                
                completed = False
                for line in r.iter_lines():
                    if not line:
                        continue
                        
                    try:
                        data = json.loads(line.decode("utf-8"))
                        status = data.get('status', 'Unknown')
                        
                        if 'error' in data:
                            error_msg = data.get('error', 'Unknown error')
                            progress.update(task, status=f"❌ Error: {error_msg}")
                            console.print(f"[red]Create failed: {error_msg}[/red]")
                            return False
                        elif status == 'success':
                            progress.update(task, status="✅ Complete!")
                            completed = True
                            time.sleep(0.5)
                            break
                        else:
                            progress.update(task, status=f"🔨 {status}")
                            
                    except json.JSONDecodeError:
                        continue
                        
                return completed
                
        except Exception as e:
            console.print(f"[red]Error creating {name}: {e}[/red]")
            return False

    def push_model(self, name: str) -> bool:
        try:
            console.print(f"[cyan]Pushing {name}...[/cyan]")
            r = self._request("POST", "/api/push", json={"name": name}, stream=True)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TextColumn("•"),
                TextColumn("{task.fields[status]}", style="cyan"),
                console=console,
                transient=False
            ) as progress:
                task = progress.add_task(f"Pushing {name}", status="Starting...")
                
                completed = False
                for line in r.iter_lines():
                    if not line:
                        continue
                        
                    try:
                        data = json.loads(line.decode("utf-8"))
                        status = data.get('status', 'Unknown')
                        
                        if 'error' in data:
                            error_msg = data.get('error', 'Unknown error')
                            progress.update(task, status=f"❌ Error: {error_msg}")
                            console.print(f"[red]Push failed: {error_msg}[/red]")
                            return False
                        elif status == 'success':
                            progress.update(task, status="✅ Complete!")
                            completed = True
                            time.sleep(0.5)
                            break
                        elif 'pushing' in status:
                            progress.update(task, status=f"⬆️ {status}")
                        else:
                            progress.update(task, status=f"📤 {status}")
                            
                    except json.JSONDecodeError:
                        continue
                        
                return completed
                
        except Exception as e:
            console.print(f"[red]Error pushing {name}: {e}[/red]")
            return False

    def get_version(self) -> Dict:
        try:
            response = self._request("GET", "/api/version")
            return response.json()
        except Exception as e:
            console.print(f"[yellow]Warning: Could not fetch Ollama version: {e}[/yellow]")
            return {"version": "Unknown"}

    def unload_model(self, model_name: str) -> bool:
        try:
            self._request("POST", "/api/generate", json= {
                "model": model_name,
                "keep_alive": 0
            })
            return True
        except Exception as e:
            console.print(f"[yellow]Warning: Error unloading {model_name}: {e}[/yellow]")
            return False

    def chat_stream(self, model: str, messages: List[Dict], system: str = "", 
                   temp: float = 0.7, verbose: bool = False) -> Generator[str, None, None]:
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temp}
        }
        if system:
            payload["system"] = system
        if verbose:
            payload["options"]["verbose"] = True

        try:
            r = self._request("POST", "/api/chat", json=payload, stream=True)
            for raw in r.iter_lines():
                if not raw:
                    continue
                try:
                    data = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    continue

                # Check for errors in response
                if "error" in data:
                    yield f"\n[ERROR]: {data['error']}"
                    break

                # Always yield assistant response if present
                if "message" in data and "content" in data["message"]:
                    yield data["message"]["content"]

                if verbose:
                    # Show any extra debug keys in yellow (skip message/done)
                    for k, v in data.items():
                        if k not in ("message", "done", "error") and v and v != {} and v != []:
                            yield f"[DEBUG {k}]: {json.dumps(v, ensure_ascii=False)}"

                if data.get("done"):
                    break
        except Exception as e:
            yield f"\nError: {e}"

    def show_model(self, name: str) -> Dict:
        try:
            models = self.list_models()
            for mdl in models:
                if mdl["name"] == name:
                    return mdl
            raise ValueError(f"Model {name!r} not found")
        except Exception as e:
            console.print(f"[red]Error showing model info: {e}[/red]")
            return {}

class ThinkingProcessor:
    def __init__(self):
        self.thinking_active = False
        self.buffer = ""
        self.thinking_content = ""
        self.visible_content = ""
        self.complete_thinking = ""

    def process_chunk(self, chunk: str):
        self.buffer += chunk
        new_thinking = ""
        new_visible = ""
        started = False
        finished = False
        
        processed = self.buffer
        self.buffer = ""
        
        i = 0
        while i < len(processed):
            if not self.thinking_active:
                pos = processed.find("<think>", i)
                if pos == -1:
                    new_visible += processed[i:]
                    break
                else:
                    new_visible += processed[i:pos]
                    self.thinking_active = True
                    self.thinking_content = ""
                    started = True
                    i = pos + 7
            else:
                pos = processed.find("</think>", i)
                if pos == -1:
                    new_thinking += processed[i:]
                    self.thinking_content += processed[i:]
                    break
                else:
                    new_thinking += processed[i:pos]
                    self.thinking_content += processed[i:pos]
                    self.complete_thinking = self.thinking_content
                    self.thinking_active = False
                    finished = True
                    i = pos + 8
        
        self.visible_content += new_visible
        return new_thinking, new_visible, started, finished

    def get_display_content(self):
        return self.visible_content

    def get_complete_thinking(self):
        return self.complete_thinking

    def reset(self):
        self.thinking_active = False
        self.buffer = ""
        self.thinking_content = ""
        self.visible_content = ""
        self.complete_thinking = ""

class CLI:
    def __init__(self, host: str, timeout: float = 300.0):
        self.api = OllamaClient(host, timeout)
        self.current_model = None
        self.system_prompt = ""
        self.temp = 0.7
        self.history: List[ChatMsg] = []
        self.streaming = False
        self.loading = False
        self.verbose = False
        self.first_prompt = True
        self.thinking = True
        
        signal.signal(signal.SIGINT, self._signal_handler)
        self._check_connection()
        self._setup_readline()

    def _signal_handler(self, sig, frame):
        if self.streaming or self.loading:
            self.streaming = False
            self.loading = False
            console.print("\n[red]Generation interrupted[/red]")
        else:
            console.print("\n[yellow]Use 'exit' to quit[/yellow]")

    def _check_connection(self):
        try:
            models = self.api.list_models()
            if models is not None:  # Check for None instead of just truthy
                console.print("[green]✓ Connected to Ollama[/green]")
            else:
                console.print("[yellow]⚠ Connected to Ollama but no models found[/yellow]")
        except Exception:
            console.print("[yellow]⚠ Cannot connect to Ollama[/yellow]")
            console.print("  Make sure Ollama is running: [cyan]ollama serve[/cyan]")

    def _setup_readline(self):
        try:
            readline.parse_and_bind("tab: complete")
            histfile = os.path.expanduser("~/.ollama_history")
            try:
                readline.read_history_file(histfile)
                readline.set_history_length(1000)  # Limit history size
            except FileNotFoundError:
                pass
            import atexit
            atexit.register(readline.write_history_file, histfile)
        except Exception:
            pass

    def _get_prompt(self):
        return "[cyan]You[/cyan]" if self.current_model else "[cyan]Ollama[/cyan]"

    def _input(self):
        print()
        sys.stdout.flush()
        try:
            prompt_text = self._get_prompt() + ": "
            console.print(prompt_text, end="", highlight=False)
            return input().strip()
        except (KeyboardInterrupt, EOFError):
            return ""
        except Exception:
            return ""

    def _handle_slash_commands(self, user_input: str) -> bool:
        if not user_input.startswith("/"):
            return False

        parts = user_input.split()
        command = parts[0].lower()
        args = parts[1:]

        if command == "/set":
            if not args:
                console.print("Usage: /set <option> <value>")
                return True
            
            option = args[0].lower()
            value = args[1].lower() if len(args) > 1 else None

            if option == "verbose":
                if value == "true":
                    self.verbose = True
                    console.print("[dim]Verbose mode enabled[/dim]")
                elif value == "false":
                    self.verbose = False
                    console.print("[dim]Verbose mode disabled[/dim]")
                else:
                    console.print("Usage: /set verbose <true|false>")
            elif option == "think":
                if value == "true":
                    self.thinking = True
                    console.print("[dim]Thinking mode enabled[/dim]")
                elif value == "false":
                    self.thinking = False
                    console.print("[dim]Thinking mode disabled[/dim]")
                else:
                    console.print("Usage: /set think <true|false>")
            else:
                console.print(f"Unknown option: {option}")

        elif command == "/help":
            self.cmd_help()
        else:
            console.print(f"Unknown command: {command}")
        
        return True

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes == 0:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def _parse_message(self, user_input: str) -> tuple[str, bool]:
        return user_input, False

    

    def _get_terminal_width(self) -> int:
        """Get current terminal width using multiple methods for reliability"""
        try:
            # Method 1: Rich console size
            return console.size.width
        except:
            try:
                # Method 2: shutil.get_terminal_size()
                return shutil.get_terminal_size().columns
            except:
                try:
                    # Method 3: os.get_terminal_size()
                    return os.get_terminal_size().columns
                except:
                    # Fallback to reasonable default
                    return 80

    def _calculate_optimal_width(self) -> int:
        """Calculate optimal width based on content and terminal constraints"""
        models = self.api.list_models()
        terminal_width = self._get_terminal_width()
        
        # Set reasonable minimum width
        min_width = 60
        
        # If no models, return reasonable default within terminal bounds
        if not models:
            return min(80, terminal_width - 2)  # -2 for padding
        
        # Find longest model name
        max_name_len = max(len(m.get("name", "")) for m in models)
        
        # Calculate required width for all columns:
        # Index(3) + Name(max_name_len+2 for arrow) + ID(12) + Size(10) + Modified(16) + padding(~15)
        content_width = 3 + (max_name_len + 2) + 12 + 10 + 16 + 15
        
        # Use the larger of minimum width or content width, but cap at terminal width
        optimal_width = max(min_width, content_width)
        final_width = min(optimal_width, terminal_width - 2)  # -2 for safe margin
        
        return final_width

    def cmd_list_boxwidth(self, width=None, interactive=False):
        models = self.api.list_models()
        
        # Calculate optimal width if not provided
        if width is None:
            width = self._calculate_optimal_width()
        
        if not models:
            console.print(Panel(
                "No models found. Use 'pull <model>' to download.",
                title="Models", border_style="cyan", box=box.ROUNDED, width=width
            ))
            return False, width

        table = Table(title="Available Models", box=box.ROUNDED, border_style="cyan", width=width)
        
        # Add columns with appropriate constraints
        table.add_column("#", style="cyan", width=3, max_width=3)
        table.add_column("Name")  # Flexible for model names
        table.add_column("ID", width=12, max_width=12)
        table.add_column("Size", width=10, max_width=10)
        table.add_column("Modified", width=16, max_width=16)

        for i, m in enumerate(models, 1):
            model_id = (m.get("digest") or "-")[:12]
            size = self._format_size(m.get("size", 0))
            modified = m.get("modified_at", "")
            if modified:
                try:
                    dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
                    modified = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    modified = modified[:16]
            
            name = m.get("name", "Unknown")
            if name == self.current_model:
                name = f"→ {name}"
            
            table.add_row(str(i), name, model_id, size, modified)

        console.print(table)
        
        if interactive and models:
            try:
                choice = IntPrompt.ask("Select model number (0 to cancel)", default=0)
                if 1 <= choice <= len(models):
                    self.current_model = models[choice-1]["name"]
                    console.print(f"Selected {self.current_model}. Start chatting!")
                    return True, width
            except Exception:
                console.print("Selection cancelled")
        
        return False, width

    def cmd_list(self, interactive=False):
        _, width = self.cmd_list_boxwidth(None, interactive=interactive)
        return interactive

    def cmd_pull(self, model_name: str):
        if not model_name:
            console.print("Usage: pull <model>")
            console.print("Examples:")
            console.print("  pull llama3")
            console.print("  pull codellama:7b")
            return
        
        if self.api.pull_model(model_name):
            console.print(f"[green]Successfully pulled {model_name}[/green]")
        else:
            console.print(f"[red]Failed to pull {model_name}[/red]")

    def cmd_rm(self, args: List[str]):
        if not args:
            console.print("Usage: rm <model|number>")
            console.print("Examples:")
            console.print("  rm 2                     # Remove model #2 from list")
            console.print("  rm llama3.1             # Remove by model name")
            self.cmd_list()
            return
        
        model_arg = args[0]
        available_models = self.api.list_models()
        
        if not available_models:
            console.print("No models available to remove")
            return
        
        selected_model = None
        
        # Handle numeric selection
        try:
            model_number = int(model_arg)
            if 1 <= model_number <= len(available_models):
                selected_model = available_models[model_number - 1]["name"]
                console.print(f"[yellow]Selected model {model_number}:[/yellow] [red]{selected_model}[/red]")
            else:
                console.print(f"[red]Invalid model number. Please choose 1-{len(available_models)}[/red]")
                return
        except ValueError:
            # Handle model name selection
            model_names = [m["name"] for m in available_models]
            if model_arg in model_names:
                selected_model = model_arg
            else:
                console.print(f"Model '{model_arg}' not found locally")
                return
        
        # Safety confirmation
        if not Confirm.ask(f"[red]Are you sure you want to delete '{selected_model}'?[/red]"):
            console.print("Deletion cancelled")
            return
        
        # If currently loaded model is being deleted, unload it first
        if self.current_model == selected_model:
            console.print(f"[yellow]Unloading currently active model: {selected_model}[/yellow]")
            self.cmd_unload()
        
        # Delete the model
        console.print(f"[red]Deleting {selected_model}...[/red]")
        if self.api.delete_model(selected_model):
            console.print(f"[green]Successfully deleted {selected_model}[/green]")
        else:
            console.print(f"[red]Failed to delete {selected_model}[/red]")

    def cmd_copy(self, args: List[str]):
        if len(args) < 2:
            console.print("Usage: copy <source_model|number> <destination_name>")
            console.print("Examples:")
            console.print("  copy 2 my-custom-model    # Copy model #2 with new name")
            console.print("  copy llama3.1 llama-fine  # Copy by model name")
            self.cmd_list()
            return
        
        source_arg, destination = args[0], args[1]
        available_models = self.api.list_models()
        
        if not available_models:
            console.print("No models available to copy")
            return
        
        source_model = None
        
        # Handle numeric selection
        try:
            model_number = int(source_arg)
            if 1 <= model_number <= len(available_models):
                source_model = available_models[model_number - 1]["name"]
                console.print(f"[green]Selected model {model_number}:[/green] [cyan]{source_model}[/cyan]")
            else:
                console.print(f"[red]Invalid model number. Please choose 1-{len(available_models)}[/red]")
                return
        except ValueError:
            # Handle model name selection
            model_names = [m["name"] for m in available_models]
            if source_arg in model_names:
                source_model = source_arg
            else:
                console.print(f"Model '{source_arg}' not found locally")
                return
        
        # Copy the model
        console.print(f"[yellow]Copying {source_model} to {destination}...[/yellow]")
        if self.api.copy_model(source_model, destination):
            console.print(f"[green]Successfully copied {source_model} to {destination}[/green]")
        else:
            console.print(f"[red]Failed to copy {source_model} to {destination}[/red]")

    def cmd_create(self, args: List[str]):
        if not args:
            console.print("Usage: create <model_name> [modelfile_path]")
            console.print("Examples:")
            console.print("  create my-model ./Modelfile    # Create from file")
            console.print("  create my-model                # Create interactively")
            return
        
        model_name = args[0]
        modelfile_content = ""
        
        if len(args) > 1:
            # Read from file
            modelfile_path = os.path.expanduser(args[1])
            try:
                if not os.path.exists(modelfile_path):
                    console.print(f"[red]Modelfile not found: {modelfile_path}[/red]")
                    return
                    
                with open(modelfile_path, 'r', encoding='utf-8') as f:
                    modelfile_content = f.read()
                console.print(f"[green]Loaded Modelfile from {modelfile_path}[/green]")
            except Exception as e:
                console.print(f"[red]Error reading {modelfile_path}: {e}[/red]")
                return
        else:
            # Interactive input
            console.print("[yellow]Enter Modelfile content (type 'END' on a new line to finish):[/yellow]")
            console.print("[dim]Example: FROM llama3[/dim]")
            lines = []
            while True:
                try:
                    line = input()
                    if line.strip() == "END":
                        break
                    lines.append(line)
                except (KeyboardInterrupt, EOFError):
                    console.print("\n[red]Creation cancelled[/red]")
                    return
            modelfile_content = "\n".join(lines)
        
        if not modelfile_content.strip():
            console.print("[red]Empty Modelfile content[/red]")
            return
        
        # Create the model
        if self.api.create_model(model_name, modelfile_content):
            console.print(f"[green]Successfully created {model_name}[/green]")
        else:
            console.print(f"[red]Failed to create {model_name}[/red]")

    def cmd_push(self, args: List[str]):
        if not args:
            console.print("Usage: push <model|number>")
            console.print("Examples:")
            console.print("  push 2                    # Push model #2 from list")
            console.print("  push my-custom-model     # Push by model name")
            console.print("[dim]Note: You must be logged in to push models[/dim]")
            self.cmd_list()
            return
        
        model_arg = args[0]
        available_models = self.api.list_models()
        
        if not available_models:
            console.print("No models available to push")
            return
        
        selected_model = None
        
        # Handle numeric selection
        try:
            model_number = int(model_arg)
            if 1 <= model_number <= len(available_models):
                selected_model = available_models[model_number - 1]["name"]
                console.print(f"[green]Selected model {model_number}:[/green] [cyan]{selected_model}[/cyan]")
            else:
                console.print(f"[red]Invalid model number. Please choose 1-{len(available_models)}[/red]")
                return
        except ValueError:
            # Handle model name selection
            model_names = [m["name"] for m in available_models]
            if model_arg in model_names:
                selected_model = model_arg
            else:
                console.print(f"Model '{model_arg}' not found locally")
                return
        
        # Confirm push
        if not Confirm.ask(f"Push '{selected_model}' to registry?"):
            console.print("Push cancelled")
            return
        
        # Push the model
        if self.api.push_model(selected_model):
            console.print(f"[green]Successfully pushed {selected_model}[/green]")
        else:
            console.print(f"[red]Failed to push {selected_model}[/red]")

    def cmd_ps(self):
        """Show detailed running models info like official ollama ps"""
        try:
            response = self.api._request("GET", "/api/ps")
            data = response.json()
            running_models = data.get("models", [])
            
            if not running_models:
                console.print("[dim]No models currently running[/dim]")
                return
            
            # Collect all possible field names from all models
            all_fields = set()
            for model in running_models:
                all_fields.update(model.keys())
            
            # Define preferred column order (matching ollama ps output)
            preferred_order = [
                "name", "id", "digest", "size", "processor", "until", 
                "expires_at", "size_vram", "memory", "usage", "uptime", 
                "created_at", "port", "pid"
            ]
            
            # Build final column list with preferred ordering
            columns = []
            for field in preferred_order:
                if field in all_fields:
                    columns.append(field)
            
            # Add any remaining fields not in preferred order
            remaining_fields = sorted(all_fields - set(preferred_order))
            columns.extend(remaining_fields)
            
            # Create table
            optimal_width = self._calculate_optimal_width()
            table = Table(title="Running Models", box=box.ROUNDED, border_style="green", width=optimal_width)
            
            # Add columns with proper headers
            for col in columns:
                header = col.replace("_", " ").title()
                if col in ["name"]:
                    table.add_column(header, style="green")
                elif col in ["id", "digest"]:
                    table.add_column(header, width=12, max_width=12)
                elif col in ["size", "memory", "size_vram"]:
                    table.add_column(header, width=10, max_width=10)
                elif col in ["until", "expires_at", "created_at"]:
                    table.add_column(header, width=20, max_width=20)
                elif col in ["processor"]:
                    table.add_column(header, width=12, max_width=12)
                else:
                    table.add_column(header)
            
            # Add rows
            for model in running_models:
                row = []
                for col in columns:
                    value = model.get(col, "-")
                    
                    # Format specific field types
                    if col in ["size", "memory", "size_vram"] and isinstance(value, int):
                        value = self._format_size(value)
                    elif col in ["until", "expires_at", "created_at"] and isinstance(value, str) and value != "-":
                        try:
                            # Handle ISO datetime format
                            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                            if col == "until":
                                # Show relative time for "until" field
                                now = datetime.now(dt.tzinfo)
                                diff = dt - now
                                if diff.total_seconds() > 0:
                                    minutes = int(diff.total_seconds() / 60)
                                    if minutes < 60:
                                        value = f"{minutes} minutes from now"
                                    else:
                                        hours = minutes // 60
                                        value = f"{hours} hours from now"
                                else:
                                    value = "expired"
                            else:
                                value = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except:
                            # Keep original value if parsing fails
                            pass
                    elif col == "uptime" and isinstance(value, int):
                        # Convert uptime seconds to human readable
                        seconds = value
                        hours = seconds // 3600
                        minutes = (seconds % 3600) // 60
                        secs = seconds % 60
                        if hours > 0:
                            value = f"{hours}h {minutes}m"
                        elif minutes > 0:
                            value = f"{minutes}m {secs}s"
                        else:
                            value = f"{secs}s"
                    elif col == "processor" and isinstance(value, str):
                        # Format processor info (e.g., "100% GPU" or "CPU")
                        value = value.upper() if value != "-" else "-"
                    elif col in ["id", "digest"] and isinstance(value, str) and len(value) > 12:
                        # Truncate long IDs/digests
                        value = value[:12]
                    elif col == "usage" and isinstance(value, (int, float)):
                        value = f"{value:.1f}%"
                    elif value is None:
                        value = "-"
                    
                    row.append(str(value))
                
                table.add_row(*row)
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]Error fetching running models: {e}[/red]")

    def cmd_version(self):
        """Show both CLI and Ollama version information"""
        optimal_width = self._calculate_optimal_width()
        
        # Get Ollama version
        ollama_version_info = self.api.get_version()
        ollama_version = ollama_version_info.get('version', 'Unknown')
        
        # Create version display
        version_content = f"""
[bold cyan]CLI Version:[/bold cyan] {CLI_VERSION}
[bold green]Ollama Version:[/bold green] {ollama_version}

[dim]CLI follows Semantic Versioning (SemVer):
• MAJOR.MINOR.PATCH (e.g., {CLI_VERSION})
• PATCH (+0.0.1): Bug fixes, improvements
• MINOR (+0.1.0): New features, backward-compatible  
• MAJOR (+1.0.0): Breaking changes, major overhauls

Recent fixes in v1.0.4:
• Fixed verbose mode glitch
• Added /set command for in-chat settings
• Fixed starting message bug"""
        
        console.print(Panel(
            version_content,
            title="Version Information",
            border_style="cyan",
            box=box.ROUNDED,
            width=min(optimal_width, 70)
        ))

    def cmd_show(self, model_name: str):
        if not model_name:
            console.print("Usage: show <model>")
            return
        
        try:
            info = self.api.show_model(model_name)
            if not info:
                console.print(f"[red]Model '{model_name}' not found[/red]")
                return
                
            optimal_width = self._calculate_optimal_width()
            panel_content = f"Name: {info.get('name', 'Unknown')}\nSize: {self._format_size(info.get('size', 0))}\nModified: {info.get('modified_at', 'Unknown')}\nID: {info.get('digest', '-')[:12]}"
            console.print(Panel(panel_content, title="Model Info", border_style="cyan", box=box.ROUNDED, width=optimal_width))
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    def cmd_run(self, args: List[str]):
        if not args:
            console.print("Usage: run <model|number> [prompt]")
            console.print("Examples:")
            console.print("  run 2                    # Run model #2 from list")
            console.print("  run llama3.1            # Run by model name")
            console.print("  run 2 'Hello world'     # Run with immediate prompt")
            console.print("  run 2 --verbose         # Run with verbose mode")
            self.cmd_list()
            return

        verbose = False
        if "--verbose" in args: verbose = True; args.remove("--verbose")
        if "-v" in args: verbose = True; args.remove("-v")
        
        if not args:
            console.print("Please specify a model name or number")
            return

        model_arg = args[0]
        prompt = " ".join(args[1:]) if len(args) > 1 else ""

        available_models = self.api.list_models()
        if not available_models:
            console.print("No models available")
            return

        selected_model = None
        
        try:
            model_number = int(model_arg)
            if 1 <= model_number <= len(available_models):
                selected_model = available_models[model_number - 1]["name"]
                console.print(f"[green]Selected model {model_number}:[/green] [cyan]{selected_model}[/cyan]")
            else:
                console.print(f"[red]Invalid model number. Please choose 1-{len(available_models)}[/red]")
                return
        except ValueError:
            model_names = [m["name"] for m in available_models]
            if model_arg in model_names:
                selected_model = model_arg
            else:
                console.print(f"Model '{model_arg}' not found locally")
                if Confirm.ask(f"Pull '{model_arg}' from registry?"):
                    if not self.api.pull_model(model_arg):
                        return
                    selected_model = model_arg
                else:
                    return

        self.current_model = selected_model
        self.verbose = verbose
        console.print(f"[green]✓[/green] Using model: [cyan]{selected_model}[/cyan]")
        if verbose:
            console.print("[dim]Verbose mode enabled[/dim]")

        if prompt:
            self._send_message(prompt)
        else:
            console.print("[dim]Chat mode started. Type your message or 'exit' to quit.[/dim]")

    def cmd_select(self):
        _, width = self.cmd_list_boxwidth(None, interactive=True)
        return True

    def cmd_unload(self, args: List[str] = None):
        """Enhanced unload command that works with model identifiers"""
        if args is None:
            args = []
            
        # Stop current operations first
        if self.streaming or self.loading:
            self.streaming = False
            self.loading = False
            console.print("[yellow]Stopping current operation...[/yellow]")
            time.sleep(0.5)
        
        # Determine which model to unload
        model_to_unload = None
        
        if args and len(args) >= 1:
            # Model identifier provided
            identifier = args[0]
            available_models = self.api.list_models()
            
            if not available_models:
                console.print("[red]No models available to unload[/red]")
                return
            
            # Try to resolve identifier (number or name)
            try:
                model_number = int(identifier)
                if 1 <= model_number <= len(available_models):
                    model_to_unload = available_models[model_number - 1]["name"]
                    console.print(f"[yellow]Selected model {model_number}:[/yellow] [cyan]{model_to_unload}[/cyan]")
                else:
                    console.print(f"[red]Invalid model number. Please choose 1-{len(available_models)}[/red]")
                    return
            except ValueError:
                # Handle model name selection
                model_names = [m["name"] for m in available_models]
                if identifier in model_names:
                    model_to_unload = identifier
                else:
                    console.print(f"[red]Model '{identifier}' not found locally[/red]")
                    return
        else:
            # No argument - unload current model if any
            if self.current_model:
                model_to_unload = self.current_model
            else:
                console.print("[yellow]No model currently loaded to unload[/yellow]")
                return
        
        # Unload the model
        console.print(f"[yellow]Unloading {model_to_unload}...[/yellow]")
        if self.api.unload_model(model_to_unload):
            console.print(f"[green]Successfully unloaded {model_to_unload}[/green]")
            # Clear current model and history if this was the active model
            if self.current_model == model_to_unload:
                self.current_model = None
                self.history.clear()
        else:
            console.print(f"[yellow]Cleared local reference to {model_to_unload}[/yellow]")
            if self.current_model == model_to_unload:
                self.current_model = None
                self.history.clear()

    def cmd_stop(self):
        if self.streaming or self.loading:
            self.streaming = False
            self.loading = False
            console.print("[red]Stopped generation[/red]")
        else:
            console.print("No generation running")

    def cmd_history(self):
        if not self.history:
            console.print("No conversation history")
            return
        
        for msg in self.history:
            ts = msg.ts.strftime("%H:%M:%S")
            if msg.role == "user":
                console.print(f"[cyan]You[/cyan] [{ts}]: {msg.content}")
            else:
                console.print(f"[green]{self.current_model or 'Assistant'}[/green] [{ts}]:")
                console.print(msg.content)

    def cmd_clear(self):
        if self.history and Confirm.ask("Clear conversation history?"):
            self.history.clear()
            console.print("History cleared")

    def cmd_temp(self, value: str):
        if not value:
            console.print(f"Temperature: {self.temp}")
            return
        try:
            temp = float(value)
            if 0 <= temp <= 2:
                self.temp = temp
                console.print(f"Temperature set to {temp}")
            else:
                console.print("Temperature must be between 0.0 and 2.0")
        except ValueError:
            console.print("Invalid temperature value")

    def cmd_system(self, prompt: str):
        self.system_prompt = prompt
        if prompt:
            console.print(f"System prompt set: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
        else:
            console.print("System prompt cleared")

    def cmd_save(self, filename: str):
        save_dir = os.path.expanduser("~/Coding/Python")
        os.makedirs(save_dir, exist_ok=True)
        if not filename:
            filename = f"session_{datetime.now():%Y%m%d_%H%M%S}.json"
        if not os.path.dirname(filename):
            filepath = os.path.join(save_dir, filename)
        else:
            filepath = os.path.expanduser(filename)

        data = {
            "cli_version": CLI_VERSION,
            "model": self.current_model,
            "system_prompt": self.system_prompt,
            "temperature": self.temp,
            "history": [{"role": m.role, "content": m.content, "timestamp": m.ts.isoformat()} for m in self.history]
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            console.print(f"Session saved to {filepath}")
        except Exception as e:
            console.print(f"[red]Save error: {e}[/red]")

    def cmd_load(self, filename: str):
        if not filename:
            console.print("Usage: load <filename>")
            return

        if not os.path.dirname(filename):
            filepath = os.path.join(os.path.expanduser("~/Coding/Python"), filename)
        else:
            filepath = os.path.expanduser(filename)

        try:
            if not os.path.exists(filepath):
                console.print(f"[red]File not found: {filepath}[/red]")
                return
                
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Check CLI version compatibility
            saved_version = data.get("cli_version", "Unknown")
            if saved_version != CLI_VERSION:
                console.print(f"[yellow]Warning: Session saved with CLI version {saved_version}, current version is {CLI_VERSION}[/yellow]")
                if not Confirm.ask("Continue loading?"):
                    return
            
            self.current_model = data.get("model")
            self.system_prompt = data.get("system_prompt", "")
            self.temp = data.get("temperature", 0.7)
            
            # Safely load history
            history_data = data.get("history", [])
            self.history = []
            for h in history_data:
                try:
                    timestamp = datetime.fromisoformat(h["timestamp"])
                    self.history.append(ChatMsg(h["role"], h["content"], timestamp))
                except Exception:
                    # Fallback for malformed timestamps
                    self.history.append(ChatMsg(h["role"], h["content"]))
            
            console.print(f"[green]Session loaded from {filepath}[/green]")
            console.print(f"Model: {self.current_model or 'None'}, Messages: {len(self.history)}")
        except Exception as e:
            console.print(f"[red]Load error: {e}[/red]")

    def cmd_help(self):
        optimal_width = self._calculate_optimal_width()
        help_text = f"""Commands:
list                  - List available models with numbers
select                - Interactive model selection  
pull <model>          - Download model
run <model|number>    - Run model by name or number
show <model>          - Show model info
rm <model|number>     - Remove/delete model
copy <src> <dest>     - Copy model with new name
create <name> [file]  - Create model from Modelfile
push <model|number>   - Push model to registry
ps                    - Show detailed running models info
unload [model|number] - Unload model (current if no arg)
version               - Show CLI and Ollama versions
stop                  - Stop generation
temp [value]          - Show/set temperature
system [prompt]       - Set/clear system prompt
history               - Show conversation
clear                 - Clear conversation
save [file]           - Save session
load <file>           - Load session
help                  - Show this help
exit                  - Quit

In-Chat Commands:
  /set verbose <true|false> - Enable/disable verbose mode
  /set think <true|false>   - Enable/disable thinking mode
  /help                     - Show this help

Web Search:
  Add '--search' to any message for web search
  Example: \"what is quantum computing? --search\"

Examples:
  run 2                         # Run model #2 from list
  run qwen3-thinking           # Run by model name
  run 2 "Hello world"          # Run with immediate prompt
  run 2 --verbose              # Run with verbose mode
  rm 3                         # Remove model #3 from list
  copy 2 my-model              # Copy model #2 with new name
  create my-model ./Modelfile  # Create from Modelfile
  push my-model                # Push model to registry
  unload 2                     # Unload model #2 from list
  unload llama3.1              # Unload by model name
  unload                       # Unload current model
  ps                           # Show detailed running models
  version                      # Show version info

[dim]CLI Version: {CLI_VERSION} | Following Semantic Versioning (SemVer)[/dim]
"""
        console.print(Panel(help_text, title="Help", border_style="cyan", box=box.ROUNDED, width=optimal_width))

    def _send_message(self, message: str):
        if not self.current_model:
            console.print("No model loaded. Use 'run <model|number>' or 'select' first.")
            return

        original_message, use_search = self._parse_message(message)
        search_context = ""

        final_message = original_message

        self.history.append(ChatMsg("user", original_message))

        messages = [{"role": m.role, "content": m.content} for m in self.history]
        
        system_prompt = self.system_prompt
        
        self.streaming = True
        self.loading = True
        thinking = ThinkingProcessor()

        print()
        if self.first_prompt:
            console.print("[dim]Starting...[/dim]")
            self.first_prompt = False

        try:
            thinking_displayed = False
            thinking_done_displayed = False
            is_thinking_model = False
            collected_response = ""
            first_chunk = True

            for chunk in self.api.chat_stream(self.current_model, messages, system_prompt, self.temp, self.verbose):
                if not self.streaming:
                    break

                # Verbose debug lines start with our marker:
                if self.verbose and chunk.startswith('[DEBUG'):
                    console.print(f"\n{chunk}", style="yellow dim")
                    continue

                # Handle error messages
                if chunk.startswith('\n[ERROR]'):
                    console.print(chunk, style="red")
                    break

                if first_chunk:
                    self.loading = False
                    first_chunk = False

                if self.thinking:
                    new_thinking, new_visible, started, finished = thinking.process_chunk(chunk)
                    if started:
                        is_thinking_model = True
                else:
                    new_thinking, new_visible, started, finished = "", chunk, False, False

                if is_thinking_model and self.thinking:
                    if started and not thinking_displayed:
                        console.print(Text("Thinking...", style="dim"))
                        thinking_displayed = True

                    if thinking.thinking_active and new_thinking:
                        console.print(Text(new_thinking, style="dim"), end="")

                    if finished and not thinking_done_displayed:
                        console.print(Text("\n...done thinking\n", style="dim"))
                        thinking_done_displayed = True

                    if new_visible and thinking_done_displayed:
                        console.print(new_visible, end="", highlight=False)
                        collected_response += new_visible
                else:
                    if new_visible:
                        console.print(new_visible, end="", highlight=False)
                        collected_response += new_visible
            
            if is_thinking_model and self.thinking:
                final_response = thinking.get_display_content()
                if final_response and final_response != collected_response:
                    remaining = final_response.replace(collected_response, "")
                    if remaining:
                        console.print(remaining, end="", highlight=False)
                        collected_response = final_response

            console.print()
            if collected_response:
                self.history.append(ChatMsg("assistant", collected_response))

        except KeyboardInterrupt:
            console.print("\n[red]Generation interrupted[/red]")
        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")
        finally:
            self.streaming = False
            self.loading = False
            thinking.reset()

    def run(self):
        # Calculate optimal width based on terminal size and content
        optimal_width = self._calculate_optimal_width()
        
        banner_text = (
            f"Maternion Ollama CLI v{CLI_VERSION}"
        )
        console.print(Panel(
            banner_text,
            title="Ollama CLI",
            border_style="cyan",
            box=box.ROUNDED,
            width=optimal_width
        ))

        self.cmd_list_boxwidth(optimal_width)
        
        while True:
            try:
                # Recalculate width in case terminal was resized
                current_width = self._calculate_optimal_width()
                user_input = self._input()
                
                if not user_input:
                    continue

                if self.current_model and user_input.startswith("/"):
                    if self._handle_slash_commands(user_input):
                        continue

                if self.current_model and user_input.lower() in ["exit", "/exit"]:
                    self.current_model = None
                    console.print("Exited chat mode")
                    continue

                parts = user_input.split()
                cmd = parts[0].lower()
                args = parts[1:]

                if cmd in ["exit", "quit"]:
                    if self.history and Confirm.ask("Save session before exit?"):
                        self.cmd_save("")
                    console.print("Goodbye!")
                    break
                elif cmd == "list":
                    self.cmd_list_boxwidth(current_width)
                elif cmd == "select":
                    self.cmd_select()
                elif cmd == "pull":
                    self.cmd_pull(args[0] if args else "")
                elif cmd == "run":
                    self.cmd_run(args)
                elif cmd == "show":
                    self.cmd_show(args[0] if args else "")
                elif cmd in ["rm", "remove"]:
                    self.cmd_rm(args)
                elif cmd == "copy":
                    self.cmd_copy(args)
                elif cmd == "create":
                    self.cmd_create(args)
                elif cmd == "push":
                    self.cmd_push(args)
                elif cmd == "ps":
                    self.cmd_ps()
                elif cmd == "version":
                    self.cmd_version()
                elif cmd == "unload":
                    self.cmd_unload(args)
                elif cmd == "stop":
                    self.cmd_stop()
                elif cmd == "history":
                    self.cmd_history()
                elif cmd == "clear":
                    self.cmd_clear()
                elif cmd == "temp":
                    self.cmd_temp(args[0] if args else "")
                elif cmd == "system":
                    self.cmd_system(" ".join(args))
                elif cmd == "save":
                    self.cmd_save(args[0] if args else "")
                elif cmd == "load":
                    self.cmd_load(args[0] if args else "")
                elif cmd == "help":
                    self.cmd_help()
                else:
                    if self.current_model:
                        self._send_message(user_input)
                    else:
                        console.print(f"Unknown command: {cmd}")
                        console.print("Type 'help' for commands or 'run <number>' to select a model")

            except KeyboardInterrupt:
                console.print("\nGoodbye!")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

def main():
    parser = argparse.ArgumentParser(
        description=f"Ollama CLI v{CLI_VERSION}",
        epilog=f"CLI Version: {CLI_VERSION} | Following Semantic Versioning (SemVer)"
    )
    parser.add_argument("--host", default="http://localhost:11434", help="Ollama host")
    parser.add_argument("--timeout", type=float, default=300.0, help="API timeout in seconds (default: 300)")
    parser.add_argument("--version", action="version", version=f"CLI Version: {CLI_VERSION}")
    parser.add_argument("command", nargs="*", help="Command to run")
    args = parser.parse_args()

    cli = CLI(args.host, args.timeout)

    if args.command:
        cmd_str = " ".join(args.command)
        parts = cmd_str.split()
        cmd = parts[0].lower()
        cmd_args = parts[1:]

        if cmd == "list":
            cli.cmd_list()
        elif cmd == "select":
            cli.cmd_select()
        elif cmd == "run":
            cli.cmd_run(cmd_args)
        elif cmd == "pull":
            cli.cmd_pull(cmd_args[0] if cmd_args else "")
        elif cmd == "show":
            cli.cmd_show(cmd_args[0] if cmd_args else "")
        elif cmd in ["rm", "remove"]:
            cli.cmd_rm(cmd_args)
        elif cmd == "copy":
            cli.cmd_copy(cmd_args)
        elif cmd == "create":
            cli.cmd_create(cmd_args)
        elif cmd == "push":
            cli.cmd_push(cmd_args)
        elif cmd == "ps":
            cli.cmd_ps()
        elif cmd == "unload":
            cli.cmd_unload(cmd_args)
        elif cmd == "version":
            cli.cmd_version()
        else:
            console.print(f"Unknown command: {cmd}")
    else:
        cli.run()

if __name__ == "__main__":
    main()
