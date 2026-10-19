import { Component, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { Api } from '../core/api';
import { Cue, fmtTime } from '../core/models';
import { ProjectStore } from '../core/project-store';
import { Icon } from '../shared/icon';
import { JobProgress } from '../shared/job-progress';
import { Toast } from '../shared/toast';

/** Optional: Whisper subtitles, editable before upload. */
@Component({
  selector: 'app-step-subtitles',
  imports: [FormsModule, Icon, JobProgress],
  template: `
    @if (store.project(); as p) {
      <section class="card">
        <div class="card-head">
          <label class="switch"><input type="checkbox" [checked]="p.subtitles.enabled"
                 (change)="store.patch({ subtitles: { enabled: $any($event.target).checked } })" />
            Generate subtitles for this video</label>
        </div>
        @if (p.subtitles.enabled) {
          <div class="row">
            <label class="field model"><span>Whisper model</span>
              <select [ngModel]="p.subtitles.model" (ngModelChange)="store.patch({ subtitles: { model: $event } })">
                <option value="small">small (fast)</option>
                <option value="medium">medium (more accurate)</option>
                <option value="large-v3">large-v3 (best, slow)</option>
              </select></label>
            <button class="btn gen" [class.btn-primary]="!cues().length" [class.btn-secondary]="cues().length"
                    [disabled]="store.busy('subtitles')" (click)="generate()">
              <app-icon name="captions" /> {{ p.files.srt ? 'Generate again' : 'Generate subtitles' }}</button>
          </div>
          <app-job-progress [job]="store.jobs()['subtitles']" />
        } @else {
          <p class="muted">Turn this on to transcribe the video with Whisper (runs on your computer). You can fix the text before
            uploading.</p>
        }
      </section>

      @if (p.subtitles.enabled && cues().length) {
        <section class="card cues-card">
          <div class="card-head"><h3>{{ cues().length }} subtitles <span class="muted small">· edit the text, then save</span></h3>
            <button class="btn btn-primary" (click)="save()"><app-icon name="save" /> Save subtitles</button></div>
          <div class="cues">
            @for (c of cues(); track $index) {
              <div class="cue">
                <div class="times">
                  <input class="inline-input" type="number" step="0.01" [(ngModel)]="c.start" title="start (s)" />
                  <input class="inline-input" type="number" step="0.01" [(ngModel)]="c.end" title="end (s)" />
                  <span class="muted small">{{ fmtTime(c.start) }}</span>
                </div>
                <textarea class="inline-input" rows="2" [(ngModel)]="c.text"></textarea>
                <button class="btn btn-icon btn-sm" title="Delete this subtitle" (click)="remove($index)"><app-icon name="trash" [size]="16" /></button>
              </div>
            }
          </div>
        </section>
      }
    }
  `,
  styles: `
    .row { align-items: end; } .model { width: 240px; } .gen { margin-bottom: 1px; }
    .cues-card { margin-top: 16px; }
    .cues { display: grid; gap: 8px; max-height: 60vh; overflow: auto; padding-right: 4px; }
    .cue { display: grid; grid-template-columns: 140px 1fr auto; gap: 12px; align-items: center; padding: 10px 12px;
           border: 1px solid var(--line); border-radius: var(--r); background: var(--page); }
    .times { display: grid; gap: 4px; min-width: 0; } .times input { width: 100%; }
    textarea { width: 100%; resize: vertical; min-width: 0; font-size: 15px; }
  `,
})
export class StepSubtitles {
  readonly store = inject(ProjectStore);
  private api = inject(Api);
  private toast = inject(Toast);
  readonly fmtTime = fmtTime;
  readonly cues = signal<Cue[]>([]);
  private loadedFor = '';

  constructor() {
    effect(() => {  // load the cues once the project (or a new .srt) is there
      const p = this.store.project();
      const key = p ? `${p.id}:${p.files.srt}:${this.store.version()}` : '';
      if (p?.files.srt && key !== this.loadedFor && !this.store.busy('subtitles')) {
        this.loadedFor = key;
        this.api.cues(p.id).then((r) => this.cues.set(r.cues));
      }
    });
  }

  async generate() {
    await this.store.run('subtitles', `/projects/${this.store.id()}/subtitles`, { model: this.store.project()!.subtitles.model });
  }

  remove(i: number) { this.cues.update((c) => c.filter((_, j) => j !== i)); }

  async save() {
    await this.api.put(`/projects/${this.store.id()}/subtitles`, { cues: this.cues() });
    this.toast.show('Subtitles saved', 'ok');
  }
}
