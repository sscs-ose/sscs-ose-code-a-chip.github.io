"""In-memory JSON transport checks; no sockets, project, model or EDA actions."""
from __future__ import annotations

from email.message import Message
import gzip
import io
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from hullcirq.server import JSON_GZIP_MIN_BYTES, RequestHandler


class MemoryResponse(RequestHandler):
    def __init__(self, encodings=()):
        self.headers = Message()
        for encoding in encodings:
            self.headers.add_header("Accept-Encoding", encoding)
        self.wfile = io.BytesIO()
        self.sent_headers = []
        self.status = None

    def send_response(self, status):
        self.status = status

    def send_header(self, name, value):
        self.sent_headers.append((name, value))

    def end_headers(self):
        pass

    def header(self, name):
        return [value for key, value in self.sent_headers if key.lower() == name.lower()]


class JsonResponseCompressionTests(unittest.TestCase):
    @staticmethod
    def encoded(value):
        return json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")

    def large(self):
        return {"software_fixture": True, "original_text": "History \u03bb\u65e5\u672c\u8a9e\n" * 10000}

    def response(self, value, accept=None, extra=None, status=200):
        response = MemoryResponse(() if accept is None else (accept,))
        response._json(value, status, extra)
        self.assertEqual(response.status, status)
        self.assertEqual(response.header("Content-Type"), ["application/json; charset=utf-8"])
        self.assertEqual(response.header("Content-Length"), [str(len(response.wfile.getvalue()))])
        self.assertEqual(response.header("Cache-Control"), ["no-store"])
        self.assertEqual(response.header("X-Content-Type-Options"), ["nosniff"])
        self.assertEqual(response.header("Referrer-Policy"), ["no-referrer"])
        self.assertIn("default-src 'self'", response.header("Content-Security-Policy")[0])
        return response

    def test_negotiated_large_json_decompresses_to_exact_original_bytes(self):
        value = self.large()
        response = self.response(value, "gzip", status=202)
        self.assertEqual(response.header("Content-Encoding"), ["gzip"])
        self.assertEqual(response.header("Vary"), ["Accept-Encoding"])
        self.assertEqual(gzip.decompress(response.wfile.getvalue()), self.encoded(value))
        self.assertLess(len(response.wfile.getvalue()), len(self.encoded(value)))
        self.assertEqual(response.wfile.getvalue()[4:8], b"\x00\x00\x00\x00")
        self.assertEqual(response.wfile.getvalue(), self.response(value, "gzip").wfile.getvalue())

    def test_absent_or_unlisted_encoding_retains_original_body_and_vary(self):
        for accept in (None, "", "br, deflate", "identity"):
            with self.subTest(accept=accept):
                value = self.large()
                response = self.response(value, accept)
                self.assertEqual(response.header("Content-Encoding"), [])
                self.assertEqual(response.header("Vary"), ["Accept-Encoding"])
                self.assertEqual(response.wfile.getvalue(), self.encoded(value))

    def test_zero_and_malformed_quality_do_not_enable_gzip(self):
        for accept in ("gzip;q=0", "br;q=1, gzip;q=0", "gzip;q=0, *;q=1",
                       "gzip;q=0.000", "gzip;q=nan", "gzip;q=2", "gzip;q=-1", "gzip;q=.5",
                       "gzip;q=0.1234", "gzip;q=1.001", "gzip;q=", "gzip;quality=1",
                       "gzip;q=0.5;q=1", "gzip;q=oops, *;q=1", "gzip;q=1, gzip;q=0"):
            with self.subTest(accept=accept):
                value = self.large()
                response = self.response(value, accept)
                self.assertEqual(response.header("Content-Encoding"), [])
                self.assertEqual(response.wfile.getvalue(), self.encoded(value))

    def test_positive_mixed_quality_and_case_enable_gzip(self):
        for accept in ("br;q=1, gzip;q=0.5", "GZIP; Q=0.001", "gzip;q=1.000",
                       "deflate, gzip", "*;q=0.5", "*;q=0, gzip;q=0.5"):
            with self.subTest(accept=accept):
                value = self.large()
                response = self.response(value, accept)
                self.assertEqual(response.header("Content-Encoding"), ["gzip"])
                self.assertEqual(gzip.decompress(response.wfile.getvalue()), self.encoded(value))

    def test_repeated_accept_encoding_headers_respect_explicit_exclusion(self):
        response = MemoryResponse(("*;q=1", "gzip;q=0"))
        value = self.large()
        response._json(value)
        self.assertEqual(response.header("Content-Encoding"), [])
        self.assertEqual(response.wfile.getvalue(), self.encoded(value))

    def test_small_json_and_exact_threshold_are_based_on_encoded_bytes(self):
        # The JSON string quotes account for the final two UTF-8 bytes.
        for length in (JSON_GZIP_MIN_BYTES - 1, JSON_GZIP_MIN_BYTES):
            value = "x" * (length - 2)
            response = self.response(value, "gzip")
            self.assertEqual(len(self.encoded(value)), length)
            if length < JSON_GZIP_MIN_BYTES:
                self.assertEqual(response.header("Content-Encoding"), [])
                self.assertEqual(response.wfile.getvalue(), self.encoded(value))
            else:
                self.assertEqual(response.header("Content-Encoding"), ["gzip"])
                self.assertEqual(gzip.decompress(response.wfile.getvalue()), self.encoded(value))

    def test_extra_headers_and_existing_vary_are_preserved_without_mutation(self):
        extra = {"X-Software-Fixture": "retained", "vary": "Origin, accept-encoding"}
        original = dict(extra)
        response = self.response(self.large(), "gzip", extra)
        self.assertEqual(extra, original)
        self.assertEqual(response.header("X-Software-Fixture"), ["retained"])
        self.assertEqual(response.header("Vary"), ["Origin, accept-encoding"])
        self.assertEqual(response.header("Content-Encoding"), ["gzip"])
        response = self.response(self.large(), "gzip", {"Vary": "Origin"})
        self.assertEqual(response.header("Vary"), ["Origin, Accept-Encoding"])
        response = self.response(self.large(), "gzip", {"Vary": "*"})
        self.assertEqual(response.header("Vary"), ["*"])

    def test_json_download_is_never_compressed(self):
        value = self.large()
        for key in ("Content-Disposition", "content-disposition"):
            with self.subTest(key=key):
                response = self.response(value, "gzip", {key: 'attachment; filename="fixture.json"'})
                self.assertEqual(response.header("Content-Encoding"), [])
                self.assertEqual(response.header("Content-Disposition"), ['attachment; filename="fixture.json"'])
                self.assertEqual(response.wfile.getvalue(), self.encoded(value))

    def test_static_and_raw_response_header_path_does_not_negotiate_compression(self):
        raw = b"software fixture raw bytes\n" * 10000
        for mime in ("text/javascript; charset=utf-8", "application/octet-stream", "image/png"):
            with self.subTest(mime=mime):
                response = MemoryResponse(("gzip",))
                response._headers(200, mime, len(raw))
                response.wfile.write(raw)
                self.assertEqual(response.header("Content-Encoding"), [])
                self.assertEqual(response.header("Vary"), [])
                self.assertEqual(response.header("Content-Length"), [str(len(raw))])
                self.assertEqual(response.wfile.getvalue(), raw)

    def test_nonfinite_json_still_rejected_before_headers_or_body(self):
        response = MemoryResponse(("gzip",))
        with self.assertRaises(ValueError):
            response._json({"invalid": float("nan")})
        self.assertEqual(response.sent_headers, [])
        self.assertEqual(response.wfile.getvalue(), b"")


if __name__ == "__main__":
    unittest.main()
