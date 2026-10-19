import { inject } from '@angular/core';
import { CanActivateFn, Router, Routes } from '@angular/router';

import { ChannelStore } from './core/channel';

/** Every page works on a channel: without one chosen in this tab, go pick one. */
const channelGuard: CanActivateFn = async () => {
  const store = inject(ChannelStore), router = inject(Router);  // inject before the await
  if (!store.currentId()) return router.parseUrl('/browse');
  if (!store.channels().length) await store.refresh().catch(() => null);
  return store.currentId() ? true : router.parseUrl('/browse');
};

export const routes: Routes = [
  { path: 'browse', loadComponent: () => import('./pages/browse').then((m) => m.BrowsePage) },
  { path: '', canActivate: [channelGuard], loadComponent: () => import('./pages/recordings').then((m) => m.RecordingsPage) },
  { path: 'project/:id', canActivate: [channelGuard], loadComponent: () => import('./pages/project').then((m) => m.ProjectPage) },
  { path: 'settings', canActivate: [channelGuard], loadComponent: () => import('./pages/settings').then((m) => m.SettingsPage) },
  { path: '**', redirectTo: '' },
];
