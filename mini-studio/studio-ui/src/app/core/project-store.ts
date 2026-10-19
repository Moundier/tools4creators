import { Injectable, computed, inject, signal } from '@angular/core';

import { Api } from './api';
import { Job, Project } from './models';

/** Partial update; nested objects are merged by the backend (PATCH /api/projects/{id}). */
export type ProjectPatch = { [K in keyof Project]?: Partial<Project[K]> };

/** State of the project open in the wizard, shared by all step components (provided per page). */
@Injectable()
export class ProjectStore {
  private api = inject(Api);
  readonly project = signal<Project | null>(null);
  readonly jobs = signal<Record<string, Job>>({}); // latest job per kind ("short:2" for a Short)
  readonly version = signal(Date.now()); // cache-buster for regenerated images
  readonly id = computed(() => this.project()?.id ?? '');

  async load(id: string) {
    const p = await this.api.project(id);
    this.project.set(p);
    for (const j of p.jobs) this.follow(j.kind, j).catch(() => {}); // resume jobs after a page reload
    return p;
  }

  async reload() {
    if (this.id()) this.project.set(await this.api.project(this.id()));
    this.version.set(Date.now());
  }

  async patch(part: ProjectPatch) {
    const p = await this.api.patch<Project>(`/projects/${this.id()}`, part);
    this.project.update((old) => (old ? { ...old, ...p } : old));
  }

  /** Track a background job under `key`, reload the project when it ends. */
  async follow(key: string, job: Job): Promise<Job> {
    try {
      return await this.api.waitJob(job, (j) => this.jobs.update((all) => ({ ...all, [key]: j })));
    } finally {
      await this.reload();
    }
  }

  async run(key: string, url: string, body: unknown = {}): Promise<Job> {
    return this.follow(key, await this.api.post<Job>(url, body));
  }

  busy(key: string) {
    const j = this.jobs()[key];
    return !!j && (j.status === 'queued' || j.status === 'running');
  }

  file(path: string) {
    return `/api/projects/${this.id()}/files/${path}?v=${this.version()}`;
  }
}
