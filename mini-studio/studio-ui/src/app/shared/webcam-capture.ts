import { Component, ElementRef, OnDestroy, OnInit, output, signal, viewChild } from '@angular/core';

import { Icon } from './icon';

type State = 'starting' | 'live' | 'countdown' | 'shot' | 'error';

/** Live webcam preview with a framing guide; shoot -> review -> emits the photo as a JPEG File. */
@Component({
  selector: 'app-webcam-capture',
  imports: [Icon],
  template: `
    <div class="cam">
      @if (state() === 'error') {
        <div class="callout err">
          <b>{{ error().title }}</b>
          <p>{{ error().help }}</p>
          <div class="row"><button class="btn btn-secondary btn-sm" (click)="start()"><app-icon name="refresh" [size]="16" /> Try again</button></div>
        </div>
      } @else {
        <div class="stage" [style.aspect-ratio]="aspect()">
          <video #video autoplay playsinline muted [hidden]="state() === 'shot'"></video>
          @if (state() === 'shot') { <img class="still" [src]="shotUrl()" alt="your photo" /> }
          @if (state() === 'live' || state() === 'countdown') {
            <svg class="guide" viewBox="0 0 160 90" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
              <ellipse cx="80" cy="33" rx="13" ry="17" />
              <path d="M44 90 C46 72 58 63 70 61 L90 61 C102 63 114 72 116 90" />
              <rect x="64" y="20" width="32" height="30" rx="3" class="face" />
            </svg>
            <span class="tip">Keep your face in the box and your shoulders in view · plain background · good light</span>
          }
          @if (state() === 'countdown') { <span class="count">{{ count() }}</span> }
          @if (state() === 'starting') { <span class="center muted">Starting camera…</span> }
          @if (res()) { <span class="res">{{ res() }}</span> }
          @if (flash()) { <span class="flash"></span> }
        </div>

        <div class="row controls">
          @if (cameras().length > 1 && state() !== 'shot') {
            <select class="inline-input" [value]="deviceId()" (change)="switchCamera($any($event.target).value)" title="Camera">
              @for (c of cameras(); track c.deviceId; let i = $index) {
                <option [value]="c.deviceId">{{ c.label || 'Camera ' + (i + 1) }}</option>
              }
            </select>
          }
          @if (state() !== 'shot') {
            <label class="check"><input type="checkbox" [checked]="timer()" (change)="timer.set($any($event.target).checked)" />
              <app-icon name="timer" [size]="16" /> 3 s timer</label>
          }
          <span class="grow"></span>
          <button class="btn btn-ghost" (click)="cancel.emit()">Cancel</button>
          @if (state() === 'shot') {
            <button class="btn btn-secondary" (click)="retake()"><app-icon name="refresh" /> Retake</button>
            <button class="btn btn-primary" (click)="use()"><app-icon name="check" /> Use this photo</button>
          } @else {
            <button class="btn btn-primary" [disabled]="state() !== 'live'" (click)="shoot()"><app-icon name="camera" /> Shoot</button>
          }
        </div>
      }
    </div>
  `,
  styles: `
    .cam { display: grid; gap: 12px; }
    .stage { position: relative; width: 100%; max-width: 860px; max-height: 70vh; margin: 0 auto; background: #111;
             border-radius: var(--r-lg); overflow: hidden; }
    video, .still { width: 100%; height: 100%; object-fit: contain; display: block; border-radius: 0; }
    video { transform: scaleX(-1); }  /* mirrored like a selfie camera; the saved photo is mirrored the same way */
    .guide { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
    .guide ellipse, .guide path { fill: none; stroke: rgba(255,255,255,.75); stroke-width: .6; stroke-dasharray: 2 1.5; }
    .guide .face { fill: none; stroke: #ff2d8a; stroke-width: .5; opacity: .9; }
    .tip { position: absolute; left: 50%; bottom: 12px; transform: translateX(-50%); width: max-content; max-width: 92%;
           background: rgba(0,0,0,.6); color: #fff; font-size: 12px; padding: 5px 12px; border-radius: 999px; text-align: center; }
    .res { position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,.65); color: #fff; font-size: 12px;
           font-weight: 700; padding: 3px 9px; border-radius: 6px; }
    .count { position: absolute; inset: 0; display: grid; place-items: center; font-size: 120px; font-weight: 900; color: #fff;
             text-shadow: 0 4px 30px rgba(0,0,0,.6); }
    .center { position: absolute; inset: 0; display: grid; place-items: center; color: #bbb; }
    .flash { position: absolute; inset: 0; background: #fff; animation: flash .35s ease-out forwards; }
    @keyframes flash { from { opacity: .9; } to { opacity: 0; } }
    .controls { max-width: 860px; width: 100%; margin: 0 auto; }
    .callout p { margin: 6px 0 10px; }
  `,
})
export class WebcamCapture implements OnInit, OnDestroy {
  readonly captured = output<File>();
  readonly cancel = output<void>();

