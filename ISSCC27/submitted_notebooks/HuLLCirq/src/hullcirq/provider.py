"""Bounded Chat Completions transport for explicit local/network profiles.

No model download, automatic retry/fallback, redirects, or tool execution.
"""

from __future__ import annotations

import copy
import http.client
import ipaddress
import json
import math
import os
import re
import socket
import threading
import time
from urllib.parse import urlsplit, urlunsplit

from .domain import DomainError
from .store import strict_loads

PROFILE_FIELDS = frozenset(("id", "name", "api_type", "execution_location", "base_url", "model",
                            "credential_env", "timeout_seconds", "context_window", "max_output_tokens",
                            "temperature", "seed", "reasoning_effort", "model_revision", "quantization", "runtime_version"))
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_LINE_BYTES = 256 * 1024
MAX_CONTENT_BYTES = 512 * 1024


def estimate_message_input(messages: list) -> int:
    """Conservative byte budget for the exact transport message serialization."""
    return len(json.dumps(messages, ensure_ascii=False, allow_nan=False).encode("utf-8"))


def validate_profile(profile: dict) -> dict:
    if type(profile) is not dict or set(profile) - PROFILE_FIELDS:
        raise DomainError("invalid_profile", "Provider profile has unknown or restricted fields.")
    defaults = {"api_type": "chat_completions", "credential_env": "", "timeout_seconds": 180,
                "context_window": 8192, "max_output_tokens": 2048, "temperature": 0.2, "seed": 101,
                "reasoning_effort": None,
                "model_revision": "unknown", "quantization": "unknown", "runtime_version": "unknown"}
    value = defaults | copy.deepcopy(profile)
    for field in ("id", "name", "api_type", "execution_location", "base_url", "model", "credential_env",
                  "model_revision", "quantization", "runtime_version"):
        if type(value.get(field)) is not str or field != "credential_env" and not value[field].strip():
            raise DomainError("invalid_profile", f"Provider {field} must be text.")
        if len(value[field]) > 2048 or any(ord(char) < 32 for char in value[field]):
            raise DomainError("invalid_profile", f"Provider {field} contains invalid text.")
    if value["api_type"] != "chat_completions" or value["execution_location"] not in ("Local", "Network"):
        raise DomainError("unsupported_profile", "Use chat_completions with an explicit Local or Network location.")
    if not (value["reasoning_effort"] is None or type(value["reasoning_effort"]) is str and value["reasoning_effort"] == "none"):
        raise DomainError("unsupported_profile", "reasoning_effort supports null or explicit 'none' only; provider support must be verified.")
    if value["credential_env"] and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value["credential_env"]):
        raise DomainError("invalid_credential_reference", "credential_env must be an environment-variable name, not a key value.")
    try:
        parsed = urlsplit(value["base_url"])
        port = parsed.port
    except ValueError as error:
        raise DomainError("invalid_endpoint", "Provider endpoint is malformed.") from error
    if (parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment or "\\" in value["base_url"]):
        raise DomainError("invalid_endpoint", "Endpoint must be HTTP(S), without credentials, query, or fragment.")
    if port is not None and not 1 <= port <= 65535:
        raise DomainError("invalid_endpoint", "Endpoint port must be from 1 to 65535.")
    if value["execution_location"] == "Local":
        try:
            loopback = ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:
            loopback = parsed.hostname.lower() == "localhost"
        if not loopback or "%" in parsed.hostname:
            raise DomainError("local_endpoint_required", "Local profiles require localhost or a literal loopback address.")
    elif parsed.scheme != "https":
        raise DomainError("network_tls_required", "Network profiles require explicit HTTPS.")
    if parsed.path and (not parsed.path.startswith("/") or any(segment in (".", "..") for segment in parsed.path.split("/"))):
        raise DomainError("invalid_endpoint", "Endpoint base path must not contain traversal segments.")
    value["base_url"] = urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))
    for field, minimum, maximum in (("context_window", 64, 1048576), ("max_output_tokens", 1, 65536), ("seed", 0, 4294967295)):
        if type(value[field]) is not int or not minimum <= value[field] <= maximum:
            raise DomainError("invalid_profile", f"Provider {field} must be an integer from {minimum} to {maximum}.")
    for field, minimum, maximum in (("timeout_seconds", 0.05, 3600), ("temperature", 0, 2)):
        try:
            valid = type(value[field]) in (int, float) and math.isfinite(value[field]) and minimum <= value[field] <= maximum
        except OverflowError:
            valid = False
        if not valid:
            raise DomainError("invalid_profile", f"Provider {field} must be a finite number from {minimum} to {maximum}.")
    if value["max_output_tokens"] >= value["context_window"]:
        raise DomainError("invalid_profile", "Output token limit must leave room for input context.")
    return value


