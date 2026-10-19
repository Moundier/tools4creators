import { AfterViewInit, Component, ElementRef, OnInit, computed, inject, signal, viewChildren } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { Channel, ChannelStore } from '../core/channel';
import { Confirm } from '../shared/confirm-dialog';
import { Icon } from '../shared/icon';
import { Toast } from '../shared/toast';

interface Draft { id: string | null; name: string; color: string; }

/** "Which channel?": pick the channel to work on (like Netflix's profile picker), add, rename, recolor or delete one. */
@Component({
  selector: 'app-browse',
  imports: [Icon],
  template: `
    <div class="page" [style.--glow]="glow()">
      <header>
        <span>mini-studio</span>
      </header>

      <main>
        <h1>{{ managing() ? 'Manage channels' : 'Which channel?' }}</h1>
        @if (loaded()) {
          <ul class="tiles">
            @for (c of store.channels(); track c.id) {
              <li>
                <button #tile class="tile" [class.managing]="managing()" (click)="pick(c)"
                        [attr.aria-label]="(managing() ? 'Edit ' : 'Open ') + c.name">
                  <span class="square" [style.background]="c.color">
                    <span class="initial">{{ initial(c.name) }}</span>
                    @if (managing()) { <span class="pencil"><app-icon name="edit" [size]="34" [stroke]="1.75" /></span> }
                  </span>
                  <span class="name">{{ c.name }}</span>
                  @if (!managing()) {
                    <span class="meta">{{ c.connected ? 'YouTube connected' : 'not connected' }}</span>
                  }
                </button>
              </li>
            }
            <li>
              <button class="tile add" (click)="openDraft(null)" aria-label="Add channel">
                <span class="square"><app-icon name="plus" [size]="56" [stroke]="1.5" /></span>
                <span class="name">Add channel</span>
              </button>
            </li>
          </ul>
          <button class="manage" (click)="managing.set(!managing())">
            @if (managing()) { Done } @else { <app-icon name="edit" [size]="16" /> Manage channels }
          </button>
        }
      </main>
    </div>

    @if (draft(); as d) {
      <div class="scrim" (click)="draft.set(null)"></div>
      <form class="sheet" role="dialog" aria-modal="true" [attr.aria-label]="d.id ? 'Edit channel' : 'Add channel'"
            (submit)="$event.preventDefault(); saveDraft()">
        <h2>{{ d.id ? 'Edit channel' : 'Add channel' }}</h2>
        <div class="preview">
          <span class="square sm" [style.background]="d.color"><span class="initial">{{ initial(d.name) || '?' }}</span></span>
          <label class="field grow"><span>Name</span>
            <input #nameInput maxlength="40" [value]="d.name" (input)="setDraft({ name: $any($event.target).value })"
                   placeholder="Channel name" required /></label>
        </div>
        <div class="field"><span>Color</span>
          <div class="swatches" role="radiogroup" aria-label="Color">
            @for (col of store.colors(); track col) {
              <button type="button" class="swatch" role="radio" [attr.aria-checked]="col === d.color" [attr.aria-label]="col"
                      [style.background]="col" [class.on]="col === d.color" (click)="setDraft({ color: col })"></button>
            }
          </div>
        </div>
        <div class="actions">
          @if (d.id) {
            <button type="button" class="btn btn-danger" (click)="remove(d)"><app-icon name="trash" [size]="16" /> Delete channel</button>
          }
          <span class="grow"></span>
          <button type="button" class="btn btn-ghost" (click)="draft.set(null)">Cancel</button>
          <button type="submit" class="btn btn-primary" [disabled]="!d.name.trim() || saving()">{{ d.id ? 'Save' : 'Add' }}</button>
        </div>
      </form>
    }
  `,
  styles: `
    :host { display: block; }
    .page { --glow: #c00fc9; /* MANUAL CHANGE */ min-height: 105vh; display: flex; flex-direction: column;
            background: radial-gradient(ellipse 90% 70% at 50% 0%, color-mix(in srgb, var(--glow) 32%, #1f1f1f) 0%, #161616 60%, #0f0f0f 100%); }
    header { display: flex; align-items: center; gap: 4px; padding: 28px 56px; }
    header span { font-size: 21px; font-weight: 500; letter-spacing: -.02em; }
    main { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px 16px 96px; }
    h1 { font-size: 34px; font-weight: 500; margin-bottom: 28px; text-align: center; }

    .tiles { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; justify-content: center; gap: 28px 40px; max-width: 1000px; }
    .tile { all: unset; cursor: pointer; display: grid; justify-items: center; gap: 10px; width: 128px; text-align: center; }
    .square { position: relative; width: 128px; height: 128px; border-radius: 16px; display: grid; place-items: center;
              box-shadow: inset 0 0 0 3px transparent; transition: box-shadow .12s, transform .12s; overflow: hidden; }
    .initial { font-size: 64px; font-weight: 500; color: #fff; text-shadow: 0 2px 8px rgba(0,0,0,.25); }
    .name { font-size: 17px; color: var(--muted); max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
            transition: color .12s; }
    .meta { font-size: 12px; color: #777; margin-top: -6px; }
    .tile:hover .square, .tile:focus-visible .square { box-shadow: inset 0 0 0 3px #f1f1f1; }
    .tile:hover .name, .tile:focus-visible .name { color: var(--text); }
    .tile:focus-visible { outline: none; }
    .managing .square::after { content: ''; position: absolute; inset: 0; background: rgba(0,0,0,.5); }
    .managing .initial { opacity: 0; }
    .pencil { position: absolute; inset: 0; display: grid; place-items: center; color: #fff; z-index: 1; }
    .add .square { background: transparent; border: 2px solid #3e3e3e; color: var(--muted); box-sizing: border-box; }
    .add:hover .square, .add:focus-visible .square { color: var(--text); border-color: transparent; }

    .manage { all: unset; cursor: pointer; margin-top: 44px; display: inline-flex; align-items: center; gap: 8px; padding: 9px 18px;
              border: 1px solid #8a8a8a; border-radius: 999px; font-size: 15px; font-weight: 500; color: var(--text);
              background: rgba(0,0,0,.35); }
    .manage:hover { background: rgba(255,255,255,.08); border-color: #f1f1f1; }
    .manage:focus-visible { box-shadow: var(--focus); }

    .scrim { position: fixed; inset: 0; background: rgba(0,0,0,.6); z-index: 50; }
    .sheet { position: fixed; z-index: 51; left: 50%; top: 50%; transform: translate(-50%, -50%); width: min(460px, calc(100vw - 32px));
             background: var(--card); border-radius: 12px; padding: 24px; box-shadow: var(--shadow-lg); display: grid; gap: 18px; }
    .preview { display: flex; align-items: end; gap: 16px; }
    .square.sm { width: 72px; height: 72px; flex: none; } .square.sm .initial { font-size: 36px; }
    .swatches { display: flex; gap: 10px; flex-wrap: wrap; }
    .swatch { all: unset; cursor: pointer; width: 34px; height: 34px; border-radius: 50%; box-shadow: 0 0 0 2px transparent; }
    .swatch.on { box-shadow: 0 0 0 2px var(--card), 0 0 0 4px #f1f1f1; }
    .swatch:focus-visible { box-shadow: 0 0 0 2px var(--card), 0 0 0 4px var(--accent); }
    .actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

    @media (max-width: 600px) {
      header { padding: 20px 16px; }
      h1 { font-size: 26px; }
      .tiles { gap: 20px 24px; }
      .tile { width: 96px; } .square { width: 96px; height: 96px; } .initial { font-size: 48px; }
      .name { font-size: 15px; }
    }
  `,
})
export class BrowsePage implements OnInit, AfterViewInit {
  readonly store = inject(ChannelStore);
  private http = inject(HttpClient);
  private router = inject(Router);
  private confirm = inject(Confirm);
  private toast = inject(Toast);
  readonly loaded = signal(false);
  readonly managing = signal(false);
  readonly saving = signal(false);
  readonly draft = signal<Draft | null>(null);
  private tiles = viewChildren<ElementRef<HTMLButtonElement>>('tile');
  readonly glow = computed(() => this.store.channels().find((c) => c.id === this.store.lastId())?.color ?? '#c00fc9');

