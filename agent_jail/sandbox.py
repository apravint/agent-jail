"""
Agent-Jail Bubblewrap (bwrap) Sandbox Runtime
Executes arbitrary agent Python code and shell commands inside an isolated rootless container.
"""

import os
import sys
import shutil
import tempfile
import subprocess
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class ExecutionResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    quarantined: bool = False
    blocked_by_firewall: bool = False

class Sandbox:
    def __init__(
        self,
        timeout: int = 15,
        allow_network: bool = True,
        extra_ro_paths: Optional[List[str]] = None,
        workspace_dir: Optional[str] = None
    ):
        self.timeout = timeout
        self.allow_network = allow_network
        self.extra_ro_paths = extra_ro_paths or []
        self.workspace_dir = workspace_dir or os.getcwd()
        self.bwrap_bin = shutil.which("bwrap")

    def run_python(self, code: str) -> ExecutionResult:
        """
        Executes a Python code string inside the sandboxed container.
        """
        home = os.path.expanduser("~")
        wrapper_script = f"""
import sys
import os
import json

try:
{chr(10).join('    ' + line for line in code.splitlines())}
except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"""
        return self._execute_command(["python3", "-c", wrapper_script])

    def run_bash(self, script: str) -> ExecutionResult:
        """
        Executes a Bash shell script inside the sandboxed container.
        """
        return self._execute_command(["bash", "-c", script])

    def _execute_command(self, cmd_args: List[str]) -> ExecutionResult:
        home = os.path.expanduser("~")

        if not self.bwrap_bin:
            # Fallback if bwrap is not installed on host
            try:
                res = subprocess.run(
                    cmd_args,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=self.workspace_dir
                )
                return ExecutionResult(
                    success=(res.returncode == 0),
                    exit_code=res.returncode,
                    stdout=res.stdout,
                    stderr=res.stderr,
                    quarantined=False
                )
            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    success=False,
                    exit_code=124,
                    stdout="",
                    stderr=f"Execution timed out ({self.timeout}s limit exceeded).",
                    timed_out=True
                )

        # Bubblewrap Argument Construction
        bwrap_cmd = [
            self.bwrap_bin,
            "--ro-bind", "/", "/",               # System root is strictly READ-ONLY
            "--dev", "/dev",                     # Provide required device nodes
            "--proc", "/proc",                   # Mount isolated process tree
            "--tmpfs", "/tmp",                   # Ephemeral isolated temporary filesystem
            "--bind", self.workspace_dir, self.workspace_dir,  # Working directory read/write
        ]

        if not self.allow_network:
            bwrap_cmd.append("--unshare-net")   # Disallow outbound network access

        # Credential & Sensitive Store Protection (Forced Read-Only)
        sensitive_stores = [
            os.path.join(home, ".ssh"),
            os.path.join(home, ".gnupg"),
            os.path.join(home, ".aws"),
            os.path.join(home, ".kube"),
            os.path.join(home, ".config", "environment.d")
        ]
        sensitive_stores.extend(self.extra_ro_paths)

        for path in sensitive_stores:
            if os.path.exists(path):
                bwrap_cmd.extend(["--ro-bind-try", path, path])

        bwrap_cmd.extend(cmd_args)

        try:
            res = subprocess.run(
                bwrap_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.workspace_dir
            )
            return ExecutionResult(
                success=(res.returncode == 0),
                exit_code=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
                timed_out=False,
                quarantined=True
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                exit_code=124,
                stdout="",
                stderr=f"Execution timed out ({self.timeout}s limit exceeded). Process killed.",
                timed_out=True,
                quarantined=True
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                exit_code=1,
                stdout="",
                stderr=f"Sandbox execution error: {e}",
                quarantined=True
            )