class _TransportFailure(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)


class _EventCallbackFailure(_TransportFailure):
    """Local event handling has a separate origin from provider transport."""
    def __init__(self, error: Exception):
        code = "storage_error" if isinstance(error, OSError) else "event_handler_error"
        super().__init__(code, "Local stream event handling failed; provider transport failure was not established and no request was repeated.")


class ChatCompletionsClient:
    def __init__(self, profile: dict):
        self.profile = validate_profile(profile)

    def _credentials(self) -> str:
        name = self.profile["credential_env"]
        secret = os.environ.get(name, "") if name else ""
        if name and not secret:
            raise _TransportFailure("credentials_missing", "Configured backend credential is unavailable.")
        if any(ord(character) < 32 for character in secret):
            raise _TransportFailure("invalid_credentials", "Configured backend credential contains invalid characters.")
        if len(secret) > 8192:
            raise _TransportFailure("invalid_credentials", "Configured backend credential exceeds the supported size.")
        return secret

    def _connection(self):
        parsed = urlsplit(self.profile["base_url"])
        host = "127.0.0.1" if parsed.hostname.lower() == "localhost" else parsed.hostname
        cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        return cls(host, parsed.port, timeout=self.profile["timeout_seconds"]), parsed.path.rstrip("/")

    @staticmethod
    def _abort(connection, response_holder: list) -> None:
        sockets = [connection.sock]
        if response_holder:
            raw = getattr(getattr(response_holder[0], "fp", None), "raw", None)
            sockets.append(getattr(raw, "_sock", None))
        for stream_socket in sockets:
            if stream_socket is not None:
                try:
                    stream_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        connection.close()

    def _watch(self, connection, response_holder, cancel_event, finished, timed_out):
        deadline = time.monotonic() + self.profile["timeout_seconds"]
        while not finished.wait(0.025):
            if cancel_event.is_set():
                self._abort(connection, response_holder)
                return
            if time.monotonic() >= deadline:
                timed_out.set()
                self._abort(connection, response_holder)
                return

    @staticmethod
    def _check_status(response) -> None:
        status = response.status
        if 300 <= status < 400:
            raise _TransportFailure("redirect_rejected", "Provider redirects are not followed.")
        if status in (401, 403):
            raise _TransportFailure("authentication", "Provider rejected authentication or access.")
        if status == 429:
            raise _TransportFailure("rate_limit", "Provider rate limit reached; no automatic retry was made.")
        if status >= 500:
            raise _TransportFailure("provider_error", "Provider returned a server error; no automatic retry was made.")
        if not 200 <= status < 300:
            raise _TransportFailure("http_error", f"Provider request returned HTTP {status}.")

    def probe(self, cancel_event=None) -> dict:
        cancel = cancel_event or threading.Event()
        finished, timed_out = threading.Event(), threading.Event()
        connection, base = self._connection()
        response_holder = []
        watcher = threading.Thread(target=self._watch, args=(connection, response_holder, cancel, finished, timed_out), daemon=True)
        start = time.monotonic()
        result = {"models": [], "status": "Failed", "capabilities": {
            "model_listing": "tested_by_probe", "streaming": "not_verified_by_model_listing",
            "usage": "unverified", "seed": "unverified", "token_counting": "not_available",
            "reasoning_effort": "not_verified_by_model_listing",
            "cancellation": "client_disconnect_server_stop_not_guaranteed"}, "error": None}
        try:
            if cancel.is_set():
                raise _TransportFailure("cancelled", "Connection probe was cancelled.")
            secret = self._credentials()
            headers = {"Accept": "application/json"}
            if secret:
                headers["Authorization"] = f"Bearer {secret}"
            watcher.start()
            connection.request("GET", f"{base}/models", headers=headers)
            response = connection.getresponse()
            response_holder.append(response)
            self._check_status(response)
            encoded = response.read(MAX_RESPONSE_BYTES + 1)
            if len(encoded) > MAX_RESPONSE_BYTES:
                raise _TransportFailure("response_limit", "Model-list response exceeds the size limit.")
            data = strict_loads(encoded.decode("utf-8"))
            if type(data) is not dict or type(data.get("data")) is not list:
                raise _TransportFailure("invalid_response", "Provider did not return a model-list object.")
            models = []
            for model in data["data"]:
                if type(model) is not dict or type(model.get("id")) is not str:
                    raise _TransportFailure("invalid_response", "Provider model entry has no string ID.")
                if secret and secret in model["id"]:
                    raise _TransportFailure("credential_echo", "Provider response echoed a credential and was not saved.")
                models.append(model["id"])
            result["models"] = models
            result["selected_model_available"] = self.profile["model"] in models
            if not result["selected_model_available"]:
                raise _TransportFailure("model_unavailable", "Selected model is not present in the provider's model list.")
            result["status"] = "Connected"
        except Exception as error:
            code, message = self._failure(error, cancel, timed_out)
            result["status"] = "Cancelled" if code == "cancelled" else "Failed"
            result["error"] = {"code": code, "message": message}
        finally:
            finished.set()
            self._abort(connection, response_holder)
            if watcher.is_alive():
                watcher.join(timeout=0.1)
            result["elapsed_seconds"] = round(time.monotonic() - start, 3)
        return result

    @staticmethod
    def _failure(error, cancel, timed_out) -> tuple[str, str]:
        if isinstance(error, _EventCallbackFailure):
            return error.code, error.message
        if cancel.is_set():
            return "cancelled", "Client disconnected after cancellation; server-side inference stop is not guaranteed."
        if timed_out.is_set() or isinstance(error, (TimeoutError, socket.timeout)):
            return "timeout", "Provider request timed out; server-side completion is unknown and no retry was made."
        if isinstance(error, _TransportFailure):
            return error.code, error.message
        if isinstance(error, (DomainError, UnicodeError, ValueError)):
            return "invalid_response", "Provider returned malformed JSON or text."
        if isinstance(error, (OSError, http.client.HTTPException)):
            return "connection_error", "Provider connection failed or was interrupted; no retry was made."
        return "adapter_error", "Provider request could not be completed."

    def generate(self, messages: list, parameters: dict | None = None, cancel_event=None, on_event=None) -> dict:
        if type(messages) is not list or not messages:
            raise DomainError("invalid_messages", "Generation needs a nonempty text-message array.")
        for message in messages:
            if (type(message) is not dict or set(message) != {"role", "content"}
                    or message.get("role") not in ("system", "user", "assistant") or type(message.get("content")) is not str):
                raise DomainError("invalid_messages", "Messages must contain only a supported role and text content.")
        params = {"temperature": self.profile["temperature"], "seed": self.profile["seed"],
                  "max_tokens": self.profile["max_output_tokens"], "reasoning_effort": self.profile["reasoning_effort"]}
        if parameters is not None:
            if type(parameters) is not dict or set(parameters) - set(params):
                raise DomainError("unsupported_parameter", "Only temperature, seed, max_tokens, and optional reasoning_effort='none' are supported.")
            params.update(parameters)
        temp = params["temperature"]
        try:
            valid_temperature = type(temp) in (int, float) and math.isfinite(temp) and 0 <= temp <= 2
        except OverflowError:
            valid_temperature = False
        if (not valid_temperature or type(params["seed"]) is not int or not 0 <= params["seed"] <= 4294967295
                or type(params["max_tokens"]) is not int or not 1 <= params["max_tokens"] <= self.profile["max_output_tokens"]
                or not (params["reasoning_effort"] is None or type(params["reasoning_effort"]) is str and params["reasoning_effort"] == "none")):
            raise DomainError("unsupported_parameter", "Generation settings exceed the validated profile bounds.")
        if estimate_message_input(messages) + params["max_tokens"] > self.profile["context_window"]:
            raise DomainError("context_limit", "Conservative input estimate plus output limit exceeds the profile context window; nothing was truncated.", 422)
        cancel = cancel_event or threading.Event()
        finished, timed_out = threading.Event(), threading.Event()
        connection, base = self._connection()
        response_holder = []
        watcher = threading.Thread(target=self._watch, args=(connection, response_holder, cancel, finished, timed_out), daemon=True)
        start = time.monotonic()
        result = {"raw_content": "", "raw_reasoning": "", "finish_reason": None, "usage": None,
                  "events": [], "execution_status": "Failed", "error": None,
                  "provider_request_id": None, "streaming": True, "done_received": False,
                  "cancellation_scope": "client_disconnect_server_stop_not_guaranteed"}
        secret = ""
        pending_text = {"raw_content": "", "raw_reasoning": ""}

        def clean(value):
            if type(value) is dict:
                return {clean(key): clean(child) for key, child in value.items()}
            if type(value) is list:
                return [clean(child) for child in value]
            if type(value) is str and secret and secret in value:
                result["credential_redaction"] = True
                return value.replace(secret, "[REDACTED]")
            return value

        def emit(kind: str, **fields) -> None:
            event = clean({"type": kind, **fields})
            result["events"].append(event)
            if on_event is not None:
                try:
                    on_event(copy.deepcopy(event))
                except Exception as error:
                    # Callback I/O must not be mislabeled as a provider connection failure.
                    raise _EventCallbackFailure(error) from error

        def append_text(target: str, event_type: str, text: str, flush: bool = False) -> None:
            # With credentials, retain a suffix that could be the beginning of
            # the key. A key split across SSE deltas must never reach a saved
            # event or reconstruct itself in the concatenated raw response.
            combined = pending_text[target] + text
            if secret and secret in combined:
                result["credential_redaction"] = True
                combined = combined.replace(secret, "[REDACTED]")
            overlap = 0
            if secret and not flush:
                for length in range(min(len(secret) - 1, len(combined)), 0, -1):
                    if combined.endswith(secret[:length]):
                        overlap = length
                        break
            pending_text[target] = combined[-overlap:] if overlap else ""
            safe = combined[:-overlap] if overlap else combined
            if safe:
                result[target] += safe
                if len(result[target].encode("utf-8")) > MAX_CONTENT_BYTES:
                    raise _TransportFailure("response_limit", "Provider content exceeds the size limit.")
                emit(event_type, content=safe)

        def flush_text() -> None:
            for target, event_type in (("raw_content", "content"), ("raw_reasoning", "reasoning")):
                if pending_text[target]:
                    append_text(target, event_type, "", flush=True)

        def chunk(data: dict, streaming: bool = True) -> None:
            if type(data) is not dict:
                raise _TransportFailure("invalid_response", "Provider chunk must be a JSON object.")
            if data.get("error") is not None:
                raise _TransportFailure("provider_error", "Provider reported an error within its response.")
            if type(data.get("id")) is str:
                result["provider_request_id"] = clean(data["id"])
            if data.get("usage") is not None:
                if type(data["usage"]) is not dict:
                    raise _TransportFailure("invalid_response", "Provider usage must be an object.")
                result["usage"] = clean(data["usage"])
                emit("usage", usage=result["usage"])
            choices = data.get("choices")
            if type(choices) is not list:
                raise _TransportFailure("invalid_response", "Provider chunk must contain a choices array.")
            if len(choices) > 1:
                raise _TransportFailure("unsupported_response", "Multiple generated candidates are not supported.")
            for choice in choices:
                if type(choice) is not dict:
                    raise _TransportFailure("invalid_response", "Provider choice must be an object.")
                delta = choice.get("delta" if streaming else "message", {})
                if type(delta) is not dict:
                    raise _TransportFailure("invalid_response", "Provider message delta must be an object.")
                if delta.get("tool_calls") or delta.get("function_call"):
                    raise _TransportFailure("unsupported_tool_call", "Tool calls are not executed by the RTL adapter.")
                if delta.get("refusal"):
                    raise _TransportFailure("refusal", "Provider refused the generation request.")
                if delta.get("reasoning_content") is not None and delta.get("reasoning") is not None:
                    raise _TransportFailure("invalid_response", "Provider returned ambiguous reasoning fields.")
                reasoning = delta.get("reasoning_content")
                if reasoning is None:
                    reasoning = delta.get("reasoning")
                for text, target, event_type in ((delta.get("content"), "raw_content", "content"), (reasoning, "raw_reasoning", "reasoning")):
                    if text is not None:
                        if type(text) is not str:
                            raise _TransportFailure("invalid_response", "Provider text delta must be a string.")
                        if text:
                            if result["finish_reason"] is not None:
                                raise _TransportFailure("invalid_response", "Provider sent content after a terminal finish reason.")
                            append_text(target, event_type, text)
                reason = choice.get("finish_reason")
                if reason is not None:
                    if type(reason) is not str or result["finish_reason"] is not None:
                        raise _TransportFailure("invalid_response", "Provider sent conflicting terminal finish reasons.")
                    result["finish_reason"] = clean(reason)
                    emit("finish", finish_reason=reason)

        try:
            if cancel.is_set():
                raise _TransportFailure("cancelled", "Generation was cancelled before sending.")
            secret = self._credentials()
            request_parameters = {key: value for key, value in params.items() if key != "reasoning_effort" or value is not None}
            body = json.dumps({"model": self.profile["model"], "messages": messages, "stream": True,
                               "stream_options": {"include_usage": True}, **request_parameters}, ensure_ascii=False, allow_nan=False).encode("utf-8")
            headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
            if secret:
                headers["Authorization"] = f"Bearer {secret}"
            emit("started", model=self.profile["model"], execution_location=self.profile["execution_location"])
            watcher.start()
            connection.request("POST", f"{base}/chat/completions", body=body, headers=headers)
            response = connection.getresponse()
            response_holder.append(response)
            self._check_status(response)
            if response.getheader("Content-Type", "").split(";", 1)[0].strip() == "application/json":
                encoded = response.read(MAX_RESPONSE_BYTES + 1)
                if len(encoded) > MAX_RESPONSE_BYTES:
                    raise _TransportFailure("response_limit", "Provider response exceeds the size limit.")
                result["streaming"] = False
                emit("warning", content="Provider returned a non-streamed response to a streaming request.")
                chunk(strict_loads(encoded.decode("utf-8")), streaming=False)
            else:
                data_lines = []
                total_bytes = 0
                while True:
                    if cancel.is_set():
                        raise _TransportFailure("cancelled", "Generation was cancelled.")
                    if timed_out.is_set():
                        raise _TransportFailure("timeout", "Provider request timed out.")
                    raw = response.readline(MAX_LINE_BYTES + 1)
                    total_bytes += len(raw)
                    if len(raw) > MAX_LINE_BYTES or total_bytes > MAX_RESPONSE_BYTES:
                        raise _TransportFailure("response_limit", "Provider stream exceeds the size limit.")
                    if not raw:
                        if data_lines:
                            raise _TransportFailure("stream_incomplete", "Provider stream ended within an event.")
                        break
                    line = raw.decode("utf-8").rstrip("\r\n")
                    if not line:
                        if not data_lines:
                            continue
                        text = "\n".join(data_lines)
                        data_lines = []
                        if text == "[DONE]":
                            result["done_received"] = True
                            break
                        chunk(strict_loads(text))
                    elif line.startswith("data:"):
                        data_lines.append(line[5:].lstrip(" "))
                    elif line.startswith(":") or line.startswith(("event:", "id:", "retry:")):
                        continue
                    else:
                        raise _TransportFailure("invalid_response", "Provider returned a non-SSE response line.")
            if cancel.is_set():
                raise _TransportFailure("cancelled", "Generation was cancelled.")
            if timed_out.is_set():
                raise _TransportFailure("timeout", "Provider request timed out.")
            flush_text()
            if result.get("credential_redaction"):
                raise _TransportFailure("credential_echo", "Provider echoed a credential; returned text was redacted and is not an acceptable candidate.")
            if result["finish_reason"] == "length":
                raise _TransportFailure("output_truncated", "Provider reached its output limit; the partial answer is retained.")
            if result["finish_reason"] != "stop":
                raise _TransportFailure("stream_incomplete", "No explicit normal stop finish reason was received.")
            if not result["raw_content"].strip():
                raise _TransportFailure("empty_response", "Provider finished without candidate text.")
            result["execution_status"] = "Completed"
            emit("completed", finish_reason=result["finish_reason"])
        except Exception as error:
            try:
                flush_text()
            except Exception:
                pass
            code, message = self._failure(error, cancel, timed_out)
            if result.get("credential_redaction"):
                code, message = "credential_echo", "Provider echoed a credential; returned text was redacted and is not an acceptable candidate."
            result["execution_status"] = "Cancelled" if code == "cancelled" else "Failed"
            result["error"] = {"code": code, "message": message}
            try:
                emit("cancelled" if code == "cancelled" else "error", error=result["error"])
            except Exception:
                pass
        finally:
            finished.set()
            self._abort(connection, response_holder)
            if watcher.is_alive():
                watcher.join(timeout=0.1)
            result["elapsed_seconds"] = round(time.monotonic() - start, 3)
        return result
