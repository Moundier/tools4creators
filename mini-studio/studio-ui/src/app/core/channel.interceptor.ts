import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

import { ChannelStore } from './channel';

/** Adds X-Channel (the channel this tab works on) to every /api request. */
export const channelInterceptor: HttpInterceptorFn = (req, next) => {
  const id = inject(ChannelStore).currentId();
  return next(id && req.url.startsWith('/api') ? req.clone({ setHeaders: { 'X-Channel': id } }) : req);
};
