use serde::Serialize;
use std::fs::File;
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::{AppHandle, Emitter, Manager, State};

const LANGUAGE: &str = "pt";
const THREADS: &str = "8";
const FILE_MODEL: &str = "ggml-large-v3.bin";
const LIVE_MODEL: &str = "ggml-large-v3-turbo.bin";

struct Paths {
    cli: PathBuf,
    stream: PathBuf,
    models: PathBuf,
}

fn paths(app: &AppHandle) -> Result<Paths, String> {
    let base = app
        .path()
        .home_dir()
        .map_err(|e| e.to_string())?
        .join(".local/share/creator-tools");
    let bin = base.join("whisper.cpp/build/bin");
    Ok(Paths {
        cli: bin.join("whisper-cli"),
        stream: bin.join("whisper-stream"),
        models: base.join("models"),
    })
}

#[derive(Serialize)]
pub struct WhisperStatus {
    installed: bool,
    missing: Vec<String>,
}

#[tauri::command]
pub fn whisper_status(app: AppHandle) -> Result<WhisperStatus, String> {
    let p = paths(&app)?;
    let required = [
        p.cli.clone(),
        p.stream.clone(),
        p.models.join(FILE_MODEL),
        p.models.join(LIVE_MODEL),
    ];
    let missing: Vec<String> = required
        .iter()
        .filter(|path| !path.exists())
        .map(|path| path.display().to_string())
        .collect();
    Ok(WhisperStatus {
        installed: missing.is_empty(),
        missing,
    })
}

#[derive(Default)]
pub struct LiveTranscription(Mutex<Option<Child>>);

const LIVE_LIMIT_SECS: u64 = 30;

#[derive(Serialize, Clone, Default)]
#[serde(rename_all = "camelCase")]
struct LiveState {
    state: &'static str,
    error: Option<String>,
    limit_secs: Option<u64>,
    csv: Option<String>,
}

fn emit_state(app: &AppHandle, state: LiveState) {
    let _ = app.emit("live-state", state);
}

fn stop_after_limit(app: AppHandle, pid: u32) {
    std::thread::spawn(move || {
        std::thread::sleep(std::time::Duration::from_secs(LIVE_LIMIT_SECS));
        let live = app.state::<LiveTranscription>();
        let mut slot = live.0.lock().unwrap();
        if slot.as_ref().is_some_and(|c| c.id() == pid) {
            let mut child = slot.take().unwrap();
            let _ = child.kill();
            let _ = child.wait();
        }
    });
}

fn strip_ansi(line: &str) -> String {
    let mut out = String::with_capacity(line.len());
    let mut chars = line.chars();
    while let Some(c) = chars.next() {
        if c == '\x1b' {
            for c in chars.by_ref() {
                if c.is_ascii_alphabetic() {
                    break;
                }
            }
        } else {
            out.push(c);
        }
    }
    out
}

fn end_sentence(text: &str) -> String {
    let text = text.trim_end_matches([',', ';', ':', ' ']);
    if text.ends_with(['.', '!', '?', '…']) {
        text.to_string()
    } else {
        format!("{text}.")
    }
}

fn capitalize(text: &str) -> String {
    let mut chars = text.chars();
    match chars.next() {
        Some(c) => c.to_uppercase().chain(chars).collect(),
        None => String::new(),
    }
}

fn parse_timestamp(stamp: &str) -> Option<i64> {
    let (hms, ms) = stamp.trim().split_once('.')?;
    let mut parts = hms.split(':').map(|p| p.parse::<i64>().ok());
    let (h, m, sec) = (parts.next()??, parts.next()??, parts.next()??);
    Some(((h * 60 + m) * 60 + sec) * 1000 + ms.parse::<i64>().ok()?)
}

#[derive(Default)]
struct StreamParser {
    block_start: i64,
    block: Vec<Segment>,
    shown: Vec<Segment>,
}

struct Segment {
    start: i64,
    end: i64,
    text: String,
}

