import { Component, input } from '@angular/core';

import { Job } from '../core/models';

/** Spinner for a background job (+ progress bar and % when the job reports progress). The job's message
 * is only a tooltip / screen-reader label. */
@Component({
  selector: 'app-job-progress',
  template: `
    @if (job(); as j) {
      @if (j.status === 'queued' || j.status === 'running') {
        <div class="job" role="status" [attr.aria-label]="j.message || 'Working'" [title]="j.message || ''">
          <span class="spinner"></span>
          @if (j.progress != null) {
            <div class="progress"><i [style.width.%]="j.progress * 100"></i></div>
            <span class="muted small pct">{{ (j.progress * 100).toFixed(0) }}%</span>
          }
        </div>
      } @else if (j.status === 'error') {
        <div class="callout err">{{ j.error }}</div>
      }
    }
  `,
  styles: `
    .job { display: flex; align-items: center; gap: 10px; margin: 12px 0; min-height: 22px; }
    .progress { flex: 1; }
    .pct { min-width: 3ch; text-align: right; font-variant-numeric: tabular-nums; }
    .callout { margin: 12px 0; white-space: pre-wrap; }
  `,
})
export class JobProgress {
  job = input<Job | undefined>();
}
