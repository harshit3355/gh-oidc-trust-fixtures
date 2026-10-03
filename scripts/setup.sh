#!/usr/bin/env bash
# Install the pinned scanners into $TOOLS_DIR (default ~/.cache/gh-oidc-trust-fixtures).
# Linux/WSL; needs python3 (venv), git and go. No cloud access or credentials needed.
set -euo pipefail
CHECKOV_VERSION=3.3.21
KICS_TAG=v2.2.0
TOOLS_DIR=${TOOLS_DIR:-$HOME/.cache/gh-oidc-trust-fixtures}
mkdir -p "$TOOLS_DIR" && cd "$TOOLS_DIR"

venv() { [ -x "$1/bin/checkov" ] || { python3 -m venv "$1" && "$1/bin/pip" install -q "checkov==$CHECKOV_VERSION"; }; }
venv checkov
venv checkov-pr7610

# Apply the one-line regex change from bridgecrewio/checkov PR #7610 (immutable subject support).
checkov-pr7610/bin/python - <<'EOF'
import pathlib
import checkov.common.util.oidc_utils as m
p = pathlib.Path(m.__file__)
s = p.read_text()
old, new = r"(\})?/[^/]+", r"(@[0-9]+)?(\})?/[^/]+"
if new not in s:
    assert s.count(old) == 1, "unexpected oidc_utils.py; PR #7610 patch does not apply"
    p.write_text(s.replace(old, new))
print("checkov-pr7610: patch applied")
EOF

if [ ! -x kics/bin/kics ]; then
  [ -d kics ] || git clone -q --depth 1 --branch "$KICS_TAG" https://github.com/Checkmarx/kics
  (cd kics && go build -o bin/kics -ldflags "-X github.com/Checkmarx/kics/v2/internal/constants.Version=$KICS_TAG" ./cmd/console)
fi
echo "tools ready in $TOOLS_DIR"
