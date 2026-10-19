import { invoke } from "@tauri-apps/api/core";
import { Window } from "@tauri-apps/api/window";
import { useObs } from "./obs";
import { Icon, type IconName } from "./icons";
import "./App.css";

type Button = { name: IconName; label: string };

const buttons: Button[] = [
  { name: "record", label: "Record" },
  { name: "pause", label: "Pause" },
  { name: "mark", label: "Mark" },
  { name: "mic", label: "Mic mute" },
  { name: "scene", label: "Scene" },
  { name: "clip", label: "Clip last 30s" },
  { name: "images", label: "Search images" },
  { name: "settings", label: "Settings" },
];

function ProgressRing({ percent }: { percent: number }) {
  const r = 28;
  const circumference = 2 * Math.PI * r;
  return (
    <svg className="progress-ring" viewBox="0 0 64 64">
      <title>{`Transcribing ${percent}%`}</title>
      <circle cx="32" cy="32" r={r} />
      <circle
        className="value"
        cx="32"
        cy="32"
        r={r}
        strokeDasharray={circumference}
        strokeDashoffset={circumference * (1 - percent / 100)}
      />
    </svg>
  );
}

async function openWindow(label: string) {
  const win = await Window.getByLabel(label);
  if (!win) return;
  await win.show();
  await win.setFocus();
}

function App() {
  const obs = useObs();

  const actions: Partial<Record<IconName, () => void>> = {
    record: obs.toggleRecord,
    pause: obs.togglePause,
    mark: obs.addMark,
    mic: obs.toggleMic,
    scene: () => invoke("log", { message: "Scene" }),
    clip: () => invoke("log", { message: "Clip last 30s" }),
    images: () => openWindow("images"),
    settings: () => openWindow("panel"),
  };

  const disabled: Partial<Record<IconName, boolean>> = {
    record: !obs.connected,
    pause: !obs.recording,
    mark: !obs.recording,
    mic: !obs.connected,
  };

  const active: Partial<Record<IconName, boolean>> = {
    record: obs.recording && !obs.paused,
    pause: obs.paused,
    mic: obs.micMuted,
  };

  return (
    <nav className="menu">
      <div className="grip" data-tauri-drag-region title="Drag">
        <Icon name="grip" />
      </div>
      {buttons.map((btn: Button) => (
        <button
          key={btn.name}
          className={`${btn.name}${active[btn.name] ? " active" : ""}`}
          title={btn.label}
          disabled={disabled[btn.name]}
          onClick={actions[btn.name]}
        >
          <Icon name={btn.name} />
          {btn.name === "mark" && obs.marks.length > 0 && <span className="badge">{obs.marks.length}</span>}
          {btn.name === "settings" && obs.transcribing !== null && (
            <ProgressRing percent={obs.transcribing} />
          )}
        </button>
      ))}
    </nav>
  );
}

export default App;
