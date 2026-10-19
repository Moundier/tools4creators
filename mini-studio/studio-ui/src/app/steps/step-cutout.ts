import { Component, OnInit, inject, signal } from '@angular/core';

import { Api } from '../core/api';
import { Library } from '../core/models';
import { ProjectStore } from '../core/project-store';
import { Confirm } from '../shared/confirm-dialog';
import { Icon } from '../shared/icon';
import { ImagePicker } from '../shared/image-picker';
import { WebcamCapture } from '../shared/webcam-capture';
import { JobProgress } from '../shared/job-progress';

/** Required: upload a photo of you, rembg removes the background. Photos saved to the channel's library are reused
 *  in other projects without removing the background again. */
@Component({
  selector: 'app-step-cutout',
  imports: [Icon, ImagePicker, JobProgress, WebcamCapture],
  template: `
    @if (store.project(); as p) {
      <section class="card">
        <div class="card-head">
          <h3>Your photo</h3>
          @if (p.files.person && !store.busy('cutout') && !camera()) {
            <button class="btn btn-ghost" (click)="cut()"><app-icon name="refresh" /> Remove background again</button>
          }
          @if (p.files.cutout && !store.busy('cutout') && !camera()) {
            @if (lib()?.current) {
              <span class="saved muted"><app-icon name="check" [size]="16" /> Saved for reuse</span>
            } @else {
              <button class="btn btn-secondary" (click)="save()"><app-icon name="save" /> Save for reuse</button>
            }
          }
          @if (!camera()) {
            <button class="btn" [class.btn-primary]="!p.files.person" [class.btn-secondary]="p.files.person"
                    [disabled]="store.busy('cutout')" (click)="camera.set(true)"><app-icon name="webcam" /> Use webcam</button>
            <app-image-picker [label]="p.files.person ? 'Upload another photo' : 'Upload photo'" icon="upload"
                              variant="btn-secondary" [disabled]="store.busy('cutout')" (picked)="upload($event)" />
          }
        </div>
        <p class="muted">The AI (BiRefNet portrait) removes the background, and the cutout is used in every thumbnail template.
          Best results: waist-up or head-and-shoulders, good light. Your face is placed automatically in each template.</p>
        <app-job-progress [job]="store.jobs()['cutout']" />

        @if (camera()) {
          <div class="camera"><app-webcam-capture (captured)="fromCamera($event)" (cancel)="camera.set(false)" /></div>
        } @else if (p.files.person) {
          <div class="trio">
            <figure><img class="preview" [src]="store.file(p.files.person)" alt="photo" /><figcaption>Original</figcaption></figure>
            @if (p.files.cutout) {
              <figure><div class="checker frame"><img class="preview" [src]="store.file('cutout.png')" alt="cutout" /></div>
                <figcaption><app-icon name="check" [size]="16" /> Background removed</figcaption></figure>
              <figure><div class="dark frame"><img class="preview" [src]="store.file('cutout.png')" alt="cutout on dark" /></div>
                <figcaption>On dark (leftovers show up here)</figcaption></figure>
            }
          </div>
        } @else {
          <div class="drop muted"><app-icon name="image" [size]="40" [stroke]="1.5" /><p>No photo yet: use your webcam or upload one</p></div>
        }
      </section>

      @if (lib()?.photos?.length && !camera()) {
        <section class="card library">
          <div class="card-head"><h3>Saved photos</h3></div>
          <p class="muted">Pick one to use it here: its background is already removed.</p>
          <div class="shelf">
            @for (ph of lib()!.photos; track ph.id) {
              <div class="item" [class.current]="ph.id === lib()!.current">
                <button class="pick checker" [disabled]="store.busy('cutout')" (click)="use(ph.id)"
                        [title]="ph.id === lib()!.current ? 'In use' : 'Use this photo'">
                  <img [src]="api.libraryFile(ph.id, 'cutout')" alt="saved cutout" />
                </button>
                <button class="btn btn-icon btn-sm del" title="Delete from saved photos" (click)="remove(ph.id)">
                  <app-icon name="trash" [size]="16" /></button>
              </div>
            }
          </div>
        </section>
      }
    }
  `,
  styles: `
    .trio { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 320px)); gap: 20px; margin-top: 18px; }
    figure { margin: 0; } figcaption { margin-top: 8px; font-weight: 700; display: flex; align-items: center; gap: 6px; font-size: 14px; }
    figcaption app-icon { color: var(--ok); }
    .frame { border-radius: var(--r); overflow: hidden; } .dark { background: #1a1a1a; }
    .camera { margin-top: 18px; }
    .saved { display: inline-flex; align-items: center; gap: 6px; font-weight: 700; } .saved app-icon { color: var(--ok); }
    .library { margin-top: 20px; }
    .shelf { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; }
    .item { position: relative; }
    .pick { display: block; width: 120px; height: 150px; padding: 0; border: 2px solid var(--line); border-radius: var(--r);
            overflow: hidden; cursor: pointer; }
    .pick:hover { border-color: var(--purple-100); } .current .pick { border-color: var(--green); }
    .pick img { width: 100%; height: 100%; object-fit: contain; }
    .del { position: absolute; top: 4px; right: 4px; }
    .drop { margin-top: 18px; border: 2px dashed var(--line-strong); border-radius: var(--r-lg); padding: 40px;
            display: grid; justify-items: center; gap: 8px; }
  `,
})
export class StepCutout implements OnInit {
  readonly store = inject(ProjectStore);
  readonly api = inject(Api);
  private confirm = inject(Confirm);
  readonly camera = signal(false);  // webcam panel open
  readonly lib = signal<Library | null>(null);

  ngOnInit() { return this.loadLibrary(); }

  async loadLibrary() { this.lib.set(await this.api.library(this.store.id())); }

  async fromCamera(file: File) {
    this.camera.set(false);
    await this.upload(file);
  }

  async upload(file: File) {
    await this.api.uploadImage(this.store.id(), 'person', file);
    await this.store.reload();
    await this.loadLibrary();
    const saved = this.lib()?.current;  // the same picture was saved before: reuse its cutout
    await (saved ? this.use(saved) : this.cut());
  }

  async cut() {
    await this.store.run('cutout', `/projects/${this.store.id()}/cutout`);
    await this.loadLibrary();
  }

  async save() {
    await this.api.post(`/projects/${this.store.id()}/library/save`);
    await this.loadLibrary();
  }

  async use(photo: string) {
    await this.api.post(`/projects/${this.store.id()}/library/use/${photo}`);
    await this.store.reload();
    await this.loadLibrary();
  }

  async remove(photo: string) {
    const ok = await this.confirm.ask({ title: 'Delete this saved photo?', confirm: 'Delete',
      message: 'It is removed from the saved photos. Projects already using it keep their copy.' });
    if (!ok) return;
    await this.api.delete(`/library/photos/${photo}`);
    await this.loadLibrary();
  }
}
