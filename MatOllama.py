#!/usr/bin/env python3
"""
Ollama CLI
Version: 1.1.0
"""
import argparse
import json
import os
import sys
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Generator, List, Dict, Optional
from pathlib import Path
import requests
from requests.exceptions import RequestException
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, IntPrompt
from rich.text import Text
from rich import box
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
import inquirer

CLI_VERSION = "1.1.0"

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
                        status = data.get('status', 'Unknown')
                        
                        if status == 'pulling manifest':
                            progress.update(task, status="📋 Pulling manifest...")
                        elif status == 'downloading':
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
                            time.sleep(0.5)
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
            self._request("POST", "/api/generate", json={
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

                if "error" in data:
                    yield f"\n[ERROR]: {data['error']}"
                    break

                if "message" in data and "content" in data["message"]:
                    yield data["message"]["content"]

                if verbose:
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
        self.blocking_operation = False
        
        # Setup directories relative to script location
        self.base_dir = Path(__file__).parent.absolute()
        self.sessions_dir = self.base_dir / "Sessions"
        self.exports_dir = self.base_dir / "Exports"
        self.config_file = self.base_dir / "config.json"
        
        # Create directories
        self.sessions_dir.mkdir(exist_ok=True)
        self.exports_dir.mkdir(exist_ok=True)
        
        # Load configuration (including theme color)
        self._load_config()
        
        # Setup prompt_toolkit history (FIXED: no autocomplete)
        self.history_file = FileHistory(str(self.base_dir / ".ollama_history"))
        
        signal.signal(signal.SIGINT, self._signal_handler)
        self._check_connection()

    def _load_config(self):
        """Load configuration from config.json"""
        default_config = {
            "theme_color": "cyan",
            "temperature": 0.7,
            "verbose": False,
            "thinking": True
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                self.theme_color = config.get("theme_color", "cyan")
                self.temp = config.get("temperature", 0.7)
                self.verbose = config.get("verbose", False)
                self.thinking = config.get("thinking", True)
            else:
                self.theme_color = default_config["theme_color"]
                self._save_config()
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load config, using defaults: {e}[/yellow]")
            self.theme_color = default_config["theme_color"]

    def _save_config(self):
        """Save configuration to config.json"""
        config = {
            "theme_color": self.theme_color,
            "temperature": self.temp,
            "verbose": self.verbose,
            "thinking": self.thinking
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not save config: {e}[/yellow]")

    def _signal_handler(self, sig, frame):
        if self.streaming or self.loading:
            self.streaming = False
            self.loading = False
            console.print("\n[red]Generation interrupted[/red]")
        else:
            console.print("\n[yellow]Use '/exit' to quit chat mode[/yellow]")

    def _check_connection(self):
        try:
            models = self.api.list_models()
            if models is not None:
                console.print("[green]✓ Connected to Ollama[/green]")
            else:
                console.print("[yellow]⚠ Connected to Ollama but no models found[/yellow]")
        except Exception:
            console.print("[yellow]⚠ Cannot connect to Ollama[/yellow]")
            console.print("  Make sure Ollama is running: [cyan]ollama serve[/cyan]")

    def _get_prompt(self):
        return "You: " if self.current_model else "Ollama: "

    def _input(self):
        if self.blocking_operation:
            return ""
            
        print()
        try:
            # FIXED: Removed AutoSuggestFromHistory() to fix autocomplete issues
            return prompt(
                self._get_prompt(),
                history=self.history_file
            ).strip()
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

        elif command == "/switch":
            if not args:
                console.print("Usage: /switch <model|number>")
                console.print("Examples:")
                console.print("  /switch 2              # Switch to model #2")
                console.print("  /switch qwen3-coder   # Switch to model by name")
                self.cmd_list()
                return True
            
            if self.current_model:
                console.print(f"[yellow]Unloading {self.current_model}...[/yellow]")
                self.api.unload_model(self.current_model)
            
            model_arg = args[0]
            available_models = self.api.list_models()
            
            if not available_models:
                console.print("[red]No models available[/red]")
                return True
            
            selected_model = None
            
            try:
                model_number = int(model_arg)
                if 1 <= model_number <= len(available_models):
                    selected_model = available_models[model_number - 1]["name"]
                    console.print(f"[green]Selected model {model_number}:[/green] [cyan]{selected_model}[/cyan]")
                else:
                    console.print(f"[red]Invalid model number. Please choose 1-{len(available_models)}[/red]")
                    return True
            except ValueError:
                model_names = [m["name"] for m in available_models]
                if model_arg in model_names:
                    selected_model = model_arg
                else:
                    console.print(f"Model '{model_arg}' not found locally")
                    if Confirm.ask(f"Pull '{model_arg}' from registry?"):
                        if self.api.pull_model(model_arg):
                            selected_model = model_arg
                        else:
                            return True
                    else:
                        return True
            
            if selected_model:
                if self.history:
                    context_prompt = "Previous conversation context:\n\n"
                    for msg in self.history:
                        context_prompt += f"{msg.role.title()}: {msg.content}\n\n"
                    context_prompt += f"You are now {selected_model}. Please continue this conversation naturally, acknowledging the context above."
                    
                    self.system_prompt = context_prompt
                    console.print(f"[dim]Transferring conversation context to {selected_model}...[/dim]")
                
                self.current_model = selected_model
                console.print(f"[green]✓ Switched to:[/green] [{self.theme_color}]{selected_model}[/{self.theme_color}]")
                console.print("[dim]Continue chatting with the new model...[/dim]")

        elif command == "/exit":
            self.current_model = None
            self.history.clear()
            console.print("Exited chat mode")
            return "EXIT"

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

    def _get_terminal_width(self) -> int:
        try:
            return console.size.width
        except:
            return 80

    def _calculate_optimal_width(self) -> int:
        """FIXED: Simple width calculation that works reliably"""
        models = self.api.list_models()
        terminal_width = self._get_terminal_width()
        
        min_width = 60
        max_width = 120
        
        if not models:
            return min(80, terminal_width - 2)
        
        # Simple approach: use terminal width if reasonable, otherwise default
        if terminal_width >= min_width and terminal_width <= max_width:
            return terminal_width - 2
        else:
            return min_width

    def cmd_list_boxwidth(self, width=None, interactive=False):
        models = self.api.list_models()
        
        if width is None:
            width = self._calculate_optimal_width()
        
        if not models:
            console.print(Panel(
                "No models found. Use 'pull <model>' to download.",
                title="Models", border_style=self.theme_color, box=box.ROUNDED, width=width
            ))
            return False, width

        table = Table(title="Available Models", box=box.ROUNDED, border_style=self.theme_color, width=width)
        
        # FIXED: Restore proper columns with serial numbers
        table.add_column("#", style=self.theme_color, width=3, max_width=3)
        table.add_column("Name")
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
            
            # FIXED: Add serial numbers back
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
            self.cmd_list()
            return
        
        model_arg = args[0]
        available_models = self.api.list_models()
        
        if not available_models:
            console.print("No models available to remove")
            return
        
        selected_model = None
        
        try:
            model_number = int(model_arg)
            if 1 <= model_number <= len(available_models):
                selected_model = available_models[model_number - 1]["name"]
                console.print(f"[yellow]Selected model {model_number}:[/yellow] [red]{selected_model}[/red]")
            else:
                console.print(f"[red]Invalid model number. Please choose 1-{len(available_models)}[/red]")
                return
        except ValueError:
            model_names = [m["name"] for m in available_models]
            if model_arg in model_names:
                selected_model = model_arg
            else:
                console.print(f"Model '{model_arg}' not found locally")
                return
        
        if not Confirm.ask(f"[red]Are you sure you want to delete '{selected_model}'?[/red]"):
            console.print("Deletion cancelled")
            return
        
        if self.current_model == selected_model:
            console.print(f"[yellow]Unloading currently active model: {selected_model}[/yellow]")
            self.cmd_unload()
        
        console.print(f"[red]Deleting {selected_model}...[/red]")
        if self.api.delete_model(selected_model):
            console.print(f"[green]Successfully deleted {selected_model}[/green]")
        else:
            console.print(f"[red]Failed to delete {selected_model}[/red]")

    def cmd_rename(self, args: List[str]):
        if len(args) < 2:
            console.print("Usage: rename <old_model|number> <new_name>")
            self.cmd_list()
            return
        
        old_arg, new_name = args[0], args[1]
        available_models = self.api.list_models()
        
        if not available_models:
            console.print("No models available to rename")
            return
        
        old_model = None
        
        try:
            model_number = int(old_arg)
            if 1 <= model_number <= len(available_models):
                old_model = available_models[model_number - 1]["name"]
                console.print(f"[green]Selected model {model_number}:[/green] [{self.theme_color}]{old_model}[/{self.theme_color}]")
            else:
                console.print(f"[red]Invalid model number. Please choose 1-{len(available_models)}[/red]")
                return
        except ValueError:
            model_names = [m["name"] for m in available_models]
            if old_arg in model_names:
                old_model = old_arg
            else:
                console.print(f"Model '{old_arg}' not found locally")
                return
        
        self.blocking_operation = True
        console.print(f"[yellow]Renaming {old_model} to {new_name}...[/yellow]")
        console.print(f"[dim]Please wait, this may take some time on slower drives...[/dim]")
        
        try:
            console.print(f"[dim]Copying {old_model}...[/dim]")
            if not self.api.copy_model(old_model, new_name):
                console.print(f"[red]Failed to copy {old_model}[/red]")
                return
            
            console.print(f"[dim]Removing original {old_model}...[/dim]")
            if not self.api.delete_model(old_model):
                console.print(f"[yellow]Warning: Copy succeeded but failed to delete original {old_model}[/yellow]")
                console.print(f"[yellow]You now have both {old_model} and {new_name}[/yellow]")
            else:
                console.print(f"[green]Successfully renamed {old_model} to {new_name}[/green]")
            
            if self.current_model == old_model:
                self.current_model = new_name
                console.print(f"[dim]Updated active model to {new_name}[/dim]")
                
        except Exception as e:
            console.print(f"[red]Rename operation failed: {e}[/red]")
        finally:
            self.blocking_operation = False

    def cmd_copy(self, args: List[str]):
        if len(args) < 2:
            console.print("Usage: copy <source_model|number> <destination_name>")
            self.cmd_list()
            return
        
        source_arg, destination = args[0], args[1]
        available_models = self.api.list_models()
        
        if not available_models:
            console.print("No models available to copy")
            return
        
        source_model = None
        
        try:
            model_number = int(source_arg)
            if 1 <= model_number <= len(available_models):
                source_model = available_models[model_number - 1]["name"]
                console.print(f"[green]Selected model {model_number}:[/green] [{self.theme_color}]{source_model}[/{self.theme_color}]")
            else:
                console.print(f"[red]Invalid model number. Please choose 1-{len(available_models)}[/red]")
                return
        except ValueError:
            model_names = [m["name"] for m in available_models]
            if source_arg in model_names:
                source_model = source_arg
            else:
                console.print(f"Model '{source_arg}' not found locally")
                return
        
        console.print(f"[yellow]Copying {source_model} to {destination}...[/yellow]")
        if self.api.copy_model(source_model, destination):
            console.print(f"[green]Successfully copied {source_model} to {destination}[/green]")
        else:
            console.print(f"[red]Failed to copy {source_model} to {destination}[/red]")

    def cmd_create(self, args: List[str]):
        if not args:
            console.print("Usage: create <model_name> [modelfile_path]")
            return
        
        model_name = args[0]
        modelfile_content = ""
        
        if len(args) > 1:
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
            console.print("[yellow]Enter Modelfile content (type 'END' on a new line to finish):[/yellow]")
            console.print("[dim]Example: FROM llama3[/dim]")
            lines = []
            while True:
                try:
                    line = prompt("Modelfile> ")
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
        
        if self.api.create_model(model_name, modelfile_content):
            console.print(f"[green]Successfully created {model_name}[/green]")
        else:
            console.print(f"[red]Failed to create {model_name}[/red]")

    def cmd_push(self, args: List[str]):
        if not args:
            console.print("Usage: push <model|number>")
            console.print("[dim]Note: You must be logged in to push models[/dim]")
            self.cmd_list()
            return
        
        model_arg = args[0]
        available_models = self.api.list_models()
        
        if not available_models:
            console.print("No models available to push")
            return
        
        selected_model = None
        
        try:
            model_number = int(model_arg)
            if 1 <= model_number <= len(available_models):
                selected_model = available_models[model_number - 1]["name"]
                console.print(f"[green]Selected model {model_number}:[/green] [{self.theme_color}]{selected_model}[/{self.theme_color}]")
            else:
                console.print(f"[red]Invalid model number. Please choose 1-{len(available_models)}[/red]")
                return
        except ValueError:
            model_names = [m["name"] for m in available_models]
            if model_arg in model_names:
                selected_model = model_arg
            else:
                console.print(f"Model '{model_arg}' not found locally")
                return
        
        if not Confirm.ask(f"Push '{selected_model}' to registry?"):
            console.print("Push cancelled")
            return
        
        if self.api.push_model(selected_model):
            console.print(f"[green]Successfully pushed {selected_model}[/green]")
        else:
            console.print(f"[red]Failed to push {selected_model}[/red]")

    def cmd_ps(self):
        try:
            response = self.api._request("GET", "/api/ps")
            data = response.json()
            running_models = data.get("models", [])
            
            if not running_models:
                console.print("[dim]No models currently running[/dim]")
                return
            
            optimal_width = self._calculate_optimal_width()
            table = Table(title="Running Models", box=box.ROUNDED, border_style=self.theme_color, width=optimal_width)
            
            table.add_column("Name", style=self.theme_color)
            table.add_column("Size", width=10, max_width=10)
            table.add_column("Processor", width=12, max_width=12)
            table.add_column("Until", width=20, max_width=20)
            
            for model in running_models:
                name = model.get("name", "Unknown")
                size = self._format_size(model.get("size", 0))
                processor = model.get("processor", "-")
                until = model.get("until", "-")
                
                if until != "-":
                    try:
                        dt = datetime.fromisoformat(until.replace("Z", "+00:00"))
                        now = datetime.now(dt.tzinfo)
                        diff = dt - now
                        if diff.total_seconds() > 0:
                            minutes = int(diff.total_seconds() / 60)
                            until = f"{minutes} min" if minutes < 60 else f"{minutes//60} hrs"
                        else:
                            until = "expired"
                    except:
                        until = until[:16]
                
                table.add_row(name, size, processor, until)
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]Error fetching running models: {e}[/red]")

    def cmd_version(self):
        optimal_width = self._calculate_optimal_width()
        
        ollama_version_info = self.api.get_version()
        ollama_version = ollama_version_info.get('version', 'Unknown')
        
        version_content = f"""
[bold {self.theme_color}]CLI Version:[/bold {self.theme_color}] {CLI_VERSION}
[bold green]Ollama Version:[/bold green] {ollama_version}

[dim]Enhanced Ollama CLI with:
• Context-aware model switching
• Persistent themes & settings  
• Conversation export (JSON/text)
• Dynamic model list display
• Professional terminal UI[/dim]"""
        
        console.print(Panel(
            version_content,
            title="Version Information",
            border_style=self.theme_color,
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
            console.print(Panel(panel_content, title="Model Info", border_style=self.theme_color, box=box.ROUNDED, width=optimal_width))
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    def cmd_run(self, args: List[str]):
        if not args:
            console.print("Usage: run <model|number> [prompt]")
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
                console.print(f"[green]Selected model {model_number}:[/green] [{self.theme_color}]{selected_model}[/{self.theme_color}]")
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
        console.print(f"[green]✓[/green] Using model: [{self.theme_color}]{selected_model}[/{self.theme_color}]")
        if verbose:
            console.print("[dim]Verbose mode enabled[/dim]")

        if prompt:
            self._send_message(prompt)
        else:
            console.print("[dim]Chat mode started. Type your message or '/exit' to quit.[/dim]")

    def cmd_select(self):
        models = self.api.list_models()
        
        if not models:
            console.print(Panel(
                "No models found. Use 'pull <model>' to download.",
                title="Models", border_style=self.theme_color, box=box.ROUNDED
            ))
            return False
        
        choices = []
        for i, m in enumerate(models, 1):
            name = m.get("name", "Unknown")
            size = self._format_size(m.get("size", 0))
            if name == self.current_model:
                name = f"→ {name}"
            choices.append(f"{i:2d}. {name} ({size})")
        
        try:
            questions = [
                inquirer.List(
                    'model',
                    message="Select a model (use arrow keys, Enter to confirm)",
                    choices=choices,
                    carousel=True
                ),
            ]
            
            answers = inquirer.prompt(questions)
            if answers and answers['model']:
                selected_text = answers['model']
                model_num = int(selected_text.split('.')[0].strip())
                
                if 1 <= model_num <= len(models):
                    self.current_model = models[model_num-1]["name"]
                    console.print(f"[green]✓ Selected:[/green] [{self.theme_color}]{self.current_model}[/{self.theme_color}]")
                    console.print("[dim]Start chatting or type '/exit' to return to command mode.[/dim]")
                    return True
            
            console.print("Selection cancelled")
            return False
            
        except (KeyboardInterrupt, EOFError):
            console.print("\nSelection cancelled")
            return False

    def cmd_unload(self, args: List[str] = None):
        if args is None:
            args = []
            
        if self.streaming or self.loading:
            self.streaming = False
            self.loading = False
            console.print("[yellow]Stopping current operation...[/yellow]")
            time.sleep(0.5)
        
        model_to_unload = None
        
        if args and len(args) >= 1:
            identifier = args[0]
            available_models = self.api.list_models()
            
            if not available_models:
                console.print("[red]No models available to unload[/red]")
                return
            
            try:
                model_number = int(identifier)
                if 1 <= model_number <= len(available_models):
                    model_to_unload = available_models[model_number - 1]["name"]
                    console.print(f"[yellow]Selected model {model_number}:[/yellow] [{self.theme_color}]{model_to_unload}[/{self.theme_color}]")
                else:
                    console.print(f"[red]Invalid model number. Please choose 1-{len(available_models)}[/red]")
                    return
            except ValueError:
                model_names = [m["name"] for m in available_models]
                if identifier in model_names:
                    model_to_unload = identifier
                else:
                    console.print(f"[red]Model '{identifier}' not found locally[/red]")
                    return
        else:
            if self.current_model:
                model_to_unload = self.current_model
            else:
                console.print("[yellow]No model currently loaded to unload[/yellow]")
                return
        
        console.print(f"[yellow]Unloading {model_to_unload}...[/yellow]")
        if self.api.unload_model(model_to_unload):
            console.print(f"[green]Successfully unloaded {model_to_unload}[/green]")
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
                console.print(f"[{self.theme_color}]You[/{self.theme_color}] [{ts}]: {msg.content}")
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
                self._save_config()
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

    def cmd_theme(self, color: str):
        if not color:
            console.print(f"Current theme: [{self.theme_color}]{self.theme_color}[/{self.theme_color}]")
            console.print("Available: red, green, yellow, blue, magenta, cyan")
            return
            
        available_colors = ["red", "green", "yellow", "blue", "magenta", "cyan"]
        if color.lower() in available_colors:
            self.theme_color = color.lower()
            self._save_config()
            console.print(f"[{self.theme_color}]Theme color set to {color}[/{self.theme_color}]")
        else:
            console.print("Available: red, green, yellow, blue, magenta, cyan")

    def cmd_export(self, args: List[str]):
        if not self.history:
            console.print("[yellow]No conversation history to export[/yellow]")
            return
        
        export_format = "json"
        filename = None
        
        if args:
            if args[0].lower() in ["json", "text", "txt"]:
                export_format = "json" if args[0].lower() == "json" else "text"
                filename = args[1] if len(args) > 1 else None
            else:
                filename = args[0]
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_name = self.current_model or "unknown"
            safe_model_name = model_name.replace(":", "_").replace("/", "_")
            extension = "json" if export_format == "json" else "txt"
            filename = f"chat_{safe_model_name}_{timestamp}.{extension}"
        
        if export_format == "json" and not filename.endswith('.json'):
            filename += '.json'
        elif export_format == "text" and not (filename.endswith('.txt') or filename.endswith('.md')):
            filename += '.txt'
        
        filepath = self.exports_dir / filename
        
        try:
            if export_format == "json":
                export_data = {
                    "conversation_id": f"ollama_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "model": self.current_model or "unknown",
                    "created": datetime.now().isoformat(),
                    "message_count": len(self.history),
                    "messages": [
                        {
                            "role": msg.role,
                            "content": msg.content,
                            "timestamp": msg.ts.isoformat()
                        }
                        for msg in self.history
                    ]
                }
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                    
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Ollama CLI Conversation Export\n")
                    f.write(f"Model: {self.current_model or 'Unknown'}\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Messages: {len(self.history)}\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for msg in self.history:
                        timestamp = msg.ts.strftime("%H:%M:%S")
                        if msg.role == "user":
                            f.write(f"You [{timestamp}]: {msg.content}\n\n")
                        else:
                            f.write(f"{self.current_model or 'Assistant'} [{timestamp}]:\n{msg.content}\n\n")
            
            console.print(f"[green]Exported to:[/green] {filepath}")
            console.print(f"[dim]Format: {export_format.upper()}, Messages: {len(self.history)}[/dim]")
            
        except Exception as e:
            console.print(f"[red]Export failed: {e}[/red]")

    def cmd_save(self, filename: str):
        if not filename:
            filename = f"session_{datetime.now():%Y%m%d_%H%M%S}.json"
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = self.sessions_dir / filename

        data = {
            "cli_version": CLI_VERSION,
            "model": self.current_model,
            "system_prompt": self.system_prompt,
            "temperature": self.temp,
            "theme_color": self.theme_color,
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

        if not filename.endswith('.json'):
            filename += '.json'
        
        filepath = self.sessions_dir / filename
        
        if not filepath.exists():
            filepath = Path(filename).expanduser()

        try:
            if not filepath.exists():
                console.print(f"[red]File not found: {filepath}[/red]")
                return
                
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            saved_version = data.get("cli_version", "Unknown")
            if saved_version != CLI_VERSION:
                console.print(f"[yellow]Warning: Session saved with CLI version {saved_version}, current version is {CLI_VERSION}[/yellow]")
                if not Confirm.ask("Continue loading?"):
                    return
            
            self.current_model = data.get("model")
            self.system_prompt = data.get("system_prompt", "")
            self.temp = data.get("temperature", 0.7)
            self.theme_color = data.get("theme_color", "cyan")
            
            self._save_config()
            
            history_data = data.get("history", [])
            self.history = []
            for h in history_data:
                try:
                    timestamp = datetime.fromisoformat(h["timestamp"])
                    self.history.append(ChatMsg(h["role"], h["content"], timestamp))
                except Exception:
                    self.history.append(ChatMsg(h["role"], h["content"]))
            
            console.print(f"[green]Session loaded from {filepath}[/green]")
            console.print(f"Model: {self.current_model or 'None'}, Messages: {len(self.history)}")
        except Exception as e:
            console.print(f"[red]Load error: {e}[/red]")

    def cmd_help(self):
        optimal_width = self._calculate_optimal_width()
        help_text = f"""Commands:
list                  - List available models
select                - Interactive model selection  
run <model|number>    - Run model by name or number
show <model>          - Show model info
rm <model|number>     - Remove model
rename <old> <new>    - Rename model (copy and delete original)
copy <src> <dest>     - Copy model with new name
create <name> [file]  - Create model from Modelfile
push <model|number>   - Push model to registry
ps                    - Show running models
unload [model|number] - Unload model
stop                  - Stop generation
history               - Show conversation history
clear                 - Clear conversation
export [format] [file]- Export conversation (json/text)
theme [color]         - Set color theme (persistent)
temp [value]          - Set temperature (persistent)
save [file]           - Save session
load <file>           - Load session
version               - Show version info
help                  - Show this help
exit                  - Quit

In Chat:
  /switch <model|number> - Switch model with context
  /set verbose <true|false> - Toggle verbose mode
  /set think <true|false>   - Toggle thinking mode
  /exit                     - Exit chat mode

Examples:
  run 1
  rename 1 mymodel  
  export json
  theme cyan
  /switch 2

[dim]CLI Version: {CLI_VERSION} | Settings persist between sessions[/dim]
"""
        console.print(Panel(help_text, title="Help", border_style=self.theme_color, box=box.ROUNDED, width=optimal_width))

    def _send_message(self, message: str):
        if not self.current_model:
            console.print("No model loaded. Use 'run <model|number>' or 'select' first.")
            return

        self.history.append(ChatMsg("user", message))

        messages = [{"role": m.role, "content": m.content} for m in self.history]
        
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

            for chunk in self.api.chat_stream(self.current_model, messages, self.system_prompt, self.temp, self.verbose):
                if not self.streaming:
                    break

                if self.verbose and chunk.startswith('[DEBUG'):
                    console.print(f"\n{chunk}", style="yellow dim")
                    continue

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
        optimal_width = self._calculate_optimal_width()
        
        banner_text = (
            f"Enhanced Ollama CLI v{CLI_VERSION}\n"
            f"[{self.theme_color}]✓ Context-aware switching • Persistent themes • Conversation export[/{self.theme_color}]"
        )
        console.print(Panel(
            banner_text,
            title="Ollama CLI",
            border_style=self.theme_color,
            box=box.ROUNDED,
            width=optimal_width
        ))

        self.cmd_list_boxwidth(optimal_width)
        
        while True:
            try:
                current_width = self._calculate_optimal_width()
                user_input = self._input()

                if not user_input:
                    continue

                if self.current_model:
                    if user_input.startswith("/"):
                        result = self._handle_slash_commands(user_input)
                        if result == "EXIT":
                            continue
                        elif result:
                            continue
                    else:
                        self._send_message(user_input)
                else:
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
                    elif cmd == "rename":
                        self.cmd_rename(args)
                    elif cmd == "copy":
                        self.cmd_copy(args)
                    elif cmd == "create":
                        self.cmd_create(args)
                    elif cmd == "push":
                        self.cmd_push(args)
                    elif cmd == "export":
                        self.cmd_export(args)
                    elif cmd == "theme":
                        self.cmd_theme(args[0] if args else "")
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
                        console.print(f"Unknown command: {cmd}")
                        console.print("Type 'help' for commands or 'select' to choose a model")

            except KeyboardInterrupt:
                console.print("\nGoodbye!")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

def main():
    parser = argparse.ArgumentParser(
        description=f"Enhanced Ollama CLI v{CLI_VERSION}",
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
        elif cmd == "rename":
            cli.cmd_rename(cmd_args)
        elif cmd == "copy":
            cli.cmd_copy(cmd_args)
        elif cmd == "create":
            cli.cmd_create(cmd_args)
        elif cmd == "push":
            cli.cmd_push(cmd_args)
        elif cmd == "export":
            cli.cmd_export(cmd_args)
        elif cmd == "theme":
            cli.cmd_theme(cmd_args[0] if cmd_args else "")
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
