export type Status = 'new' | 'editing' | 'uploaded' | 'recording';
export type Box = [number, number, number, number]; // x, y, w, h in video pixels

export interface Recording {
  name: string;
  project: string;
  status: Status;
  size: number;
  mtime: number;
  duration: number | null;
  elsewhere?: string[];  // other channels that already have a project for this recording
}

export interface UploadResult {
  id: string;
  url: string;
  studio: string;
  scheduled: string | null;
}

export interface ShortClip {
  n: number;
  start: number;
  end: number;
  face: Box | null;
  game: Box | null;
  title: string;
  captions: boolean;
  rendered: boolean;
  file: string | null;
  upload: (PublishFields & { result: UploadResult }) | null;
}

export interface PublishFields {
  title: string;
  description: string;
  tags: string;
  privacy: 'private' | 'unlisted' | 'public';
  schedule: string | null; // "YYYY-MM-DD HH:MM" local time
  playlist: string;
}

export interface Project {
  id: string;
  file: string;
  name: string;
  status: Status;
  duration: number | null;
  subtitles: { enabled: boolean; model: string; done: boolean };
  shorts: ShortClip[];
  cutout: { done: boolean };
  thumbnail: { title: string; subtitle?: string; color: string | null; rendered: string[]; template: string | null;
               news?: NewsItem[] };
  publish: PublishFields & { include_subtitles: boolean; result: UploadResult | null };
  files: { person: string | null; bg: string | null; art: string | null; art2: string | null;
           cutout: boolean; thumb: boolean; srt: boolean };
  jobs: Job[];
}

export interface Job {
  id: string;
  kind: string;
  project: string | null;
  status: 'queued' | 'running' | 'done' | 'error';
  progress: number | null;
  message: string;
  log: string[];
  result: any;
  error: string | null;
}

export interface Cue { start: number; end: number; text: string; }

export interface TemplateInfo { name: string; description: string; color: string | null; max_chars: number | null; family: string;
  needs: string[]; }
export interface TemplateFamily { id: string; label: string; }

/** A news item for the collage magazines + the picture Claude Code found for it (in news/) and its cover text. */
export interface NewsItem { text: string; file: string | null; title?: string; }

export interface Settings {
  watch_folder: string;
  privacy: string;
  publish_time: string;
  description_template: string;
  tags: string;
  whisper_model: string;
}

export function fmtTime(s: number | null | undefined): string {
  if (s == null) return '–';
  const m = Math.floor(s / 60), sec = s - m * 60;
  const h = Math.floor(m / 60);
  const mm = h ? String(m % 60).padStart(2, '0') : String(m);
  return (h ? h + ':' : '') + mm + ':' + sec.toFixed(1).padStart(4, '0');
}

export function fmtSize(bytes: number): string {
  const u = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  while (bytes >= 1024 && i < u.length - 1) { bytes /= 1024; i++; }
  return bytes.toFixed(i > 1 ? 1 : 0) + ' ' + u[i];
}

/** The channel's library (reused across projects): saved photos with their cutout, and custom thumbnail colors. */
export interface Library { photos: { id: string; photo: string | null }[]; colors: string[]; current: string | null; }
