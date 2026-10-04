mod config;
mod obs_pull;
mod whisper;

#[tauri::command]
fn log(message: &str) {
    println!("[ui] {message}");
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(whisper::LiveTranscription::default())
        .invoke_handler(tauri::generate_handler![
            log,
            config::get_config,
            config::set_config,
            obs_pull::pull_obs_config,
            whisper::whisper_status,
            whisper::start_live_transcription,
            whisper::stop_live_transcription,
            whisper::transcribe_file
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