  readonly state = signal<State>('starting');
  readonly res = signal('');
  readonly aspect = signal('16 / 9');
  readonly cameras = signal<MediaDeviceInfo[]>([]);
  readonly deviceId = signal('');
  readonly timer = signal(false);
  readonly count = signal(3);
  readonly flash = signal(false);
  readonly shotUrl = signal('');
  readonly error = signal({ title: '', help: '' });

  private video = viewChild<ElementRef<HTMLVideoElement>>('video');
  private stream: MediaStream | null = null;
  private shotBlob: Blob | null = null;
  private countdown?: ReturnType<typeof setInterval>;

  ngOnInit() { this.start(); }

  ngOnDestroy() { this.stop(); }

  async start(deviceId = this.deviceId()) {
    this.stop();
    this.state.set('starting');
    if (!navigator.mediaDevices?.getUserMedia) {
      return this.fail('Camera not available', 'This browser does not allow camera access on this page.');
    }
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { ...(deviceId ? { deviceId: { exact: deviceId } } : {}), width: { ideal: 1920 }, height: { ideal: 1080 } },
      });
    } catch (e: any) {
      const name = e?.name ?? '';
      if (name === 'NotAllowedError' || name === 'SecurityError') {
        return this.fail('Camera permission was blocked',
          'Click the camera icon in the address bar, choose "Allow", then press Try again.');
      }
      if (name === 'NotFoundError' || name === 'OverconstrainedError') {
        return this.fail('No camera found', 'Connect a webcam (or start OBS Virtual Camera) and press Try again.');
      }
      if (name === 'NotReadableError' || name === 'AbortError') {
        return this.fail('The camera is busy', 'Another app (OBS, Discord, a video call) is using it. Close it there and press Try again.');
      }
      return this.fail('Could not start the camera', String(e?.message ?? e));
    }
    const track = this.stream.getVideoTracks()[0];
    const s = track.getSettings();
    this.deviceId.set(s.deviceId ?? '');
    if (s.width && s.height) {
      this.res.set(`${s.width}×${s.height}${s.frameRate ? ' · ' + Math.round(s.frameRate) + ' fps' : ''}`);
      this.aspect.set(`${s.width} / ${s.height}`);
    }
    this.cameras.set((await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === 'videoinput'));
    this.state.set('live');
    queueMicrotask(() => this.attach());
  }

  private attach() {
    const el = this.video()?.nativeElement;
    if (el && this.stream) {
      el.srcObject = this.stream;
      el.play().catch(() => {});
    }
  }

  private fail(title: string, help: string) {
    this.stop();
    this.error.set({ title, help });
    this.state.set('error');
  }

  stop() {
    clearInterval(this.countdown);
    this.stream?.getTracks().forEach((t) => t.stop());  // turns the webcam light off
    this.stream = null;
  }

  switchCamera(id: string) { this.start(id); }

  shoot() {
    if (!this.timer()) return this.capture();
    this.count.set(3);
    this.state.set('countdown');
    this.countdown = setInterval(() => {
      if (this.count() > 1) {
        this.count.update((c) => c - 1);
      } else {
        clearInterval(this.countdown);
        this.capture();
      }
    }, 1000);
  }

  private capture() {
    const v = this.video()?.nativeElement;
    if (!v || !v.videoWidth) return;
    const canvas = document.createElement('canvas');
    canvas.width = v.videoWidth;   // full camera resolution
    canvas.height = v.videoHeight;
    const ctx = canvas.getContext('2d')!;
    ctx.setTransform(-1, 0, 0, 1, canvas.width, 0);  // mirror, so the photo matches the preview
    ctx.drawImage(v, 0, 0);
    this.flash.set(true);
    setTimeout(() => this.flash.set(false), 350);
    canvas.toBlob((blob) => {
      if (!blob) return;
      this.shotBlob = blob;
      URL.revokeObjectURL(this.shotUrl());
      this.shotUrl.set(URL.createObjectURL(blob));
      this.state.set('shot');
    }, 'image/jpeg', 0.92);
  }

  retake() {
    this.shotBlob = null;
    this.state.set('live');
    queueMicrotask(() => this.attach());
  }

  use() {
    if (!this.shotBlob) return;
    const d = new Date(), pad = (n: number) => String(n).padStart(2, '0');
    const name = `webcam_${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}.jpg`;
    this.stop();
    this.captured.emit(new File([this.shotBlob], name, { type: 'image/jpeg' }));
  }
}
