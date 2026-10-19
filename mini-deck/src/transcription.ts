import { useCallback, useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

type WhisperStatus = { installed: boolean; missing: string[] };
type LiveState = {
  state: "loading" | "listening" | "stopped";
  error: string | null;
  limitSecs: number | null;
  csv: string | null;
};

export type LivePhase = "off" | "loading" | "listening";

export function useLiveTranscription() {
  const [installed, setInstalled] = useState<boolean | null>(null);
  const [phase, setPhase] = useState<LivePhase>("off");
  const [lines, setLines] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);
  const [savedCsv, setSavedCsv] = useState<string | null>(null);

  useEffect(() => {
    invoke<WhisperStatus>("whisper_status").then((s) => {
      setInstalled(s.installed);
      if (!s.installed) invoke("log", { message: `Whisper missing: ${s.missing.join(", ")}` });
    });

    const unlistenState = listen<LiveState>("live-state", (e) => {
      const { state, error, limitSecs, csv } = e.payload;
      setPhase(state === "stopped" ? "off" : state);
      if (error) setError(error);
      if (limitSecs) setSecondsLeft(limitSecs);
      if (state === "stopped") {
        setSecondsLeft(null);
        setSavedCsv(csv);
      }
    });
    const unlistenText = listen<string[]>("live-transcript", (e) => setLines(e.payload));

    return () => {
      unlistenState.then((fn) => fn());
      unlistenText.then((fn) => fn());
      invoke("stop_live_transcription");
    };
  }, []);

  useEffect(() => {
    if (phase !== "listening" || secondsLeft === null || secondsLeft <= 0) return;
    const tick = window.setTimeout(() => setSecondsLeft((s) => (s === null ? s : s - 1)), 1000);
    return () => window.clearTimeout(tick);
  }, [phase, secondsLeft]);

  const start = useCallback(async (limitSecs: number) => {
    setLines([]);
    setError(null);
    setSavedCsv(null);
    setPhase("loading");
    try {
      await invoke("start_live_transcription", { limitSecs });
    } catch (e) {
      setError(String(e));
      setPhase("off");
    }
  }, []);

  const stop = useCallback(async () => {
    await invoke("stop_live_transcription");
    setPhase("off");
  }, []);

  const toggle = useCallback(
    (limitSecs: number) => (phase === "off" ? start(limitSecs) : stop()),
    [phase, start, stop],
  );

  return { installed, phase, lines, error, secondsLeft, savedCsv, toggle, stop };
}
