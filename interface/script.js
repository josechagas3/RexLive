'use strict';
const $ = id => document.getElementById(id);
const capture = new URLSearchParams(location.search).get('captura') === '1';
document.body.classList.toggle('capture', capture);
function fitCapture() { document.documentElement.style.setProperty('--capture-scale', Math.min(innerWidth / 1080, innerHeight / 1920)); }
if (capture) { fitCapture(); addEventListener('resize', fitCapture); }
const stats = [['fome','🍖','Saciedade','#dcb260'],['vida','❤️','Vida','#d98980'],['felicidade','😊','Felicidade','#9ab879'],['energia','⚡','Energia','#86b9b5']];
for (const [key, icon, title, color] of stats) {
  const node = document.createElement('div'); node.className = 'stat';
  node.innerHTML = `<div class="stat-heading"><span>${icon} ${title}</span><strong id="value-${key}">100%</strong></div><div class="track" role="progressbar" aria-label="${title}" aria-valuemin="0" aria-valuemax="100" id="track-${key}"><div id="bar-${key}" style="background:${color}"></div></div>`;
  $('stats').append(node);
}
const moods = {normal:'De boa por aqui',fome:'Uma fominha…',feliz:'Feliz da vida!',dormindo:'Recarregando os sonhos',comemorando:'Subiu de nível! 🎉',triste:'Preciso de carinho'};
const phrases = {normal:'Oi! Que bom ter você aqui. 🐾',fome:'Tem um petisco por aí? 🦴',feliz:'Você fez meu dia! 💛',dormindo:'Só mais cinco minutinhos… 💤',comemorando:'Crescemos juntos! Obrigado! 🎉',triste:'Fica um pouquinho comigo? 💛'};
const queue = new LiveEventQueue();
let busy = false, connected = false, alertActive = false, alertTimer;
let level = null, celebrationTimer, revision = 0, renderedRevision = 0;
let rankingKey = '', eventsKey = '';
let tiktokBusy = false, tiktokActive = false, tiktokAvailable = false, perfilLoaded = false;
try { $('nome').value = localStorage.getItem('rex-cuidador') || 'João'; } catch {}
function applyMotion(reduced) {
  document.body.classList.toggle('reduced-motion', reduced);
  $('reduce-motion').checked = reduced;
}
try { applyMotion(localStorage.getItem('rex-reduced-motion') === 'true'); } catch {}
$('reduce-motion').addEventListener('change', () => {
  applyMotion($('reduce-motion').checked);
  try { localStorage.setItem('rex-reduced-motion', String($('reduce-motion').checked)); } catch {}
});
addEventListener('storage', event => { if (event.key === 'rex-reduced-motion') applyMotion(event.newValue === 'true'); });
function connection(ok) {
  connected = ok;
  $('conexao').textContent = ok ? 'Jardim conectado' : 'Servidor desconectado';
  $('conexao').classList.toggle('offline', !ok);
  $('capture-connection').hidden = ok;
  document.body.classList.toggle('disconnected', !ok);
  if (!ok) {
    $('live-badge').textContent = 'CONEXÃO INTERROMPIDA';
    $('capture-mode').textContent = 'Aguardando o servidor do Rex…';
  }
  if (ok) showNextAlert();
}
function burst() {
  $('particles').replaceChildren();
  if (document.body.classList.contains('reduced-motion') || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  for (let i = 0; i < 12; i++) {
    const piece = document.createElement('span'); piece.textContent = i % 3 ? '✦' : '♥';
    piece.style.setProperty('--x', `${8 + i * 7.5}%`);
    piece.style.setProperty('--delay', `${i * .045}s`);
    $('particles').append(piece);
  }
}
function showNextAlert() {
  if (alertActive || !connected) return;
  const event = queue.next();
  if (!event) return;
  alertActive = true;
  $('alert-name').textContent = event.agrupado ? event.nome : `Obrigado, ${event.nome}!${event.origem === 'simulador' ? ' (teste)' : ''}`;
  $('alert-message').textContent = event.mensagem;
  $('care-alert').hidden = false;
  burst();
  clearTimeout(alertTimer);
  alertTimer = setTimeout(() => {
    $('care-alert').hidden = true;
    alertActive = false;
    showNextAlert();
  }, queue.pending.length > 3 ? 2200 : 4200);
}
function renderRanking(ranking) {
  const key = JSON.stringify(ranking);
  if (key === rankingKey) return;
  rankingKey = key; $('ranking').replaceChildren();
  ranking.forEach((item, i) => {
    const li = document.createElement('li');
    const name = item.nome + (item.origem === 'simulador' ? ' (teste)' : ' · TikTok');
    for (const [tag, cls, text] of [['span','rank',String(i+1).padStart(2,'0')],['span','avatar',Array.from(item.nome)[0].toUpperCase()],['span','caregiver-name',name],['strong','',`${item.pontos} XP`]]) {
      const el = document.createElement(tag); el.className = cls; el.textContent = text; li.append(el);
    }
    $('ranking').append(li);
  });
  if (!ranking.length) { const li = document.createElement('li'); li.className = 'empty'; li.textContent = 'O primeiro cuidado pode ser seu. 💛'; $('ranking').append(li); }
}
function render(data, requestRevision) {
  // Um GET iniciado antes de um clique não pode desfazer sua atualização.
  if (requestRevision < renderedRevision) return;
  renderedRevision = requestRevision;
  renderTikTok(data.tiktok);
  const r = data.cachorro;
  $('nivel').textContent = `NÍVEL ${r.nivel}`;
  $('rex').className = `dog ${r.estado}`;
  $('rex').setAttribute('aria-label', `Rex: ${moods[r.estado]}`);
  $('humor').textContent = moods[r.estado];
  $('fala').textContent = phrases[r.estado];
  $('sleep-label').textContent = r.dormindo ? 'Acordar' : 'Dormir';
  for (const [key] of stats) {
    $('value-'+key).textContent = `${Math.round(r[key])}%`;
    $('bar-'+key).style.width = `${r[key]}%`;
    $('track-'+key).setAttribute('aria-valuenow', Math.round(r[key]));
  }
  $('xp-text').textContent = `${r.xp_nivel} / ${r.xp_meta} XP`;
  $('xp-bar').style.width = `${r.xp_nivel}%`;
  $('dica').textContent = r.dormindo ? 'Enquanto dorme, Rex recupera 8 de energia por minuto. Clique em Acordar quando quiser.' : 'Brincar gasta 10 de energia e 3 de saciedade. Dormir ajuda o Rex a se recuperar.';
  if (level !== null && r.nivel > level) {
    $('celebracao').textContent = `🎉 Juntos, chegamos ao nível ${r.nivel}!`;
    $('celebracao').hidden = false;
    clearTimeout(celebrationTimer);
    celebrationTimer = setTimeout(() => { $('celebracao').hidden = true; }, 7000);
    burst();
  }
  level = r.nivel;
  queue.ingest(data.eventos);
  renderRanking(data.ranking);
  const recent = data.eventos.slice(0, 3);
  const key = JSON.stringify(recent);
  if (key !== eventsKey) {
    eventsKey = key; $('eventos').replaceChildren();
    for (const item of recent) {
      const el = document.createElement('div'); el.className = 'event';
      const name = document.createElement('b'); name.textContent = item.nome + (item.origem === 'simulador' ? ' (teste)' : ' · TikTok');
      const msg = document.createElement('span'); msg.textContent = item.mensagem;
      el.append(name, msg); $('eventos').append(el);
    }
  }
}
async function request(url, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const response = await fetch(url, {...options, signal: controller.signal});
    const data = await response.json();
    if (!response.ok) { const error = new Error(data.erro || 'Não foi possível cuidar agora.'); error.validation = response.status === 400; throw error; }
    return data;
  } finally { clearTimeout(timeout); }
}
async function refresh() {
  if (!busy && !tiktokBusy) {
    const current = ++revision;
    try { const data = await request('/api/estado'); if (current >= renderedRevision) { render(data, current); connection(true); } }
    catch { if (current >= renderedRevision) connection(false); }
  }
  setTimeout(refresh, 1000);
}
async function act(command) {
  if (busy || tiktokBusy || tiktokActive) return;
  busy = true;
  const current = ++revision;
  const actionButtons = document.querySelectorAll('.controls button');
  actionButtons.forEach(b => b.disabled = true);
  $('feedback').classList.remove('error');
  try {
    const nome = $('nome').value.trim();
    if (queue.cursor === null) { const initial = await request('/api/estado'); render(initial, current); }
    const data = await request('/api/acao', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nome, comando:command})});
    render(data, current); connection(true);
    $('feedback').textContent = data.eventos[0].mensagem;
    try { localStorage.setItem('rex-cuidador', nome); } catch {}
    $('comando').value = '';
  } catch (error) {
    if (!error.validation) connection(false);
    $('feedback').textContent = error.validation ? error.message : 'Conexão interrompida. Confira o histórico antes de repetir o cuidado.';
    $('feedback').classList.add('error');
  } finally { busy = false; syncControls(); }
}
function syncControls() {
  document.querySelectorAll('.controls button').forEach(button => button.disabled = busy || tiktokBusy || tiktokActive);
  $('tiktok-connect').disabled = tiktokBusy || busy || tiktokActive || !tiktokAvailable;
  $('tiktok-disconnect').disabled = tiktokBusy || !tiktokActive;
  $('tiktok-perfil').disabled = tiktokBusy || tiktokActive;
  $('comando').disabled = tiktokActive;
  $('nome').disabled = tiktokActive;
}
function renderTikTok(status) {
  if (!status) return;
  tiktokActive = status.ativo;
  tiktokAvailable = status.disponivel;
  if (!perfilLoaded) { $('tiktok-perfil').value = '@' + status.perfil; perfilLoaded = true; }
  const labels = {conectado:'● Conectado', conectando:'◌ Conectando…', reconectando:'◌ Reconectando…', desconectado:'○ Desconectado', dependencia_ausente:'Instalação necessária', offline:'Perfil fora do ar', erro:'Conexão indisponível'};
  $('tiktok-status').textContent = labels[status.estado] || status.estado;
  $('tiktok-status').dataset.state = status.estado;
  $('tiktok-message').textContent = status.mensagem;
  $('tiktok-counts').textContent = `${status.recebidos} comentários · ${status.aplicados} cuidados · ${status.ignorados} ignorados`;
  $('tiktok-last').textContent = status.ultimo ? `Último resultado: ${status.ultimo}` : '';
  const live = status.estado === 'conectado';
  $('live-badge').textContent = live ? 'COMENTÁRIOS AO VIVO' : status.ativo ? 'CONECTANDO AO TIKTOK' : 'MODO SIMULADOR';
  const mode = live ? `Comente para cuidar · @${status.perfil}` : status.ativo ? 'Chat pausado · tentando conectar…' : 'Modo simulador · TikTok desconectado';
  $('capture-mode').textContent = mode;
  $('footer-mode').textContent = mode;
  document.body.classList.toggle('tiktok-live', live);
  syncControls();
}
async function changeTikTok(connect) {
  if (tiktokBusy || busy) return;
  tiktokBusy = true; syncControls();
  $('tiktok-feedback').textContent = '';
  const current = ++revision;
  try {
    const data = await request(connect ? '/api/tiktok/conectar' : '/api/tiktok/desconectar', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(connect ? {perfil:$('tiktok-perfil').value} : {})});
    render(data, current); connection(true);
  } catch (error) {
    $('tiktok-feedback').textContent = error.validation ? error.message : 'Não foi possível falar com o servidor. Confira se o Rex está aberto.';
  } finally { tiktokBusy = false; syncControls(); }
}
$('tiktok-form').addEventListener('submit', event => { event.preventDefault(); changeTikTok(true); });
$('tiktok-disconnect').addEventListener('click', () => changeTikTok(false));
$('copy-capture').addEventListener('click', async () => {
  const url = new URL('/?captura=1', location.href).href;
  try { await navigator.clipboard.writeText(url); $('capture-feedback').textContent = 'Endereço copiado. Use uma fonte de 1080 × 1920.'; }
  catch { $('capture-feedback').textContent = `Copie este endereço: ${url}`; }
});
document.querySelectorAll('[data-command]').forEach(button => button.addEventListener('click', () => act(button.dataset.command)));
$('comando-form').addEventListener('submit', event => { event.preventDefault(); act($('comando').value); });
refresh();
