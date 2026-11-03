"""Transport tests using a loopback HTTP fixture, never real LLM evidence."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from hullcirq.domain import DomainError
from hullcirq.provider import ChatCompletionsClient, validate_profile


FIXTURE_ORIGIN = "development_assistant"
FIXTURE_RTL = """module m1_producer(
    input clk, input rst,
    output reg signed [31:0] data_out,
    output reg data_out_valid, input data_out_ready
);
always @(posedge clk) begin
    if (rst) begin
        data_out <= 32'sd0;
        data_out_valid <= 1'b0;
    end else begin
        data_out_valid <= 1'b1;
        if (data_out_valid && data_out_ready)
            data_out <= data_out + 32'sd1;
    end
end
endmodule
"""


def profile(base_url="http://127.0.0.1:8080/v1", **overrides):
    value = {
        "id": "fixture-profile", "name": "Transport Fixture",
        "api_type": "chat_completions", "execution_location": "Local",
        "base_url": base_url, "model": "fixture-model", "credential_env": "",
        "timeout_seconds": 2, "context_window": 8192, "max_output_tokens": 256,
        "temperature": 0.2, "seed": 101,
        "model_revision": "unknown", "quantization": "unknown", "runtime_version": "unknown",
    }
    value.update(overrides)
    return value


class FakeChatServer:
    """Real sockets exercise fragmented SSE without a model or external API.

    Any RTL sent by this server is a development_assistant test fixture. Its
    receipt must never be counted as successful local-model RTL generation.
    """

    def __init__(self, payload: bytes = b"", *, content_type="text/event-stream", status=200,
                 fragments=None, delay=0.0, models=None):
        self.payload = payload
        self.content_type = content_type
        self.status = status
        self.fragments = fragments
        self.delay = delay
        self.models = models if models is not None else [{"id": "fixture-model"}]
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                owner.requests.append({"path": self.path, "method": "GET"})
                body = json.dumps({"object": "list", "data": owner.models}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                owner.requests.append({"path": self.path, "method": "POST", "body": body,
                                       "authorization": self.headers.get("Authorization")})
                self.send_response(owner.status)
                self.send_header("Content-Type", owner.content_type)
                self.send_header("Content-Length", str(len(owner.payload)))
                self.end_headers()
                try:
                    if owner.delay:
                        time.sleep(owner.delay)
                    pieces = owner.fragments or [owner.payload]
                    for piece in pieces:
                        self.wfile.write(piece)
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.server.server_address[1]}/v1"


def sse_events(text, *, finish_reason="stop", include_done=True, usage=True):
    messages = [
        {"id": "chatcmpl-fixture", "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}]},
        {"id": "chatcmpl-fixture", "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}]},
    ]
    if usage:
        messages.append({"id": "chatcmpl-fixture", "choices": [], "usage": {
            "prompt_tokens": 7, "completion_tokens": 13, "total_tokens": 20}})
    body = "".join("data: " + json.dumps(item, ensure_ascii=False) + "\n\n" for item in messages)
    if include_done:
        body += "data: [DONE]\n\n"
    return body.encode("utf-8")


class ProviderProfileTests(unittest.TestCase):
    def test_local_and_network_locations_are_explicit(self):
        local = validate_profile(profile())
        self.assertEqual(local["execution_location"], "Local")
        network = validate_profile(profile("https://provider.invalid/v1", execution_location="Network"))
        self.assertEqual(network["execution_location"], "Network")

    def test_local_profile_cannot_silently_send_to_a_network_host(self):
        with self.assertRaises(DomainError):
            validate_profile(profile("http://provider.invalid/v1"))

    def test_network_profile_requires_explicit_https(self):
        with self.assertRaises(DomainError):
            validate_profile(profile("http://provider.invalid/v1", execution_location="Network"))

    def test_url_credentials_query_and_fragment_are_rejected(self):
        for endpoint in ("http://user:password@127.0.0.1:8080/v1",
                         "http://127.0.0.1:8080/v1?api_key=fixture-secret",
                         "http://127.0.0.1:8080/v1#fixture-secret"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(DomainError):
                    validate_profile(profile(endpoint))

    def test_profile_rejects_credential_values_and_unsupported_api_fields(self):
        for field in ("api_key", "headers", "shell_command"):
            with self.subTest(field=field):
                with self.assertRaises(DomainError):
                    validate_profile(profile(**{field: "fixture-secret"}))
        with self.assertRaises(DomainError):
            validate_profile(profile(credential_env="secret-value-with-hyphens"))

    def test_invalid_limits_are_not_silently_ignored(self):
        for override in ({"timeout_seconds": 0}, {"context_window": 0},
                         {"max_output_tokens": 0}, {"temperature": float("nan")},
                         {"api_type": "unknown_api"}):
            with self.subTest(override=override):
                with self.assertRaises(DomainError):
                    validate_profile(profile(**override))

    def test_reasoning_effort_defaults_to_null_and_rejects_unimplemented_modes(self):
        self.assertIsNone(validate_profile(profile())["reasoning_effort"])
        self.assertIsNone(validate_profile(profile(reasoning_effort=None))["reasoning_effort"])
        self.assertEqual(validate_profile(profile(reasoning_effort="none"))["reasoning_effort"], "none")
        for value in ("low", "high", "auto", "", True, 1):
            with self.subTest(value=value):
                with self.assertRaises(DomainError):
                    validate_profile(profile(reasoning_effort=value))


class ProviderTransportTests(unittest.TestCase):
    messages = [{"role": "system", "content": "Transport fixture, not an LLM."},
                {"role": "user", "content": "Send the fixture text."}]

    def test_probe_lists_models_without_generating(self):
        with FakeChatServer() as server:
            result = ChatCompletionsClient(profile(server.base_url)).probe()
            self.assertIn("fixture-model", result["models"])
            self.assertEqual([item["method"] for item in server.requests], ["GET"])
            self.assertEqual(server.requests[0]["path"], "/v1/models")

    def test_null_reasoning_effort_is_omitted_from_provider_request(self):
        with FakeChatServer(sse_events("fixture")) as server:
            result = ChatCompletionsClient(profile(server.base_url, reasoning_effort=None)).generate(self.messages)
            self.assertEqual(result["execution_status"], "Completed")
            self.assertNotIn("reasoning_effort", server.requests[0]["body"])

    def test_explicit_none_reasoning_effort_is_sent_as_configured(self):
        with FakeChatServer(sse_events("fixture")) as server:
            result = ChatCompletionsClient(profile(server.base_url, reasoning_effort="none")).generate(self.messages)
            self.assertEqual(result["execution_status"], "Completed")
            self.assertEqual(server.requests[0]["body"]["reasoning_effort"], "none")

    def test_reasoning_aliases_are_preserved_separately_from_candidate_content(self):
        for reasoning_key in ("reasoning_content", "reasoning"):
            with self.subTest(reasoning_key=reasoning_key):
                chunks = [
                    {"choices": [{"delta": {reasoning_key: "Fixture reasoning only."}, "finish_reason": None}]},
                    {"choices": [{"delta": {"content": FIXTURE_RTL}, "finish_reason": None}]},
                    {"choices": [{"delta": {}, "finish_reason": "stop"}]},
                ]
                payload = ("".join("data: " + json.dumps(item) + "\n\n" for item in chunks) + "data: [DONE]\n\n").encode()
                with FakeChatServer(payload) as server:
                    result = ChatCompletionsClient(profile(server.base_url)).generate(self.messages)
                    self.assertEqual(result["execution_status"], "Completed")
                    self.assertEqual(result["raw_content"], FIXTURE_RTL)
                    self.assertEqual(result["raw_reasoning"], "Fixture reasoning only.")

    def test_conflicting_reasoning_aliases_are_not_silently_duplicated(self):
        delta = {"reasoning_content": "First reasoning stream.", "reasoning": "Second reasoning stream."}
        payload = ("data: " + json.dumps({"choices": [{"delta": delta, "finish_reason": None}]}) + "\n\n").encode()
        with FakeChatServer(payload) as server:
            result = ChatCompletionsClient(profile(server.base_url)).generate(self.messages)
            self.assertEqual(result["execution_status"], "Failed")
            self.assertTrue(result.get("error"))

    def test_fragmented_utf8_sse_retains_complete_answer_usage_and_explicit_finish(self):
        answer = "半導体 fixture only\n```verilog\n" + FIXTURE_RTL + "```"
        payload = sse_events(answer)
        fragments = [payload[index:index + 3] for index in range(0, len(payload), 3)]
        observed = []
        with FakeChatServer(payload, fragments=fragments) as server:
            result = ChatCompletionsClient(profile(server.base_url)).generate(self.messages, on_event=observed.append)
            self.assertEqual(result["execution_status"], "Completed", result)
            self.assertEqual(result["raw_content"], answer)
            self.assertEqual(result["finish_reason"], "stop")
            self.assertEqual(result["usage"]["total_tokens"], 20)
            self.assertTrue(any(item.get("content") for item in observed))
            self.assertEqual(len(server.requests), 1)
            request = server.requests[0]
            self.assertEqual(request["path"], "/v1/chat/completions")
            self.assertEqual(request["body"]["model"], "fixture-model")
            self.assertEqual(request["body"]["messages"], self.messages)
            self.assertTrue(request["body"]["stream"])

    def test_unknown_usage_is_not_reported_as_zero(self):
        with FakeChatServer(sse_events("fixture", usage=False)) as server:
            result = ChatCompletionsClient(profile(server.base_url)).generate(self.messages)
            self.assertEqual(result["execution_status"], "Completed")
            self.assertIsNone(result["usage"])

    def test_output_truncation_keeps_partial_text_but_never_completes(self):
        with FakeChatServer(sse_events("partial fixture", finish_reason="length")) as server:
            result = ChatCompletionsClient(profile(server.base_url)).generate(self.messages)
            self.assertEqual(result["execution_status"], "Failed")
            self.assertEqual(result["raw_content"], "partial fixture")
            self.assertEqual(result["finish_reason"], "length")
            self.assertTrue(result.get("error"))

    def test_eof_without_finish_reason_is_interrupted_not_completed(self):
        payload = ("data: " + json.dumps({"choices": [{"delta": {"content": "partial"},
                                                     "finish_reason": None}]}) + "\n\n").encode()
        with FakeChatServer(payload) as server:
            result = ChatCompletionsClient(profile(server.base_url)).generate(self.messages)
            self.assertEqual(result["execution_status"], "Failed")
            self.assertEqual(result["raw_content"], "partial")
            self.assertTrue(result.get("error"))

    def test_malformed_event_keeps_earlier_text_and_has_no_automatic_retry(self):
        prefix = ("data: " + json.dumps({"choices": [{"delta": {"content": "partial"},
                                                    "finish_reason": None}]}) + "\n\n").encode()
        with FakeChatServer(prefix + b"data: {broken-json}\n\n") as server:
            result = ChatCompletionsClient(profile(server.base_url)).generate(self.messages)
            self.assertEqual(result["execution_status"], "Failed")
            self.assertEqual(result["raw_content"], "partial")
            self.assertTrue(result.get("error"))
            self.assertEqual(len(server.requests), 1)

    def test_server_error_does_not_retry_or_fall_back_to_another_provider(self):
        payload = json.dumps({"error": {"message": "Transport fixture server failure."}}).encode()
        with FakeChatServer(payload, status=503, content_type="application/json") as server:
            result = ChatCompletionsClient(profile(server.base_url)).generate(self.messages)
            self.assertEqual(result["execution_status"], "Failed")
            self.assertTrue(result.get("error"))
            self.assertEqual(len(server.requests), 1)

    def test_timeout_is_a_failed_attempt_and_retains_the_request_boundary(self):
        with FakeChatServer(sse_events("delayed"), delay=0.4) as server:
            result = ChatCompletionsClient(profile(server.base_url, timeout_seconds=0.1)).generate(self.messages)
            self.assertEqual(result["execution_status"], "Failed")
            self.assertTrue(result.get("error"))
            self.assertEqual(len(server.requests), 1)

    def test_cancel_before_connection_does_not_send_a_request(self):
        cancel = threading.Event()
        cancel.set()
        with FakeChatServer(sse_events("unused")) as server:
            result = ChatCompletionsClient(profile(server.base_url)).generate(self.messages, cancel_event=cancel)
            self.assertEqual(result["execution_status"], "Cancelled")
            self.assertEqual(server.requests, [])

    def test_cancel_after_partial_event_keeps_text_without_adopting_it(self):
        cancel = threading.Event()

        def on_event(event):
            if event.get("content"):
                cancel.set()

        with FakeChatServer(sse_events("partial before cancel")) as server:
            result = ChatCompletionsClient(profile(server.base_url)).generate(
                self.messages, cancel_event=cancel, on_event=on_event)
            self.assertEqual(result["execution_status"], "Cancelled")
            self.assertEqual(result["raw_content"], "partial before cancel")

    def test_backend_environment_credential_is_not_returned_in_result_events(self):
        fake_key = "fixture-only-bearer-secret"
        with FakeChatServer(sse_events("fixture")) as server, patch.dict(os.environ, {"HULLCIRQ_TEST_KEY": fake_key}):
            connection = profile(server.base_url, credential_env="HULLCIRQ_TEST_KEY")
            normalized = validate_profile(connection)
            result = ChatCompletionsClient(normalized).generate(self.messages)
            self.assertEqual(server.requests[0]["authorization"], "Bearer " + fake_key)
            self.assertNotIn(fake_key, json.dumps(normalized))
            self.assertNotIn(fake_key, json.dumps(result))

    def test_credential_echo_split_between_sse_deltas_is_redacted_and_rejected(self):
        fake_key = "fixture-only-bearer-secret"
        chunks = [
            {"choices": [{"delta": {"content": fake_key[:12]}, "finish_reason": None}]},
            {"choices": [{"delta": {"content": fake_key[12:]}, "finish_reason": None}]},
            {"choices": [{"delta": {}, "finish_reason": "stop"}]},
        ]
        payload = ("".join("data: " + json.dumps(item) + "\n\n" for item in chunks) + "data: [DONE]\n\n").encode()
        observed = []
        with FakeChatServer(payload) as server, patch.dict(os.environ, {"HULLCIRQ_TEST_KEY": fake_key}):
            result = ChatCompletionsClient(profile(server.base_url, credential_env="HULLCIRQ_TEST_KEY")).generate(
                self.messages, on_event=observed.append)
            self.assertEqual(result["execution_status"], "Failed")
            self.assertEqual(result["error"]["code"], "credential_echo")
            self.assertNotIn(fake_key, json.dumps(result))
            self.assertNotIn(fake_key, "".join(item.get("content", "") for item in observed))


if __name__ == "__main__":
    unittest.main()
