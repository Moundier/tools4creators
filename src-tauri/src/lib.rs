#[tauri::command]
fn log(message: &str) {
    println!("[ui] {message}");
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![log])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
