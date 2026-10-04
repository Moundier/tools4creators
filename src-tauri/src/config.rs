use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use tauri::{AppHandle, Manager};

#[derive(Serialize, Deserialize, Clone)]
#[serde(default, rename_all = "camelCase")]
pub struct Config {
    pub obs_url: String,
    pub obs_password: String,
    pub mic_input: String,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            obs_url: "ws://127.0.0.1:4455".into(),
            obs_password: String::new(),
            mic_input: String::new(),
        }
    }
}

fn config_path(app: &AppHandle) -> Result<PathBuf, String> {
    let dir = app.path().app_config_dir().map_err(|e| e.to_string())?;
    Ok(dir.join("config.json"))
}

#[tauri::command]
pub fn get_config(app: AppHandle) -> Result<Config, String> {
    let path = config_path(&app)?;
    match fs::read_to_string(&path) {
        Ok(text) => serde_json::from_str(&text).map_err(|e| e.to_string()),
        Err(_) => Ok(Config::default()),
    }
}

#[tauri::command]
pub fn set_config(app: AppHandle, config: Config) -> Result<(), String> {
    let path = config_path(&app)?;
    fs::create_dir_all(path.parent().unwrap()).map_err(|e| e.to_string())?;
    let text = serde_json::to_string_pretty(&config).map_err(|e| e.to_string())?;
    fs::write(&path, text).map_err(|e| e.to_string())
}
