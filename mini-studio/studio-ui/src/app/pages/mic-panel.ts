import { Component, OnInit, computed, inject, input, signal } from '@angular/core';

import { Api } from '../core/api';
import { Job } from '../core/models';
import { Confirm } from '../shared/confirm-dialog';
import { Icon } from '../shared/icon';
import { JobProgress } from '../shared/job-progress';
import { Toast } from '../shared/toast';

type Preset = 'studio' | 'basic';
interface MicStatus {
  installed: boolean; running: boolean; rnnoise: boolean; deepfilter: boolean; preset: Preset | null;
  vad: number | null; denoise: number | null; makeup: number | null; gate?: number | null; notch?: number[];  // missing from a server started before they existed
  raw_source: string | null; raw_source_name: string | null; default_source: string; is_default: boolean;
  mic: string | null; sources: { name: string; description: string }[];
}
interface Check { key: string; title: string; ok: boolean; detail: string; effect: string; }
interface InstallOptions {
  preset?: Preset; vad?: number; denoise?: number; makeup?: number; gate?: number; notch?: number[];
  mic?: string | null; default?: boolean;
}

const CHAINS: Record<Preset, string> = {
  studio: 'DeepFilterNet (AI noise + room-echo removal) → hiss gate → high-pass 100 Hz → notch (hum) → EQ (warmth, −3 dB boxiness, +2.5 dB presence) → low-pass 14 kHz → input gain → leveler 2.5:1 → peak compressor 4:1 → limiter −1 dB',
  basic: 'RNNoise → high-pass 80 Hz → notch (hum) → EQ (−3 dB 300 Hz, +3 dB 3.5 kHz) → compressor 3:1 → limiter −1 dB',
};
interface MicResult {
  checks: Check[]; seconds: number;
  suggestion: { preset: Preset; vad: number; denoise: number; makeup: number; gate?: number; notch?: number[]; command: string } | null;
  metrics: { raw: { noise: number; peak: number; speech: number | null }; clean: { noise: number; peak: number; speech: number | null } };
  levels: { raw: number[]; clean: number[] };
  raw_issues?: { tones: number[]; dropouts: number };
}
interface WhisperText { text: string; words: number; seconds: number; }
interface WhisperResult { model: string; raw: WhisperText; clean: WhisperText; }

const SECONDS = 10;
const QUIET = 3; // last seconds: stay quiet so the background noise can be measured