impl StreamParser {
    fn parse(&mut self, line: &str) -> Option<Vec<String>> {
        let line = strip_ansi(line);
        let line = line.trim();

        if let Some(header) = line.strip_prefix("### Transcription") {
            if header.contains("START") {
                let t0 = header.split("t0 = ").nth(1)?.split_whitespace().next()?;
                self.block_start = t0.parse().ok()?;
                self.block.clear();
                return None;
            }
            if header.contains("END") {
                return self.commit_block();
            }
            return None;
        }

        let (stamp, text) = line.strip_prefix('[')?.split_once("]  ")?;
        let (from, to) = stamp.split_once(" --> ")?;
        let text = text.trim();
        let marker = (text.starts_with('[') && text.ends_with(']'))
            || (text.starts_with('(') && text.ends_with(')'));
        if !text.is_empty() && !marker {
            self.block.push(Segment {
                start: self.block_start + parse_timestamp(from)?,
                end: self.block_start + parse_timestamp(to)?,
                text: text.to_string(),
            });
        }
        None
    }

    fn to_csv(&self) -> String {
        let mut csv = String::from("start,end,text\n");
        for s in &self.shown {
            csv.push_str(&format!(
                "{},{},\"{}\"\n",
                s.start,
                s.end,
                s.text.replace('"', "\"\"")
            ));
        }
        csv
    }

    fn commit_block(&mut self) -> Option<Vec<String>> {
        let first = self.block.first()?.start;
        if let Some(seg) = self.block.first_mut() {
            seg.text = capitalize(&seg.text);
        }
        if let Some(seg) = self.block.last_mut() {
            seg.text = end_sentence(&seg.text);
        }
        self.shown.retain(|s| (s.start + s.end) / 2 < first);
        self.shown.append(&mut self.block);
        Some(self.shown.iter().map(|s| s.text.clone()).collect())
    }
}

fn wake_default_mic() {
    const SOURCE: &str = "@DEFAULT_AUDIO_SOURCE@";
    let muted = Command::new("wpctl")
        .args(["get-volume", SOURCE])
        .output()
        .map(|o| String::from_utf8_lossy(&o.stdout).contains("MUTED"))
        .unwrap_or(true);
    if muted {
        return;
    }
    let set_mute = |on: &str| {
        let _ = Command::new("wpctl")
            .args(["set-mute", SOURCE, on])
            .status();
    };
    set_mute("1");
    std::thread::sleep(std::time::Duration::from_millis(300));
    set_mute("0");
    println!("[whisper-stream] mic woken (muted and unmuted the default source)");
}

#[tauri::command]
pub fn start_live_transcription(
    app: AppHandle,
    live: State<LiveTranscription>,
) -> Result<(), String> {
    let mut slot = live.0.lock().unwrap();
    if slot.is_some() {
        return Ok(());
    }

    let p = paths(&app)?;
    let mut child = Command::new(&p.stream)
        .args(["-m", &p.models.join(LIVE_MODEL).to_string_lossy()])
        .args(["-l", LANGUAGE, "-t", THREADS])
        .args(["--step", "0", "--length", "8000", "-vth", "0.6"])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Could not start whisper-stream: {e}"))?;

    emit_state(
        &app,
        LiveState {
            state: "loading",
            ..Default::default()
        },
    );

    let log_dir = app.path().app_log_dir().map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&log_dir).map_err(|e| e.to_string())?;
    let log = std::sync::Arc::new(Mutex::new(
        File::create(log_dir.join("whisper-stream.log")).map_err(|e| e.to_string())?,
    ));

    let last_error = std::sync::Arc::new(Mutex::new(None::<String>));
    let stderr = child.stderr.take().unwrap();
    let stderr_error = last_error.clone();
    let stderr_log = log.clone();
    std::thread::spawn(move || {
        for line in BufReader::new(stderr).lines().map_while(Result::ok) {
            eprintln!("[whisper-stream] {line}");
            let _ = writeln!(stderr_log.lock().unwrap(), "{line}");
            let lower = line.to_lowercase();
            if lower.contains("error") || lower.contains("failed") {
                *stderr_error.lock().unwrap() = Some(line.trim().to_string());
            }
        }
    });

    let csv_dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("../transcripts");
    std::fs::create_dir_all(&csv_dir).map_err(|e| e.to_string())?;
    let csv_path = csv_dir.join(format!(
        "{}.csv",
        chrono::Local::now().format("%Y-%m-%d_%H-%M-%S")
    ));

    let pid = child.id();
    let stdout = child.stdout.take().unwrap();
    let reader_app = app.clone();
    std::thread::spawn(move || {
        let mut parser = StreamParser::default();
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            println!("[whisper-stream] {line}");
            let _ = writeln!(log.lock().unwrap(), "{line}");
            if line.contains("[Start speaking]") {
                wake_default_mic();
                stop_after_limit(reader_app.clone(), pid);
                emit_state(
                    &reader_app,
                    LiveState {
                        state: "listening",
                        limit_secs: Some(LIVE_LIMIT_SECS),
                        ..Default::default()
                    },
                );
            } else if let Some(lines) = parser.parse(&line) {
                let _ = reader_app.emit("live-transcript", lines);
                if let Err(e) = std::fs::write(&csv_path, parser.to_csv()) {
                    eprintln!(
                        "[whisper-stream] could not save {}: {e}",
                        csv_path.display()
                    );
                }
            }
        }
        if let Some(mut child) = reader_app
            .state::<LiveTranscription>()
            .0
            .lock()
            .unwrap()
            .take()
        {
            let _ = child.wait();
        }
        let error = last_error.lock().unwrap().take();
        let saved = csv_path.exists().then(|| csv_path.display().to_string());
        emit_state(
            &reader_app,
            LiveState {
                state: "stopped",
                error,
                csv: saved,
                ..Default::default()
            },
        );
    });

    *slot = Some(child);
    Ok(())
}

