import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { emit, listen } from "@tauri-apps/api/event";
import { getCurrentWindow, LogicalSize } from "@tauri-apps/api/window";
import type { Config } from "./obs";
import { Icon } from "./icons";
import { useLiveTranscription } from "./transcription";
import "./Panel.css";

const PANEL_WIDTH = 440;
const PANEL_HEIGHT = 511;
const TRANSCRIPT_HEIGHT = 160 + 12;

const durations = [
  { secs: 30, label: "30 s" },
  { secs: 900, label: "15 min" },
];

function formatCountdown(secs: number) {
  return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`;
}

const fields: { key: keyof Config; label: string; type?: string }[] = [
  { key: "obsUrl", label: "WebSocket URL" },
  { key: "obsPassword", label: "Password", type: "password" },
];

function Panel() {
  const [config, setConfig] = useState<Config | null>(null);
  const savedRef = useRef<Config | null>(null);
  const [audioInputs, setAudioInputs] = useState<string[]>([]);
  const [pullStatus, setPullStatus] = useState<string | null>(null);
  const live = useLiveTranscription();
  const transcriptRef = useRef<HTMLDivElement>(null);
  const liveOn = live.phase !== "off";

  useEffect(() => {
    invoke<Config>("get_config").then((c) => {
      savedRef.current = c;
      setConfig(c);
    });
    const unlisten = listen<string[]>("audio-inputs", (e) => setAudioInputs(e.payload));
    unlisten.then(() => emit("get-audio-inputs"));
    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  useEffect(() => {
    const height = PANEL_HEIGHT + (liveOn ? TRANSCRIPT_HEIGHT : 0);
    getCurrentWindow().setSize(new LogicalSize(PANEL_WIDTH, height));
  }, [liveOn]);

  useEffect(() => {
    const el = transcriptRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [live.lines]);

  if (!config) return null;

  async function save(next: Config) {
    if (JSON.stringify(next) === JSON.stringify(savedRef.current)) return;
    const obsChanged = (["obsUrl", "obsPassword", "micInput"] as const).some(
      (key) => next[key] !== savedRef.current?.[key],
    );
    savedRef.current = next;
    await invoke("set_config", { config: next });
    if (obsChanged) await emit("config-changed");
  }

  async function pullObsConfig() {
    try {
      setPullStatus(await invoke<string>("pull_obs_config"));
    } catch (e) {
      setPullStatus(String(e));
    }
    window.setTimeout(() => setPullStatus(null), 3000);
  }

  return (
    <div className="panel">
      <header data-tauri-drag-region>
        <h1 data-tauri-drag-region>Settings</h1>
        <button
          className="close"
          title="Close"
          onClick={async () => {
            await live.stop();
            await getCurrentWindow().hide();
          }}
        >
          <Icon name="close" />
        </button>
      </header>

      <div className="group">
        {fields.map((field) => (
          <label className="row" key={field.key}>
            <span>{field.label}</span>
            <input
              type={field.type ?? "text"}
              value={config[field.key]}
              spellCheck={false}
              onChange={(e) => setConfig({ ...config, [field.key]: e.target.value })}
              onBlur={() => save(config)}
              onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
            />
          </label>
        ))}
        <label className="row">
          <span>Mic input</span>
          <select
            value={config.micInput}
            onChange={(e) => {
              const next = { ...config, micInput: e.target.value };
              setConfig(next);
              save(next);
            }}
          >
            <option value="">Mic/Aux</option>
            {config.micInput && !audioInputs.includes(config.micInput) && (
              <option value={config.micInput}>{config.micInput}</option>
            )}
            {audioInputs
              .filter((name) => name !== "Mic/Aux")
              .map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
          </select>
        </label>
      </div>

      <div className="group">
        <label className="row">
          <span>Duration</span>
          <select
            value={config.liveLimitSecs}
            disabled={liveOn}
            onChange={(e) => {
              const next = { ...config, liveLimitSecs: Number(e.target.value) };
              setConfig(next);
              save(next);
            }}
          >
            {durations.map((d) => (
              <option key={d.secs} value={d.secs}>
                {d.label}
              </option>
            ))}
          </select>
        </label>
        <button
          className="row action"
          role="switch"
          aria-checked={liveOn}
          disabled={!live.installed}
          onClick={() => live.toggle(config.liveLimitSecs)}
        >
          <span>Test transcription</span>
          {live.installed === false && <span className="status">Not installed</span>}
          {live.installed && live.error && !liveOn && (
            <span className="status error" title={live.error}>
              {live.error}
            </span>
          )}
          {live.installed && !live.error && !liveOn && live.savedCsv && (
            <span className="status" title={live.savedCsv}>
              Saved {live.savedCsv.split("/").pop()}
            </span>
          )}
          {live.phase === "listening" && live.secondsLeft !== null && (
            <span className="status countdown">{formatCountdown(live.secondsLeft)}</span>
          )}
          {live.installed && <span className={`switch${liveOn ? " on" : ""}`} />}
        </button>
      </div>

      {liveOn && (
        <div className="transcript" ref={transcriptRef}>
          {live.lines.length === 0 ? (
            <p className="placeholder">
              {live.phase === "loading" ? "Loading model" : "Listening, speak in Portuguese"}
            </p>
          ) : (
            <p>
              {live.lines.slice(0, -1).join(" ")} <span className="latest">{live.lines[live.lines.length - 1]}</span>
            </p>
          )}
        </div>
      )}

      <div className="group">
        <button className="row action" disabled={pullStatus !== null} onClick={pullObsConfig}>
          <span>Pull OBS config</span>
          {pullStatus && <span className="status">{pullStatus}</span>}
        </button>
      </div>
    </div>
  );
}

export default Panel;
