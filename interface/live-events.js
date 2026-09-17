'use strict';
class LiveEventQueue {
  constructor(limit = 30) { this.limit = limit; this.cursor = null; this.pending = []; this.grouped = 0; }
  ingest(events) {
    const ordered = [...events].sort((a,b) => a.id - b.id);
    const newest = ordered.at(-1)?.id || 0;
    // Ao abrir a tela, não repete o histórico.
    if (this.cursor === null) { this.cursor = newest; return; }
    const fresh = ordered.filter(event => event.id > this.cursor);
    if (!fresh.length) return;
    this.grouped += Math.max(0, fresh[0].id - this.cursor - 1);
    this.cursor = newest;
    this.pending.push(...fresh);
    const excess = Math.max(0, this.pending.length - this.limit);
    if (excess) { this.pending.splice(0, excess); this.grouped += excess; }
  }
  next() {
    if (this.grouped) {
      const count = this.grouped; this.grouped = 0;
      return {nome:'Comunidade do Rex', mensagem:`${count} cuidados recebidos! Todos contam no ranking.`, agrupado:true};
    }
    return this.pending.shift() || null;
  }
}
if (typeof module !== 'undefined') module.exports = {LiveEventQueue};
