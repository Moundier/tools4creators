#!/usr/bin/env bash
set -euo pipefail

# One command to run mini-news: creates .venv and installs requirements when
# needed, checks Claude Code and GIMP, then starts the web app (:8010).
# Extra args go to news.py, e.g. `./dev.sh draft <link>`.

cd "$(dirname "$(realpath "$0")")"

step() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null || fail "python3 not found"
if [ ! -x .venv/bin/python ]; then
  step "Creating .venv"
  python3 -m venv .venv
fi
if [ ! -f .venv/.installed ] || [ requirements.txt -nt .venv/.installed ]; then
  step "Installing Python dependencies"
  .venv/bin/pip install -r requirements.txt
  touch .venv/.installed
fi

command -v claude >/dev/null || echo "!! claude not found, drafts will fail (install Claude Code and log in)"
flatpak info org.gimp.GIMP >/dev/null 2>&1 || command -v gimp-console >/dev/null \
  || echo "!! GIMP 3 not found, images won't render (flatpak install flathub org.gimp.GIMP)"

step "Starting mini-news"
exec .venv/bin/python news.py "$@"
