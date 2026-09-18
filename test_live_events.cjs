const {test} = require('node:test');
const assert = require('node:assert/strict');
const {LiveEventQueue, carePresentation} = require('./interface/live-events.js');
const event = id => ({id, nome:`Pessoa ${id}`, mensagem:'Carinho!'});

test('abrir a tela não repete cuidados antigos', () => {
  const q = new LiveEventQueue(); q.ingest([event(5), event(4)]);
  assert.equal(q.next(), null);
});
test('rajada é apresentada em ordem, sem duplicar nas consultas seguintes', () => {
  const q = new LiveEventQueue(); q.ingest([]);
  q.ingest([event(3), event(2), event(1)]);
  q.ingest([event(3), event(2), event(1)]);
  assert.deepEqual([q.next().id, q.next().id, q.next().id], [1,2,3]);
  assert.equal(q.next(), null);
});
test('resposta atrasada não retrocede o cursor', () => {
  const q = new LiveEventQueue(); q.ingest([event(10)]);
  q.ingest([event(11)]); q.ingest([event(9)]); q.ingest([event(11)]);
  assert.equal(q.next().id, 11); assert.equal(q.next(), null);
});
test('sobrecarga agrupa antigos e conserva os 30 mais novos', () => {
  const q = new LiveEventQueue(); q.ingest([]);
  q.ingest(Array.from({length:40}, (_,i) => event(i+1)));
  assert.equal(q.pending.length, 30);
  assert.match(q.next().mensagem, /^10 cuidados/);
  assert.equal(q.next().id, 11);
});
test('reconexão após perda de histórico mostra resumo da lacuna', () => {
  const q = new LiveEventQueue(); q.ingest([event(5)]);
  q.ingest([event(110), event(109)]);
  assert.match(q.next().mensagem, /^103 cuidados/);
  assert.equal(q.next().id, 109); assert.equal(q.next().id, 110);
});
test('alerta nomeia o cuidado e mostra apenas o ganho real', () => {
  const view = carePresentation({nome:'João', comando:'comida', efeitos:{fome:4,energia:0}});
  assert.equal(view.title,'João alimentou o Rex!');
  assert.equal(view.detail,'+4 comida');
  assert.equal(view.action,'comida');
});
test('atributos cheios mostram XP sem inventar ganho de comida', () => {
  const view = carePresentation({nome:'Ana',comando:'comida',efeitos:{fome:0}});
  assert.equal(view.detail,'+10 XP de cuidado');
});
test('histórico antigo continua apresentável', () => {
  const view = carePresentation({nome:'Ana',mensagem:'Rex comeu!'});
  assert.equal(view.detail,'Rex comeu!');
});
const {RexEventSound} = require('./interface/live-events.js');
test('comida destaca nome e ganho limitado sem perder o título', () => {
  const view = carePresentation({nome:'<João>',comando:'comida',efeitos:{fome:10}});
  assert.equal(view.name,'<João>'); assert.equal(view.gain,'+10 🍖'); assert.equal(view.highlight,true);
  assert.equal(carePresentation({nome:'Ana',comando:'comida',efeitos:{fome:0}}).gain,null);
});
function audioMock() {
  const nodes=[];
  const parameter=()=>({setValueAtTime(){},exponentialRampToValueAtTime(){},linearRampToValueAtTime(){}});
  return {nodes,state:'suspended',currentTime:0,destination:{},async resume(){this.state='running'},
    createGain(){return {gain:parameter(),connect(){},disconnect(){}}},
    createOscillator(){const node={frequency:parameter(),connect(){},disconnect(){},start(){},stop(){this.stopped=true}};nodes.push(node);return node}
  };
}
test('som exige ativação, toca só comida e silencia os sons pendentes', async () => {
  const ctx=audioMock(), sound=new RexEventSound(()=>ctx);
  assert.equal(sound.play('comida'),false); assert.equal(ctx.nodes.length,0);
  assert.equal(await sound.enable(),true); assert.equal(sound.play('carinho'),false);
  assert.equal(sound.play('comida'),true); assert.equal(ctx.nodes.length,2);
  sound.mute(); assert.ok(ctx.nodes.every(n=>n.stopped)); assert.equal(sound.play('comida'),false);
});
test('volume zero, suspensão e navegador sem áudio não impedem os eventos', async () => {
  const ctx=audioMock(), sound=new RexEventSound(()=>ctx); await sound.enable();
  sound.setVolume(-1); assert.equal(sound.volume,0); assert.equal(sound.play('comida'),false);
  sound.setVolume(20); assert.equal(sound.volume,1);
  ctx.state='suspended'; assert.equal(sound.play('comida'),false);
  const unavailable=new RexEventSound(()=>{throw Error('indisponível')});
  assert.equal(await unavailable.enable(),false); assert.equal(unavailable.play('comida'),false);
});
const {giftPresentation, supporterLine} = require('./interface/live-events.js');
const giftEvent = (effect, delta=10) => ({id:1,tipo:'presente',nome:'João',presente:{nome:'Presente',efeito:effect,quantidade:1,efeito_aplicado:true},efeitos:{fome:delta,felicidade:delta,energia:delta}});
test('cada presente tem tema, partículas e duração própria sem XP', () => {
  for (const [effect,action] of [['saciedade','gift-rose'],['felicidade','gift-heart'],['energia','gift-coffee'],['especial','gift-lion']]) {
    const view=carePresentation(giftEvent(effect));
    assert.equal(view.action,action); assert.equal(view.name,'João'); assert.equal(view.gift,true);
    assert.ok(view.particles.length>=3); assert.doesNotMatch(view.detail,/XP/);
    assert.equal(view.duration,effect==='especial'?7500:5000);
  }
});
test('presentes mostram ganho efetivo, limite cheio e cooldown sem promessas falsas', () => {
  assert.match(giftPresentation(giftEvent('saciedade',2)).detail,/\+2 saciedade/);
  assert.doesNotMatch(giftPresentation(giftEvent('saciedade',2)).detail,/felicidade/);
  assert.match(giftPresentation(giftEvent('energia',0)).detail,/abastecido/);
  const event=giftEvent('energia'); event.presente.efeito_aplicado=false;
  assert.match(giftPresentation(event).detail,/Apoio registrado/);
  assert.doesNotMatch(giftPresentation(event).detail,/\+|XP/);
});
test('combo mantém quantidade e presente desconhecido tem agradecimento seguro', () => {
  const event=giftEvent('saciedade'); event.presente.quantidade=5; event.presente.nome='Rosa 🌹';
  assert.match(giftPresentation(event).title,/5 × Rosa/);
  assert.equal(giftPresentation({nome:'Ana',presente:{}}).action,'gift-other');
  assert.equal(supporterLine({nome:'Ana',quantidade:3,presente:'Rosa 🌹'}),'Ana enviou 3 × Rosa 🌹');
});
test('fila mista mantém ordem e não repete presentes após consulta ou reabertura', () => {
  const q=new LiveEventQueue();q.ingest([]);
  const gifts=[{...giftEvent('saciedade'),id:2}, {...event(1),comando:'comida'}, {...giftEvent('especial'),id:3}];
  q.ingest(gifts);q.ingest(gifts);
  assert.deepEqual([q.next().id,q.next().id,q.next().id],[1,2,3]); assert.equal(q.next(),null);
  const reopened=new LiveEventQueue(); reopened.ingest(gifts); assert.equal(reopened.next(),null);
});
test('som dos quatro presentes respeita ativação e silêncio', async () => {
  const ctx=audioMock(), sound=new RexEventSound(()=>ctx);
  for (const action of ['gift-rose','gift-heart','gift-coffee','gift-lion']) assert.equal(sound.play(action),false);
  await sound.enable();
  for (const action of ['gift-rose','gift-heart','gift-coffee','gift-lion']) assert.equal(sound.play(action),true);
  assert.equal(ctx.nodes.length,15);
  sound.mute(); assert.equal(sound.play('gift-lion'),false);
});
