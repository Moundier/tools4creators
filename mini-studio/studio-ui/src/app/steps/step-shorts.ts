import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { Api } from '../core/api';
import { Box, Job, ShortClip, fmtTime } from '../core/models';
import { ProjectStore } from '../core/project-store';
import { BoxKind, BoxSelector } from '../shared/box-selector';
import { Icon } from '../shared/icon';
import { ShortCard } from './short-card';

/** Optional: cut 9:16 Shorts from the recording (facecam on top, gameplay below, captions). */
@Component({
  selector: 'app-step-shorts',
  imports: [FormsModule, Icon, BoxSelector, ShortCard],
  template: `
    @if (store.project(); as p) {
      <section class="card">
        <div class="card-head"><h3>New Short</h3>
          <button class="btn btn-primary" [disabled]="!canAdd()" (click)="add()"><app-icon name="clapper" /> Make Short</button></div>
        <div class="layout">
          <div class="stack">
            <h4><span class="n">1</span> Mark the clip</h4>
            <div class="toolbar-gap" aria-hidden="true"></div>
            <video #vid [src]="'/api/projects/' + p.id + '/video'" controls preload="metadata"
                   (timeupdate)="now.set(vid.currentTime)" (loadedmetadata)="videoWidth.set(vid.videoWidth)"></video>
            <div class="row">
              <button class="btn btn-secondary btn-sm mark-start" (click)="start.set(now())"><app-icon name="mark-in" [size]="16" /> Start {{ fmtTime(start()) }}</button>
              <button class="btn btn-secondary btn-sm mark-end" (click)="end.set(now())"><app-icon name="mark-out" [size]="16" /> End {{ fmtTime(end()) }}</button>
              @if (start() != null && end() != null) {
                <span class="small" [class.text-warn]="len() <= 0 || len() > 60">{{ len().toFixed(1) }}s{{ len() > 60 ? ' · over 60 s' : '' }}</span>
              }
            </div>
          </div>

          <div class="stack">
            <h4><span class="n">2</span> Facecam and gameplay areas</h4>
            <div class="row">
              <div class="segmented">
                <label><input type="radio" name="box" [checked]="active() === 'face'" (change)="active.set('face')" /><span>Facecam</span></label>
                <label><input type="radio" name="box" [checked]="active() === 'game'" (change)="active.set('game')" /><span>Gameplay</span></label>
              </div>
              <span class="grow"></span>
              <button class="btn btn-icon btn-sm" title="Use the current video frame" (click)="frameT.set(now())"><app-icon name="camera" [size]="16" /></button>
              <button class="btn btn-ghost btn-sm" (click)="face.set(null); game.set(null)">Clear</button>
            </div>
            @if (videoWidth()) {
              <app-box-selector [src]="'/api/projects/' + p.id + '/frame?width=960&t=' + frameT()" [sourceWidth]="videoWidth()"
                                [active]="active()" [boxes]="{ face: face(), game: game() }" (boxChange)="setBox($event.kind, $event.box)" />
            }
            <p class="muted small">Drag on the frame. {{ face() ? 'Face on top, gameplay below.' : 'No facecam box: the Short is a center crop.' }}</p>
          </div>
        </div>

        <h4 class="details-h"><span class="n">3</span> Details</h4>
        <div class="row">
          <label class="field grow"><span>Banner title (first 3 s, optional)</span><input [(ngModel)]="title" /></label>
          <label class="check captions"><input type="checkbox" [(ngModel)]="captions" /> Animated captions</label>
        </div>
      </section>

      @if (p.shorts.length) {
        <section class="list-wrap">
          <div class="card-head"><h3>Your Shorts ({{ p.shorts.length }})</h3>
            <span class="muted small">Saved in <code>work/{{ p.id }}/shorts/</code> · upload each one whenever you want</span></div>
          <div class="list">
            @for (c of p.shorts; track c.n) { <app-short-card [clip]="c" /> }
          </div>
        </section>
      }
    }
  `,
  styles: `
    /* the columns share rows (heading, toolbar, media, footer), so the video lines up with the frame */
    .layout { display: grid; grid-template-columns: 1fr 1fr; column-gap: 24px; }
    .layout > .stack { grid-row: span 4; grid-template-rows: subgrid; row-gap: 12px; align-content: start; }
    @media (max-width: 1000px) { .layout { grid-template-columns: 1fr; row-gap: 24px; } }
    h4 { display: flex; align-items: center; gap: 8px; }
    .n { width: 22px; height: 22px; border-radius: 50%; background: var(--purple-50); color: var(--purple);
         display: grid; place-items: center; font-size: 12px; }
    .details-h { margin: 22px 0 10px; }
    .row { align-items: end; } .captions { margin-bottom: 10px; }
    .list-wrap { margin-top: 24px; } .list { display: grid; gap: 12px; }
  `,
})
export class StepShorts {
  readonly store = inject(ProjectStore);
  private api = inject(Api);
  readonly fmtTime = fmtTime;
  readonly now = signal(0);
  readonly videoWidth = signal(0);
  readonly start = signal<number | null>(null);
  readonly end = signal<number | null>(null);
  readonly frameT = signal(1);
  readonly active = signal<BoxKind>('face');
  readonly face = signal<Box | null>(null);
  readonly game = signal<Box | null>(null);
  title = '';
  captions = true;

  len() { return (this.end() ?? 0) - (this.start() ?? 0); }
  canAdd() { return this.start() != null && this.end() != null && this.len() > 0; }

  setBox(kind: BoxKind, box: Box) {
    (kind === 'face' ? this.face : this.game).set(box);
    if (kind === 'face' && !this.game()) this.active.set('game');
  }

  async add() {
    const res = await this.api.post<{ short: ShortClip; job: Job }>(`/projects/${this.store.id()}/shorts`, {
      start: this.start(), end: this.end(), face: this.face(), game: this.game(), title: this.title, captions: this.captions,
    });
    this.start.set(null);
    this.end.set(null);
    this.title = '';
    await this.store.reload();
    await this.store.follow('short:' + res.short.n, res.job);
  }
}
