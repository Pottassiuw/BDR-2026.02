// Gera os modelos do bdr_api no formato XML nativo do brModelo 3.x
// (o mesmo que "Salvar como -> .xml" produz) + uma pré-visualização SVG.
// Uso: node scripts/brmodelo_conceitual.js modelos   (PREVIEW=1 também grava um .svg aproximado)
'use strict';
const fs = require('fs');
const path = require('path');
const OUT = process.argv[2] || path.join(__dirname, '..', 'modelos');

// ---------------------------------------------------------------- utilidades
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
// larguras aproximadas da Arial 12px
const W = {};
'ijl'.split('').forEach((c) => (W[c] = 2.7));
'ftrI ,.()'.split('').forEach((c) => (W[c] = 3.4));
'r'.split('').forEach((c) => (W[c] = 4.0));
'ckszvxyJ'.split('').forEach((c) => (W[c] = 6.0));
'abdeghnopqu0123456789_L'.split('').forEach((c) => (W[c] = 6.7));
'FTZ'.split('').forEach((c) => (W[c] = 7.4));
'ABEKPSVXYw'.split('').forEach((c) => (W[c] = 8.0));
'CDHNRU'.split('').forEach((c) => (W[c] = 8.7));
'GOQ'.split('').forEach((c) => (W[c] = 9.4));
'mM'.split('').forEach((c) => (W[c] = 10.0));
W.W = 11.4;
const tw = (s) => Math.ceil([...s].reduce((a, c) => a + (W[c] || 6.7), 0));
const FONTE = '<Fonte Nome="Arial" Estilo="0" Tamanho="12"/>';

let nextId = 0;
const id = () => ++nextId;

// =====================================================================
// MODELO CONCEITUAL
// =====================================================================
const EW = 170, ROW = 19, GAP = 30;
const ents = {}, itens = [], svg = [];

function entidade(nome, cx, cy, lado, atts, EW = 170) {
  const h = Math.max(56, atts.length * ROW + 10);
  const e = { tipo: 'Entidade', id: id(), nome, x: cx - EW / 2, y: cy - h / 2, w: EW, h };
  ents[nome] = e;
  itens.push(e);
  atts.forEach((spec, i) => atributo(e, spec, lado, e.y + 5 + ROW * i + ROW / 2));
  return e;
}

// "*nome" = identificador, "?nome" = opcional (0,1)
function atributo(dono, spec, lado, ay) {
  const ident = spec[0] === '*', opc = spec[0] === '?';
  const nome = ident || opc ? spec.slice(1) : spec;
  const w = tw(nome) + 14 + 8 + 4;
  const ax = lado === 'R' ? dono.x + dono.w + GAP : dono.x - GAP - w;
  const a = { tipo: 'Atributo', id: id(), nome, x: ax, y: ay - 7, w, h: 14, ident, opc, dir: lado === 'R' ? 0 : 1 };
  itens.push(a);
  const pDono = lado === 'R' ? [dono.x + dono.w, ay] : [dono.x, ay];
  const pAtt = lado === 'R' ? [ax, ay] : [ax + w, ay];
  ligacao(dono, pDono, a, pAtt, null);
}

function ligacao(A, pA, B, pB, card, papel) {
  const cardId = card !== null && card !== undefined ? id() : null; // id do card < id da ligação (maxID fica num item de topo)
  const l = { tipo: 'Ligacao', id: id(), A, B, pA, pB, card, cardId, papel: papel || '' };
  itens.push(l);
  return l;
}

function borda(e, s, f) {
  switch (s) {
    case 'T': return [e.x + e.w * f, e.y];
    case 'B': return [e.x + e.w * f, e.y + e.h];
    case 'L': return [e.x, e.y + e.h * f];
    default: return [e.x + e.w, e.y + e.h * f];
  }
}
function vertice(r, s) {
  const cx = r.x + r.w / 2, cy = r.y + r.h / 2;
  return { T: [cx, r.y], B: [cx, r.y + r.h], L: [r.x, cy], R: [r.x + r.w, cy] }[s];
}
const CARD = { '11': 0, '01': 1, '1N': 2, '0N': 3 };
const CARDTXT = ['(1,1)', '(0,1)', '(1,n)', '(0,n)'];