/** Settings card: CASA NOVA Mic status, a 10 s test that checks every effect, and one-click tuning. */
@Component({
  selector: 'app-mic-panel',
  imports: [Icon, JobProgress],
  template: `
    <section class="card" id="mic">
      <div class="card-head">
        <h2>Microphone</h2>
        @if (status(); as s) {
          <span class="chip" [class.uploaded]="s.running" [class.recording]="!s.running">{{ s.running ? 'CASA NOVA Mic on' : 'not installed' }}</span>
        }
      </div>

      @if (status(); as s) {
        <div class="pick">
          <label class="field preset"><span>Sound</span>
            <select (change)="pickedPreset.set($any($event.target).value)">
              <option value="studio" [selected]="(pickedPreset() ?? s.preset ?? 'studio') === 'studio'">Studio (best quality)</option>
              <option value="basic" [selected]="(pickedPreset() ?? s.preset) === 'basic'">Basic (lighter on CPU)</option>
            </select></label>
          <label class="field grow"><span>Microphone the effects listen to</span>
            <select (change)="picked.set($any($event.target).value)">
              @for (m of s.sources; track m.name) {
                <option [value]="m.name" [selected]="m.name === (picked() ?? s.raw_source)">{{ m.description }}</option>
              }
            </select></label>
          <label class="check"><input type="checkbox" [checked]="makeDefault()" (change)="makeDefault.set($any($event.target).checked)" />
            Make CASA NOVA Mic the default input</label>
          <button class="btn btn-secondary" [disabled]="busy() || !pickChanged()" (click)="applyMic()">Apply</button>
        </div>
        @if (s.running) {
          <p class="muted small info">
            <b>{{ s.preset === 'studio' ? 'Studio' : 'Basic' }}</b> sound from <b>{{ s.raw_source_name || s.raw_source || '?' }}</b>{{ s.is_default ? ' · default input' : '' }} ·
            @if (s.preset === 'studio') { noise removal up to <b>{{ s.denoise }} dB</b> · hiss gate <b>{{ s.gate }} dB</b> · input gain <b>{{ s.makeup }} dB</b> }
            @else { noise gate (VAD) <b>{{ s.vad }}%</b> · makeup gain <b>{{ s.makeup }} dB</b> } ·
            @if (s.notch?.length) { notch <b>{{ hz(s.notch!) }}</b> · }
            chain: {{ chain(s.preset) }}.
            In OBS / Discord choose <b>"CASA NOVA Mic"</b> as the input.
          </p>
        } @else {
          <div class="callout warn">The CASA NOVA Mic (noise suppression + EQ + compressor + limiter) isn't installed.
            <div class="row act"><button class="btn btn-primary btn-sm" [disabled]="busy()" (click)="applyMic()">
              <app-icon name="mic" [size]="16" /> Install CASA NOVA Mic</button></div></div>
        }
      }

      @if (status()?.running) {
        <div class="tester">
          @if (phase(); as ph) {
            <div class="live" [class.quiet]="ph.quiet">
              <span class="count">{{ ph.left }}</span>
              <span class="what">{{ ph.text }}</span>
            </div>
          } @else {
            <div class="how">
              <b>Test it:</b> click, then <b>talk normally for ~{{ SECONDS - QUIET }} seconds</b> (like in a video, some loud, some soft),
              and <b>stay quiet for the last {{ QUIET }} seconds</b> so the background noise can be measured.
            </div>
            <button class="btn btn-primary" [disabled]="busy()" (click)="test()"><app-icon name="mic" /> Test microphone ({{ SECONDS }} s)</button>
          }
        </div>
        <app-job-progress [job]="installJob()" />
        @if (testJob()?.status === 'error') { <app-job-progress [job]="testJob()" /> }
      }

      @if (result(); as r) {
        <div class="results">
          <div class="checks">
            <h3>Effects check <span class="muted small">{{ passed() }}/{{ r.checks.length }} OK</span></h3>
            @for (c of r.checks; track c.key) {
              <div class="check-row" [class.bad]="!c.ok">
                <span class="mark">@if (c.ok) { <app-icon name="check" [size]="16" [stroke]="3" /> } @else { <app-icon name="alert" [size]="16" /> }</span>
                <div class="grow"><b>{{ c.title }}</b><p class="muted small">{{ c.detail }}</p></div>
                <span class="tag">{{ c.effect }}</span>
              </div>
            }
            @if (r.suggestion; as sg) {
              <div class="callout warn sugg">
                <b>Suggested tuning:</b>
                @if (sg.preset === 'studio') { noise removal {{ sg.denoise }} dB · hiss gate {{ sg.gate }} dB · input gain {{ sg.makeup }} dB }
                @else { noise gate {{ sg.vad }}% · makeup gain {{ sg.makeup }} dB }
                @if (sg.notch?.length) { · notch {{ hz(sg.notch!) }} }
                <div class="row act">
                  <button class="btn btn-primary btn-sm" [disabled]="busy()"
                          (click)="install({ preset: sg.preset, vad: sg.vad, denoise: sg.denoise, makeup: sg.makeup,
                                             gate: sg.gate, notch: sg.notch })">Apply (restarts audio)</button>
                  <code class="small">{{ sg.command }}</code>
                </div>
              </div>
            }
            @if (r.raw_issues; as ri) { @if (ri.tones.length || ri.dropouts) {
              <div class="callout warn sugg">
                <b>The raw mic itself has {{ ri.tones.length ? 'a hum / whine (' + hz(ri.tones) + ')' : '' }}{{
                  ri.tones.length && ri.dropouts ? ' and ' : '' }}{{ ri.dropouts ? 'gaps' : '' }}.</b>
                The filters can only hide part of it; fix it at the source:
                <ul>
                  <li>Unplug the laptop charger and test again (a hum that disappears = ground loop).</li>
                  <li>Plug the camera into another USB port, directly (no hub or long extension).</li>
                  <li>On the DJI Pocket 3, check whether it uses the built-in mic or a DJI Mic, and keep it close to your mouth:
                    over USB its gain can't be changed, so a quiet voice brings its hiss up with it.</li>
                </ul>
              </div>
            } }
          </div>

          <div class="listen">
            <h3>Listen and compare</h3>
            <svg class="chart" viewBox="0 0 600 140" preserveAspectRatio="none" aria-label="Levels over time">
              <rect x="0" [attr.y]="y(-12)" width="600" [attr.height]="y(-24) - y(-12)" class="target" />
              <line x1="0" x2="600" [attr.y1]="y(-1)" [attr.y2]="y(-1)" class="limit" />
              <polyline [attr.points]="points(r.levels.raw)" class="raw" />
              <polyline [attr.points]="points(r.levels.clean)" class="clean" />
            </svg>
            <div class="legend small muted">
              <span><i class="sw raw"></i> raw mic</span><span><i class="sw clean"></i> CASA NOVA Mic</span>
              <span><i class="sw target"></i> good voice level</span><span><i class="sw limit"></i> limiter −1 dB</span>
            </div>
            <div class="players">
              <label class="small"><b>Raw mic</b><audio controls [src]="'/api/mic/files/raw.wav?v=' + stamp()"></audio></label>
              <label class="small"><b>CASA NOVA Mic</b><audio controls [src]="'/api/mic/files/clean.wav?v=' + stamp()"></audio></label>
            </div>
            <p class="muted small">Use headphones when comparing, so the speakers don't feed back into the mic.</p>
          </div>
        </div>

        <div class="whisper">
          <div class="row">
            <h3 class="grow">Whisper test <span class="muted small">what the subtitles would say</span></h3>
            <button class="btn btn-secondary btn-sm" [disabled]="busy()" (click)="transcribe()">
              <app-icon name="mic" [size]="16" /> Transcribe with {{ whisperModel() }}</button>
          </div>
          <app-job-progress [job]="whisperJob()" />
          @if (whisper(); as w) {
            <div class="texts">
              <div><b class="small">Raw mic</b> <span class="muted small">{{ w.raw.words }} words · {{ w.raw.seconds }} s</span>
                <p class="said">{{ w.raw.text || '(nothing understood)' }}</p></div>
              <div><b class="small">CASA NOVA Mic</b> <span class="muted small">{{ w.clean.words }} words · {{ w.clean.seconds }} s</span>
                <p class="said">{{ w.clean.text || '(nothing understood)' }}</p></div>
            </div>
            <p class="muted small">Model <b>{{ w.model }}</b>. Change it in "Whisper model" above to compare (no need to save).</p>
          }
        </div>
      }
    </section>
  `,
  styles: `
    .info { margin-bottom: 14px; } .act { margin-top: 10px; }
    .pick { display: flex; gap: 14px; align-items: end; flex-wrap: wrap; margin-bottom: 12px; }
    .pick .field { min-width: 260px; } .pick .field.preset { min-width: 200px; } .pick .check { margin-bottom: 10px; }
    .tester { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; padding: 14px; border-radius: var(--r);
              background: var(--page); border: 1px solid var(--line); }
    .how { flex: 1; min-width: 260px; font-size: 14px; }
    .live { display: flex; align-items: center; gap: 16px; }
    .count { width: 64px; height: 64px; border-radius: 50%; display: grid; place-items: center; font-size: 28px; font-weight: 900;
             color: #fff; background: #e11d48; box-shadow: 0 0 0 6px rgba(225,29,72,.18); animation: pulse 1s infinite; }
    .live.quiet .count { background: var(--purple); box-shadow: 0 0 0 6px var(--accent-bg); animation: none; }
    .what { font-size: 18px; font-weight: 500; }
    @keyframes pulse { 50% { box-shadow: 0 0 0 12px rgba(225,29,72,.08); } }
    .results { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 24px; margin-top: 20px; }
    @media (max-width: 1000px) { .results { grid-template-columns: 1fr; } }
    h3 { margin-bottom: 10px; }
    .check-row { display: flex; gap: 10px; align-items: flex-start; padding: 9px 0; border-bottom: 1px solid var(--line); }
    .mark { width: 24px; height: 24px; border-radius: 50%; display: grid; place-items: center; flex: none;
            background: var(--ok-bg); color: var(--ok); }
    .bad .mark { background: var(--warn-bg); color: var(--warn); }
    .tag { font-size: 11px; font-weight: 500; color: var(--accent); background: var(--accent-bg); padding: 2px 8px;
           border-radius: 999px; white-space: nowrap; }
    .sugg { margin-top: 14px; } .sugg ul { margin: 6px 0 0 18px; } .sugg code { overflow-wrap: anywhere; }
    .chart { width: 100%; height: 140px; background: var(--page); border: 1px solid var(--line); border-radius: var(--r); }
    .chart polyline { fill: none; stroke-width: 1.6; vector-effect: non-scaling-stroke; }
    .chart .raw { stroke: #717171; } .chart .clean { stroke: var(--purple); stroke-width: 2; }
    .chart .target { fill: rgba(43, 166, 64, .14); } .chart .limit { stroke: var(--err); stroke-dasharray: 4 3; vector-effect: non-scaling-stroke; }
    .legend { display: flex; gap: 14px; flex-wrap: wrap; margin: 8px 0 14px; }
    .sw { display: inline-block; width: 14px; height: 4px; border-radius: 2px; vertical-align: middle; margin-right: 4px; }
    .sw.raw { background: #717171; } .sw.clean { background: var(--purple); } .sw.target { background: rgba(46,155,69,.35); height: 8px; }
    .sw.limit { background: var(--err); }
    .players { display: grid; gap: 10px; margin-bottom: 8px; } .players label { display: grid; gap: 4px; }
    audio { width: 100%; }
    .whisper { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--line); }
    .whisper h3 { margin: 0; }
    .texts { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 12px 0 8px; }
    @media (max-width: 1000px) { .texts { grid-template-columns: 1fr; } }
    .said { margin-top: 6px; padding: 10px 12px; background: var(--page); border: 1px solid var(--line); border-radius: var(--r); }
  `,
})
export class MicPanel implements OnInit {
  private api = inject(Api);
  private confirm = inject(Confirm);
  private toast = inject(Toast);
  /** Whisper model chosen on the Settings page (may be unsaved). */
  readonly whisperModel = input('small');
  readonly SECONDS = SECONDS;
  readonly QUIET = QUIET;
  readonly status = signal<MicStatus | null>(null);
  readonly testJob = signal<Job | undefined>(undefined);
  readonly installJob = signal<Job | undefined>(undefined);
  readonly result = signal<MicResult | null>(null);
  readonly whisperJob = signal<Job | undefined>(undefined);
  readonly whisper = signal<WhisperResult | null>(null);
  readonly stamp = signal(Date.now());
  readonly picked = signal<string | null>(null);   // microphone chosen in the dropdown (null = unchanged)
  readonly pickedPreset = signal<Preset | null>(null);
  readonly makeDefault = signal(true);
  readonly pickChanged = computed(() => {
    const s = this.status();
    return !!s && ((this.picked() ?? s.raw_source) !== s.mic || this.makeDefault() !== s.is_default || !s.running
                   || (this.pickedPreset() ?? s.preset) !== s.preset);
  });

