#!/usr/bin/env bash
set -euo pipefail

WHISPER_VERSION="v1.9.4"
CUDA_ARCH="86"
BASE="$HOME/.local/share/creator-tools"
SRC="$BASE/whisper.cpp"
MODELS="$BASE/models"
NVCC="${NVCC:-/usr/local/cuda/bin/nvcc}"

if [ ! -x "$NVCC" ]; then
  echo "nvcc not found at $NVCC. Install cuda-toolkit first (see README)." >&2
  exit 1
fi

mkdir -p "$BASE" "$MODELS"

if [ ! -d "$SRC" ]; then
  git clone --depth 1 --branch "$WHISPER_VERSION" https://github.com/ggml-org/whisper.cpp "$SRC"
fi

cmake -S "$SRC" -B "$SRC/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES="$CUDA_ARCH" \
  -DCMAKE_CUDA_COMPILER="$NVCC" \
  -DWHISPER_SDL2=ON
cmake --build "$SRC/build" -j "$(nproc)" --target whisper-cli whisper-stream

for model in large-v3 large-v3-turbo; do
  if [ ! -f "$MODELS/ggml-$model.bin" ]; then
    bash "$SRC/models/download-ggml-model.sh" "$model" "$MODELS"
  fi
done

echo
echo "Done:"
ls -lh "$SRC/build/bin/whisper-cli" "$SRC/build/bin/whisper-stream" "$MODELS"/*.bin
