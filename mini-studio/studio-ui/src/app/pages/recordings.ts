import { Component, OnDestroy, OnInit, computed, effect, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Router, RouterLink } from '@angular/router';

import { Api } from '../core/api';
import { Recording, fmtSize } from '../core/models';
import { Search } from '../core/search';
import { Confirm, DISCARD } from '../shared/confirm-dialog';
import { Icon } from '../shared/icon';
import { Toast } from '../shared/toast';

type Tab = 'all' | 'new' | 'editing' | 'uploaded';

const SUBTITLE: Record<string, string> = {
  new: 'Not started', editing: 'In progress', uploaded: 'Uploaded to YouTube', recording: 'Recording in OBS…',
};

/** Recordings OBS saved in the watch folder, as a YouTube Studio-style table with tabs and pages. */
@Component({
  selector: 'app-recordings',
  imports: [DatePipe, RouterLink, Icon],
  template: `
    <h1>Recordings</h1>

    <div class="tabbar">
      <div class="tabs" role="tablist">
        @for (t of tabs; track t.id) {
          <button role="tab" [class.active]="tab() === t.id" [attr.aria-selected]="tab() === t.id" (click)="setTab(t.id)">
            {{ t.label }}<span class="count">{{ count(t.id) }}</span></button>
        }
      </div>
      <div class="where muted small">
        <span>Watching <code [title]="folder()">{{ folder() }}</code> · <a routerLink="/settings">change</a></span>
        <button class="btn btn-icon btn-sm" title="Refresh" aria-label="Refresh" (click)="refresh()"><app-icon name="refresh" [size]="16" /></button>
      </div>
    </div>

    <div class="table" role="table" aria-label="Recordings">
      <div class="tr th" role="row">
        <span role="columnheader">Video</span><span role="columnheader">Status</span>
        <span role="columnheader">Size</span><span role="columnheader">Modified</span>
      </div>

      @if (loading()) {
        <p class="empty muted">Loading recordings…</p>
      } @else if (!shown().length) {
        <div class="empty">
          <app-icon name="folder" [size]="40" [stroke]="1.5" />
          <p>{{ search.text() ? 'No recording matches "' + search.text() + '".'
               : tab() === 'new' || tab() === 'all' ? 'No recordings yet. Record something in OBS and it shows up here.'
               : 'Nothing here yet.' }}</p>
        </div>
      }

      @for (r of page(); track r.name) {
        <div class="tr" role="row" [class.disabled]="r.status === 'recording'">
          <button class="open" role="cell" [disabled]="r.status === 'recording'" (click)="open(r)" [attr.aria-label]="'Open ' + r.name">
            <span class="thumb">
              @if (r.status !== 'recording') { <img [src]="poster(r)" loading="lazy" alt="" /> }
              @else { <span class="live"><app-icon name="record" [size]="16" /></span> }
              @if (r.duration != null) { <span class="dur">{{ badge(r.duration) }}</span> }
            </span>
            <span class="text">
              <span class="name" [title]="r.name">{{ r.name }}</span>
              <span class="sub">{{ subtitle(r) }}@if (r.elsewhere?.length) { · also in {{ r.elsewhere!.join(', ') }} }</span>
              <span class="mobile-meta"><span class="chip" [class]="r.status">{{ r.status }}</span>
                {{ r.mtime * 1000 | date: 'MMM d, y' }}</span>
            </span>
          </button>
          <span role="cell" class="col"><span class="chip" [class]="r.status">{{ r.status }}</span></span>
          <span role="cell" class="col">{{ fmtSize(r.size) }}</span>
          <span role="cell" class="col">{{ r.mtime * 1000 | date: 'MMM d, y' }}
            <span class="sub">{{ r.mtime * 1000 | date: 'HH:mm' }}</span></span>
          <div class="acts">
            @if (r.status === 'editing' || r.status === 'uploaded') {
              <button class="btn btn-icon btn-sm" title="Discard changes" aria-label="Discard changes" (click)="discard(r)">
                <app-icon name="undo" [size]="16" /></button>
            }
            @if ((tab() === 'all' || tab() === 'new') && r.status !== 'recording') {
              <button class="btn btn-icon btn-sm danger" title="Delete video from this computer" aria-label="Delete video"
                      (click)="deleteVideo(r)"><app-icon name="trash" [size]="16" /></button>
            }
          </div>
        </div>
      }

      @if (shown().length) {
        <div class="pager">
          <label class="rows">Rows per page
            <select [value]="size()" (change)="setSize(+$any($event.target).value)">
              @for (n of sizes; track n) { <option [value]="n" [selected]="n === size()">{{ n }}</option> }
            </select></label>
          <span>{{ from() }}–{{ to() }} of {{ shown().length }}</span>
          <button class="btn btn-icon" title="First page" aria-label="First page" [disabled]="pageIdx() === 0" (click)="pageIdx.set(0)">
            <app-icon name="first" [size]="20" /></button>
          <button class="btn btn-icon" title="Previous page" aria-label="Previous page" [disabled]="pageIdx() === 0"
                  (click)="pageIdx.set(pageIdx() - 1)"><app-icon name="chevron-left" [size]="20" /></button>
          <button class="btn btn-icon" title="Next page" aria-label="Next page" [disabled]="pageIdx() >= pages() - 1"
                  (click)="pageIdx.set(pageIdx() + 1)"><app-icon name="chevron-right" [size]="20" /></button>
          <button class="btn btn-icon" title="Last page" aria-label="Last page" [disabled]="pageIdx() >= pages() - 1"
                  (click)="pageIdx.set(pages() - 1)"><app-icon name="last" [size]="20" /></button>
        </div>
      }
    </div>
  `,
  styles: `
    :host { display: block; margin: 0 -32px; }
    h1 { font-size: 32px; padding: 8px 40px 20px; }
    .tabbar { display: flex; align-items: center; gap: 16px; padding: 0 40px; border-bottom: 1px solid var(--line); }
    .tabs { border-bottom: none; flex: 1; min-width: 0; }
    .where { display: flex; align-items: center; gap: 6px; min-width: 0; }
    .where > span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 380px; }

    .tr { position: relative; display: grid; grid-template-columns: minmax(0, 1fr) 140px 120px 180px; gap: 16px; align-items: start;
          padding: 12px 40px; border-bottom: 1px solid var(--line); }
    .tr:not(.th):hover { background: var(--hover-soft); }
    .th { align-items: center; padding-top: 14px; padding-bottom: 14px; font-size: 13px; color: var(--muted); }
    .col { padding-top: 6px; font-size: 14px; display: grid; gap: 2px; justify-items: start; }

    .open { all: unset; display: flex; gap: 18px; min-width: 0; cursor: pointer; border-radius: 4px; padding-right: 40px; }
    .open:focus-visible { box-shadow: var(--focus); }
    .disabled .open { cursor: default; opacity: .7; }
    .thumb { position: relative; flex: none; width: 144px; aspect-ratio: 16/9; border-radius: 4px; overflow: hidden; background: #000; }
    .thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .live { height: 100%; display: grid; place-items: center; color: var(--err); }
    .dur { position: absolute; right: 4px; bottom: 4px; background: rgba(0,0,0,.8); color: #fff; padding: 1px 4px;
           border-radius: 4px; font-size: 12px; font-weight: 500; }
    .text { display: grid; gap: 4px; min-width: 0; align-content: start; padding-top: 4px; }
    .name { font-size: 15px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .tr:hover .name { text-decoration: underline; text-underline-offset: 3px; }
    .disabled:hover .name { text-decoration: none; }
    .sub { font-size: 13px; color: var(--muted); }
    .mobile-meta { display: none; }

    .acts { position: absolute; left: calc(40px + 144px + 18px - 6px); bottom: 10px; display: flex; gap: 2px;
            opacity: 0; transition: opacity .12s; }
    .tr:hover .acts, .tr:focus-within .acts { opacity: 1; }
    .acts .danger:hover { color: var(--err) !important; background: var(--err-bg) !important; }

    .empty { padding: 48px 40px; text-align: center; color: var(--muted); display: grid; justify-items: center; gap: 10px; }

    .pager { display: flex; align-items: center; justify-content: flex-end; gap: 8px; padding: 12px 32px; font-size: 13px; color: var(--muted); }
    .pager span { margin: 0 16px 0 8px; }
    .rows { display: flex; align-items: center; gap: 10px; }
    .rows select { background: transparent; color: var(--text); border: none; font: inherit; font-size: 13px; cursor: pointer; }
    .rows option { background: var(--card); }

    @media (max-width: 900px) {
      :host { margin: 0 -16px; }
      h1 { padding: 4px 16px 12px; font-size: 26px; }
      .tabbar, .tr { padding-left: 16px; padding-right: 16px; }
      .tr { grid-template-columns: minmax(0, 1fr) 110px 120px; }
      .tr > :nth-child(3) { display: none; }
      .where > span { display: none; }
      .acts { left: calc(16px + 144px + 18px - 6px); }
      .pager { padding: 12px 8px; }
    }
    @media (max-width: 700px) {
      .tr { grid-template-columns: minmax(0, 1fr); }
      .th, .col { display: none !important; }
      .thumb { width: 120px; }
      .open { gap: 12px; }
      .mobile-meta { display: flex; gap: 8px; align-items: center; font-size: 12px; color: var(--muted); }
      .acts { left: auto; right: 8px; bottom: auto; top: 12px; opacity: 1; }
      .rows { display: none; }
    }
  `,
})
export class RecordingsPage implements OnInit, OnDestroy {
  private api = inject(Api);
  private router = inject(Router);
  private confirm = inject(Confirm);
  private toast = inject(Toast);
  readonly search = inject(Search);
  readonly fmtSize = fmtSize;
  readonly tabs: { id: Tab; label: string }[] = [
    { id: 'all', label: 'All' }, { id: 'new', label: 'New' }, { id: 'editing', label: 'Editing' }, { id: 'uploaded', label: 'Uploaded' }];
  readonly sizes = [10, 30, 50];
  readonly recordings = signal<Recording[]>([]);
  readonly folder = signal('');
  readonly loading = signal(true);
  readonly tab = signal<Tab>('all');
  readonly size = signal(10);
  readonly pageIdx = signal(0);

