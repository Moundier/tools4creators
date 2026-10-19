import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { Api } from '../core/api';
import { TemplateFamily, TemplateInfo, fmtTime } from '../core/models';
import { ProjectStore } from '../core/project-store';
import { Icon } from '../shared/icon';
import { ImagePicker } from '../shared/image-picker';
import { JobProgress } from '../shared/job-progress';

const ALL = 'all';  // pseudo tab: every family

/** Required: render the GIMP templates with your cutout (one family tab at a time, or All) and pick one. */
@Component({
  selector: 'app-step-thumbnail',
  imports: [FormsModule, Icon, ImagePicker, JobProgress],
  template: `
    @if (store.project(); as p) {
      <div class="layout">
        <aside class="card side">
          <label class="field"><span>Thumbnail title</span>
            <input [(ngModel)]="title" placeholder="VAZOU / DE NOVO" />
            <div class="hints"><span>Use / to choose where lines break</span>
              <span class="end" [class.warn]="length(title) > 46">{{ length(title) }} chars</span></div></label>
          @if (length(title) > 22) {
            <p class="callout warn small">Long title: some templates get small text. The previews say which ones are over their
              recommended length. Short, punchy titles (under ~30 characters) work best.</p>
          }
          <label class="field"><span>Second text <span class="muted small">optional</span></span>
            <input [(ngModel)]="subtitle" placeholder="...SÓ PORQUE EU QUERO / ROUBÁ-LOS?" />
            <div class="hints"><span>Speech bubble, lyric video label, documentary info line</span></div></label>
          <div class="field"><span>Color</span>
            <div class="color-row">
              <div class="segmented">
                <label><input type="radio" name="color" [checked]="color === null" (change)="color = null" /><span>Template default</span></label>
                <label><input type="radio" name="color" [checked]="color !== null" (change)="color = customColor" /><span>Custom</span></label>
              </div>
              @if (color !== null) {
                <input type="color" class="picker" aria-label="Custom color" [ngModel]="customColor" (ngModelChange)="pick($event)" />
                <input class="hex" aria-label="Hex code" maxlength="7" spellcheck="false" [ngModel]="customColor"
                       (ngModelChange)="typed($event)" />
              }
            </div>
            @if (color !== null && savedColors().length) {
              <div class="swatches-row" role="radiogroup" aria-label="Saved colors">
                @for (c of savedColors(); track c) {
                  <span class="saved-color" [class.on]="c === color">
                    <button type="button" role="radio" [attr.aria-checked]="c === color" (click)="pick(c)">
                      <i [style.background]="c"></i>{{ c.toUpperCase() }}</button>
                    <button type="button" class="forget" title="Forget this color" (click)="forget(c)">
                      <app-icon name="x" [size]="12" /></button>
                  </span>
                }
              </div>
            }
            <div class="hints"><span>Custom colors you render with are saved for your next thumbnails</span></div></div>

          <div class="group">
            <h4>Background (game art)</h4>
            <div class="row">
              @if (p.files.bg) { <img class="mini" [src]="store.file(p.files.bg)" alt="background" /> }
              <app-image-picker label="Upload" variant="btn-secondary btn-sm" (picked)="upload('bg', $event)" />
              @if (p.files.bg) { <button class="btn btn-icon btn-sm" title="Remove" (click)="remove('bg')"><app-icon name="x" [size]="16" /></button> }
            </div>
            <video [src]="'/api/projects/' + p.id + '/video'" controls preload="metadata" class="small-vid"
                   (timeupdate)="vidT.set($any($event.target).currentTime)"></video>
            <button class="btn btn-ghost btn-sm frame-btn" (click)="bgFromVideo()"><app-icon name="camera" [size]="16" /> Use frame at {{ fmtTime(vidT()) }}</button>
          </div>

          <div class="group">
            <h4>Extra images <span class="muted small">optional</span></h4>
            @for (slot of ['art', 'art2']; track slot) {
              <div class="row slot">
                <span class="lbl small">{{ slot === 'art' ? 'Game logo' : 'Second logo' }}</span>
                @if ($any(p.files)[slot]) { <img class="mini checker" [src]="store.file($any(p.files)[slot])" alt="" /> }
                <span class="grow"></span>
                <app-image-picker label="Upload" variant="btn-ghost btn-sm" (picked)="upload(slot, $event)" />
                @if ($any(p.files)[slot]) { <button class="btn btn-icon btn-sm" title="Remove" (click)="remove(slot)"><app-icon name="x" [size]="16" /></button> }
              </div>
            }
          </div>

          @if (needsNews()) {
            <div class="group">
              <h4>News for the magazines</h4>
              <p class="muted small">Claude Code finds a picture for each one and writes its cover text (small line / big line).
                Edit the cover text if you like.</p>
              @for (n of news; track $index; let i = $index) {
                <div class="news">
                  @if (pictureOf(n); as f) { <img class="mini news-img" [src]="store.file('news/' + f)" alt="" /> }
                  @else { <span class="mini news-img none" [title]="searched(n) ? 'No picture found' : 'Not searched yet'">?</span> }
                  <input [(ngModel)]="news[i]" [placeholder]="'News ' + (i + 1) + ', e.g. ' + examples[i % examples.length]" />
                  <button class="btn btn-icon btn-sm" title="Remove" (click)="news.splice(i, 1); covers.splice(i, 1)">
                    <app-icon name="x" [size]="16" /></button>
                  <input class="cover" [(ngModel)]="covers[i]" placeholder="Cover text, e.g. DISCO POLÊMICO DE / GTA VI" />
                </div>
              }
              <div class="row">
                <button class="btn btn-ghost btn-sm" (click)="news.push(''); covers.push('')"><app-icon name="plus" [size]="16" /> Add news</button>
                <span class="grow"></span>
                <button class="btn btn-secondary btn-sm" [disabled]="!newsList().length || store.busy('news')" (click)="findImages()">
                  <app-icon name="search" [size]="16" /> Find images</button>
              </div>
              <app-job-progress [job]="store.jobs()['news']" />
            </div>
          }

          <button class="btn btn-primary btn-block" [disabled]="!title.trim() || store.busy('thumbnails')" (click)="render()">
            <app-icon name="sparkles" /> Render {{ label(tab()) }}{{ inTab(p.thumbnail.rendered).length ? ' again' : '' }}</button>
          <app-job-progress [job]="store.jobs()['thumbnails']" />
        </aside>

        <section>
          <div class="tabs" role="tablist">
            @for (f of tabs(); track f.id) {
              <button role="tab" [class.active]="tab() === f.id" [attr.aria-selected]="tab() === f.id" (click)="tab.set(f.id)">
                @if (namesOf(f.id, p.thumbnail.rendered).length) { <app-icon name="check" [size]="14" [stroke]="3" /> }
                {{ f.label }}<span class="count">{{ namesOf(f.id).length }}</span></button>
            }
          </div>
          @let shown = inTab(p.thumbnail.rendered);
          @if (shown.length) {
            <div class="card-head"><h3>Pick one</h3>
              @if (p.thumbnail.template) {
                <a class="btn btn-ghost btn-sm" [href]="store.file('thumbs/' + p.thumbnail.template + '.xcf')" download>
                  <app-icon name="download" [size]="16" /> .xcf (edit in GIMP)</a>
              }
            </div>
            <div class="gallery">
              @for (name of shown; track name) {
                <button class="thumb" [class.chosen]="p.thumbnail.template === name" (click)="choose(name)" [title]="describe(name)">
                  <img [src]="store.file('thumbs/' + name + '.png')" loading="lazy" [alt]="name" />
                  <span class="cap">
                    @if (p.thumbnail.template === name) { <app-icon name="check" [size]="14" [stroke]="3" /> }
                    <span class="grow">{{ name }}</span>
                    @if (over(name, p.thumbnail.title); as n) {
                      <b class="long" [title]="'Looks best up to ' + limit(name) + ' characters'">{{ n }} chars too long</b>
                    }
                  </span>
                </button>
              }
            </div>
          } @else {
            <div class="card empty muted">
              <app-icon name="image" [size]="40" [stroke]="1.5" />
              <p>Type a title and render: the {{ namesOf(tab()).length }} {{ label(tab()) }} templates are made with your cutout, then you pick the best.</p>
            </div>
          }
        </section>
      </div>
    }
  `,
  styles: `
    .tabs { margin-bottom: 16px; }
    .layout { display: grid; grid-template-columns: 340px 1fr; gap: 24px; align-items: start; }
    @media (max-width: 1000px) { .layout { grid-template-columns: 1fr; } }
    .side { display: grid; gap: 16px; }
    .group { display: grid; gap: 8px; padding-top: 14px; border-top: 1px solid var(--line); }
    .mini { height: 40px; border-radius: 6px; }
    .small-vid { max-height: 150px; }
    .frame-btn { justify-self: start; }
    .color-row { display: flex; gap: 10px; align-items: center; }
    .hex { width: 90px; font-family: monospace; text-transform: uppercase; }
    .swatches-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
    .saved-color { display: inline-flex; align-items: center; border: 1px solid var(--line); border-radius: 999px;
                   background: var(--soft); font: 12px monospace; }
    .saved-color.on { border-color: var(--green); box-shadow: 0 0 0 1px var(--green); }
    .saved-color button { border: 0; background: none; color: inherit; font: inherit; cursor: pointer;
                          display: inline-flex; align-items: center; gap: 6px; padding: 4px 4px 4px 8px; }
    .saved-color .forget { padding: 4px 8px 4px 2px; color: var(--muted); }
    .saved-color i { width: 14px; height: 14px; border-radius: 50%; border: 1px solid rgba(0, 0, 0, .2); }
    .picker { width: 44px; height: 32px; padding: 2px; border: 1px solid var(--line); border-radius: 6px; cursor: pointer; }
    .slot { gap: 8px; } .lbl { width: 84px; font-weight: 700; color: var(--muted); }
    .news { display: grid; grid-template-columns: 56px 1fr auto; gap: 6px 8px; align-items: center; }
    .news input { min-width: 0; }
    .news .cover { grid-column: 2 / 4; font-size: 13px; }
    .news-img { width: 56px; height: 40px; object-fit: cover; grid-row: span 2; }
    .news-img.none { display: grid; place-items: center; background: var(--soft); color: var(--muted); font-weight: 700; }
    .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }
    .thumb { all: unset; cursor: pointer; border-radius: var(--r); overflow: hidden; background: var(--card);
             border: 1px solid var(--line); box-shadow: var(--shadow-sm); transition: box-shadow .12s, border-color .12s; }
    .thumb img { width: 100%; display: block; aspect-ratio: 16/9; background: #000; }
    .thumb:hover { border-color: var(--purple-100); box-shadow: var(--shadow); }
    .thumb:focus-visible { box-shadow: var(--focus); }
    .cap { display: flex; align-items: center; gap: 6px; padding: 7px 10px; font-size: 12px; font-weight: 700; }
    .thumb.chosen { border-color: var(--green); box-shadow: 0 0 0 2px var(--green); }
    .thumb.chosen .cap { background: var(--green); color: #fff; }
    .long { color: var(--warn); font-size: 11px; } .thumb.chosen .long { color: #fff3c4; }
    .empty { padding: 48px; text-align: center; display: grid; justify-items: center; gap: 10px; }
  `,
})
export class StepThumbnail implements OnInit {
  readonly store = inject(ProjectStore);
  private api = inject(Api);
  readonly fmtTime = fmtTime;
  readonly templates = signal<TemplateInfo[]>([]);
  readonly families = signal<TemplateFamily[]>([]);
  readonly tab = signal('');
  readonly colors = signal<Record<string, string>>({});  // named themes -> hex (older projects saved a name)
  readonly vidT = signal(0);
  title = '';
  subtitle = '';
  news: string[] = [];
  covers: string[] = [];  // cover text per news row ("SMALL LINE / BIG LINE")
  readonly examples = ['Kojima novo jogo', 'GTA 6 trailer 3', 'Tokyo Game Show 2026', "Marvel's Wolverine"];
  color: string | null = null;  // null = each template's own color, else "#RRGGBB"
  customColor = '#6B2A8F';  // the picker's value, kept while "Template default" is on
  readonly savedColors = signal<string[]>([]);  // the channel's custom colors, most recent first

