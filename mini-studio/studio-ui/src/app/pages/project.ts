import { Component, computed, effect, inject, input, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { Api } from '../core/api';
import { fmtTime } from '../core/models';
import { ProjectStore } from '../core/project-store';
import { Confirm, DISCARD } from '../shared/confirm-dialog';
import { Icon } from '../shared/icon';
import { StepDef, Stepper } from '../shared/stepper';
import { Toast } from '../shared/toast';
import { StepCutout } from '../steps/step-cutout';
import { StepPublish } from '../steps/step-publish';
import { StepRecording } from '../steps/step-recording';
import { StepShorts } from '../steps/step-shorts';
import { StepSubtitles } from '../steps/step-subtitles';
import { StepThumbnail } from '../steps/step-thumbnail';

const HINTS = [
  'Check the recording, then continue.',
  'Optional: generate subtitles, or skip.',
  'Optional: cut Shorts from the video, or skip.',
  'Required: upload a photo of you and remove its background.',
  'Required: render the templates and pick one.',
  'Fill in the details and upload.',
];

/** The wizard: recording -> subtitles (optional) -> shorts (optional) -> cutout -> thumbnail -> upload. */
@Component({
  selector: 'app-project',
  providers: [ProjectStore],
  imports: [RouterLink, Icon, Stepper, StepRecording, StepSubtitles, StepShorts, StepCutout, StepThumbnail, StepPublish],
  template: `
    @if (store.project(); as p) {
      <div class="head">
        <a class="btn btn-icon" routerLink="/" title="Back to recordings"><app-icon name="back" /></a>
        <div class="grow title">
          <h1>{{ p.name }}</h1>
          <div class="meta"><span class="chip" [class]="p.status">{{ p.status }}</span>
            <span class="muted small">{{ fmtTime(p.duration) }}</span></div>
        </div>
        <details class="menu" #menu>
          <summary class="btn btn-icon" title="More actions"><app-icon name="more" [size]="22" [stroke]="3" /></summary>
          <div class="menu-items" (click)="menu.open = false">
            @if (p.status !== 'uploaded') {
              <button (click)="mark('uploaded')"><app-icon name="check-all" /> Mark as done (uploaded myself)</button>
            } @else {
              <button (click)="mark('editing')"><app-icon name="undo" /> Move back to Editing</button>
            }
            <button class="danger" (click)="discard()"><app-icon name="trash" /> Discard changes…</button>
          </div>
        </details>
      </div>

      <app-stepper [steps]="steps()" [current]="current()" (select)="go($event)" />

      <section class="body">
        @if (visited().has(0)) { <app-step-recording [hidden]="current() !== 0" /> }
        @if (visited().has(1)) { <app-step-subtitles [hidden]="current() !== 1" /> }
        @if (visited().has(2)) { <app-step-shorts [hidden]="current() !== 2" /> }
        @if (visited().has(3)) { <app-step-cutout [hidden]="current() !== 3" /> }
        @if (visited().has(4)) { <app-step-thumbnail [hidden]="current() !== 4" /> }
        @if (visited().has(5)) { <app-step-publish [hidden]="current() !== 5" /> }
      </section>

      <nav class="stepbar">
        <div class="inner">
          <button class="btn btn-ghost" [disabled]="current() === 0" (click)="go(current() - 1)"><app-icon name="back" /> Back</button>
          <span class="hint muted" [class.text-warn]="blocked()">{{ hint() }}</span>
          @if (current() < 5) {
            <button class="btn btn-primary" [disabled]="blocked()" (click)="go(current() + 1)">
              {{ isSkip() ? 'Skip' : 'Next' }} <app-icon name="next" /></button>
          }
        </div>
      </nav>
    } @else {
      <p class="muted">Loading…</p>
    }
  `,
  styles: `
    .head { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
    .title { min-width: 0; } h1 { font-size: 28px; overflow-wrap: anywhere; }
    .meta { display: flex; gap: 8px; align-items: center; margin-top: 4px; }
    .stepbar { position: fixed; left: var(--side, 0px); right: 0; bottom: 0; z-index: 15; background: rgba(40,40,40,.94);
               backdrop-filter: blur(6px); border-top: 1px solid var(--line); }
    .stepbar .inner { max-width: 1280px; margin: 0 auto; padding: 12px 16px; display: flex; align-items: center; gap: 16px; }
    .hint { flex: 1; text-align: center; font-size: 13px; }
  `,
})
export class ProjectPage {
  readonly store = inject(ProjectStore);
  private api = inject(Api);
  private router = inject(Router);
  private confirm = inject(Confirm);
  private toast = inject(Toast);
  readonly id = input.required<string>(); // route param
  readonly fmtTime = fmtTime;
  readonly current = signal(0);
  readonly visited = signal(new Set<number>([0]));

  readonly steps = computed<StepDef[]>(() => {
    const p = this.store.project();
    if (!p) return [];
    const cut = p.files.cutout, thumb = p.files.thumb && !!p.thumbnail.template;
    return [
      { label: 'Recording', done: true, locked: false },
      { label: 'Subtitles', optional: true, done: p.files.srt, locked: false },
      { label: 'Shorts', optional: true, done: p.shorts.length > 0, locked: false },
      { label: 'Background removal', done: cut, locked: false },
      { label: 'Thumbnail', done: thumb, locked: !cut },
      { label: 'Upload & schedule', done: p.status === 'uploaded', locked: !cut || !thumb },
    ];
  });

  /** Required step not finished yet: Next is disabled. */
  readonly blocked = computed(() => {
    const s = this.steps()[this.current()];
    return this.current() < 5 && !!s && !s.optional && !s.done;
  });

  readonly isSkip = computed(() => {
    const p = this.store.project(), i = this.current();
    return !!p && ((i === 1 && !p.files.srt) || (i === 2 && !p.shorts.length));
  });

  readonly hint = computed(() => HINTS[this.current()]);

  constructor() {
    effect(() => {
      this.store.load(this.id()).then((p) => {
        // reopen where the user left off: uploaded / thumbnail chosen -> upload step, cutout done -> thumbnail
        this.go(p.status === 'uploaded' || (p.files.thumb && p.thumbnail.template) ? 5 : p.files.cutout ? 4 : 0);
      });
    });
  }

  go(i: number) {
    const s = this.steps()[i];
    if (i < 0 || i > 5 || (s && s.locked)) return;
    // a project stays "new" while only the recording was looked at; moving past step 1 starts the editing
    if (this.current() === 0 && i > 0 && this.store.project()?.status === 'new') {
      this.api.post(`/projects/${this.store.id()}/status`, { status: 'editing' }).then(() => this.store.reload());
    }
    this.visited.update((v) => new Set(v).add(i));
    this.current.set(i);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async mark(status: 'uploaded' | 'editing') {
    await this.api.post(`/projects/${this.store.id()}/status`, { status });
    await this.store.reload();
    this.toast.show(status === 'uploaded' ? 'Marked as done' : 'Moved back to Editing', 'ok');
  }

  async discard() {
    if (!(await this.confirm.ask(DISCARD))) return;
    await this.api.delete(`/projects/${this.store.id()}`);
    this.router.navigate(['/']);
  }
}
