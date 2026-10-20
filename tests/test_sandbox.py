import unittest
import os
from agent_jail.sandbox import Sandbox

class TestSandbox(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox(timeout=5)

    def test_basic_python_execution(self):
        res = self.box.run_python("print('HELLO_JAIL')")
        self.assertTrue(res.success)
        self.assertEqual(res.exit_code, 0)
        self.assertIn("HELLO_JAIL", res.stdout)

    def test_root_filesystem_read_only(self):
        # Trying to create a file in / should fail
        code = """
import os
try:
    with open('/agent_jail_test.txt', 'w') as f:
        f.write('fail')
    print('FAIL_ALLOWED')
except Exception as e:
    print('SUCCESS_BLOCKED:', e)
"""
        res = self.box.run_python(code)
        self.assertTrue(res.success)
        self.assertIn("SUCCESS_BLOCKED:", res.stdout)
        self.assertNotIn("FAIL_ALLOWED", res.stdout)

    def test_timeout_termination(self):
        # Infinite loop must terminate at 2s limit
        quick_box = Sandbox(timeout=2)
        res = quick_box.run_python("import time; time.sleep(10)")
        self.assertFalse(res.success)
        self.assertTrue(res.timed_out)
        self.assertEqual(res.exit_code, 124)

    def test_basic_bash_execution(self):
        res = self.box.run_bash("echo 'BASH_JAIL_OK'")
        self.assertTrue(res.success)
        self.assertIn("BASH_JAIL_OK", res.stdout)

if __name__ == "__main__":
    unittest.main()
