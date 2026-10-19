import { Component, ElementRef, Injectable, effect, inject, signal, viewChild } from '@angular/core';

export interface ConfirmData { title: string; message: string; confirm: string; }

interface Pending extends ConfirmData { resolve: (ok: boolean) => void; }

/** Yes/no question in a native <dialog>: `await confirm.ask({...})` -> true / false. */
@Injectable({ providedIn: 'root' })
export class Confirm {
  readonly pending = signal<Pending | null>(null);

  ask(data: ConfirmData): Promise<boolean> {
    this.pending()?.resolve(false);
    return new Promise((resolve) => this.pending.set({ ...data, resolve }));
  }

  close(ok: boolean) {
    this.pending()?.resolve(ok);
    this.pending.set(null);
  }
}

@Component({
  selector: 'app-confirm-host',
  template: `
    <dialog #dlg (cancel)="$event.preventDefault(); confirm.close(false)" (click)="backdrop($event)">
      @if (confirm.pending(); as p) {
        <h2>{{ p.title }}</h2>
        <p class="msg">{{ p.message }}</p>
        <div class="actions">
          <button class="btn btn-ghost" (click)="confirm.close(false)">Cancel</button>
          <button class="btn btn-primary btn-danger" (click)="confirm.close(true)">{{ p.confirm }}</button>
        </div>
      }
    </dialog>
  `,
  styles: `
    dialog { border: none; border-radius: 12px; padding: 24px; width: min(460px, calc(100vw - 32px));
             background: var(--card); box-shadow: var(--shadow-lg); color: var(--text); }
    dialog::backdrop { background: rgba(0, 0, 0, .6); }
    h2 { margin-bottom: 10px; } .msg { white-space: pre-line; color: var(--muted); }
    .actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 22px; }
  `,
})
export class ConfirmHost {
  readonly confirm = inject(Confirm);
  private dlg = viewChild.required<ElementRef<HTMLDialogElement>>('dlg');

  constructor() {
    effect(() => {
      const el = this.dlg().nativeElement;
      if (this.confirm.pending() && !el.open) el.showModal();
      if (!this.confirm.pending() && el.open) el.close();
    });
  }

  backdrop(e: MouseEvent) {  // click outside the box = cancel
    if (e.target === this.dlg().nativeElement) this.confirm.close(false);
  }
}

export const DISCARD: ConfirmData = {
  title: 'Discard changes?',
  message: 'Everything made for this video (subtitles, Shorts, photo, cutout, thumbnails, upload details) will be deleted.\n' +
           'The recording itself is kept and goes back to New.',
  confirm: 'Discard',
};
