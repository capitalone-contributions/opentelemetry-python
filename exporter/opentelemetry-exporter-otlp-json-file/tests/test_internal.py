# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import base64
import gzip
import json
import unittest

from opentelemetry.exporter.otlp.json.file._internal import (
    _format_line,
    _normalize_marker_prefix,
)


class TestFormatLine(unittest.TestCase):
    def test_produces_valid_json(self):
        result = _format_line({"a": 1, "b": "hello"}, token="TRACE")
        parsed = json.loads(result.strip())
        self.assertEqual(parsed, {"a": 1, "b": "hello"})

    def test_newline_terminated(self):
        result = _format_line({"x": 0}, token="TRACE")
        self.assertTrue(result.endswith("\n"))

    def test_compact_no_spaces(self):
        result = _format_line({"a": 1, "b": 2}, token="TRACE")
        self.assertNotIn(" ", result)

    def test_nested_structure(self):
        entry = {"outer": {"inner": [1, 2, 3]}, "flag": True}
        result = _format_line(entry, token="TRACE")
        parsed = json.loads(result.strip())
        self.assertEqual(parsed, entry)


class TestBase64Encoding(unittest.TestCase):
    def test_payload_is_base64_of_json(self):
        entry = {"a": 1, "b": "hello"}
        result = _format_line(entry, token="TRACE", base64_encode=True)
        decoded = base64.b64decode(result.strip()).decode("utf-8")
        self.assertEqual(json.loads(decoded), entry)


class TestGzipCompression(unittest.TestCase):
    def test_gzip_alone_still_base64_wrapped(self):
        entry = {"a": 1, "b": "hello"}
        result = _format_line(entry, token="METRIC", gzip_compress=True)
        decompressed = gzip.decompress(base64.b64decode(result.strip())).decode("utf-8")
        self.assertEqual(json.loads(decompressed), entry)


class TestMarkerPrefix(unittest.TestCase):
    def test_marker_prepended_with_signal_token(self):
        result = _format_line({"x": 1}, token="LOG", marker_prefix="OTEL_EXPORT")
        marker, payload = result.rstrip("\n").split(" ", 1)
        self.assertEqual(marker, "OTEL_EXPORT_LOG")
        self.assertEqual(json.loads(payload), {"x": 1})

    def test_marker_with_base64_payload(self):
        entry = {"x": 1}
        result = _format_line(entry, token="TRACE", marker_prefix="P", base64_encode=True)
        marker, payload = result.rstrip("\n").split(" ", 1)
        self.assertEqual(marker, "P_TRACE")
        self.assertEqual(json.loads(base64.b64decode(payload)), entry)


class TestNormalizeMarkerPrefix(unittest.TestCase):
    def test_prefix_is_stripped(self):
        self.assertEqual(_normalize_marker_prefix("  P  "), "P")

    def test_empty_prefix_becomes_none(self):
        self.assertIsNone(_normalize_marker_prefix("   "))

    def test_none_stays_none(self):
        self.assertIsNone(_normalize_marker_prefix(None))

    def test_prefix_with_internal_whitespace_rejected(self):
        self.assertIsNone(_normalize_marker_prefix("bad prefix"))

    def test_prefix_with_control_char_rejected(self):
        self.assertIsNone(_normalize_marker_prefix("bad\tprefix"))
