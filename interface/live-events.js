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
function carePresentation(event) {
  const actions = {comida:['🍖','alimentou o Rex!','AU AU! ❤️'], agua:['💧','deu água ao Rex!','ÁGUA FRESQUINHA! 💧'], brincar:['🎾','brincou com o Rex!','AU AU! VEM BRINCAR!'], dormir:['🌙','colocou Rex para dormir!','BONS SONHOS… 💤'], acordar:['☀️','acordou o Rex!','AU AU! BOM DIA! ❤️'], carinho:['💛','fez carinho no Rex!','AU AU! AMO VOCÊS!']};
  if (event.agrupado || !actions[event.comando]) return {icon:'💛', title:event.agrupado ? event.nome : `Obrigado, ${event.nome}!`, detail:event.mensagem, bark:'AU AU! ❤️', action:'carinho'};
  const [icon, verb, bark] = actions[event.comando];
  const names = {fome:'comida',vida:'vida',felicidade:'felicidade',energia:'energia'};
  const gains = Object.entries(event.efeitos || {}).filter(([key,value]) => names[key] && value > 0).map(([key,value]) => `+${Number(value.toFixed(1))} ${names[key]}`);
  const food = event.comando === 'comida';
  const amount = Number(Number(event.efeitos?.fome || 0).toFixed(1));
  return {name:event.nome, verb, highlight:food, gain:food && amount > 0 ? `+${Number(amount.toFixed(1))} 🍖` : null, icon, title:`${event.nome} ${verb}`, detail:gains.length ? gains.slice(0,2).join(' · ') : '+10 XP de cuidado', bark, action:event.comando};
}
// O áudio só é liberado por um clique nesta janela, evitando som duplicado.
class RexEventSound {
  constructor(factory = () => new (globalThis.AudioContext || globalThis.webkitAudioContext)()) {
    this.factory = factory; this.context = null; this.enabled = false; this.volume = .25; this.nodes = new Set();
  }
  setVolume(value) { this.volume = Number.isFinite(Number(value)) ? Math.max(0, Math.min(1, Number(value))) : .25; }
  async enable() {
    try {
      this.context ||= this.factory();
      await this.context.resume();
      this.enabled = this.context.state === 'running';
    } catch { this.enabled = false; }
    return this.enabled;
  }
  mute() {
    this.enabled = false;
    for (const node of this.nodes) { try { node.stop(); } catch {} }
    this.nodes.clear();
  }
  play(action) {
    if (action !== 'comida' || !this.enabled || !this.volume || this.context?.state !== 'running') return false;
    try {
      for (const delay of [0, .19]) {
        const oscillator = this.context.createOscillator();
        const gain = this.context.createGain();
        const start = this.context.currentTime + delay;
        oscillator.type = 'triangle';
        oscillator.frequency.setValueAtTime(360, start);
        oscillator.frequency.exponentialRampToValueAtTime(130, start + .12);
        gain.gain.setValueAtTime(0, start);
        gain.gain.linearRampToValueAtTime(this.volume * .35, start + .015);
        gain.gain.exponentialRampToValueAtTime(.001, start + .14);
        oscillator.connect(gain); gain.connect(this.context.destination);
        this.nodes.add(oscillator);
        oscillator.onended = () => { this.nodes.delete(oscillator); oscillator.disconnect(); gain.disconnect(); };
        oscillator.start(start); oscillator.stop(start + .15);
      }
      return true;
    } catch { this.mute(); return false; }
  }
}
if (typeof module !== 'undefined') module.exports = {LiveEventQueue, carePresentation, RexEventSound};