  readonly shown = computed(() => {
    const q = this.search.text().trim().toLowerCase();
    return this.recordings()
      .filter((r) => this.inTab(r, this.tab()) && (!q || r.name.toLowerCase().includes(q)))
      .sort((a, b) => b.mtime - a.mtime);
  });
  readonly pages = computed(() => Math.max(1, Math.ceil(this.shown().length / this.size())));
  readonly page = computed(() => this.shown().slice(this.pageIdx() * this.size(), (this.pageIdx() + 1) * this.size()));
  readonly from = computed(() => (this.shown().length ? this.pageIdx() * this.size() + 1 : 0));
  readonly to = computed(() => Math.min(this.shown().length, (this.pageIdx() + 1) * this.size()));
  private timer?: ReturnType<typeof setInterval>;

  constructor() {
    effect(() => { // back to the first page when the search changes; stay in range when the list shrinks
      this.search.text();
      this.pageIdx.set(0);
    });
    effect(() => { if (this.pageIdx() > this.pages() - 1) this.pageIdx.set(this.pages() - 1); });
  }

  ngOnInit() {
    this.refresh();
    this.timer = setInterval(() => this.refresh(), 10000); // OBS may drop new files any time
  }

  ngOnDestroy() { clearInterval(this.timer); }

  private inTab(r: Recording, tab: Tab) {
    return tab === 'all' || (tab === 'new' ? r.status === 'new' || r.status === 'recording' : r.status === tab);
  }

