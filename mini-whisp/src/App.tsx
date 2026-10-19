import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { getCurrentWindow, LogicalSize } from "@tauri-apps/api/window";
import { Icon } from "./icons";
import { useLiveTranscription } from "./transcription";
import { Waveform } from "./Waveform";
import "./App.css";

type Config = { liveLimitSecs: number };

const durations = [
  { secs: 30, label: "30 s" },
  { secs: 900, label: "15 min" },
  { secs: 3600, label: "60 min" },
];

function formatCountdown(secs: number) {
  return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`;
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
}

function App() {
  const [config, setConfig] = useState<Config | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [copied, setCopied] = useState(false);
  const live = useLiveTranscription();
  const rootRef = useRef<HTMLDivElement>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const liveOn = live.phase !== "off";
  const showTranscript = liveOn || live.lines.length > 0 || live.error !== null;
  const ready = config !== null;

  useEffect(() => {
    invoke<Config>("get_config").then(setConfig);
  }, []);

  // Window is transparent, so size it to whatever the bar and sheets need.
  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    const observer = new ResizeObserver(() => {
      const { width, height } = el.getBoundingClientRect();
      getCurrentWindow().setSize(new LogicalSize(Math.ceil(width), Math.ceil(height)));
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [ready]);

  useEffect(() => {
    const el = transcriptRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [live.lines]);

  if (!config) return null;

  async function setDuration(liveLimitSecs: number) {
    const next = { liveLimitSecs };
    setConfig(next);
    await invoke("set_config", { config: next });
  }

  async function copy() {
    await copyText(live.lines.join(" "));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  let label: string | null = null;
  if (live.installed === false) label = "Not installed";
  else if (live.phase === "loading") label = "Loading";
  else if (live.phase === "listening" && live.secondsLeft !== null) label = formatCountdown(live.secondsLeft);

  return (
    <div className="app" ref={rootRef}>
      <nav className="menu">
        <div className="grip" data-tauri-drag-region title="Drag">
          <Icon name="grip" />
        </div>
        <button
          className={`record${liveOn ? " active" : ""}`}
          title={liveOn ? "Stop" : "Record"}
          disabled={!live.installed}
          onClick={() => live.toggle(config.liveLimitSecs)}
        >
          <Icon name={liveOn ? "stop" : "record"} />
        </button>
        <div className="wave" data-tauri-drag-region>
          <Waveform levelsRef={live.levelsRef} phase={live.phase} />
          {label && <span className="label">{label}</span>}
        </div>
        <button title="Copy transcript" disabled={live.lines.length === 0} onClick={copy}>
          <Icon name={copied ? "check" : "copy"} />
        </button>
        <button
          className={showSettings ? "active" : undefined}
          title="Settings"
          onClick={() => setShowSettings(!showSettings)}
        >
          <Icon name="settings" />
        </button>
        <button
          title="Close"
          onClick={async () => {
            await live.stop();
            await getCurrentWindow().close();
          }}
        >
          <Icon name="close" />
        </button>
      </nav>

      {showSettings && (
        <div className="sheet">
          <label className="row">
            <span>Duration</span>
            <select
              value={config.liveLimitSecs}
              disabled={liveOn}
              onChange={(e) => setDuration(Number(e.target.value))}
            >
              {durations.map((d) => (
                <option key={d.secs} value={d.secs}>
                  {d.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      {showTranscript && (
        <div className="sheet transcript" ref={transcriptRef}>
          {live.lines.length === 0 ? (
            <p className="placeholder">
              {live.phase === "loading" ? "Loading model" : liveOn ? "Listening, speak in Portuguese" : ""}
            </p>
          ) : (
            <p>
              {live.lines.slice(0, -1).join(" ")} <span className="latest">{live.lines[live.lines.length - 1]}</span>
            </p>
          )}
          {!liveOn && live.error && (
            <p className="status error" title={live.error}>
              {live.error}
            </p>
          )}
          {!liveOn && !live.error && live.savedCsv && (
            <p className="status" title={live.savedCsv}>
              Saved {live.savedCsv.split("/").pop()} + .txt
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