  async ngOnInit() {
    const t = this.store.project()!.thumbnail;
    this.title = t.title;
    this.subtitle = t.subtitle ?? '';
    this.news = (t.news ?? []).map((n) => n.text);
    this.covers = (t.news ?? []).map((n) => n.title ?? '');
    if (!this.news.length) { this.news = ['', '', '', '']; this.covers = ['', '', '', '']; }
    const res = await this.api.templates();
    this.templates.set(res.templates);
    this.families.set(res.families);
    this.colors.set(res.colors);
    this.color = t.color ? (res.colors[t.color] ?? t.color) : null;
    const lib = await this.api.library();
    this.savedColors.set(lib.colors);
    // a project that never rendered starts with your last custom color
    if (this.color === null && !t.rendered.length && lib.colors.length) this.color = lib.colors[0];
    if (this.color) this.customColor = this.color;
    this.tab.set(res.templates.find((x) => x.name === t.template)?.family ?? res.families[0]?.id ?? '');
  }

  /** The family tabs, plus an "All" tab first that renders every template. */
  tabs(): TemplateFamily[] { return [{ id: ALL, label: 'All' }, ...this.families()]; }

  label(family: string) { return this.tabs().find((f) => f.id === family)?.label ?? ''; }

  /** Template names of a family, optionally only those in `among` (e.g. the rendered ones). */
  namesOf(family: string, among?: string[]) {
    return this.templates().filter((t) => (family === ALL || t.family === family) && (!among || among.includes(t.name)))
      .map((t) => t.name);
  }

