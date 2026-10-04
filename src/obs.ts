import { useCallback, useEffect, useRef, useState } from "react";
import OBSWebSocket from "obs-websocket-js";
import { invoke } from "@tauri-apps/api/core";
import { emit, listen } from "@tauri-apps/api/event";

export type Config = {
  obsUrl: string;
  obsPassword: string;
  micInput: string;
};

export type Mark = { timecode: string; label: string };

const RETRY_MS = 3000;

const AUDIO_KIND = /audio|input_capture|output_capture|wasapi/;

export function useObs() {
  const obsRef = useRef<OBSWebSocket | null>(null);
  const micRef = useRef("");
  const [connected, setConnected] = useState(false);
  const [recording, setRecording] = useState(false);
  const [paused, setPaused] = useState(false);
  const [micMuted, setMicMuted] = useState(false);
  const [marks, setMarks] = useState<Mark[]>([]);
  const marksRef = useRef<Mark[]>([]);
  const [transcribing, setTranscribing] = useState<number | null>(null);

  useEffect(() => {
    const obs = new OBSWebSocket();
    obsRef.current = obs;
    let retry: number | undefined;
    let connecting = false;
    let stopped = false;

    function scheduleRetry() {
      window.clearTimeout(retry);
      if (!stopped) retry = window.setTimeout(connect, RETRY_MS);
    }

    async function connect() {
      if (connecting || stopped) return;
      connecting = true;
      try {
        const config = await invoke<Config>("get_config");
        if (stopped) return;
        await obs.connect(config.obsUrl, config.obsPassword || undefined);
        if (stopped) {
          obs.disconnect();
          return;
        }
        window.clearTimeout(retry);
        setConnected(true);
        await loadState(config);
      } catch (e) {
        invoke("log", { message: `OBS connect failed: ${e}` });
        scheduleRetry();
      } finally {
        connecting = false;
      }
    }

    async function sendAudioInputs() {
      if (!obs.identified) return emit("audio-inputs", []);
      const { inputs } = await obs.call("GetInputList");
      const names = inputs
        .filter((i) => AUDIO_KIND.test(String(i.unversionedInputKind)))
        .map((i) => String(i.inputName));
      await emit("audio-inputs", names);
    }

    async function loadState(config: Config) {
      sendAudioInputs();
      const status = await obs.call("GetRecordStatus");
      setRecording(status.outputActive);
      setPaused(status.outputPaused);

      const mic = config.micInput || (await obs.call("GetSpecialInputs")).mic1 || "";
      micRef.current = mic;
      if (mic) setMicMuted((await obs.call("GetInputMute", { inputName: mic })).inputMuted);
    }

    obs.on("ConnectionClosed", () => {
      setConnected(false);
      setRecording(false);
      setPaused(false);
      scheduleRetry();
    });

    obs.on("RecordStateChanged", (e) => {
      switch (e.outputState) {
        case "OBS_WEBSOCKET_OUTPUT_STARTED":
          marksRef.current = [];
          setMarks([]);
          setRecording(true);
          setPaused(false);
          break;
        case "OBS_WEBSOCKET_OUTPUT_STOPPED":
          setRecording(false);
          setPaused(false);
          invoke("log", { message: `Recording saved: ${e.outputPath}` });
          transcribe(e.outputPath);
          break;
        case "OBS_WEBSOCKET_OUTPUT_PAUSED":
          setPaused(true);
          break;
        case "OBS_WEBSOCKET_OUTPUT_RESUMED":
          setPaused(false);
          break;
      }
    });

    obs.on("InputMuteStateChanged", (e) => {
      if (e.inputName === micRef.current) setMicMuted(e.inputMuted);
    });

    async function transcribe(videoPath: string | null) {
      if (!videoPath) return;
      const status = await invoke<{ installed: boolean }>("whisper_status");
      if (!status.installed) return;
      try {
        const srt = await invoke<string>("transcribe_file", { videoPath });
        invoke("log", { message: `Transcript saved: ${srt}` });
      } catch (err) {
        invoke("log", { message: `Transcription failed: ${err}` });
      } finally {
        setTranscribing(null);
      }
    }

    const unlistenProgress = listen<{ percent: number }>("transcribe-progress", (e) =>
      setTranscribing(e.payload.percent),
    );

    const unlisten = listen("config-changed", () => obs.disconnect());
    const unlistenInputs = listen("get-audio-inputs", () => sendAudioInputs());

    connect();
    return () => {
      stopped = true;
      window.clearTimeout(retry);
      unlisten.then((fn) => fn());
      unlistenInputs.then((fn) => fn());
      unlistenProgress.then((fn) => fn());
      obs.disconnect();
    };
  }, []);

  const toggleRecord = useCallback(() => {
    obsRef.current?.call("ToggleRecord");
  }, []);

  const togglePause = useCallback(() => {
    obsRef.current?.call("ToggleRecordPause");
  }, []);

  const toggleMic = useCallback(() => {
    if (micRef.current) obsRef.current?.call("ToggleInputMute", { inputName: micRef.current });
  }, []);

  const addMark = useCallback(async () => {
    const obs = obsRef.current;
    if (!obs) return;
    const { outputTimecode } = await obs.call("GetRecordStatus");
    const mark = { timecode: outputTimecode, label: `Mark ${marksRef.current.length + 1}` };
    marksRef.current = [...marksRef.current, mark];
    setMarks(marksRef.current);
    invoke("log", { message: `${mark.timecode} ${mark.label}` });
  }, []);

  return {
    connected,
    recording,
    paused,
    micMuted,
    marks,
    transcribing,
    toggleRecord,
    togglePause,
    toggleMic,
    addMark,
  };
}
