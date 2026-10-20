"""
Agent-Jail Human-in-the-Loop (HITL) Gate
Presents unskippable desktop modals (Zenity) or terminal prompts before elevated commands run.
"""

import os
import shutil
import subprocess

def prompt_human_approval(action_summary: str, details: str = "", timeout_sec: int = 25) -> bool:
    """
    Prompts human operator for permission to execute an elevated command.
    Uses Zenity on Wayland/X11 desktops, falling back to terminal input.
    Defaults to FAIL-CLOSED (denies if unanswered or timed out).
    """
    has_display = bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))
    has_zenity = shutil.which("zenity") is not None

    if has_display and has_zenity:
        try:
            msg = (
                f"🛡️ AGENT-JAIL ELEVATED ACTION GATE\n\n"
                f"An autonomous AI agent is requesting permission to execute:\n\n"
                f"▶ {action_summary}\n\n"
                f"Details:\n{details[:250]}\n\n"
                f"Do you authorize this action?"
            )
            res = subprocess.run([
                "zenity", "--question",
                "--title=Agent-Jail Security Authorization",
                "--text=" + msg,
                "--ok-label=Authorize",
                "--cancel-label=Deny",
                "--default-cancel",
                "--width=460",
                f"--timeout={timeout_sec}"
            ])
            return (res.returncode == 0)
        except Exception:
            pass

    # Terminal Fallback
    try:
        print("\n" + "=" * 60)
        print("🛡️  [AGENT-JAIL SECURITY GATE] Human Authorization Required")
        print("=" * 60)
        print(f"Action:  {action_summary}")
        if details:
            print(f"Details: {details[:200]}")
        ans = input("\nAuthorize execution? (y/N) [default: N]: ").strip().lower()
        return ans == "y"
    except Exception:
        return False
