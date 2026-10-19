import { Component, Injectable, inject, signal } from '@angular/core';

export type ToastKind = 'info' | 'ok' | 'err';
interface ToastItem { id: number; message: string; kind: ToastKind; }

/** Short messages at the bottom of the screen (replaces Material's snackbar). */
@Injectable({ providedIn: 'root' })
export class Toast {
  readonly items = signal<ToastItem[]>([]);
  private next = 1;

  show(message: string, kind: ToastKind = 'info', ms = kind === 'err' ? 9000 : 3000) {
    const id = this.next++;
    this.items.update((all) => [...all, { id, message, kind }]);
    setTimeout(() => this.dismiss(id), ms);
  }

  dismiss(id: number) { this.items.update((all) => all.filter((t) => t.id !== id)); }
}

@Component({
  selector: 'app-toast-host',
  template: `
    <div class="toasts" aria-live="polite">
      @for (t of toast.items(); track t.id) {
        <div class="toast" [class]="t.kind">
          <span class="grow">{{ t.message }}</span>
          <button class="x" (click)="toast.dismiss(t.id)" aria-label="Close">×</button>
        </div>
      }
    </div>
  `,
  styles: `
    .toasts { position: fixed; left: 50%; bottom: 88px; transform: translateX(-50%); z-index: 100; display: grid; gap: 8px;
              width: min(560px, calc(100vw - 32px)); }
    .toast { display: flex; gap: 12px; align-items: center; padding: 12px 14px 12px 16px; border-radius: 12px;
             background: #e4e4e7; color: #18181b; box-shadow: var(--shadow-lg); font-size: 14px;
             animation: in .18s ease-out; white-space: pre-line; }
    .toast.ok { background: #e4e4e7; } .toast.err { background: #b3261e; color: #fff; }
    .x { all: unset; cursor: pointer; font-size: 20px; line-height: 1; opacity: .7; padding: 0 4px; }
    .x:hover { opacity: 1; }
    @keyframes in { from { opacity: 0; transform: translateY(8px); } }
  `,
})
export class ToastHost {
  readonly toast = inject(Toast);
}
