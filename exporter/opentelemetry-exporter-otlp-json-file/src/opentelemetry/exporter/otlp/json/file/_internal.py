# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import base64
import gzip
import json
import logging
import sys
import threading
from collections.abc import Callable
from os import PathLike
from typing import IO, Generic, Literal, TypeVar

_logger = logging.getLogger(__name__)

T = TypeVar("T")

# Marker token appended to the configured prefix, per signal kind.
_SIGNAL_TOKENS: dict[str, str] = {
    "spans": "TRACE",
    "metrics": "METRIC",
    "logs": "LOG",
}


def _has_whitespace_or_control(value: str) -> bool:
    return any(character.isspace() or ord(character) <= 0x1F or ord(character) == 0x7F for character in value)


def _normalize_marker_prefix(marker_prefix: str | None) -> str | None:
    if marker_prefix is None:
        return None
    stripped = marker_prefix.strip()
    if not stripped:
        return None
    # Whitespace/control characters would corrupt the line framing; reject them.
    if _has_whitespace_or_control(stripped):
        _logger.warning("marker_prefix contains whitespace or control characters; ignoring it and applying no prefix")
        return None
    return stripped


class _FileExporter(Generic[T]):
    def __init__(
        self,
        encode: Callable[[T], dict | None],
        kind: Literal["spans", "logs", "metrics"],
        logger: logging.Logger | None = None,
        path: str | PathLike[str] | None = None,
        stream: IO[str] | None = None,
        marker_prefix: str | None = None,
        base64_encode: bool = False,
        gzip_compress: bool = False,
    ) -> None:
        if path is not None and stream is not None:
            raise ValueError("Cannot specify both 'path' and 'stream'")
        if path is not None:
            self._stream: IO[str] = open(  # pylint: disable=consider-using-with
                path, "a", encoding="utf-8"
            )
            self._owns_stream = True
        elif stream is not None:
            self._stream = stream
            self._owns_stream = False
        else:
            self._stream = sys.stdout
            self._owns_stream = False
        self._shutdown = False
        self._encode = encode
        self._kind = kind
        self._logger = logger if logger is not None else _logger
        self._lock = threading.Lock()
        self._marker_prefix = _normalize_marker_prefix(marker_prefix)
        self._token = _SIGNAL_TOKENS[kind]
        self._gzip = gzip_compress
        # gzip output is binary, so it must be base64-encoded to live on a text line.
        self._base64 = base64_encode or gzip_compress
        if gzip_compress and not base64_encode:
            self._logger.info(
                "gzip compression enabled; base64 encoding applied so gzip output can be written to the text stream"
            )

    def export(self, data: T) -> bool:
        if self._shutdown:
            self._logger.warning("Exporter already shutdown, ignoring call")
            return False
        try:
            encoded = self._encode(data)
            with self._lock:
                if self._stream.closed:
                    self._logger.warning("Stream is closed, ignoring %s export call", self._kind)
                    return False
                if encoded is not None:
                    self._stream.write(self._render(encoded))
                self._stream.flush()
        # pylint: disable-next=broad-exception-caught
        except Exception as error:
            self._logger.exception(
                "Failed to write %s batch to stream: %s: %s",
                self._kind,
                type(error).__name__,
                error,
            )
            return False
        return True

    def _render(self, entry: dict) -> str:
        return _format_line(
            entry,
            token=self._token,
            marker_prefix=self._marker_prefix,
            base64_encode=self._base64,
            gzip_compress=self._gzip,
        )

    def shutdown(self) -> None:
        if self._shutdown:
            self._logger.warning("Exporter already shutdown, ignoring call")
            return
        self._shutdown = True
        if self._owns_stream:
            with self._lock:
                self._stream.close()


def _encode_payload(json_text: str, *, base64_encode: bool, gzip_compress: bool) -> str:
    if gzip_compress:
        compressed = gzip.compress(json_text.encode("utf-8"), compresslevel=1)
        return base64.b64encode(compressed).decode("ascii")
    if base64_encode:
        return base64.b64encode(json_text.encode("utf-8")).decode("ascii")
    return json_text


def _format_line(
    entry: dict,
    *,
    token: str = "",
    marker_prefix: str | None = None,
    base64_encode: bool = False,
    gzip_compress: bool = False,
) -> str:
    json_text = json.dumps(entry, separators=(",", ":"))
    payload = _encode_payload(json_text, base64_encode=base64_encode, gzip_compress=gzip_compress)
    if marker_prefix is None:
        return payload + "\n"
    return f"{marker_prefix}_{token} {payload}\n"
