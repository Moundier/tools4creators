import { Component, computed, input } from '@angular/core';

/** Stroke icons (24x24, Lucide-style paths), so no icon font or UI library is needed. */
const ICONS: Record<string, string[]> = {
  upload: ['M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4', 'M17 8l-5-5-5 5', 'M12 3v12'],
  download: ['M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4', 'M7 10l5 5 5-5', 'M12 15V3'],
  refresh: ['M21 12a9 9 0 1 1-3-6.7L21 8', 'M21 3v5h-5'],
  settings: ['M4 21v-7', 'M4 10V3', 'M12 21v-9', 'M12 8V3', 'M20 21v-5', 'M20 12V3', 'M1 14h6', 'M9 8h6', 'M17 16h6'],
  video: ['M3 5h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z', 'M17 10l5-3v10l-5-3'],
  trash: ['M3 6h18', 'M8 6V4h8v2', 'M19 6l-1 14H6L5 6', 'M10 11v6', 'M14 11v6'],
  back: ['M19 12H5', 'M12 19l-7-7 7-7'],
  next: ['M5 12h14', 'M12 5l7 7-7 7'],
  check: ['M20 6L9 17l-5-5'],
  'check-all': ['M18 6L7 17l-5-5', 'M22 10l-7.5 7.5L13 16'],
  scissors: ['M9 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0z', 'M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0z', 'M20 4L8.1 15.9', 'M14.5 14.5L20 20', 'M8.1 8.1L12 12'],
  sparkles: ['M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z', 'M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z'],
  camera: ['M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z', 'M16 13a4 4 0 1 1-8 0 4 4 0 0 1 8 0z'],
  cloud: ['M16 16l-4-4-4 4', 'M12 12v9', 'M20.4 18.4A5 5 0 0 0 18 9h-1.3A8 8 0 1 0 3 16.3'],
  save: ['M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z', 'M17 21v-8H7v8', 'M7 3v5h8'],
  login: ['M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4', 'M10 17l5-5-5-5', 'M15 12H3'],
  more: ['M5 12h.01', 'M12 12h.01', 'M19 12h.01'],
  x: ['M18 6L6 18', 'M6 6l12 12'],
  user: ['M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2', 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0z'],
  captions: ['M3 5h18a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z', 'M6 12h4', 'M14 12h4', 'M6 15h12'],
  clapper: ['M4 11v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8H4z', 'M4 11l-.9-3.4a1 1 0 0 1 .7-1.2L17.3 2.8a1 1 0 0 1 1.2.7L19.4 7 4 11z'],
  'mark-in': ['M19 20L9 12l10-8v16z', 'M5 19V5'],
  'mark-out': ['M5 4l10 8-10 8V4z', 'M19 5v14'],
  alert: ['M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z', 'M12 9v4', 'M12 17h.01'],
  undo: ['M3 7v6h6', 'M21 17a9 9 0 0 0-15-6.7L3 13'],
  image: ['M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z', 'M21 15l-5-5L5 21', 'M10 8.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0z'],
  external: ['M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6', 'M15 3h6v6', 'M10 14L21 3'],
  folder: ['M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z'],
  record: ['M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z'],
  webcam: ['M12 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14z', 'M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6z', 'M8 21h8', 'M12 17v4'],
  timer: ['M12 22a8 8 0 1 0 0-16 8 8 0 0 0 0 16z', 'M12 10v4l2 2', 'M10 2h4'],
  mic: ['M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z', 'M19 10v2a7 7 0 0 1-14 0v-2', 'M12 19v3'],
  menu: ['M3 6h18', 'M3 12h18', 'M3 18h18'],
  edit: ['M12 20h9', 'M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z'],
  plus: ['M12 5v14', 'M5 12h14'],
  search: ['M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z', 'M21 21l-4.3-4.3'],
  'chevron-left': ['M15 18l-6-6 6-6'],
  'chevron-right': ['M9 18l6-6-6-6'],
  first: ['M6 5v14', 'M17 18l-6-6 6-6'],
  last: ['M18 5v14', 'M7 18l6-6-6-6'],
};

@Component({
  selector: 'app-icon',
  template: `
    <svg [attr.width]="size()" [attr.height]="size()" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         [attr.stroke-width]="stroke()" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      @for (d of paths(); track $index) { <path [attr.d]="d" /> }
    </svg>
  `,
  styles: `:host { display: inline-flex; flex: none; } svg { display: block; }`,
})
export class Icon {
  name = input.required<string>();
  size = input(18);
  stroke = input(2);
  readonly paths = computed(() => ICONS[this.name()] ?? ICONS['x']);
}
