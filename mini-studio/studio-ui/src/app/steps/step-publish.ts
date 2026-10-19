import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { Api } from '../core/api';
import { PublishFields } from '../core/models';
import { ProjectStore } from '../core/project-store';
import { Icon } from '../shared/icon';
import { JobProgress } from '../shared/job-progress';

/** Upload the recording with the chosen thumbnail (+ subtitles) and schedule it. */
@Component({
  selector: 'app-step-publish',
  imports: [FormsModule, RouterLink, Icon, JobProgress],
  template: `
    @if (store.project(); as p) {
      @if (p.publish.result; as r) {
        <div class="callout ok done">
          <b>Uploaded.</b> <a [href]="r.url" target="_blank">{{ r.url }}</a> ·
          <a [href]="r.studio" target="_blank">open in YouTube Studio <app-icon name="external" [size]="14" /></a>
          @if (r.scheduled) { <div>Scheduled for <b>{{ p.publish.schedule }}</b>.</div> }
          <div class="small">Until your Google Cloud project passes the YouTube API audit, Google keeps API uploads private.</div>
        </div>
      }
      <div class="layout">
        <section class="card">
          <div class="card-head"><h3>Video details</h3></div>
          <div class="fields">
            <label class="field"><span>Title</span>
              <input maxlength="100" [(ngModel)]="f.title" (blur)="save()" />
              <div class="hints"><span class="end">{{ f.title.length }}/100</span></div></label>
            <label class="field"><span>Description</span><textarea rows="8" [(ngModel)]="f.description" (blur)="save()"></textarea></label>
            <label class="field"><span>Tags (comma separated)</span><input [(ngModel)]="f.tags" (blur)="save()" /></label>
            <div class="field"><span>When</span>
              <div class="row">
                <label class="check"><input type="checkbox" [(ngModel)]="scheduled" (change)="save()" /> Schedule</label>
                @if (scheduled) {
                  <input class="inline-input" type="date" [(ngModel)]="date" (change)="save()" />
                  <input class="inline-input" type="time" [(ngModel)]="time" (change)="save()" />
                } @else {
                  <select class="inline-input" [(ngModel)]="f.privacy" (change)="save()">
                    <option value="private">Private</option><option value="unlisted">Unlisted</option><option value="public">Public</option>
                  </select>
                }
              </div>
            </div>
            <label class="field"><span>Playlist ID (optional)</span><input [(ngModel)]="f.playlist" (blur)="save()" /></label>
            @if (p.files.srt) {
              <label class="check"><input type="checkbox" [ngModel]="p.publish.include_subtitles"
                     (ngModelChange)="store.patch({ publish: { include_subtitles: $event } })" /> Upload the subtitles</label>
            }
          </div>
        </section>

        <aside class="card side">
          <div class="card-head"><h3>Ready to upload</h3></div>
          @if (p.files.thumb) { <img class="preview" [src]="store.file('thumb.png')" alt="thumbnail" /> }
          <ul class="check-list">
            <li [class.yes]="p.files.cutout">Background removed</li>
            <li [class.yes]="p.files.thumb">Thumbnail: {{ p.thumbnail.template ?? '–' }}</li>
            <li class="opt" [class.yes]="p.files.srt">Subtitles{{ p.files.srt ? '' : ' (skipped)' }}</li>
            <li class="opt" [class.yes]="p.shorts.length > 0">{{ p.shorts.length }} Short(s){{ p.shorts.length ? ' · upload them in the Shorts step' : '' }}</li>
          </ul>
          @if (yt() && !yt()!.client_secret) {
            <div class="callout warn small">YouTube isn't set up yet: see <a routerLink="/settings">Settings</a>. A dry run still works.</div>
          }
          <div class="actions">
            <button class="btn btn-secondary" [disabled]="store.busy('publish')" (click)="publish(true)">Dry run</button>
            <button class="btn btn-primary grow" [disabled]="store.busy('publish') || !ready() || !yt()?.client_secret" (click)="publish(false)">
              <app-icon name="cloud" /> {{ p.publish.result ? 'Upload again' : 'Upload to YouTube' }}</button>
          </div>
          <app-job-progress [job]="store.jobs()['publish']" />
          @if (dry()) { <pre>{{ dry() }}</pre> }
        </aside>
      </div>
    }
  `,
  styles: `
    .done { margin-bottom: 16px; display: grid; gap: 4px; } .done a { color: var(--link-ok); }
    .layout { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 20px; align-items: start; }
    @media (max-width: 1000px) { .layout { grid-template-columns: 1fr; } }
    .side { display: grid; gap: 14px; }
    .check-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 4px; font-size: 14px; font-weight: 600; }
    .check-list li::before { content: '✗ '; color: var(--err); } .check-list li.opt::before { content: '– '; color: var(--muted); }
    .check-list li.yes::before { content: '✓ '; color: var(--ok); }
    .actions { display: flex; gap: 10px; }
  `,
})
export class StepPublish implements OnInit {
  readonly store = inject(ProjectStore);
  private api = inject(Api);
  readonly yt = signal<{ client_secret: boolean; connected: boolean } | null>(null);
  readonly dry = signal('');
  f: PublishFields = { title: '', description: '', tags: '', privacy: 'private', schedule: null, playlist: '' };
  scheduled = false;
  date = '';
  time = '18:00';

  async ngOnInit() {
    const p = this.store.project()!;
    const settings = await this.api.settings();
    const plainTitle = p.thumbnail.title.replace(/\s*\/\s*/g, ' ').trim();
    this.f = { ...this.f, ...p.publish };
    this.f.title ||= plainTitle;
    if (!this.f.description || this.f.description === settings.description_template.replace('{title}', '')) {
      this.f.description = settings.description_template.replace('{title}', this.f.title);
    }
    this.scheduled = !!p.publish.schedule || !p.publish.result;
    const tomorrow = new Date(Date.now() + 86400000);
    const local = new Date(tomorrow.getTime() - tomorrow.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    [this.date, this.time] = p.publish.schedule ? p.publish.schedule.split(' ') : [local, settings.publish_time];
    this.yt.set(await this.api.youtube());
    await this.save();
  }

  ready() {
    const p = this.store.project()!;
    return p.files.cutout && p.files.thumb && !!this.f.title.trim();
  }

  async save() {
    this.f.schedule = this.scheduled && this.date && this.time ? `${this.date} ${this.time}` : null;
    await this.store.patch({ publish: { ...this.store.project()!.publish, ...this.f } });
  }

  async publish(dry: boolean) {
    await this.save();
    const job = await this.store.run('publish', `/projects/${this.store.id()}/publish`, { dry_run: dry });
    this.dry.set(dry ? JSON.stringify(job.result, null, 2) : '');
  }
}
