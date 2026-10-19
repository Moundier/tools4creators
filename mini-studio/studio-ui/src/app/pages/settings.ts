import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { Api } from '../core/api';
import { ChannelStore } from '../core/channel';
import { Job, Settings } from '../core/models';
import { Icon } from '../shared/icon';
import { JobProgress } from '../shared/job-progress';
import { MicPanel } from './mic-panel';
import { Toast } from '../shared/toast';

@Component({
  selector: 'app-settings',
  imports: [FormsModule, Icon, JobProgress, MicPanel],
  template: `
    <h1>Settings</h1>
    <div class="cols">
      @if (s(); as s) {
        <section class="card">
          <div class="card-head"><h2>Recordings & upload defaults <span class="muted ch">· {{ channel.current()?.name }}</span></h2>
            <button class="btn btn-primary" (click)="save()"><app-icon name="save" /> Save</button></div>
          <div class="fields">
            <label class="field"><span>OBS recording folder</span><input [(ngModel)]="s.watch_folder" />
              <div class="hints">Shared by all channels. Everything below is only for {{ channel.current()?.name }}.</div></label>
            <div class="fields-3">
              <label class="field"><span>Privacy</span>
                <select [(ngModel)]="s.privacy">
                  <option value="private">Private</option><option value="unlisted">Unlisted</option><option value="public">Public</option>
                </select></label>
              <label class="field"><span>Publish time</span><input type="time" [(ngModel)]="s.publish_time" /></label>
              <label class="field"><span>Whisper model</span>
                <select [(ngModel)]="s.whisper_model">@for (m of models; track m) { <option [value]="m">{{ m }}</option> }</select></label>
            </div>
            <label class="field"><span>Default tags (comma separated)</span><input [(ngModel)]="s.tags" /></label>
            <label class="field"><span>Description template</span>
              <textarea rows="6" [(ngModel)]="s.description_template"></textarea>
              <div class="hints">{{ '{' }}title{{ '}' }} is replaced by the video title</div></label>
          </div>
        </section>
      }

      <div class="side">
        <section class="card" id="channel">
          <div class="card-head"><h2>Channel</h2>
            <button class="btn btn-primary btn-sm" [disabled]="!chName().trim() || !channelChanged() || savingChannel()"
                    (click)="saveChannel()"><app-icon name="save" [size]="16" /> Save</button></div>
          <div class="fields">
            <div class="chrow">
              <span class="chavatar" [style.background]="chColor()">{{ (chName().trim().charAt(0) || '?').toUpperCase() }}</span>
              <label class="field grow"><span>Name</span>
                <input maxlength="40" [value]="chName()" (input)="chName.set($any($event.target).value)"
                       (keydown.enter)="saveChannel()" /></label>
            </div>
            <div class="field"><span>Color</span>
              <div class="swatches" role="radiogroup" aria-label="Channel color">
                @for (col of channel.colors(); track col) {
                  <button type="button" class="swatch" role="radio" [attr.aria-checked]="col === chColor()" [attr.aria-label]="col"
                          [style.background]="col" [class.on]="col === chColor()" (click)="chColor.set(col)"></button>
                }
              </div>
            </div>
          </div>
        </section>

        <section class="card">
          <div class="card-head"><h2>YouTube <span class="muted ch">· {{ channel.current()?.name }}</span></h2></div>
          @if (yt(); as y) {
            @if (!y.client_secret) {
              <div class="callout warn">Not set up. Follow <b>"YouTube upload → One-time setup"</b> in the README and save the file as
                <code>{{ y.client_secret_path }}</code>.</div>
            } @else if (y.connected) {
              <div class="row"><span class="callout ok grow">Connected: uploads from {{ channel.current()?.name }} go to this YouTube account.</span>
                <button class="btn btn-ghost btn-sm" (click)="connect()">Log in again</button></div>
            } @else {
              <p class="muted">OAuth file found. Log in once with the Google account of {{ channel.current()?.name }}:</p>
              <button class="btn btn-primary" (click)="connect()"><app-icon name="login" /> Connect YouTube</button>
            }
            <app-job-progress [job]="connectJob()" />
            <p class="muted small note">Until Google audits your API project, videos uploaded through it stay private (scheduled ones too).</p>
          }
        </section>

      </div>
    </div>
    <div class="mic"><app-mic-panel [whisperModel]="s()?.whisper_model ?? 'small'" /></div>
  `,
  styles: `
    h1 { margin-bottom: 20px; } .ch { font-weight: 400; }
    .cols { display: grid; grid-template-columns: 3fr 2fr; gap: 20px; align-items: start; }
    @media (max-width: 1000px) { .cols { grid-template-columns: 1fr; } }
    .side { display: grid; gap: 20px; }
    .mic { margin-top: 20px; }
    .fields-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    @media (max-width: 700px) { .fields-3 { grid-template-columns: 1fr; } }
    .chrow { display: flex; align-items: end; gap: 14px; }
    .chavatar { width: 40px; height: 40px; border-radius: 50%; display: grid; place-items: center; color: #fff; font-size: 20px; flex: none; }
    .swatches { display: flex; gap: 10px; flex-wrap: wrap; }
    .swatch { all: unset; cursor: pointer; width: 28px; height: 28px; border-radius: 50%; }
    .swatch.on { box-shadow: 0 0 0 2px var(--card), 0 0 0 4px #e4e4e7; }
    .swatch:focus-visible { box-shadow: 0 0 0 2px var(--card), 0 0 0 4px var(--accent); }
    .side p { margin-bottom: 10px; } .note { margin-top: 12px; } pre { margin-top: 8px; }
  `,
})
export class SettingsPage implements OnInit {
  private api = inject(Api);
  private toast = inject(Toast);
  readonly channel = inject(ChannelStore);
  readonly models = ['tiny', 'base', 'small', 'medium', 'large-v3'];
  readonly s = signal<Settings | null>(null);
  readonly yt = signal<{ client_secret: boolean; connected: boolean; client_secret_path: string } | null>(null);
  readonly connectJob = signal<Job | undefined>(undefined);
  readonly chName = signal('');
  readonly chColor = signal('');
  readonly savingChannel = signal(false);
  readonly channelChanged = computed(() => {
    const c = this.channel.current();
    return !!c && (this.chName().trim() !== c.name || this.chColor() !== c.color);
  });

  async ngOnInit() {
    await this.channel.refresh().catch(() => null);
    this.chName.set(this.channel.current()?.name ?? '');
    this.chColor.set(this.channel.current()?.color ?? '');
    this.s.set(await this.api.settings());
    this.yt.set(await this.api.youtube());
  }

  async save() {
    this.s.set(await this.api.put<Settings>('/settings', this.s()));
    this.toast.show('Settings saved', 'ok');
  }

  async saveChannel() {
    const c = this.channel.current();
    if (!c || !this.chName().trim() || !this.channelChanged()) return;
    this.savingChannel.set(true);
    try {
      await this.api.patch(`/channels/${c.id}`, { name: this.chName().trim(), color: this.chColor() });
      await this.channel.refresh();
      this.chName.set(this.channel.current()?.name ?? '');
      this.toast.show('Channel saved', 'ok');
    } finally {
      this.savingChannel.set(false);
    }
  }

  async connect() {
    const job = await this.api.post<Job>('/youtube/connect');
    try {
      await this.api.waitJob(job, (j) => this.connectJob.set(j));
    } finally {
      this.yt.set(await this.api.youtube());
    }
  }
}