#[tauri::command]
pub fn stop_live_transcription(live: State<LiveTranscription>) {
    if let Some(mut child) = live.0.lock().unwrap().take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}

#[derive(Serialize, Clone)]
struct TranscribeProgress {
    path: String,
    percent: u32,
}

#[tauri::command]
pub async fn transcribe_file(app: AppHandle, video_path: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || transcribe_blocking(&app, &video_path))
        .await
        .map_err(|e| e.to_string())?
}

fn transcribe_blocking(app: &AppHandle, video_path: &str) -> Result<String, String> {
    let p = paths(app)?;
    let video = Path::new(video_path);
    let stem = video.with_extension("");
    let wav = std::env::temp_dir().join(format!(
        "creator-tools-{}.wav",
        stem.file_name().unwrap_or_default().to_string_lossy()
    ));

    let progress = |percent: u32| {
        let _ = app.emit(
            "transcribe-progress",
            TranscribeProgress {
                path: video_path.to_string(),
                percent,
            },
        );
    };
    progress(0);

    let status = Command::new("ffmpeg")
        .args(["-y", "-loglevel", "error", "-i", video_path])
        .args(["-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le"])
        .arg(&wav)
        .status()
        .map_err(|e| format!("Could not run ffmpeg: {e}"))?;
    if !status.success() {
        return Err("ffmpeg could not extract the audio".into());
    }

    let mut child = Command::new(&p.cli)
        .args(["-m", &p.models.join(FILE_MODEL).to_string_lossy()])
        .args([
            "-l", LANGUAGE, "-t", THREADS, "-pp", "-osrt", "-otxt", "-ocsv",
        ])
        .arg("-of")
        .arg(&stem)
        .arg(&wav)
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Could not start whisper-cli: {e}"))?;

    for line in BufReader::new(child.stderr.take().unwrap())
        .lines()
        .map_while(Result::ok)
    {
        if let Some(rest) = line.split("progress =").nth(1) {
            if let Ok(percent) = rest.trim().trim_end_matches('%').trim().parse() {
                progress(percent);
            }
        }
    }

    let status = child.wait().map_err(|e| e.to_string())?;
    let _ = std::fs::remove_file(&wav);
    if !status.success() {
        return Err("whisper-cli failed".into());
    }
    progress(100);
    Ok(stem.with_extension("srt").display().to_string())
}

#[cfg(test)]
mod tests {
    use super::StreamParser;

    fn parse_all(output: &str) -> Vec<String> {
        let mut parser = StreamParser::default();
        output
            .lines()
            .filter_map(|l| parser.parse(l))
            .last()
            .unwrap_or_default()
    }

