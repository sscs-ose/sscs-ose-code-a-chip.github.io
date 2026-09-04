
import time

class Playbook:
    def __init__(self, task_id="general", hard_guard_chars=300_000):
        self.task_id = task_id
        self.logs = []
        self.hard_guard_chars = hard_guard_chars

    def _hard_guard(self, s, label="text"):
        if s is None:
            return ""
        s = str(s)
        if self.hard_guard_chars is None:
            return s
        if len(s) <= self.hard_guard_chars:
            return s
        keep_head = int(self.hard_guard_chars * 0.4)
        keep_tail = self.hard_guard_chars - keep_head
        return (
            s[:keep_head]
            + f"\n\n# --- TRUNCATED ({label}) ---\n\n"
            + s[-keep_tail:]
        )

    def add_log(self, code, error_msg, iteration=0):
        """Record a failure"""
        entry = {
            "iteration": iteration,
            "code": self._hard_guard(code, label="code"),
            "error": self._hard_guard(error_msg, label="error"),
            "timestamp": time.time()
        }
        self.logs.append(entry)
        print(f"[Playbook] Recorded failure for Task {self.task_id}, Iter {iteration}")

    def get_reflexion_prompt(self):
        if not self.logs:
            return ""

        last_entry = self.logs[-1]

        return (
            f"\n\n[REFLEXION ON PREVIOUS FAILURE (Iter {last_entry['iteration']})]\n"
            f"You previously wrote the following code, but it failed:\n"
            "```python\n"
            f"{last_entry['code']}\n"
            "```\n\n"
            "Here is the error message:\n"
            "```\n"
            f"{last_entry['error']}\n"
            "```\n"
        )
