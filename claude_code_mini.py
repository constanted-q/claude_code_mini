#!/usr/bin/env python3
"""Minimal Claude‑Code‑like assistant in pure Python.

This single‑file prototype shows the end‑to‑end flow so you can
 iterate quickly; once it works, split into packages (cli.py, agent.py …).
 It borrows interaction patterns from Aider (CLI / repo map / patch) and
 Goose (agent loop, tools, sub‑agents) but keeps dependencies minimal.
"""
from __future__ import annotations
import argparse
import os
import pathlib
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional

# --- Section 1: Repo Context Gatherer ------------------------------------

def discover_repo(root: pathlib.Path) -> List[pathlib.Path]:
    """Return a list of project files under *root* (git‑tracked if possible)."""
    git_dir = root / '.git'
    if git_dir.exists():
        try:
            tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files'], text=True)
            return [root / p for p in tracked.strip().splitlines() if p]
        except subprocess.CalledProcessError:
            pass  # fall back to walking the tree if git fails
    return [p for p in root.rglob('*') if p.is_file() and not p.name.startswith('.')]


def build_context_snippets(paths: List[pathlib.Path], max_bytes: int = 30_000) -> str:
    """Read files until *max_bytes* and return concatenated snippet for the model."""
    out, used = [], 0
    for p in paths:
        try:
            data = p.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue  # skip binaries
        snippet = f"\n# File: {p.relative_to(pathlib.Path.cwd())}\n" + data
        if used + len(snippet) > max_bytes:
            break
        out.append(snippet)
        used += len(snippet)
    return "\n".join(out)

# --- Section 2: Patch Engine --------------------------------------------

def apply_unified_patch(patch: str, root: pathlib.Path = pathlib.Path('.')) -> None:
    """Apply a unified‑diff *patch* inside *root* using the `patch` utility."""
    proc = subprocess.run(['patch', '-p0', '-s'], input=patch, text=True, cwd=root)
    if proc.returncode != 0:
        raise RuntimeError('patch command failed')

# --- Section 3: Tool Abstractions ---------------------------------------

ToolFn = Callable[[Dict[str, Any]], Any]

@dataclass
class Tool:
    name: str
    description: str
    schema: Dict[str, Any]
    run: ToolFn


# Example built‑in tool ---------------------------------------------------

def shell_tool(args: Dict[str, Any]) -> str:
    """Run a shell command and return its stdout/stderr."""
    cmd = args['command']
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.stdout + res.stderr

SHELL_TOOL = Tool(
    name='shell',
    description='Execute arbitrary shell commands and return the output',
    schema={'type': 'object', 'properties': {'command': {'type': 'string'}}, 'required': ['command']},
    run=shell_tool,
)

# --- Section 4: Agent Loop ---------------------------------------------

@dataclass
class AgentConfig:
    model: str = 'anthropic/claude-3-sonnet'
    max_tokens: int = 4096
    temperature: float = 0.2


def call_llm(prompt: str, tools: List[Tool], cfg: AgentConfig) -> Dict[str, Any]:
    """Cheap stub that returns a fake tool call for demonstration.
    Replace with real SDK call (OpenAI, Anthropic, etc.) that supports
    function‑/tool‑calling and returns tool invocations in JSON.
    """
    # For demo purposes, pretend the model wants to run the shell tool
    return {
        'type': 'tool',
        'name': 'shell',
        'arguments': {'command': 'echo "Hello from sub‑shell"'},
    }

@dataclass
class Agent:
    cfg: AgentConfig
    tools: Dict[str, Tool]
    history: List[Dict[str, Any]] = field(default_factory=list)

    def run(self, user_message: str) -> str:
        """Single iteration of the Claude‑Code mini agent loop."""
        self.history.append({'role': 'user', 'content': user_message})
        tool_call = call_llm(user_message, list(self.tools.values()), self.cfg)
        if tool_call['type'] == 'tool':
            tool = self.tools[tool_call['name']]
            result = tool.run(tool_call['arguments'])
            self.history.append({'role': 'tool', 'name': tool.name, 'content': result})
            # In real impl.: call LLM again with tool result to get final answer
            return result
        else:
            # Direct answer from model
            return tool_call.get('content', '')

# --- Section 5: Sub‑Agents ---------------------------------------------

def spawn_subagent(prompt: str, cfg: AgentConfig, tools: Dict[str, Tool]) -> str:
    """Fire off a sub‑agent in a separate process to keep state isolated."""
    import multiprocessing as mp

    def _worker(q: mp.Queue):
        agent = Agent(cfg, tools)
        q.put(agent.run(prompt))

    q: mp.Queue = mp.Queue()
    p = mp.Process(target=_worker, args=(q,))
    p.start()
    p.join()
    return q.get()

# --- Section 6: CLI -----------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description='Minimal Claude‑Code Python re‑implementation')
    parser.add_argument('task', nargs='*', help='Task to instruct the agent')
    parser.add_argument('--repo', default='.', help='Path to the code repository root')
    parser.add_argument('--context-bytes', type=int, default=30_000, help='Bytes of repo context to send')
    parser.add_argument('--shell', action='store_true', help='Open interactive REPL instead of one‑shot')
    args = parser.parse_args()

    repo_root = pathlib.Path(args.repo).resolve()
    context = build_context_snippets(discover_repo(repo_root), args.context_bytes)

    cfg = AgentConfig()
    tools = {SHELL_TOOL.name: SHELL_TOOL}
    agent = Agent(cfg, tools)

    if args.shell:
        print('Entering Claude‑Code mini REPL. Type "exit" to quit.')
        while True:
            try:
                user_in = input('>>> ')
            except EOFError:
                break
            if user_in.strip().lower() in {'exit', 'quit'}:
                break
            full_prompt = textwrap.dedent(f"""
            ## Repo Context (truncated)
            {context}

            ## User Task
            {user_in}
            """)
            print(agent.run(full_prompt))
    else:
        full_prompt = textwrap.dedent(f"""
        ## Repo Context (truncated)
        {context}

        ## User Task
        {' '.join(args.task)}
        """)
        print(agent.run(full_prompt))

if __name__ == '__main__':
    main()
