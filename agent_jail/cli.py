"""
Agent-Jail Command Line Interface
"""

import sys
import argparse
from .firewall import evaluate_risk, RiskLevel
from .sandbox import Sandbox
from .hitl import prompt_human_approval

def main():
    parser = argparse.ArgumentParser(
        prog="agent-jail",
        description="Rootless Bubblewrap Sandbox & Human-in-the-Loop Security Firewall for AI Agents"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # Run
    p_run = subparsers.add_parser("run", help="Run Python code or shell command inside sandbox")
    p_run.add_argument("code_or_command", help="The code or command string to run")
    p_run.add_argument("--bash", action="store_true", help="Execute as Bash command instead of Python")
    p_run.add_argument("--timeout", type=int, default=15, help="Execution timeout in seconds (default: 15)")
    p_run.add_argument("--no-network", action="store_true", help="Disallow outbound network access")
    p_run.add_argument("--no-hitl", action="store_true", help="Skip human-in-the-loop modal prompt")

    # Check
    p_check = subparsers.add_parser("check", help="Evaluate security risk of a command without running it")
    p_check.add_argument("code_or_command", help="The code or command string to evaluate")

    # Audit
    subparsers.add_parser("audit", help="Check host bubblewrap and desktop dialog readiness")

    args = parser.parse_args()

    if args.subcommand == "check":
        risk, reasons = evaluate_risk(args.code_or_command)
        print(f"Risk Level: [{risk.value}]")
        for r in reasons:
            print(f"  • {r}")
        sys.exit(0 if risk == RiskLevel.ALLOW else (1 if risk == RiskLevel.DENY else 2))

    elif args.subcommand == "audit":
        import shutil
        bwrap = shutil.which("bwrap")
        zenity = shutil.which("zenity")
        print("=== Agent-Jail Environment Audit ===")
        print(f"  • Bubblewrap (bwrap):  {'✓ Available (' + bwrap + ')' if bwrap else '✗ Missing (apt install bubblewrap)'}")
        print(f"  • Zenity GUI Dialog:  {'✓ Available (' + zenity + ')' if zenity else '✗ Missing (apt install zenity)'}")
        sys.exit(0 if bwrap else 1)

    elif args.subcommand == "run":
        # 1. Firewall check
        risk, reasons = evaluate_risk(args.code_or_command)
        if risk == RiskLevel.DENY:
            print("🛑 [AGENT-JAIL DENIED] Action blocked by security firewall:")
            for r in reasons:
                print(f"   ✗ {r}")
            sys.exit(1)

        if risk == RiskLevel.PROMPT and not args.no_hitl:
            approved = prompt_human_approval(
                action_summary=f"Elevated {'Bash' if args.bash else 'Python'} Action",
                details=args.code_or_command
            )
            if not approved:
                print("🚫 Action cancelled by user.")
                sys.exit(2)
            print("✓ Action authorized by user.")

        # 2. Run in sandbox
        box = Sandbox(timeout=args.timeout, allow_network=not args.no_network)
        if args.bash:
            res = box.run_bash(args.code_or_command)
        else:
            res = box.run_python(args.code_or_command)

        if res.stdout:
            print(res.stdout)
        if res.stderr:
            print(res.stderr, file=sys.stderr)

        sys.exit(res.exit_code)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