// perna: "ENTIDADE:card:ladoEntidade:fração:verticeDoLosango[:papel]"
// card = cardinalidade escrita junto à entidade (notação do brModelo/Heuser)
function rel(nome, cx, cy, pernas, attsRel) {
  const w = Math.max(100, tw(nome) + 56), h = 50;
  const r = { tipo: 'Relacionamento', id: id(), nome, x: cx - w / 2, y: cy - h / 2, w, h };
  itens.push(r);
  for (const p of pernas) {
    const [en, c, s, f, v, papel] = p.split(':');
    const e = ents[en];
    if (!e) throw new Error('entidade? ' + en);
    ligacao(e, borda(e, s, +f), r, vertice(r, v), CARD[c], papel);
  }
  (attsRel || []).forEach(([spec, lado, dy]) => {
    // atributo do relacionamento, saindo do vértice de cima/baixo
    const ident = false, opc = false, nome = spec;
    const wA = tw(nome) + 26;
    const ay = cy + dy;
    const a = { tipo: 'Atributo', id: id(), nome, x: cx + 30, y: ay - 7, w: wA, h: 14, ident, opc, dir: 0 };
    itens.push(a);
    ligacao(r, vertice(r, dy < 0 ? 'T' : 'B'), a, [a.x, ay], null);
  });
  return r;
}

// ---------------- entidades ----------------
const DY = 60; // margem superior
const E = (n, cx, cy, l, at, w) => entidade(n, cx, cy + DY, l, at, w);
const R = (n, cx, cy, p, at) => rel(n, cx, cy + DY, p, at);
E("CLIENTE", 330, 130, "L", ["*id", "nome", "ativo", "criado_em", "atualizado_em"]);
E("PROJETO", 1040, 330, "L", ["*id", "nome", "local_instalacao", "?descricao", "ativo", "criado_em", "atualizado_em"]);
E("EQUIPE", 1960, 130, "L", ["*id", "nome", "?descricao", "ativo", "criado_em", "atualizado_em"]);

E("CARGO", 330, 640, "L", ["*codigo", "nome", "descricao", "pode_abrir_ticket", "pode_aprovar_encerramento"]);
E("USUARIO", 1040, 680, "L", ["*id", "nome", "email", "senha_hash", "ativo", "senha_provisoria", "criado_em", "atualizado_em"], 280);
E("TICKET", 1960, 680, "R", ["*id", "titulo", "descricao", "categoria", "sla_em", "?encerrado_em", "criado_em", "atualizado_em"]);
E("PRIORIDADE", 2800, 470, "R", ["*codigo", "nome", "peso", "sla_horas", "alerta_horas"]);
E("STATUS_TICKET", 2800, 900, "R", ["*codigo", "nome", "descricao", "finalizado", "ordem"]);

E("ATIVIDADE_CONTA", 330, 1050, "L", ["*id", "tipo", "descricao", "criado_em"]);
E("RELATORIO", 1060, 1250, "L", ["*id", "trabalho_realizado", "materiais_utilizados", "outros_detalhes", "criado_em", "atualizado_em"]);
E("HISTORICO_TICKET", 1960, 1250, "R", ["*id", "evento", "descricao", "criado_em"]);

