import { Component, computed, effect, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';

import { ChannelStore } from './core/channel';
import { Search } from './core/search';
import { ConfirmHost } from './shared/confirm-dialog';
import { Icon } from './shared/icon';
import { ToastHost } from './shared/toast';

const COLLAPSED_KEY = 'studio.sidebar.collapsed';

function readCollapsed() {
  try { return localStorage.getItem(COLLAPSED_KEY) === '1'; } catch { return false; }
}

/** YouTube Studio-like shell: top bar with search, channel sidebar (collapsible; a drawer on small screens). */
@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Icon, ToastHost, ConfirmHost],
  template: `
    @if (bare()) {
      <router-outlet />
    } @else {
    <div class="shell" [class.collapsed]="collapsed()" [class.drawer-open]="drawer()">
      <header class="top">
        <button class="btn btn-icon" title="Menu" aria-label="Menu" (click)="toggle()"><app-icon name="menu" [size]="22" /></button>
        <a routerLink="/" class="brand" aria-label="mini-studio">
          <span>mini-studio</span>
        </a>
        <label class="search">
          <app-icon name="search" [size]="20" />
          <input type="search" placeholder="Search recordings" [value]="search.text()" (input)="onSearch($any($event.target).value)" />
        </label>
        <div class="actions">
          <a class="btn btn-icon" routerLink="/settings" title="Settings" aria-label="Settings"><app-icon name="settings" [size]="20" /></a>
          <details class="menu" #menu>
            <summary class="avatar sm" [style.background]="color()" [title]="name()" aria-label="Channel menu">{{ letter() }}</summary>
            <div class="menu-items">
              <div class="who-menu"><span class="avatar sm" [style.background]="color()">{{ letter() }}</span><b>{{ name() }}</b></div>
              <button (click)="menu.open = false; switchChannel()"><app-icon name="user" [size]="18" /> Switch channel</button>
            </div>
          </details>
        </div>
      </header>

      <div class="scrim" (click)="drawer.set(false)"></div>
      <aside class="side" aria-label="Main menu">
        <div class="channel">
          <a class="avatar lg" routerLink="/browse" [style.background]="color()" title="Switch channel" aria-label="Switch channel">{{ letter() }}</a>
          <div class="who"><b>Your channel</b><span>{{ name() }}</span></div>
          <a class="btn btn-icon btn-sm rename" routerLink="/settings" fragment="channel" title="Edit channel name"
             aria-label="Edit channel name"><app-icon name="edit" [size]="16" /></a>
        </div>
        <nav>
          <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }" title="Recordings">
            <app-icon name="video" [size]="22" [stroke]="1.75" /><span>Recordings</span></a>
          <a routerLink="/settings" routerLinkActive="active" [routerLinkActiveOptions]="exactNoFragment"
             title="Settings"><app-icon name="settings" [size]="22" [stroke]="1.75" /><span>Settings</span></a>
          <a routerLink="/settings" fragment="mic" routerLinkActive="active" [routerLinkActiveOptions]="exactNoFragment" title="Microphone">
            <app-icon name="mic" [size]="22" [stroke]="1.75" /><span>Microphone</span></a>
        </nav>
      </aside>

      <main><router-outlet /></main>
    </div>
    }
    <app-toast-host />
    <app-confirm-host />
  `,
  styles: `
    .shell { --top: 64px; --side: 255px; min-height: 100vh; }
    .shell.collapsed { --side: 72px; }
    @media (max-width: 900px) { .shell, .shell.collapsed { --side: 0px; } }

    .top { position: fixed; inset: 0 0 auto 0; height: var(--top); z-index: 30; background: var(--card);
           display: flex; align-items: center; gap: 12px; padding: 0 16px 0 12px; box-shadow: 0 1px 2px rgba(0,0,0,.4); }
    .top .btn-icon { color: var(--text); width: 40px; height: 40px; }
    .brand { display: flex; align-items: center; text-decoration: none; color: var(--text); margin: 0 8px 0 4px; }
    .brand span { font-size: 21px; font-weight: 500; letter-spacing: -.02em; }
    .search { flex: 1 1 0; max-width: 760px; min-width: 0; margin: 0 auto; display: flex; align-items: center; gap: 12px; height: 40px; padding: 0 16px;
              border-radius: 999px; background: var(--page); border: 1px solid var(--line); color: var(--muted); }
    .search:focus-within { border-color: var(--accent); }
    .search input { all: unset; flex: 1; min-width: 0; color: var(--text); font-size: 15px; }
    .search input::placeholder { color: var(--muted); }
    .actions { display: flex; align-items: center; gap: 8px; }
    .avatar { display: grid; place-items: center; border-radius: 50%; background: var(--magenta); color: #fff; font-weight: 400; flex: none; }
    .avatar.sm { width: 32px; height: 32px; font-size: 17px; cursor: pointer; }
    a.avatar { text-decoration: none; }
    .who-menu { display: flex; align-items: center; gap: 10px; padding: 8px 12px 12px; border-bottom: 1px solid var(--line); margin-bottom: 6px; }
    .who-menu .avatar { cursor: default; }
    .avatar.lg { width: 40px; height: 40px; font-size: 20px; }

    .side { position: fixed; top: var(--top); bottom: 0; left: 0; width: 255px; z-index: 25; background: var(--card);
            border-right: 1px solid var(--line); overflow-y: auto; overflow-x: hidden; transition: width .15s, transform .2s; }
    .collapsed .side { width: 72px; }
    /* channel: avatar on the left, "Your channel" + name on the right */
    .channel { display: flex; align-items: center; gap: 12px; padding: 16px 26px 12px; border-bottom: 1px solid var(--line); }
    .who { display: grid; gap: 1px; min-width: 0; } .who b { font-weight: 500; font-size: 14px; }
    .who span { font-size: 13px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .collapsed .channel { justify-content: center; padding: 16px 0 12px; }
    .collapsed .avatar.lg { width: 32px; height: 32px; font-size: 17px; }
    .who { flex: 1; }
    .channel { position: relative; }
    .rename { position: absolute; right: 12px; top: 50%; translate: 0 -50%; opacity: 0; transition: opacity .12s;
              background: var(--card) !important; box-shadow: -10px 0 10px var(--card); }
    .rename:hover { background: var(--soft) !important; }
    .channel:hover .rename, .rename:focus-visible { opacity: 1; }
    .collapsed .who, .collapsed .rename { display: none; }
    nav { display: grid; gap: 2px; padding: 8px 12px; }
    nav a { display: flex; align-items: center; gap: 24px; height: 48px; padding: 0 14px; border-radius: 8px;
            text-decoration: none; color: var(--text); font-size: 15px; white-space: nowrap; }
    nav a:hover { background: var(--hover-soft); }
    nav a.active { background: var(--hover); font-weight: 500; }
    nav a:focus-visible { outline: none; box-shadow: var(--focus); }
    .collapsed nav { padding: 8px 4px; }
    .collapsed nav a { justify-content: center; padding: 0; gap: 0; }
    .collapsed nav a span { display: none; }

    .scrim { display: none; }
    main { margin-left: var(--side); padding: calc(var(--top) + 24px) 32px 110px; min-width: 0; transition: margin-left .15s; }

    @media (max-width: 900px) {
      .side, .collapsed .side { width: 255px; transform: translateX(-100%); box-shadow: var(--shadow-lg); }
      .collapsed nav a { justify-content: flex-start; padding: 0 14px; gap: 24px; }
      .collapsed nav a span, .collapsed .who { display: initial; }
      .collapsed .rename { display: inline-flex; }
      .rename { opacity: 1; }  /* no hover on touch screens */
      .collapsed .who { display: grid; }
      .collapsed .channel { justify-content: flex-start; padding: 16px 26px 12px; }
      .collapsed .avatar.lg { width: 40px; height: 40px; font-size: 20px; }
      .drawer-open .side { transform: none; }
      .drawer-open .scrim { display: block; position: fixed; inset: var(--top) 0 0 0; z-index: 24; background: rgba(0,0,0,.5); }
      main { padding: calc(var(--top) + 16px) 16px 110px; }
    }
    @media (max-width: 600px) {
      .search { padding: 0 12px; }
      .actions .avatar { display: none; }
    }
  `,
})
export class App {
  readonly search = inject(Search);
  private router = inject(Router);
  readonly collapsed = signal(readCollapsed());
  readonly drawer = signal(false);
  readonly channels = inject(ChannelStore);
  readonly bare = signal(location.pathname === '/browse');  // /browse: full screen, no bars
  readonly name = computed(() => this.channels.current()?.name ?? '');
  readonly color = computed(() => this.channels.current()?.color ?? 'var(--magenta)');
  readonly letter = computed(() => (this.name().trim()[0] ?? '').toUpperCase());
  readonly exactNoFragment = { paths: 'exact', queryParams: 'ignored', fragment: 'exact', matrixParams: 'ignored' } as const;

  constructor() {
    effect(() => {
      const value = this.collapsed() ? '1' : '0';
      try { localStorage.setItem(COLLAPSED_KEY, value); } catch { /* storage blocked: keep it for this visit only */ }
    });
    if (this.channels.currentId()) this.channels.refresh().catch(() => null);
    this.router.events.pipe(filter((e) => e instanceof NavigationEnd)).subscribe(() => {
      this.drawer.set(false);
      this.bare.set(this.router.url.split(/[?#]/)[0] === '/browse');
      const fragment = this.router.parseUrl(this.router.url).fragment;
      if (fragment) setTimeout(() => document.getElementById(fragment)?.scrollIntoView({ behavior: 'smooth' }), 300);
    });
  }

  switchChannel() {
    this.search.text.set('');
    this.router.navigate(['/browse']);
  }

  toggle() {
    if (matchMedia('(max-width: 900px)').matches) this.drawer.update((v) => !v);
    else this.collapsed.update((v) => !v);
  }

  onSearch(text: string) {
    this.search.text.set(text);
    if (text && this.router.url.split(/[?#]/)[0] !== '/') this.router.navigate(['/']);
  }
}
