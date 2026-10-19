import { Component, ElementRef, effect, input, output, signal, viewChild } from '@angular/core';

import { Box } from '../core/models';

export type BoxKind = 'face' | 'game';
const COLORS: Record<BoxKind, string> = { face: '#FF2D8A', game: '#4ade80' };

/** Draw rectangles on a video frame. Boxes are in source-video pixels. */
@Component({
  selector: 'app-box-selector',
  template: `
    <div #wrap class="wrap" (pointerdown)="down($event)" (pointermove)="move($event)" (pointerup)="up()"
         (pointercancel)="up()">
      <img #img [src]="src()" (load)="draw()" draggable="false" />
      <canvas #cv></canvas>
    </div>
  `,
  styles: `
    /* an invisible 12px grab ring (padding + equal negative margin, so the frame doesn't move):
       drags can start just outside the frame and snap to its edge */
    .wrap { position: relative; display: inline-block; max-width: calc(100% + 24px); margin: -12px; padding: 12px;
            box-sizing: border-box; user-select: none; cursor: crosshair; touch-action: none; }
    img { display: block; max-width: 100%; }
    canvas { position: absolute; inset: 12px; pointer-events: none; }
  `,
})
export class BoxSelector {
  src = input.required<string>();
  sourceWidth = input.required<number>(); // width of the real video, to convert display -> video pixels
  active = input<BoxKind>('face');
  boxes = input<Partial<Record<BoxKind, Box | null>>>({});
  boxChange = output<{ kind: BoxKind; box: Box }>();

  private img = viewChild.required<ElementRef<HTMLImageElement>>('img');
  private cv = viewChild.required<ElementRef<HTMLCanvasElement>>('cv');
  private wrap = viewChild.required<ElementRef<HTMLDivElement>>('wrap');
  private dragStart: [number, number] | null = null;
  private dragBox = signal<Box | null>(null); // display pixels while dragging

  constructor() {
    effect(() => { this.boxes(); this.dragBox(); this.draw(); });
  }

  private scale() {
    const el = this.img().nativeElement;
    return this.sourceWidth() / (el.clientWidth || 1);
  }

  private point(e: PointerEvent): [number, number] {
    const r = this.img().nativeElement.getBoundingClientRect();
    return [Math.max(0, Math.min(r.width, e.clientX - r.left)), Math.max(0, Math.min(r.height, e.clientY - r.top))];
  }

  down(e: PointerEvent) {
    this.dragStart = this.point(e);
    this.wrap().nativeElement.setPointerCapture(e.pointerId);
  }

  move(e: PointerEvent) {
    if (!this.dragStart) return;
    const [x0, y0] = this.dragStart, [x1, y1] = this.point(e);
    this.dragBox.set([Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0), Math.abs(y1 - y0)]);
  }

  up() {
    const b = this.dragBox();
    this.dragStart = null;
    this.dragBox.set(null);
    if (b && b[2] > 8 && b[3] > 8) {
      // convert the edges (not x/y/w/h) so a box dragged to the frame edge reaches the last video pixel
      const s = this.scale();
      const maxW = this.sourceWidth(), maxH = Math.round(this.img().nativeElement.clientHeight * s);
      const x0 = Math.round(b[0] * s), y0 = Math.round(b[1] * s);
      const x1 = Math.min(maxW, Math.round((b[0] + b[2]) * s)), y1 = Math.min(maxH, Math.round((b[1] + b[3]) * s));
      this.boxChange.emit({ kind: this.active(), box: [x0, y0, x1 - x0, y1 - y0] });
    }
  }

  draw() {
    const canvas = this.cv()?.nativeElement, el = this.img()?.nativeElement;
    if (!canvas || !el) return;
    canvas.width = el.clientWidth;
    canvas.height = el.clientHeight;
    const ctx = canvas.getContext('2d')!;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const s = this.scale();
    const rect = (b: Box, color: string, label: string) => {
      ctx.strokeStyle = color; ctx.lineWidth = 3; ctx.setLineDash([]);
      ctx.fillStyle = color + '33';
      ctx.fillRect(b[0], b[1], b[2], b[3]); ctx.strokeRect(b[0], b[1], b[2], b[3]);
      ctx.fillStyle = color; ctx.font = 'bold 14px Inter, system-ui, sans-serif';
      ctx.fillText(label, b[0] + 6, b[1] + 18);
    };
    for (const kind of ['game', 'face'] as BoxKind[]) {
      const b = this.boxes()[kind];
      if (b) rect(b.map((v) => v / s) as Box, COLORS[kind], kind === 'face' ? 'FACECAM' : 'GAMEPLAY');
    }
    const d = this.dragBox();
    if (d) rect(d, COLORS[this.active()], '');
  }
}
