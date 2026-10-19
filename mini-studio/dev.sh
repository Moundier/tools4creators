#!/usr/bin/env bash
set -euo pipefail

# One command to run mini-studio: creates .venv and installs requirements when
# needed, builds the Angular UI when its sources changed, then starts the
# Studio web app (:8000). Extra args go to studio.py, e.g. `./dev.sh thumb --list`.

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

command -v ffmpeg >/dev/null || echo "!! ffmpeg not found, subtitles and Shorts won't work (sudo apt install ffmpeg)"
flatpak info org.gimp.GIMP >/dev/null 2>&1 || command -v gimp-console >/dev/null \
  || echo "!! GIMP 3 not found, thumbnails won't render (flatpak install flathub org.gimp.GIMP)"

# Angular UI, served by the backend from studio-ui/dist (see studio_server/paths.py).
UI="studio-ui"
DIST="$UI/dist/studio-ui/browser"
if [ ! -d "$DIST" ] || [ -n "$(find "$UI/src" "$UI/angular.json" "$UI/package.json" -newer "$DIST" -print -quit)" ]; then
  # Node from studio-ui/.nvmrc (nvm.sh is not `set -u` safe).
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  [ -s "$NVM_DIR/nvm.sh" ] || fail "nvm not found in $NVM_DIR"
  set +u
  # shellcheck disable=SC1091
  . "$NVM_DIR/nvm.sh"
  cd "$UI"
  if ! nvm use >/dev/null 2>&1; then
    step "Installing Node $(cat .nvmrc)"
    nvm install >/dev/null || fail "nvm could not install Node $(cat .nvmrc)"
  fi
  set -u
  step "Node $(node -v)"
  if [ ! -d node_modules ] || [ package-lock.json -nt node_modules ] || [ package.json -nt node_modules ]; then
    step "Installing UI dependencies"
    npm install
    touch node_modules
  fi
  step "Building the Studio UI"
  npm run build
  touch "dist/studio-ui/browser"
  cd ..
fi

step "Starting mini-studio"
exec .venv/bin/python studio.py "$@"
