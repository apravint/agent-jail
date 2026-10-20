import unittest
from agent_jail.firewall import evaluate_risk, RiskLevel

class TestFirewall(unittest.TestCase):
    def test_safe_commands_allowed(self):
        safe_commands = [
            "ls -la",
            "git status",
            "python3 -c 'print(1+1)'",
            "cat README.md",
            "mkdir src"
        ]
        for cmd in safe_commands:
            risk, _ = evaluate_risk(cmd)
            self.assertEqual(risk, RiskLevel.ALLOW, f"Expected {cmd} to be ALLOW")

    def test_destructive_commands_denied(self):
        dangerous = [
            "rm -rf /",
            "rm -rf /*",
            "rm -rf $HOME/*",
            "mkfs.ext4 /dev/sda1",
            "dd if=/dev/zero of=/dev/nvme0n1",
            ":(){ :|:& };:",
            "chmod -R 777 /etc"
        ]
        for cmd in dangerous:
            risk, _ = evaluate_risk(cmd)
            self.assertEqual(risk, RiskLevel.DENY, f"Expected {cmd} to be DENY")

    def test_elevated_commands_require_prompt(self):
        elevated = [
            "systemctl stop nginx",
            "git push origin main --force",
            "git reset --hard HEAD~1",
            "sudo apt update",
            "rm -r old_directory/"
        ]
        for cmd in elevated:
            risk, _ = evaluate_risk(cmd)
            self.assertEqual(risk, RiskLevel.PROMPT, f"Expected {cmd} to be PROMPT")

if __name__ == "__main__":
    unittest.main()
