#!/bin/sh
set -eu
mkdir -p .local/verification
uv lock --check
uv export --quiet --locked --no-dev --no-emit-project --format requirements-txt --output-file /tmp/gateway-requirements-check.txt
uv export --quiet --locked --no-dev --extra ui --no-emit-project --format requirements-txt --output-file /tmp/gateway-requirements-ui-check.txt
# Export comments contain the output filename; compare all dependency/hash lines.
sed '/^#/d' requirements.txt > /tmp/gateway-requirements-expected.txt
sed '/^#/d' /tmp/gateway-requirements-check.txt > /tmp/gateway-requirements-actual.txt
diff -u /tmp/gateway-requirements-expected.txt /tmp/gateway-requirements-actual.txt
sed '/^#/d' requirements-ui.txt > /tmp/gateway-requirements-ui-expected.txt
sed '/^#/d' /tmp/gateway-requirements-ui-check.txt > /tmp/gateway-requirements-ui-actual.txt
diff -u /tmp/gateway-requirements-ui-expected.txt /tmp/gateway-requirements-ui-actual.txt
uv run --locked ruff check gateway tests scripts api_gateway.py provider_manager.py search_tool.py admin_app.py streamlit_app.py
uv run --locked black --check --workers 1 gateway tests scripts api_gateway.py provider_manager.py search_tool.py admin_app.py streamlit_app.py
uv run --locked mypy
uv run --locked --extra ui pytest -q --junitxml=.local/verification/pytest.xml
uv run --locked python scripts/source_gate.py
uv run --locked python scripts/source_gate.py --history
uv build --locked
