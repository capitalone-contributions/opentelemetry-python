OpenTelemetry JSON File Exporter
================================

|pypi|

.. |pypi| image:: https://badge.fury.io/py/opentelemetry-exporter-otlp-json-file.svg
   :target: https://pypi.org/project/opentelemetry-exporter-otlp-json-file/

This library exports telemetry as OTLP JSON to a file-like text stream, such
as a file or stdout.

The exporter writes newline delimited OTLP JSON records for file-based
collection workflows.

Output options
--------------

By default each exported batch is written as one compact OTLP JSON object per
line. The exporters accept optional keyword arguments to adjust the line format,
each opt-in and applied independently:

- ``marker_prefix`` - prefix every line with ``{marker_prefix}_{SIGNAL} ``
  (``SIGNAL`` is ``TRACE``, ``METRIC``, or ``LOG``).
- ``base64`` - base64-encode the JSON payload.
- ``gzip`` - gzip-compress the payload (implies ``base64``).

Installation
------------

::

     pip install opentelemetry-exporter-otlp-json-file


References
----------

* `OpenTelemetry Project <https://opentelemetry.io/>`_
* `OpenTelemetry Protocol File Exporter <https://opentelemetry.io/docs/specs/otel/protocol/file-exporter/>`_
* `OTLP Specification <https://opentelemetry.io/docs/specs/otlp/>`_
* `OTLP JSON Encoding Specification <https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding>`_
* `JSON Lines <https://jsonlines.org/>`_
