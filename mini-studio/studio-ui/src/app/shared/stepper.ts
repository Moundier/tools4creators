import { Component, input, output } from '@angular/core';

import { Icon } from './icon';

export interface StepDef { label: string; optional?: boolean; done: boolean; locked: boolean; }

/** Numbered step pills joined by a line. Locked steps can't be opened yet. */
@Component({
  selector: 'app-stepper',
  imports: [Icon],
  template: `
    <ol class="steps">
      @for (s of steps(); track s.label; let i = $index) {
        <li [class.current]="i === current()" [class.done]="s.done && i !== current()" [class.locked]="s.locked">
          <button type="button" [disabled]="s.locked" (click)="select.emit(i)" [attr.aria-current]="i === current() ? 'step' : null">
            <span class="dot">@if (s.done && i !== current()) { <app-icon name="check" [size]="14" [stroke]="3" /> } @else { {{ i + 1 }} }</span>
            <span class="lbl">{{ s.label }}@if (s.optional) { <small>optional</small> }</span>
          </button>
        </li>
      }
    </ol>
  `,
  styles: `
    .steps { list-style: none; margin: 0 0 22px; padding: 0; display: flex; gap: 6px; overflow-x: auto; }
    li { flex: 1; display: flex; align-items: center; min-width: max-content; }
    li:not(:last-child)::after { content: ''; flex: 1; height: 2px; background: var(--line); margin: 0 6px; min-width: 16px; }
    li.done:not(:last-child)::after { background: var(--line-strong); }
    button { all: unset; display: flex; align-items: center; gap: 10px; padding: 8px 12px 8px 8px; border-radius: 999px; cursor: pointer; }
    button:hover:not(:disabled) { background: var(--purple-50); }
    button:focus-visible { box-shadow: var(--focus); }
    button:disabled { cursor: not-allowed; opacity: .5; }
    .dot { width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; font-weight: 500; font-size: 13px;
           border: 2px solid var(--line-strong); color: var(--muted); background: var(--card); }
    .done .dot { border-color: var(--line-strong); color: var(--text); background: var(--soft); }
    .current .dot { border-color: var(--text); background: var(--text); color: #18181b; }
    .lbl { display: grid; font-weight: 500; font-size: 14px; line-height: 1.15; }
    .current .lbl { color: var(--text); }
    small { font-size: 11px; font-weight: 400; color: var(--muted); }
    @media (max-width: 1000px) { li:not(.current) .lbl { display: none; } li { min-width: 0; } }
  `,
})
export class Stepper {
  steps = input.required<StepDef[]>();
  current = input(0);
  select = output<number>();
}
