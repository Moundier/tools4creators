import { Component, computed, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { Api } from '../core/api';
import { ShortClip, fmtTime } from '../core/models';
import { ProjectStore } from '../core/project-store';
import { Confirm } from '../shared/confirm-dialog';
import { Icon } from '../shared/icon';
import { JobProgress } from '../shared/job-progress';

/** One rendered Short: preview, re-render/delete, and its own Upload panel (use it now or any time later). */
@Component({
  selector: 'app-short-card',
  imports: [FormsModule, Icon, JobProgress],
  template: `
    @let c = clip();
    <article class="short">
      <div class="vid">
        @if (c.rendered && c.file) {
          <video [src]="store.file(c.file)" controls preload="metadata"></video>
        } @else {
          <div class="placeholder muted small">{{ store.busy(key()) ? 'rendering…' : 'not rendered' }}</div>
        }
      </div>
      <div class="body">
        <div class="top">
          <div class="grow">
            <h4>Short #{{ c.n }} <span class="muted small">{{ fmtTime(c.start) }} → {{ fmtTime(c.end) }} · {{ (c.end - c.start).toFixed(0) }}s</span></h4>
            <p class="muted small">{{ c.face ? 'facecam + gameplay' : 'center crop' }}{{ c.title ? ' · "' + c.title + '"' : '' }}{{ c.captions ? ' · captions' : '' }}</p>
          </div>
          <button class="btn btn-icon btn-sm" title="Render again" [disabled]="store.busy(key())" (click)="rerender()"><app-icon name="refresh" [size]="16" /></button>
          <button class="btn btn-icon btn-sm del" title="Delete this Short" [disabled]="store.busy(key())" (click)="remove()"><app-icon name="trash" [size]="16" /></button>
        </div>
        <app-job-progress [job]="store.jobs()[key()]" />

        @if (c.upload?.result; as r) {
          <div class="callout ok">Uploaded: <a [href]="r.url" target="_blank">{{ r.url }}</a>
            @if (r.scheduled) { <span> · scheduled {{ c.upload!.schedule }}</span> }</div>
        } @else if (c.rendered) {
          @if (!open()) {
            <div><button class="btn btn-secondary btn-sm" (click)="openPanel()"><app-icon name="cloud" [size]="16" /> Upload this Short…</button></div>
          } @else {
            <div class="panel">
              <label class="field"><span>Title</span><input maxlength="100" [(ngModel)]="title" /></label>
              <label class="field"><span>Description</span><textarea rows="2" [(ngModel)]="description"></textarea></label>
              <div class="row">
                <label class="check"><input type="checkbox" [(ngModel)]="scheduled" /> Schedule</label>
                @if (scheduled) {
                  <input class="inline-input" type="date" [(ngModel)]="date" /> <input class="inline-input" type="time" [(ngModel)]="time" />
                } @else {
                  <select class="inline-input" [(ngModel)]="privacy">
                    <option value="private">Private</option><option value="unlisted">Unlisted</option><option value="public">Public</option>
                  </select>
                }
              </div>
              <div class="row actions">
                <button class="btn btn-ghost btn-sm" (click)="open.set(false)">Cancel</button>
                <span class="grow"></span>
                <button class="btn btn-secondary btn-sm" (click)="publish(true)" [disabled]="store.busy(key())">Dry run</button>
                <button class="btn btn-primary btn-sm" (click)="publish(false)" [disabled]="store.busy(key()) || !title.trim()">
                  <app-icon name="cloud" [size]="16" /> Upload</button>
              </div>
              @if (dryRun(); as d) { <pre>{{ d }}</pre> }
            </div>
          }
        }
      </div>
    </article>
  `,
  styles: `
    .short { display: grid; grid-template-columns: 150px 1fr; gap: 16px; padding: 12px; border: 1px solid var(--line);
             border-radius: var(--r-lg); background: var(--card); }
    .vid video, .placeholder { width: 150px; aspect-ratio: 9/16; border-radius: var(--r); background: #000; }
    .placeholder { display: flex; align-items: center; justify-content: center; color: #aaa; }
    .body { display: grid; gap: 10px; align-content: start; min-width: 0; }
    .top { display: flex; align-items: flex-start; gap: 4px; } h4 { margin-bottom: 2px; }
    .del:hover { color: var(--err) !important; background: var(--err-bg) !important; }
    .callout a { color: var(--link-ok); word-break: break-all; }
    .panel { display: grid; gap: 12px; padding: 14px; border-radius: var(--r); background: var(--page); border: 1px solid var(--line); }
    .actions { gap: 8px; }
  `,
})
export class ShortCard {
  readonly store = inject(ProjectStore);
  private api = inject(Api);
  private confirm = inject(Confirm);
  readonly fmtTime = fmtTime;
  clip = input.required<ShortClip>();
  readonly key = computed(() => 'short:' + this.clip().n);
  readonly open = signal(false);
  readonly dryRun = signal('');
  title = ''; description = ''; privacy = 'private'; scheduled = false; date = ''; time = '18:00';

  openPanel() {
    const c = this.clip();
    this.title = this.title || c.title || this.store.project()!.thumbnail.title.replace(/\s*\/\s*/g, ' ');
    const t = new Date(Date.now() + 86400000);  // tomorrow, local date
    this.date = this.date || new Date(t.getTime() - t.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    this.open.set(true);
  }

  rerender() { return this.store.run(this.key(), `/projects/${this.store.id()}/shorts/${this.clip().n}/render`); }

  async remove() {
    const ok = await this.confirm.ask({ title: `Delete Short #${this.clip().n}?`, message: 'The rendered video file is deleted.',
                                        confirm: 'Delete' });
    if (!ok) return;
    await this.api.delete(`/projects/${this.store.id()}/shorts/${this.clip().n}`);
    await this.store.reload();
  }

  async publish(dry: boolean) {
    const body = { title: this.title.trim(), description: this.description, privacy: this.privacy,
                   schedule: this.scheduled ? `${this.date} ${this.time}` : null, dry_run: dry };
    const job = await this.store.run(this.key(), `/projects/${this.store.id()}/shorts/${this.clip().n}/publish`, body);
    this.dryRun.set(dry ? JSON.stringify(job.result.body, null, 2) : '');
  }
}
