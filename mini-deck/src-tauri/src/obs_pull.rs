pub const OBS_CONFIG_REPO: &str = "https://github.com/OWNER/REPO";

#[tauri::command]
pub fn pull_obs_config() -> Result<String, String> {
    println!("[obs-pull] requested, repo: {OBS_CONFIG_REPO}");
    Err("OBS config pull is not implemented".into())
}
