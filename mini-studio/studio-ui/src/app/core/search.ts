import { Injectable, signal } from '@angular/core';

/** Text typed in the top bar's search box; the Recordings page filters by it. */
@Injectable({ providedIn: 'root' })
export class Search {
  readonly text = signal('');
}
