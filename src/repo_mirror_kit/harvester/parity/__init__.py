"""Behavioural parity scoring (BEAN-077/078).

Runs an application (the original or an agent's rebuild) and measures how
faithfully it reproduces the original's observable behaviour:

- :mod:`goldens`   — capture/replay recorded request→response interactions
- :mod:`gherkin_runner` — bind generated ``.feature`` scenarios to HTTP calls
- :mod:`schema_diff` — compare database design (tables/columns/foreign keys)
- :mod:`score`     — combine the three families + run telemetry into a report

Layout-agnostic by design: only the HTTP surface and the data schema are
compared, so a rebuild in a different framework is never penalised for being
different code.
"""