  readonly busy = computed(() => [this.testJob(), this.installJob(), this.whisperJob()].some((j) => j && (j.status === 'queued' || j.status === 'running')));
  readonly passed = computed(() => this.result()?.checks.filter((c) => c.ok).length ?? 0);

  /** Countdown while recording: "talk now" first, "stay quiet" for the last seconds. */
  readonly phase = computed(() => {
    const j = this.testJob();
    if (!j || (j.status !== 'queued' && j.status !== 'running')) return null;
    if (j.message === 'analyzing') return { left: '…', text: 'Checking the effects…', quiet: true };
    const left = Math.max(1, Math.ceil(SECONDS * (1 - (j.progress ?? 0))));
    return left > QUIET ? { left, text: 'Talk now…', quiet: false } : { left, text: 'Now stay quiet…', quiet: true };
  });

  async ngOnInit() { await this.refresh(); }

  async refresh() {
    try {
      const s = await this.api.get<MicStatus>('/mic/status');
      this.status.set(s);
      this.picked.set(null);
      this.pickedPreset.set(null);
      this.makeDefault.set(s.running ? s.is_default : true);
    } catch { this.status.set(null); }
  }

  chain(preset: Preset | null) { return CHAINS[preset ?? 'studio']; }

  applyMic() {
    const s = this.status()!;
    return this.install({ preset: this.pickedPreset() ?? s.preset ?? 'studio', mic: this.picked() ?? s.raw_source,
                          default: this.makeDefault() });
  }