// ---------------- relacionamentos ----------------
R("contrata", 690, 130, ["CLIENTE:11:R:0.5:L", "PROJETO:0N:T:0.5:R"]);
R("atende", 1500, 20, ["EQUIPE:11:T:0.2:R", "PROJETO:0N:T:0.8:L"]);
R("gerencia", 989, 500, ["USUARIO:11:T:0.318:B", "PROJETO:0N:B:0.2:T"]);
R("gera", 1500, 330, ["PROJETO:11:R:0.5:L", "TICKET:0N:T:0.15:R"]);
R("pertence", 1700, 520, ["USUARIO:0N:T:0.8:L", "EQUIPE:01:B:0.3:T"]);
R("alocada", 1985, 420, ["TICKET:0N:T:0.65:B", "EQUIPE:1N:B:0.65:T"], [["criado_em", "R", -45]]);
R("possui", 690, 560, ["USUARIO:0N:T:0.05:R", "CARGO:11:R:0.5:L"]);
R("abre", 1500, 640, ["USUARIO:11:R:0.25:L", "TICKET:0N:L:0.25:R"]);
R("responsavel", 1500, 740, ["USUARIO:01:R:0.87:L", "TICKET:0N:L:0.87:R"]);
R("classifica", 2470, 470, ["TICKET:0N:T:0.92:L", "PRIORIDADE:11:L:0.5:R"]);
R("esta_em", 2470, 900, ["TICKET:0N:B:0.92:L", "STATUS_TICKET:11:L:0.5:R"]);
R("cria", 790, 900, ["USUARIO:0N:B:0.02:T:criado", "USUARIO:01:B:0.3:R:criador"]);
R("realiza", 690, 1050, ["USUARIO:11:B:0.6:R", "ATIVIDADE_CONTA:0N:R:0.5:L"]);
R("escreve", 1138, 1000, ["USUARIO:11:B:0.85:T", "RELATORIO:0N:T:0.96:B"]);
R("possui", 1500, 1110, ["TICKET:11:B:0.1:T", "RELATORIO:0N:R:0.3:L"]);
R("registra", 1960, 1000, ["TICKET:11:B:0.5:T", "HISTORICO_TICKET:0N:T:0.5:B"]);
R("e_autor", 1500, 820, ["USUARIO:01:R:0.97:L", "HISTORICO_TICKET:0N:L:0.3:R"]);
R("equipe_do_autor", 2220, 1400, ["EQUIPE:01:R:0.3:T", "HISTORICO_TICKET:0N:B:0.7:L"]);
R("inicia_atividade", 2330, 1520, ["EQUIPE:01:R:0.75:T", "HISTORICO_TICKET:0N:B:0.3:L"]);

// ---------------- XML ----------------
function xmlConceitual() {
  const o = [];
  o.push('<?xml version="1.0" encoding="UTF-8" standalone="no"?>');
  o.push(`<DIAGRAMA ID="0" TIPO="tpConceitual" UniversalUnicID="${uuid()}">`);
  const forma = (it) =>
    `<Bounds Height="${Math.round(it.h)}" Left="${Math.round(it.x)}" Top="${Math.round(it.y)}" Width="${Math.round(it.w)}"/>` +
    `<DisablePainted Valor="false"/><Texto>${esc(it.nome)}</Texto><Observacao/><Dicionario/>${FONTE}<Ancorado Valor="false"/>`;
  for (const it of itens) {
    if (it.tipo === 'Entidade') {
      o.push(`<Entidade ID="${it.id}">${forma(it)}<AtributosOcultos Valor=""/></Entidade>`);
    } else if (it.tipo === 'Relacionamento') {
      o.push(`<Relacionamento ID="${it.id}">${forma(it)}</Relacionamento>`);
    } else if (it.tipo === 'Atributo') {
      o.push(
        `<Atributo ID="${it.id}">${forma(it)}<DirecaoFromInspector Valor="${it.dir}"/><Autosize Valor="true"/>` +
          `<Identificador Valor="${it.ident}"/><Opcional Valor="${it.opc}"/><Multivalorado Valor="false"/>` +
          `<CardMinFromString Valor="${it.opc ? 0 : 1}"/><CardMaxFromString Valor="1"/><TipoAtributo Valor=""/></Atributo>`
      );
    } else if (it.tipo === 'Ligacao') {
      const pt = (p) => `<Ponto Left="${Math.round(p[0]) - 3}" Top="${Math.round(p[1]) - 3}"/>`;
      let card = '';
      if (it.card !== null) {
        card =
          `<Cardinalidade ID="${it.cardId}"><DisablePainted Valor="false"/><Texto>${CARDTXT[it.card]}</Texto><Observacao/><Dicionario/>${FONTE}` +
          `<Ancorado Valor="false"/><TamanhoAutmatico Valor="true"/><Card Valor="${it.card}"/><MovimentacaoManual Valor="false"/><Papel Valor="${esc(it.papel)}"/></Cardinalidade>`;
      }
      o.push(
        `<Ligacao ID="${it.id}"><DisablePainted Valor="false"/><Tag LinhaMestre="-1"/><Dashed Valor="false"/><Ancorado Valor="false"/>` +
          `<Inteligente Valor="true"/><Largura Valor="1"/><Ligacoes PontaA="${it.A.id}" PontaB="${it.B.id}"/>` +
          `<Pontos>${pt(it.pA)}${pt(it.pB)}</Pontos>${card}</Ligacao>`
      );
    }
  }
  o.push('</DIAGRAMA>');
  return o.join('\n') + '\n';
}

function uuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

// ---------------- preview SVG (aproximação do que o brModelo desenha) ----------------
function previewConceitual() {
  let maxX = 0, maxY = 0;
  itens.forEach((i) => { if (i.w) { maxX = Math.max(maxX, i.x + i.w); maxY = Math.max(maxY, i.y + i.h); } });
  const s = [`<svg xmlns="http://www.w3.org/2000/svg" width="${maxX + 60}" height="${maxY + 60}" font-family="Arial" font-size="12">`,
    `<rect width="100%" height="100%" fill="white"/>`];
  for (const it of itens) {
    if (it.tipo === 'Ligacao') {
      const [x1, y1] = it.pA, [x2, y2] = it.pB;
      // cotovelo simples: sai na direção do lado da entidade
      const horiz = Math.abs(x1 - it.A.x) < 1 || Math.abs(x1 - (it.A.x + it.A.w)) < 1;
      const mid = horiz ? `${x2},${y1}` : `${x1},${y2}`;
      s.push(`<polyline points="${x1},${y1} ${mid} ${x2},${y2}" fill="none" stroke="black"/>`);
      if (it.card !== null) s.push(`<text x="${x1 + 4}" y="${y1 - 4}" fill="#c00">${CARDTXT[it.card]}${it.papel ? ' ' + it.papel : ''}</text>`);
    }
  }
  for (const it of itens) {
    if (it.tipo === 'Entidade') {
      s.push(`<rect x="${it.x}" y="${it.y}" width="${it.w}" height="${it.h}" fill="#eef" stroke="black"/>`);
      s.push(`<text x="${it.x + it.w / 2}" y="${it.y + it.h / 2 + 4}" text-anchor="middle" font-weight="bold">${it.nome}</text>`);
    } else if (it.tipo === 'Relacionamento') {
      const cx = it.x + it.w / 2, cy = it.y + it.h / 2;
      s.push(`<polygon points="${it.x},${cy} ${cx},${it.y} ${it.x + it.w},${cy} ${cx},${it.y + it.h}" fill="#fee" stroke="black"/>`);
      s.push(`<text x="${cx}" y="${cy + 4}" text-anchor="middle">${it.nome}</text>`);
    } else if (it.tipo === 'Atributo') {
      const cxc = it.dir === 0 ? it.x + 7 : it.x + it.w - 7;
      s.push(`<circle cx="${cxc}" cy="${it.y + 7}" r="6" fill="${it.ident ? 'black' : 'white'}" stroke="black" ${it.opc ? 'stroke-dasharray="3,2"' : ''}/>`);
      if (it.dir === 0) s.push(`<text x="${it.x + 16}" y="${it.y + 11}">${it.nome}</text>`);
      else s.push(`<text x="${it.x + it.w - 16}" y="${it.y + 11}" text-anchor="end">${it.nome}</text>`);
    }
  }
  s.push('</svg>');
  return s.join('\n');
}

fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, 'modelo-conceitual.xml'), xmlConceitual(), 'utf8');
if (process.env.PREVIEW) fs.writeFileSync(path.join(OUT, 'preview-conceitual.svg'), previewConceitual(), 'utf8');
console.log('conceitual:', itens.length, 'itens, maxId', nextId);
module.exports = { tw, esc, uuid, FONTE };