  async ngOnInit() {
    await this.store.refresh().catch(() => this.toast.show('Could not load the channels', 'err'));
    this.loaded.set(true);
    setTimeout(() => this.focusLast());
  }

  ngAfterViewInit() { this.focusLast(); }

  /** Focus the channel used last, so Enter opens it. */
  private focusLast() {
    const i = this.store.channels().findIndex((c) => c.id === this.store.lastId());
    this.tiles()[i >= 0 ? i : 0]?.nativeElement.focus();
  }

  initial(name: string) { return (name.trim()[0] ?? '').toUpperCase(); }

  pick(c: Channel) {
    if (this.managing()) return this.openDraft(c);
    this.store.select(c.id);
    this.router.navigate(['/']);
  }

  openDraft(c: Channel | null) {
    const used = new Set(this.store.channels().map((x) => x.color));
    const color = c?.color ?? this.store.colors().find((x) => !used.has(x)) ?? this.store.colors()[0] ?? '#c00fc9';
    this.draft.set({ id: c?.id ?? null, name: c?.name ?? '', color });
    setTimeout(() => (document.querySelector('.sheet input') as HTMLInputElement | null)?.focus());
  }

  setDraft(change: Partial<Draft>) { this.draft.update((d) => (d ? { ...d, ...change } : d)); }

  async saveDraft() {
    const d = this.draft();
    if (!d || !d.name.trim()) return;
    this.saving.set(true);
    try {
      const body = { name: d.name.trim(), color: d.color };
      await firstValueFrom(d.id ? this.http.patch(`/api/channels/${d.id}`, body) : this.http.post('/api/channels', body));
      this.draft.set(null);
      await this.store.refresh();
    } catch (e) {
      this.toast.show(e instanceof HttpErrorResponse ? (e.error?.detail ?? e.message) : String(e), 'err');
    } finally {
      this.saving.set(false);
    }
  }

  async remove(d: Draft) {
    const ok = await this.confirm.ask({
      title: `Delete ${d.name}?`,
      message: 'Its projects (subtitles, Shorts, cutouts, thumbnails, upload details) and its YouTube login are deleted.\n' +
               'The recordings in the OBS folder are kept, and other channels keep their projects.',
      confirm: 'Delete channel',
    });
    if (!ok || !d.id) return;
    try {
      await firstValueFrom(this.http.delete(`/api/channels/${d.id}`));
      this.draft.set(null);
      await this.store.refresh();
      this.toast.show(`${d.name} deleted`, 'ok');
    } catch (e) {
      this.toast.show(e instanceof HttpErrorResponse ? (e.error?.detail ?? e.message) : String(e), 'err');
    }
  }
}