  async test() {
    this.result.set(null);
    this.whisper.set(null);
    const job = await this.api.post<Job>('/mic/test', { seconds: SECONDS });
    const done = await this.api.waitJob(job, (j) => this.testJob.set(j)).catch(() => null);
    if (done) {
      this.result.set(done.result);
      this.stamp.set(Date.now());
    }
  }

  async transcribe() {
    const job = await this.api.post<Job>('/mic/transcribe', { model: this.whisperModel() });
    const done = await this.api.waitJob(job, (j) => this.whisperJob.set(j)).catch(() => null);
    if (done) this.whisper.set(done.result);
  }

  async install(opts: InstallOptions) {
    const s = this.status();
    const name = s?.sources.find((m) => m.name === (opts.mic ?? s?.raw_source))?.description ?? 'current microphone';
    const preset = opts.preset ?? s?.preset ?? 'studio';
    const firstStudio = preset === 'studio' && !s?.deepfilter;
    const ok = await this.confirm.ask({
      title: 'Apply microphone settings?',
      message: `${preset === 'studio' ? 'Studio' : 'Basic'} sound · ${name}.\n` +
        (firstStudio ? 'The DeepFilterNet plugin (~50 MB) is downloaded first.\n' : '') +
        'PipeWire restarts, so all audio stops for about a second.',
      confirm: 'Apply',
    });
    if (!ok) return;
    const job = await this.api.post<Job>('/mic/install', opts);
    const done = await this.api.waitJob(job, (j) => this.installJob.set(j)).catch(() => null);
    await this.refresh();
    if (done) this.toast.show('Microphone updated. Test again to check.', 'ok');
  }

  hz(freqs: number[]) { return freqs.map((f) => `${Math.round(f)} Hz`).join(', '); }

  y(db: number) { return ((0 - Math.max(-80, Math.min(0, db))) / 80) * 140; }

  points(levels: number[]) {
    const n = Math.max(1, levels.length - 1);
    return levels.map((db, i) => `${((i / n) * 600).toFixed(1)},${this.y(db).toFixed(1)}`).join(' ');
  }
}