  inTab(among: string[]) { return this.namesOf(this.tab(), among); }

  /** Does a template in the open tab use the news list (collage magazines)? */
  needsNews() { return this.templates().some((t) => this.inTab([t.name]).length && t.needs?.includes('news')); }

  newsList() { return this.news.map((n) => n.trim()).filter(Boolean); }

  private saved(text: string) { return this.store.project()?.thumbnail.news?.find((n) => n.text === text.trim()); }
  pictureOf(text: string) { return this.saved(text)?.file ?? null; }
  searched(text: string) { return !!this.saved(text); }

  async findImages() {
    await this.store.run('news', `/projects/${this.store.id()}/news-images`, { news: this.newsList(), titles: this.titles() });
    // fill the cover texts Claude wrote into the rows that are still empty
    this.covers = this.news.map((n, i) => this.covers[i]?.trim() || this.saved(n)?.title || '');
  }

  /** Send the cover texts you typed, so the render (and a new search) use them. */
  private async saveCovers() {
    const titles = this.titles();
    if (Object.keys(titles).length) await this.api.put(`/projects/${this.store.id()}/news`, { titles });
  }

  /** {news text: cover text} for the rows with a cover text typed in. */
  private titles() {
    const titles: Record<string, string> = {};
    this.news.forEach((n, i) => { if (n.trim() && this.covers[i]?.trim()) titles[n.trim()] = this.covers[i].trim(); });
    return titles;
  }

