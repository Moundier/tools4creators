import { useEffect, useRef, type RefObject } from "react";
import { LEVEL_HISTORY, type LivePhase } from "./transcription";

const BAR_WIDTH = 3;
const MIN_BAR = 3;
const EASE = 0.35;

export function Waveform({ levelsRef, phase }: { levelsRef: RefObject<number[]>; phase: LivePhase }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const heights = new Array<number>(LEVEL_HISTORY).fill(0);
    let frame = 0;

    const draw = (time: number) => {
      const dpr = window.devicePixelRatio || 1;
      const { width, height } = canvas.getBoundingClientRect();
      if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
        canvas.width = width * dpr;
        canvas.height = height * dpr;
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = getComputedStyle(canvas).color;

      // Newest level on the right, older ones scroll left.
      const levels = levelsRef.current;
      const step = width / LEVEL_HISTORY;
      for (let i = 0; i < LEVEL_HISTORY; i++) {
        let target = 0;
        if (phase === "listening") {
          target = levels[levels.length - LEVEL_HISTORY + i] ?? 0;
        } else if (phase === "loading") {
          target = 0.12 + 0.1 * Math.sin(time / 180 - i / 3);
        }
        heights[i] += (target - heights[i]) * EASE;
        const h = Math.max(MIN_BAR, heights[i] * height);
        const x = i * step + (step - BAR_WIDTH) / 2;
        ctx.beginPath();
        ctx.roundRect(x, (height - h) / 2, BAR_WIDTH, h, BAR_WIDTH / 2);
        ctx.fill();
      }
      frame = requestAnimationFrame(draw);
    };
    frame = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frame);
  }, [levelsRef, phase]);

  return <canvas className={`waveform ${phase}`} ref={canvasRef} />;
}
