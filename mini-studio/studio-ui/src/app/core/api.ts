import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { Toast } from '../shared/toast';
import { Cue, Job, Library, Project, Recording, Settings, TemplateFamily, TemplateInfo } from './models';

/** Thin wrapper over the FastAPI backend (studio_server/api.py). Errors show a toast and rethrow. */
@Injectable({ providedIn: 'root' })
export class Api {
  private http = inject(HttpClient);
  private toast = inject(Toast);

  private async call<T>(req: () => any): Promise<T> {
    try {
      return await firstValueFrom<T>(req());
    } catch (e) {
      const msg = e instanceof HttpErrorResponse ? (e.error?.detail ?? e.message) : String(e);
      this.toast.show(msg, 'err');
      throw e;
    }
  }

  get = <T>(url: string) => this.call<T>(() => this.http.get<T>('/api' + url));
  post = <T>(url: string, body: unknown = {}) => this.call<T>(() => this.http.post<T>('/api' + url, body));
  put = <T>(url: string, body: unknown) => this.call<T>(() => this.http.put<T>('/api' + url, body));
  patch = <T>(url: string, body: unknown) => this.call<T>(() => this.http.patch<T>('/api' + url, body));
  delete = <T>(url: string) => this.call<T>(() => this.http.delete<T>('/api' + url));

  recordings() { return this.get<{ folder: string; recordings: Recording[] }>('/recordings'); }
  openProject(name: string) { return this.post<Project>('/projects', { name }); }
  project(id: string) { return this.get<Project>(`/projects/${id}`); }
  templates() { return this.get<{ templates: TemplateInfo[]; families: TemplateFamily[]; colors: Record<string, string> }>('/templates'); }
  cues(id: string) { return this.get<{ cues: Cue[] }>(`/projects/${id}/subtitles`); }
  job(id: string) { return this.get<Job>(`/jobs/${id}`); }
  settings() { return this.get<Settings>('/settings'); }
  library(pid?: string) { return this.get<Library>('/library' + (pid ? `?pid=${pid}` : '')); }
  libraryFile(photo: string, kind: 'photo' | 'cutout') { return `/api/library/photos/${photo}/${kind}`; }
  youtube() { return this.get<{ client_secret: boolean; connected: boolean; client_secret_path: string }>('/youtube/status'); }

  uploadImage(id: string, slot: string, file: File) {
    const form = new FormData();
    form.append('file', file);
    return this.call<{ file: string }>(() => this.http.post('/api' + `/projects/${id}/upload/${slot}`, form));
  }

  /** Poll a job until it finishes; onUpdate gets every state. Resolves with the final job (throws on error). */
  async waitJob(job: Job, onUpdate?: (j: Job) => void): Promise<Job> {
    let j = job;
    onUpdate?.(j);
    while (j.status === 'queued' || j.status === 'running') {
      await new Promise((r) => setTimeout(r, 700));
      j = await firstValueFrom(this.http.get<Job>('/api/jobs/' + j.id));
      onUpdate?.(j);
    }
    if (j.status === 'error') {
      this.toast.show(`${j.kind} failed: ${j.error}`, 'err');
      throw new Error(j.error ?? 'job failed');
    }
    return j;
  }
}