  /** Title length as the templates count it ("/" and extra spaces ignored). */
  length(title: string) { return title.replace(/\//g, ' ').split(/\s+/).filter(Boolean).join(' ').length; }

  limit(name: string) { return this.templates().find((t) => t.name === name)?.max_chars ?? null; }

  over(name: string, title: string) {
    const max = this.limit(name);
    return max && this.length(title) > max ? this.length(title) - max : 0;
  }

  describe(name: string) { return this.templates().find((t) => t.name === name)?.description ?? name; }

  async upload(slot: string, file: File) {
    await this.api.uploadImage(this.store.id(), slot, file);
    await this.store.reload();
  }

  async remove(slot: string) {
    await this.api.delete(`/projects/${this.store.id()}/upload/${slot}`);
    await this.store.reload();
  }

  async bgFromVideo() {
    await this.api.post(`/projects/${this.store.id()}/bg-from-frame`, { t: this.vidT() });
    await this.store.reload();
  }

  pick(c: string) { this.customColor = this.color = c.toLowerCase(); }

  /** Hex typed by hand ("ff5fa8" or "#FF5FA8"): used once it is a full color. */
  typed(text: string) {
    const hex = '#' + text.trim().replace(/^#/, '');
    if (/^#[0-9a-fA-F]{6}$/.test(hex)) this.pick(hex);
  }

  async forget(c: string) {
    const res = await this.api.delete<{ colors: string[] }>(`/library/colors/${c.slice(1)}`);
    this.savedColors.set(res.colors);
  }

  async render() {
    if (this.needsNews()) await this.saveCovers();
    const job = this.store.run('thumbnails', `/projects/${this.store.id()}/thumbnails`, {
      title: this.title, subtitle: this.subtitle, color: this.color, templates: this.namesOf(this.tab()),
    });
    const c = this.color;  // the server saves it too: same order (most recent first, 12 at most)
    if (c) this.savedColors.update((all) => [c, ...all.filter((x) => x !== c)].slice(0, 12));
    return job;
  }

  async choose(name: string) {
    await this.api.post(`/projects/${this.store.id()}/thumbnail/choose`, { template: name });
    await this.store.reload();
  }
}
