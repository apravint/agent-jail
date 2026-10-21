<div align="center">

# 🛡️ agent-jail

**Rootless Bubblewrap Sandbox & Human-in-the-Loop Security Firewall for AI Agents**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-cyan.svg)](https://www.python.org/)
[![CI](https://github.com/apravint/agent-jail/actions/workflows/ci.yml/badge.svg)](https://github.com/apravint/agent-jail/actions)
[![Zero Docker](https://img.shields.io/badge/Docker-Not%20Required-success.svg)](#why-agent-jail)

<p align="center">
  <b>Safely execute AI agent code-as-action without Docker, without root privileges, and without fear of system wipes or credential theft.</b>
</p>

</div>

---

## ⚡ The Problem

Autonomous AI coding agents (Claude Computer Use, smolagents, LangChain, AutoGen, OpenDevin) execute arbitrary Python code and bash commands directly on host machines. 

Without containment, a confused or hallucinating agent can:
* 💥 Wipe your root directory or `$HOME` (`rm -rf /` or recursive deletions)
* 🔑 Read or exfiltrate your private SSH keys (`~/.ssh`), GPG keys, AWS/Kube credentials
* ♾️ Hang your active desktop session with runaway while-loops or fork bombs
* 💣 Overwrite raw storage blocks or modify systemd units

**Docker is too heavy** (requires a background root daemon, takes seconds to spin up, and consumes gigabytes of storage). 

**`agent-jail` solves this in <5 milliseconds using Linux-native Bubblewrap (`bwrap`).**

---

## 🏛️ Architecture

```
                  ┌────────────────────────────────────────┐
                  │    Autonomous AI Agent Action Plan     │
                  │   (smolagents / LangChain / Claude)    │
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   Pre-Flight Firewall     │
                        │ (7-Factor Risk Analysis)  │
                        └─────────────┬─────────────┘
                                      │
                 ┌────────────────────┴────────────────────┐
                 │                                         │
        [CRITICAL RISK]                            [ELEVATED RISK]
      (rm -rf, dd, mkfs)                       (systemctl, sudo, force)
                 │                                         │
                 ▼                                         ▼
      🛑 [IMMEDIATE DENY]                         🔔 [HITL MODAL]
     Exit with Security Block                   Unskippable Desktop
                                                  Zenity / CLI Gate
                                                           │
                                                           ▼ (If Authorized)
                                          ┌────────────────────────────────┐
                                          │     BUBBLEWRAP (bwrap) JAIL    │
                                          ├────────────────────────────────┤
                                          │ • Read-Only System Root (/)    │
                                          │ • Read-Only Credentials (~/.ssh│
                                          │ • Ephemeral In-Memory /tmp     │
                                          │ • Strict 15s Process Timeout   │
                                          │ • Optional Network Isolation   │
                                          └────────────────┬───────────────┘
                                                           │
                                                           ▼
                                            Safe & Contained Execution
```

---

## 🚀 Quickstart

### 1. Installation

Install via pip:
```bash
pip install agent-jail
```

Make sure `bubblewrap` is installed on your Linux distribution:
```bash
# Ubuntu / Debian
sudo apt install bubblewrap zenity

# Arch Linux
sudo pacman -S bubblewrap zenity

# Fedora
sudo dnf install bubblewrap zenity
```

### 2. Command-Line Usage

**Safely run Python code in the jail:**
```bash
agent-jail run -c "import os; print('Running as PID:', os.getpid())"
```

**Safely run Bash shell commands:**
```bash
agent-jail run --bash "ls -la /tmp"
```

**Attempting a destructive command is blocked immediately by the firewall:**
```bash
agent-jail run -c "import os; os.system('rm -rf /')"
# 🛑 [AGENT-JAIL DENIED] Action blocked by security firewall:
#    ✗ CRITICAL: Destructive filesystem wipe of root or home directory
```

**Attempting to write to root or sensitive folders fails inside the jail:**
```bash
agent-jail run -c "open('/test.txt', 'w').write('fail')"
# OSError: [Errno 30] Read-only file system: '/test.txt'
```

---

## 🐍 Python SDK Integration

### 1-Line Drop-in Runner
```python
from agent_jail import run_sandboxed

result = run_sandboxed(
    "import os; print('Files in workspace:', os.listdir('.'))",
    language="python",
    timeout=10,
    allow_network=True
)

if result.success:
    print("Output:", result.stdout)
else:
    print("Error:", result.stderr)
```

### Integration with Hugging Face `smolagents`
```python
from smolagents import tool
from agent_jail import Sandbox

sandbox = Sandbox(timeout=15)

@tool
def execute_python_code_action(code: str) -> str:
    """Safely executes agent Python code inside a Bubblewrap container."""
    result = sandbox.run_python(code)
    if result.timed_out:
        return "Error: Code execution timed out (limit exceeded)."
    if not result.success:
        return f"Execution Error:\n{result.stderr}"
    return result.stdout
```

### Integration with LangChain / Custom Agent Tool
```python
from agent_jail import evaluate_risk, Sandbox, RiskLevel

def agent_bash_tool(command: str) -> str:
    # 1. Pre-flight check
    risk, reasons = evaluate_risk(command)
    if risk == RiskLevel.DENY:
        return f"Refused: Command violates security policy ({reasons[0]})"

    # 2. Execute in rootless jail
    jail = Sandbox(timeout=15, allow_network=False)
    res = jail.run_bash(command)
    return res.stdout if res.success else res.stderr
```

---

## 📎 Paperclip Integration (Autonomous Company Sandboxing)

In zero-human organizations powered by [Paperclip](https://github.com/paperclipai/paperclip), autonomous agents execute tasks, write code, and run bash commands on host machines. Wrap Paperclip agent runner executions in `agent-jail` to guarantee company tasks cannot escape their assigned workspace or tamper with host system files:

```bash
# Wrap Paperclip task runner commands in agent-jail
agent-jail --workspace /path/to/paperclip/company/workspace -- "npm test && npm run build"
```

In your Paperclip agent configuration or custom execution plugin:
```json
{
  "executionRunner": "agent-jail",
  "runnerArgs": ["--workspace", "${issue.workspaceDir}", "--timeout", "60", "--"]
}
```

---

## 🛡️ Security Guarantees

| Attack Vector | Protection Mechanism |
| :--- | :--- |
| **Root Filesystem Tampering** | `/` mounted strictly read-only (`--ro-bind / /`) |
| **SSH / Cloud Key Theft** | `~/.ssh`, `~/.gnupg`, `~/.aws`, `~/.kube` forced read-only |
| **Infinite Loops / Freezes** | Automatic process termination on timeout (default 15s) |
| **Storage Device Corruption** | Block device access blocked; raw redirection blocked |
| **Privilege Escalation** | Zero root privileges required; rootless unprivileged user namespace |
| **Accidental Destructive Deletion** | Critical deny regex firewall + Human-in-the-Loop desktop modal |

---

## 📊 Comparison

| Feature | `agent-jail` | Docker | Firejail |
| :--- | :---: | :---: | :---: |
| **Root Daemon Required** | ❌ **No** | ⚠️ Yes (`dockerd`) | ❌ No |
| **Startup Overhead** | **<5 ms** | ~800–2500 ms | ~15 ms |
| **Disk Footprint** | **<1 MB** | Multiple GBs | ~20 MB |
| **Human-in-the-Loop GUI** | ✅ **Built-in (Zenity)** | ❌ No | ❌ No |
| **Agent Pre-Flight Firewall** | ✅ **Built-in** | ❌ No | ❌ No |
| **Credential Auto-Protection** | ✅ **Automated** | ⚠️ Manual volume setup | ⚠️ Profile config |

---

## 🧪 Running Tests

```bash
git clone https://github.com/apravint/agent-jail.git
cd agent-jail
pip install -e .
python -m unittest discover -s tests
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details. Created by [Ayyappa Pravin (@apravint)](https://github.com/apravint).
