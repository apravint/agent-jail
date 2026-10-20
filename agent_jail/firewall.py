"""
Agent-Jail Pre-Flight Security Firewall
Evaluates security risks of agent-generated commands or code blocks before execution.
"""

import re
from enum import Enum
from typing import Tuple, List

class RiskLevel(str, Enum):
    ALLOW = "ALLOW"
    PROMPT = "PROMPT"
    DENY = "DENY"

# Patterns that MUST be immediately blocked (never run)
CRITICAL_DENY_PATTERNS = [
    (r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*)\s+(/|/\*|~|~/\*|\$HOME|\$HOME/\*)", "Destructive filesystem wipe of root or home directory"),
    (r"mkfs\.[a-z0-9]+", "Raw filesystem format attempt"),
    (r"dd\s+if=.*of=/dev/(sd[a-z]|nvme[0-9]n[0-9]|vd[a-z])", "Direct block device write / raw partition overwrite"),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "Fork bomb denial-of-service vector"),
    (r"chmod\s+(-R\s+)?777\s+(/|/etc|/boot|/usr|/var)", "Global world-writable permissions escalation on system roots"),
    (r">\s*/dev/(sd[a-z]|nvme[0-9]|null)\s*$", "Direct redirection to storage devices"),
    (r"chown\s+(-R\s+)?.*(/|/etc|/boot|/usr)", "System ownership hijacking attempt"),
]

# Patterns that require explicit Human-in-the-Loop authorization
PROMPT_PATTERNS = [
    (r"systemctl\s+(stop|disable|mask|restart|poweroff|reboot)", "Modifies or disables persistent system services / state"),
    (r"iptables\s+(-F|-X)", "Flushes global network firewall rules"),
    (r"ufw\s+(disable|reset)", "Disables host firewall"),
    (r"git\s+push\s+.*--force", "Force push that may destroy remote git commit history"),
    (r"git\s+reset\s+--hard", "Unrecoverable local git working tree wipe"),
    (r"sudo\s+", "Privilege escalation (sudo) invoked"),
    (r"rm\s+-[a-zA-Z]*r[a-zA-Z]*\s+", "Recursive directory deletion"),
    (r"userdel|groupdel", "User or group account deletion"),
]

def evaluate_risk(content: str) -> Tuple[RiskLevel, List[str]]:
    """
    Evaluates the safety of a code string or shell command.
    Returns:
        (RiskLevel, reasons_list)
    """
    flags = []

    # 1. Check Hard Deny Rules
    for pattern, reason in CRITICAL_DENY_PATTERNS:
        if re.search(pattern, content, re.MULTILINE):
            flags.append(f"CRITICAL: {reason} (matched '{pattern}')")
            return RiskLevel.DENY, flags

    # 2. Check Elevated Prompt Rules
    for pattern, reason in PROMPT_PATTERNS:
        if re.search(pattern, content, re.MULTILINE):
            flags.append(f"ELEVATED: {reason} (matched '{pattern}')")

    if flags:
        return RiskLevel.PROMPT, flags

    return RiskLevel.ALLOW, ["Passes baseline security heuristics"]