    #[test]
    fn skips_markers_and_noise() {
        let out = parse_all(
            "[Start speaking]\n\
             ### Transcription 0 START | t0 = 0 ms | t1 = 8000 ms\n\
             [00:00:00.000 --> 00:00:02.000]  [BLANK_AUDIO]\n\
             [00:00:02.000 --> 00:00:04.000]  (música)\n\
             \x1b[2K[00:00:04.000 --> 00:00:06.000]   Olá, tudo bem?\n\
             ### Transcription 0 END",
        );
        assert_eq!(out, ["Olá, tudo bem?"]);
    }

    #[test]
    fn closes_each_block_as_a_sentence() {
        let out = parse_all(
            "### Transcription 0 START | t0 = 0 ms | t1 = 8000 ms
[00:00:00.000 --> 00:00:02.000]   isso daí aconteceu, eu não sei se
[00:00:02.000 --> 00:00:08.000]   pra aquecer, ou
### Transcription 0 END
### Transcription 1 START | t0 = 9000 ms | t1 = 17000 ms
[00:00:00.000 --> 00:00:03.000]   ficou muito bom
### Transcription 1 END
### Transcription 2 START | t0 = 18000 ms | t1 = 26000 ms
[00:00:00.000 --> 00:00:03.000]   Funciona?
### Transcription 2 END",
        );
        assert_eq!(
            out,
            [
                "Isso daí aconteceu, eu não sei se",
                "pra aquecer, ou.",
                "Ficou muito bom.",
                "Funciona?"
            ]
        );
    }

    #[test]
    fn saves_csv_like_whisper_cli() {
        let mut parser = StreamParser::default();
        for line in "### Transcription 0 START | t0 = 1000 ms | t1 = 9000 ms
[00:00:00.000 --> 00:00:02.500]   ele disse \"oi\", tudo bem
### Transcription 0 END"
            .lines()
        {
            parser.parse(line);
        }
        assert_eq!(
            parser.to_csv(),
            "start,end,text\n1000,3500,\"Ele disse \"\"oi\"\", tudo bem.\"\n"
        );
    }

    #[test]
    fn shows_overlapping_speech_once() {
        let out = parse_all(
            "### Transcription 3 START | t0 = 33994 ms | t1 = 41994 ms
[00:00:00.000 --> 00:00:04.000]   Ok, vamos ver se o script está funcionando agora
[00:00:04.000 --> 00:00:08.000]   Deveria, pelo menos deveria ter
### Transcription END
### Transcription 4 START | t0 = 37664 ms | t1 = 45664 ms
[00:00:00.000 --> 00:00:08.000]   funcionando agora, deveria, pelo menos deveria ter algo capturando, espero eu
### Transcription END
### Transcription 5 START | t0 = 40144 ms | t1 = 48144 ms
[00:00:00.000 --> 00:00:04.580]   Pelo menos deveria ter algo capturando, espero eu.
[00:00:05.660 --> 00:00:08.000]   Não estou vendo nada ser capturado.
### Transcription END
### Transcription 6 START | t0 = 45124 ms | t1 = 53124 ms
[00:00:00.000 --> 00:00:03.000]   Não estou vendo nada ser capturado
[00:00:03.000 --> 00:00:05.000]   Mas deveria
[00:00:05.000 --> 00:00:08.000]   Eu não estou vendo nada
### Transcription END
### Transcription 7 START | t0 = 47500 ms | t1 = 55500 ms
[00:00:00.000 --> 00:00:00.640]   Capturado
[00:00:00.640 --> 00:00:02.620]   Mas deveria
[00:00:02.620 --> 00:00:05.000]   Eu não estou vendo nada
[00:00:05.000 --> 00:00:08.000]   Ahn
### Transcription END
### Transcription 8 START | t0 = 49573 ms | t1 = 57573 ms
[00:00:00.000 --> 00:00:01.900]   deveria, eu não estou vendo
[00:00:01.900 --> 00:00:02.940]   nada
[00:00:02.940 --> 00:00:08.000]   eu não sei se o mic input está certo
### Transcription 8 END",
        );
        for line in &out {
            println!("{line}");
        }
        let repeated = out
            .iter()
            .filter(|l| l.contains("vendo nada ser capturado"))
            .count();
        assert!(repeated <= 1, "repeated {repeated} times");
        assert_eq!(out.last().unwrap(), "eu não sei se o mic input está certo.");
    }
}