  count(tab: Tab) { return this.recordings().filter((r) => this.inTab(r, tab)).length; }

  setTab(tab: Tab) { this.tab.set(tab); this.pageIdx.set(0); }
  setSize(n: number) { this.size.set(n); this.pageIdx.set(0); }

  subtitle(r: Recording) { return SUBTITLE[r.status] ?? r.status; }

  /** Duration badge like YouTube's: 3:50, 1:02:07. */
  badge(s: number) {
    const t = Math.round(s), h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), sec = String(t % 60).padStart(2, '0');
    return h ? `${h}:${String(m).padStart(2, '0')}:${sec}` : `${m}:${sec}`;
  }

  async refresh() {
    try {
      const res = await this.api.recordings();
      this.recordings.set(res.recordings);
      this.folder.set(res.folder);
    } finally {
      this.loading.set(false);
    }
  }

  poster(r: Recording) { return `/api/recordings/${encodeURIComponent(r.name)}/poster?m=${r.mtime}`; }

  async open(r: Recording) {
    const p = await this.api.openProject(r.name);
    this.router.navigate(['/project', p.id]);
  }

  async deleteVideo(r: Recording) {
    const used = await this.api.get<{ channels: string[] }>(`/recordings/${encodeURIComponent(r.name)}/usage`);
    const ok = await this.confirm.ask({
      title: `Delete ${r.name}?`,
      message: `The video file (${fmtSize(r.size)}) is deleted from this computer: it does not go to the trash and can't be undone.` +
        (used.channels.length ? `\nIts projects are deleted too, in: ${used.channels.join(', ')}.` : ''),
      confirm: 'Delete forever',
    });
    if (!ok) return;
    await this.api.delete(`/recordings/${encodeURIComponent(r.name)}`);
    this.toast.show(`Deleted ${r.name}`, 'ok');
    await this.refresh();
  }

  async discard(r: Recording) {
    if (!(await this.confirm.ask({ ...DISCARD, title: `Discard changes to ${r.name}?` }))) return;
    await this.api.delete(`/projects/${r.project}`);
    this.toast.show('Discarded: the recording is back in New', 'ok');
    await this.refresh();
  }
}
