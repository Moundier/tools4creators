# mini-whisp

Floating bar for live local pt-BR audio transcription (Tauri + React + whisper.cpp). Hit record, watch the mic waveform while it captures, copy the text when you're done.

Spun off from `../mini-deck` (same whisper.cpp install, no OBS).

## Versions

| Tool | Version | Pinned in |
|---|---|---|
| Rust | stable (>= 1.85) | `src-tauri/rust-toolchain.toml` |
| Node | 24 | `.nvmrc` |
| Bun | 1.4.2 | `package.json` |
| Tauri | 2 | `src-tauri/Cargo.toml` |
| whisper.cpp | v1.9.4 | `scripts/setup-whisper.sh` |
| CUDA | 13 | |
| PipeWire | `pw-record` for the waveform | |

## 1. System dependencies

**Debian / Ubuntu**
```bash
sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev git cmake ffmpeg libsdl2-dev
```

**Arch / Manjaro**
```bash
sudo pacman -S --needed webkit2gtk-4.1 base-devel curl wget file openssl appmenu-gtk-module libappindicator-gtk3 librsvg xdotool git cmake ffmpeg sdl2
```

**Fedora / RHEL**
```bash
sudo dnf install webkit2gtk4.1-devel openssl-devel curl wget file libappindicator-gtk3-devel librsvg2-devel libxdo-devel git cmake ffmpeg-free SDL2-devel
sudo dnf group install "c-development"
```

**openSUSE**
```bash
sudo zypper in webkit2gtk3-devel libopenssl-devel curl wget file libappindicator3-1 librsvg-devel git cmake ffmpeg libSDL2-devel
sudo zypper in -t pattern devel_basis
```

## 2. Rust

```bash
sudo apt remove rustc cargo    # Ubuntu only, if Rust came from apt
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
rustup show                    # installs the toolchain from rust-toolchain.toml
cargo --version
```

## 3. Node + TypeScript

```bash
nvm install && nvm use         # reads .nvmrc
curl -fsSL https://bun.sh/install | bash
bun install
bunx tsc --noEmit
```

## 4. Tauri

```bash
bun run tauri dev              # dev with hot reload
bun run tauri build            # .deb / .rpm / AppImage in src-tauri/target/release/bundle
```

> Prefer `./dev.sh`: it clears the env vars Snap VS Code's terminal injects, which otherwise crash the app (`libpthread ... __libc_pthread_init`).

## 5. Whisper (pt-BR, CUDA)

**CUDA toolkit**

**Debian / Ubuntu**
```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb && sudo apt update
sudo apt install cuda-toolkit    # not Ubuntu's nvidia-cuda-toolkit (too old for gcc 13)
```

**Arch / Manjaro**
```bash
sudo pacman -S cuda              # installs to /opt/cuda
```

**Fedora / RHEL**
```bash
sudo dnf config-manager addrepo --from-repofile=https://developer.download.nvidia.com/compute/cuda/repos/fedora42/x86_64/cuda-fedora42.repo
sudo dnf install cuda-toolkit
```

**openSUSE**
```bash
sudo zypper addrepo https://developer.download.nvidia.com/compute/cuda/repos/opensuse15/x86_64/cuda-opensuse15.repo
sudo zypper refresh && sudo zypper install cuda-toolkit
```

**Build whisper.cpp + download models** (`large-v3` and `large-v3-turbo`, about 5 GB)
```bash
/usr/local/cuda/bin/nvcc --version
./scripts/setup-whisper.sh
NVCC=/opt/cuda/bin/nvcc ./scripts/setup-whisper.sh    # Arch
```

> Not an RTX 30xx? Set `CUDA_ARCH` in the script (`"native"` detects the GPU).

> Already set up for mini-deck? Nothing to do, mini-whisp reads the same `~/.local/share/creator-tools/`. Only `whisper-stream` and `large-v3-turbo` are used.

## 6. Run

```bash
./dev.sh                       # bun run tauri dev, minus snap env vars and a stale Cargo cache
```

- ● starts listening (Portuguese), ■ stops. The countdown shows the time left.
- The waveform is the mic level from a parallel `pw-record` on the same source whisper hears (`casanova_mic` when present, otherwise the default mic).
- ⚙ picks the max duration: 30 s, 15 min or 60 min.

## Where things live

| What | Path |
|---|---|
| whisper.cpp + models | `~/.local/share/creator-tools/` (not in git) |
| App config (duration) | `~/.config/com.mini-whisp/config.json` |
| Transcripts | `transcripts/<timestamp>.csv` + `.txt` (git-ignored) |
