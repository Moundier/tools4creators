import { Component, input, output } from '@angular/core';

import { Icon } from './icon';

/** Button that opens a file dialog for one image. */
@Component({
  selector: 'app-image-picker',
  imports: [Icon],
  template: `
    <input #f type="file" accept="image/png,image/jpeg,image/webp" hidden (change)="pick(f)" />
    <button type="button" class="btn" [class]="variant()" [disabled]="disabled()" (click)="f.click()">
      <app-icon [name]="icon()" /> {{ label() }}
    </button>
  `,
  styles: `:host { display: inline-flex; }`,
})
export class ImagePicker {
  label = input('Choose image');
  icon = input('upload');
  variant = input('btn-secondary');
  disabled = input(false);
  picked = output<File>();

  pick(el: HTMLInputElement) {
    const file = el.files?.[0];
    if (file) this.picked.emit(file);
    el.value = '';
  }
}
