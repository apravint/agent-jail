"""
Agent-Jail
Rootless Bubblewrap Sandbox & Human-in-the-Loop Security Firewall for AI Agents.
"""

from .firewall import evaluate_risk, RiskLevel
from .hitl import prompt_human_approval
from .sandbox import Sandbox, ExecutionResult

__version__ = "0.1.0"
__all__ = [
    "Sandbox",
    "ExecutionResult",
    "evaluate_risk",
    "RiskLevel",
    "prompt_human_approval",
    "run_sandboxed"
]

def run_sandboxed(
    code_or_command: str,
    language: str = "python",
    timeout: int = 15,
    allow_network: bool = True,
    workspace_dir: str = None,
    enforce_hitl: bool = True
) -> ExecutionResult:
    """
    Convenience one-liner function to evaluate and safely execute agent actions.
    """
    # 1. Pre-flight Risk Evaluation
    risk, reasons = evaluate_risk(code_or_command)
    if risk == RiskLevel.DENY:
        return ExecutionResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="Blocked by Agent-Jail Safety Firewall:\n" + "\n".join(f"  • {r}" for r in reasons),
            blocked_by_firewall=True
        )

    # 2. Human-in-the-loop authorization if elevated
    if risk == RiskLevel.PROMPT and enforce_hitl:
        approved = prompt_human_approval(
            action_summary="Elevated Agent Action",
            details=code_or_command
        )
        if not approved:
            return ExecutionResult(
                success=False,
                exit_code=2,
                stdout="",
                stderr="Action cancelled by human operator.",
                blocked_by_firewall=True
            )

    # 3. Sandbox execution
    box = Sandbox(timeout=timeout, allow_network=allow_network, workspace_dir=workspace_dir)
    if language.lower() in ("bash", "sh", "shell"):
        return box.run_bash(code_or_command)
    return box.run_python(code_or_command)
