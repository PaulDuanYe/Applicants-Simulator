// Monotonic visible-page duration; checkpoints are cumulative, not deltas.
export class VisibleTimer {
  constructor() { this.total = 0; this.since = null; }
  reset(value) { this.pause(); this.total = value; }
  resume() { if (!document.hidden && this.since === null) this.since = performance.now(); }
  pause() {
    if (this.since !== null) this.total += performance.now() - this.since;
    this.since = null;
  }
  value() { return Math.floor(this.total + (this.since === null ? 0 : performance.now() - this.since)); }
}
