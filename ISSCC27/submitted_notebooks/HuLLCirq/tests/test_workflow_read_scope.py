"""Standalone workflow GETs share nested views once per response, not forever."""
from pathlib import Path
from types import SimpleNamespace
import sys
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hullcirq.envelope_cache import memoized_envelope
from hullcirq.server import HuLLCirqServer, RequestHandler


class ReadView:
    def __init__(self):
        self.value, self.calls = 0, 0

    @memoized_envelope
    def envelope(self):
        self.calls += 1
        return {"value": self.value}


class WorkflowReadScopeTests(unittest.TestCase):
    def test_second_gui_cannot_bind_an_already_listening_port(self):
        # Bind only; no requests, project, model or EDA worker are created.
        first = HuLLCirqServer(("127.0.0.1", 0), RequestHandler)
        try:
            with self.assertRaises(OSError):
                duplicate = HuLLCirqServer(first.server_address, RequestHandler)
                duplicate.server_close()
        finally:
            first.server_close()

    def test_standalone_get_reuses_nested_views_but_next_request_sees_change(self):
        manager = ReadView()
        responses = []

        def respond():
            # One node table and nineteen retained batch source checks.
            values = [manager.envelope() for _ in range(20)]
            responses.append([value["value"] for value in values])

        handler = SimpleNamespace(path='/api/workflow', server=SimpleNamespace(context_lock=threading.RLock()), _do_GET=respond)
        RequestHandler.do_GET(handler)
        self.assertEqual(manager.calls, 1)
        manager.value = 7
        RequestHandler.do_GET(handler)
        self.assertEqual(manager.calls, 2)
        self.assertEqual(responses, [[0] * 20, [7] * 20])
        # The read cache does not escape into an action or worker read.
        manager.value = 9
        self.assertEqual(manager.envelope(), {"value": 9})
        self.assertEqual(manager.calls, 3)

    def test_failed_get_discards_snapshot_and_releases_context_lock(self):
        manager = ReadView()
        lock = threading.RLock()

        def failed_response():
            manager.envelope()
            raise RuntimeError("isolated response failure")

        handler = SimpleNamespace(path='/api/workflow', server=SimpleNamespace(context_lock=lock), _do_GET=failed_response)
        with self.assertRaises(RuntimeError):
            RequestHandler.do_GET(handler)
        manager.value = 4
        self.assertEqual(manager.envelope(), {"value": 4})
        self.assertEqual(manager.calls, 2)
        self.assertTrue(lock.acquire(blocking=False))
        lock.release()


if __name__ == "__main__":
    unittest.main()
