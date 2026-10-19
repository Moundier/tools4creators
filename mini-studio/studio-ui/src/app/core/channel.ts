import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

export interface Channel { id: string; name: string; color: string; connected: boolean; projects: number; }

const SESSION_KEY = 'studio.channel';   // chosen in this tab (gone when the browser closes): /browse asks again
const LAST_KEY = 'studio.lastChannel';  // remembered across visits: /browse focuses it

function read(store: () => Storage, key: string): string | null {
  try { return store().getItem(key); } catch { return null; }
}
function write(store: () => Storage, key: string, value: string | null) {
  try { value === null ? store().removeItem(key) : store().setItem(key, value); } catch { /* storage blocked */ }
}

/** The channels and the one this tab works on. Every /api call carries it (see channel.interceptor.ts). */
@Injectable({ providedIn: 'root' })
export class ChannelStore {
  private http = inject(HttpClient);
  readonly channels = signal<Channel[]>([]);
  readonly colors = signal<string[]>([]);
  readonly currentId = signal<string | null>(read(() => sessionStorage, SESSION_KEY));
  readonly current = computed(() => this.channels().find((c) => c.id === this.currentId()) ?? null);
  readonly lastId = signal<string | null>(read(() => localStorage, LAST_KEY));

  constructor() {
    if (this.currentId()) this.setCookie(this.currentId()!);
  }

  async refresh() {
    const res = await firstValueFrom(this.http.get<{ channels: Channel[]; colors: string[] }>('/api/channels'));
    this.channels.set(res.channels);
    this.colors.set(res.colors);
    if (this.currentId() && !res.channels.some((c) => c.id === this.currentId())) this.clear();
    return res.channels;
  }

  select(id: string) {
    this.currentId.set(id);
    this.lastId.set(id);
    write(() => sessionStorage, SESSION_KEY, id);
    write(() => localStorage, LAST_KEY, id);
    this.setCookie(id);
  }

  clear() {
    this.currentId.set(null);
    write(() => sessionStorage, SESSION_KEY, null);
  }

  /** For <img>/<video>/<audio> requests, which can't send the X-Channel header. */
  private setCookie(id: string) {
    document.cookie = `studio_channel=${encodeURIComponent(id)}; path=/; SameSite=Strict`;
  }
}
