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
  if (event.tipo === 'presente') return giftPresentation(event);
  const actions = {comida:['🍖','alimentou o Rex!','AU AU! ❤️'], agua:['💧','deu água ao Rex!','ÁGUA FRESQUINHA! 💧'], brincar:['🎾','brincou com o Rex!','AU AU! VEM BRINCAR!'], dormir:['🌙','colocou Rex para dormir!','BONS SONHOS… 💤'], acordar:['☀️','acordou o Rex!','AU AU! BOM DIA! ❤️'], carinho:['💛','fez carinho no Rex!','AU AU! AMO VOCÊS!']};
  if (event.agrupado || !actions[event.comando]) return {icon:'💛', title:event.agrupado ? event.nome : `Obrigado, ${event.nome}!`, detail:event.mensagem, bark:'AU AU! ❤️', action:'carinho'};
  const [icon, verb, bark] = actions[event.comando];
  const names = {fome:'comida',vida:'vida',felicidade:'felicidade',energia:'energia'};
  const gains = Object.entries(event.efeitos || {}).filter(([key,value]) => names[key] && value > 0).map(([key,value]) => `+${Number(value.toFixed(1))} ${names[key]}`);
  const food = event.comando === 'comida';
  const amount = Number(Number(event.efeitos?.fome || 0).toFixed(1));
  return {name:event.nome, verb, highlight:food, gain:food && amount > 0 ? `+${Number(amount.toFixed(1))} 🍖` : null, icon, title:`${event.nome} ${verb}`, detail:gains.length ? gains.slice(0,2).join(' · ') : '+10 XP de cuidado', bark, action:event.comando};
}
const GIFT_THEMES = {
  saciedade: {action:'gift-rose', icon:'🌹', label:'UM PRESENTE PARA O REX', particles:['🌹','🌸','❤️'], attribute:'fome', unit:'saciedade', single:'enviou uma Rosa!'},
  felicidade: {action:'gift-heart', icon:'❤️', label:'CARINHO QUE BRILHA', particles:['❤️','💖','✨'], attribute:'felicidade', unit:'felicidade', single:'deu carinho ao Rex!'},
  energia: {action:'gift-coffee', icon:'☕', label:'UMA DOSE DE ENERGIA', particles:['⚡','☕','✨'], attribute:'energia', unit:'energia', single:'deu energia ao Rex!'},
  especial: {action:'gift-lion', icon:'🦁', label:'🚨 PRESENTE RARO', particles:['👑','⭐','🦁'], single:'enviou um Leão!'}
};
function giftPresentation(event) {
  const gift = event.presente || {};
  const theme = GIFT_THEMES[gift.efeito] || {action:'gift-other',icon:'🎁',label:'OBRIGADO PELO APOIO',particles:['🎁','✨','❤️'],single:'enviou um presente!'};
  const quantity = Number.isInteger(gift.quantidade) && gift.quantidade > 0 ? gift.quantidade : 1;
  const verb = quantity > 1 ? `enviou ${quantity} × ${gift.nome || 'presentes'}!` : theme.single;
  const delta = Number(event.efeitos?.[theme.attribute]);
  let detail = 'Seu apoio faz parte desta história!';
  if (gift.efeito_aplicado === false) detail = 'Apoio registrado! Obrigado por cuidar ❤️';
  else if (theme.attribute && Number.isFinite(delta)) detail = delta > 0 ? `+${Number(delta.toFixed(1))} ${theme.unit} ${theme.icon}` : 'Rex já está abastecido. Obrigado! ❤️';
  else if (gift.efeito === 'especial') detail = 'Uma homenagem especial ao Rex! 👑';
  return {...theme, name:event.nome, verb, title:`${event.nome} ${verb}`, detail,
    bark:'AU AU! ❤️', highlight:true, gift:true, duration:gift.efeito === 'especial' ? 7500 : 5000};
}
function supporterLine(item) {
  return `${item.nome} enviou ${item.quantidade > 1 ? item.quantidade + ' × ' : ''}${item.presente}`;
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
    const notes = {comida:[360,360], 'gift-rose':[523,659,784], 'gift-heart':[659,784,988], 'gift-coffee':[392,523,784,1047], 'gift-lion':[262,392,523,659,784], 'gift-other':[523,784]}[action];
    if (!notes || !this.enabled || !this.volume || this.context?.state !== 'running') return false;
    try {
      for (const [index, frequency] of notes.entries()) {
        const delay = index * .19;
        const oscillator = this.context.createOscillator();
        const gain = this.context.createGain();
        const start = this.context.currentTime + delay;
        oscillator.type = action === 'comida' ? 'triangle' : 'sine';
        oscillator.frequency.setValueAtTime(frequency, start);
        oscillator.frequency.exponentialRampToValueAtTime(action === 'comida' ? 130 : frequency * .99, start + .12);
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
if (typeof module !== 'undefined') module.exports = {LiveEventQueue, carePresentation, giftPresentation, supporterLine, RexEventSound};
