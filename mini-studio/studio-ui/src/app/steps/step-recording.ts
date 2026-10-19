import { Component, inject } from '@angular/core';

import { fmtTime } from '../core/models';
import { ProjectStore } from '../core/project-store';

@Component({
  selector: 'app-step-recording',
  template: `
    @if (store.project(); as p) {
      <div class="layout">
        <video [src]="'/api/projects/' + p.id + '/video'" controls preload="metadata"></video>
        <section class="card">
          <div class="card-head"><h3>About this recording</h3></div>
          <dl>
            <dt>File</dt><dd>{{ p.name }}</dd>
            <dt>Duration</dt><dd>{{ fmtTime(p.duration) }}</dd>
            <dt>Folder</dt><dd class="muted small">{{ p.file }}</dd>
          </dl>
          <p class="muted small note">Subtitles and Shorts are optional. Background removal and the thumbnail are required before
            uploading. Everything is saved in <code>work/{{ p.id }}/</code>; the recording itself is never changed.</p>
        </section>
      </div>
    }
  `,
  styles: `
    .layout { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; align-items: start; }
    @media (max-width: 900px) { .layout { grid-template-columns: 1fr; } }
    dl { display: grid; grid-template-columns: auto 1fr; gap: 6px 14px; margin: 0; }
    dt { font-size: 12px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; padding-top: 2px; }
    dd { margin: 0; overflow-wrap: anywhere; font-weight: 600; }
    .note { margin-top: 16px; }
  `,
})
export class StepRecording {
  readonly store = inject(ProjectStore);
  readonly fmtTime = fmtTime;
}
