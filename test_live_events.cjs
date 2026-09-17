const {test} = require('node:test');
const assert = require('node:assert/strict');
const {LiveEventQueue} = require('./interface/live-events.js');
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
