use std::io::Read;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::{AppHandle, Emitter, Manager};

// whisper-stream reads the mic through SDL, so the waveform taps the same
// source with a parallel pw-record. 512 samples at 16 kHz is one level per 32 ms.
const RATE: &str = "16000";
const CHUNK_SAMPLES: usize = 512;
const FLOOR_DB: f64 = -60.0;

#[derive(Default)]
pub struct LevelMeter(Mutex<Option<Child>>);

fn level(rms: f64) -> f32 {
    let db = 20.0 * rms.max(1e-9).log10();
    ((db - FLOOR_DB) / -FLOOR_DB).clamp(0.0, 1.0) as f32
}

fn chunk_rms(bytes: &[u8]) -> f64 {
    let sum: f64 = bytes
        .chunks_exact(2)
        .map(|b| {
            let s = i16::from_le_bytes([b[0], b[1]]) as f64 / 32768.0;
            s * s
        })
        .sum();
    (sum / (bytes.len() / 2).max(1) as f64).sqrt()
}

pub fn start(app: &AppHandle, source: Option<&str>) {
    stop(app);
    let mut command = Command::new("pw-record");
    if let Some(source) = source {
        command.args(["--target", source]);
    }
    let spawned = command
        .args(["--format", "s16", "--rate", RATE, "--channels", "1", "-"])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn();
    let mut child = match spawned {
        Ok(child) => child,
        Err(e) => {
            eprintln!("[level] could not start pw-record: {e}");
            return;
        }
    };

    let mut stdout = child.stdout.take().unwrap();
    let reader_app = app.clone();
    std::thread::spawn(move || {
        let mut buf = [0u8; CHUNK_SAMPLES * 2];
        while stdout.read_exact(&mut buf).is_ok() {
            let _ = reader_app.emit("audio-level", level(chunk_rms(&buf)));
        }
    });

    *app.state::<LevelMeter>().0.lock().unwrap() = Some(child);
}

pub fn stop(app: &AppHandle) {
    if let Some(mut child) = app.state::<LevelMeter>().0.lock().unwrap().take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}

#[cfg(test)]
mod tests {
    use super::{chunk_rms, level};

    #[test]
    fn maps_decibels_to_unit_range() {
        assert_eq!(level(0.0), 0.0);
        assert_eq!(level(1.0), 1.0);
        assert!((level(0.001) - 0.0).abs() < 1e-6);
        assert!((level(0.0316) - 0.5).abs() < 0.01);
    }

    #[test]
    fn computes_rms_of_s16le() {
        let full: Vec<u8> = [i16::MAX, i16::MIN]
            .iter()
            .flat_map(|s| s.to_le_bytes())
            .collect();
        assert!((chunk_rms(&full) - 1.0).abs() < 1e-3);
        assert_eq!(chunk_rms(&[0, 0, 0, 0]), 0.0);
    }
}
