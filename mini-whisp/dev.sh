#!/usr/bin/env bash
set -euo pipefail

# One command to run mini-whisp: picks the right Node, installs deps when
# needed, checks whisper.cpp, then starts `tauri dev`.

cd "$(dirname "$(realpath "$0")")"

step() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

# Snap VS Code's terminal points GTK/glibc at /snap/core20, which crashes the
# app (`libpthread ... __libc_pthread_init`). Drop those overrides.
unset GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE GIO_MODULE_DIR GSETTINGS_SCHEMA_DIR \
  GDK_PIXBUF_MODULE_FILE GDK_PIXBUF_MODULEDIR LOCPATH LD_LIBRARY_PATH

# Node from .nvmrc (nvm.sh is not `set -u` safe).
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
[ -s "$NVM_DIR/nvm.sh" ] || fail "nvm not found in $NVM_DIR (see README, step 3)"
set +u
# shellcheck disable=SC1091
. "$NVM_DIR/nvm.sh"
if ! nvm use >/dev/null 2>&1; then
  step "Installing Node $(cat .nvmrc)"
  nvm install >/dev/null || fail "nvm could not install Node $(cat .nvmrc)"
fi
set -u
step "Node $(node -v)"

export PATH="$HOME/.bun/bin:$HOME/.cargo/bin:$PATH"
command -v bun >/dev/null || fail "bun not found (curl -fsSL https://bun.sh/install | bash)"
command -v cargo >/dev/null || fail "cargo not found (see README, step 2)"
command -v pw-record >/dev/null || echo "!! pw-record not found, the waveform will stay flat"

if [ ! -d node_modules ] || [ bun.lock -nt node_modules ] || [ package.json -nt node_modules ]; then
  step "Installing JS dependencies"
  bun install
  touch node_modules
fi

WHISPER="$HOME/.local/share/creator-tools"
if [ ! -x "$WHISPER/whisper.cpp/build/bin/whisper-stream" ] || [ ! -f "$WHISPER/models/ggml-large-v3-turbo.bin" ]; then
  echo "!! whisper.cpp is not installed, recording stays disabled. Run ./scripts/setup-whisper.sh (about 5 GB)."
fi

# Cargo's build cache stores absolute paths, so moving the project breaks
# `tauri dev`. Remember where the cache was built and clean it after a move.
TARGET="src-tauri/target"
MARKER="$TARGET/.project-path"
if [ -f "$MARKER" ] && [ "$(cat "$MARKER")" != "$PWD" ]; then
  step "Project moved from $(cat "$MARKER"), cleaning Cargo cache"
  cargo clean --manifest-path src-tauri/Cargo.toml
fi
mkdir -p "$TARGET"
echo "$PWD" > "$MARKER"

step "Starting mini-whisp"
exec bun run tauri dev "$@"
