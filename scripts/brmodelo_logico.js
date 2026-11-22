// MODELO LÓGICO (MySQL 8) no formato XML do brModelo — espelha sql/01_ddl.sql
// Uso: node scripts/brmodelo_logico.js modelos   (gera também o conceitual; PREVIEW=1 grava .svg aproximados)
'use strict';
const fs = require('fs');
const path = require('path');
const { tw, esc, uuid, FONTE } = require('./brmodelo_conceitual.js'); // também regenera o conceitual
const OUT = process.argv[2] || path.join(__dirname, '..', 'modelos');

let nextId = 0;
const id = () => ++nextId;
const tabs = {}, tlist = [], linhas = [];
const UUID = 'CHAR(36)', DT = 'DATETIME(3)', BOOL = 'BOOLEAN';

// campo: [nome, tipo, flags, dicionario]  flags: K = PK, N = aceita NULL
function tabela(nome, x, y, campos, uniques) {
  const cs = campos.map(([n, t, fl = '', d = '']) => ({ n, t, k: fl.includes('K'), nul: fl.includes('N'), u: false, fk: false, d }));
  (uniques || []).forEach((u) => u.cols.forEach((c) => (cs.find((f) => f.n === c).u = true)));
  const w = Math.max(190, ...cs.map((c) => tw(`${c.n}: ${c.t}`) + 16 + 4 + 14), tw(nome) + 30);
  const h = 26 + cs.length * 22 + 4;
  const t = { id: id(), nome, x, y, w, h, campos: cs, uniques: uniques || [], fks: [] };
  tabs[nome] = t;
  tlist.push(t);
  return t;
}

function lado(t, s, f) {
  switch (s) {
    case 'T': return [t.x + t.w * f, t.y];
    case 'B': return [t.x + t.w * f, t.y + t.h];
    case 'L': return [t.x, t.y + t.h * f];
    default: return [t.x + t.w, t.y + t.h * f];
  }
}

// pos = "ladoPK:f:ladoFK:f" (null = autorrelacionamento, sem linha)
// cardinalidades (como o conversor do brModelo): junto à tabela da PK (1,1) ou (0,1) se a FK aceita NULL;
// junto à tabela da FK (0,n).
function fk(tf, col, tp, nome, upd, del, pos) {
  const F = tabs[tf], P = tabs[tp];
  const c = F.campos.find((x) => x.n === col);
  const pkc = P.campos.find((x) => x.k);
  if (!c || c.t !== pkc.t) throw new Error(`tipo FK ${tf}.${col} != ${tp}.${pkc.n}`);
  c.fk = true;
  let lin = null;
  if (pos) {
    const [sa, fa, sb, fb] = pos.split(':');
    const cardAid = id(), cardBid = id(); // ids dos cards < id da linha
    lin = { id: id(), A: P, B: F, pA: lado(P, sa, +fa), pB: lado(F, sb, +fb), cardA: c.nul ? 1 : 0, cardB: 3, cardAid, cardBid };
    linhas.push(lin);
  }
  F.fks.push({ nome, col, P, upd, del, lin });
}

// ---------------- tabelas (posição = canto superior esquerdo) ----------------
tabela('clientes', 60, 60, [['id', UUID, 'K'], ['nome', 'VARCHAR(150)'], ['ativo', BOOL], ['criado_em', DT], ['atualizado_em', DT]],
  [{ nome: 'uq_clientes_nome', cols: ['nome'] }]);
tabela('projetos', 520, 60, [['id', UUID, 'K'], ['nome', 'VARCHAR(150)'], ['local_instalacao', 'VARCHAR(255)'], ['descricao', 'TEXT', 'N'], ['ativo', BOOL],
  ['criado_em', DT], ['atualizado_em', DT], ['cliente_id', UUID], ['equipe_id', UUID], ['gestor_id', UUID]],
  [{ nome: 'uq_projetos_cliente_nome', cols: ['cliente_id', 'nome'] }]);
tabela('equipes', 1500, 60, [['id', UUID, 'K'], ['nome', 'VARCHAR(100)'], ['descricao', 'VARCHAR(255)', 'N'], ['ativo', BOOL], ['criado_em', DT], ['atualizado_em', DT]],
  [{ nome: 'uq_equipes_nome', cols: ['nome'] }]);
tabela('ticket_equipes', 1500, 290, [['id', UUID, 'K'], ['criado_em', DT], ['ticket_id', UUID], ['equipe_id', UUID]],
  [{ nome: 'uq_ticket_equipes_ticket_equipe', cols: ['ticket_id', 'equipe_id'] }]);

tabela('cargos', 60, 470, [['codigo', 'ENUM', 'K', "ENUM('TECNICO','GESTOR','SUPORTE','SUPORTE_INTERNO','COMERCIAL')"], ['nome', 'VARCHAR(60)'],
  ['descricao', 'VARCHAR(255)'], ['pode_abrir_ticket', BOOL], ['pode_aprovar_encerramento', BOOL]], [{ nome: 'uq_cargos_nome', cols: ['nome'] }]);
tabela('usuarios', 520, 470, [['id', UUID, 'K'], ['nome', 'VARCHAR(120)'], ['email', 'VARCHAR(254)'], ['senha_hash', 'VARCHAR(255)'],
  ['cargo', 'ENUM', '', "ENUM('TECNICO','GESTOR','SUPORTE','SUPORTE_INTERNO','COMERCIAL')"], ['ativo', BOOL], ['senha_provisoria', BOOL],
  ['criado_em', DT], ['atualizado_em', DT], ['equipe_id', UUID, 'N'], ['criado_por_id', UUID, 'N']],
  [{ nome: 'uq_usuarios_email', cols: ['email'] }]);
tabela('tickets', 1010, 540, [['id', UUID, 'K'], ['titulo', 'VARCHAR(180)'], ['descricao', 'TEXT'], ['categoria', 'ENUM', '', "ENUM('MANUTENCAO','INSTALACAO')"],
  ['prioridade', 'ENUM', '', "ENUM('BAIXA','MEDIA','ALTA','CRITICA') DEFAULT 'MEDIA'"],
  ['status', 'ENUM', '', "ENUM('NAO_INICIADO','EM_ANDAMENTO','SOLICITACAO_ENCERRAMENTO','ENCERRADO','EM_REVISAO') DEFAULT 'EM_ANDAMENTO'"],
  ['sla_em', DT], ['encerrado_em', DT, 'N'], ['criado_em', DT], ['atualizado_em', DT],
  ['projeto_id', UUID], ['aberto_por_id', UUID], ['responsavel_id', UUID, 'N']]);
tabela('prioridades', 1500, 570, [['codigo', 'ENUM', 'K', "ENUM('BAIXA','MEDIA','ALTA','CRITICA')"], ['nome', 'VARCHAR(30)'], ['peso', 'TINYINT UNSIGNED'],
  ['sla_horas', 'SMALLINT UNSIGNED'], ['alerta_horas', 'SMALLINT UNSIGNED']], [{ nome: 'uq_prioridades_peso', cols: ['peso'] }]);
tabela('status_ticket', 1500, 760, [['codigo', 'ENUM', 'K', "ENUM('NAO_INICIADO','EM_ANDAMENTO','SOLICITACAO_ENCERRAMENTO','ENCERRADO','EM_REVISAO')"],
  ['nome', 'VARCHAR(40)'], ['descricao', 'VARCHAR(255)'], ['finalizado', BOOL], ['ordem', 'TINYINT UNSIGNED']], [{ nome: 'uq_status_ticket_ordem', cols: ['ordem'] }]);

tabela('atividades_conta', 60, 990, [['id', UUID, 'K'], ['tipo', 'VARCHAR(20)'], ['descricao', 'TEXT'], ['criado_em', DT], ['usuario_id', UUID]]);
tabela('relatorios', 520, 990, [['id', UUID, 'K'], ['trabalho_realizado', 'TEXT'], ['materiais_utilizados', 'TEXT'], ['outros_detalhes', 'TEXT'],
  ['criado_em', DT], ['atualizado_em', DT], ['ticket_id', UUID], ['autor_id', UUID]]);
tabela('historico_ticket', 1010, 990, [['id', UUID, 'K'], ['evento', 'VARCHAR(50)'], ['descricao', 'TEXT'], ['criado_em', DT], ['ticket_id', UUID],
  ['usuario_id', UUID, 'N'], ['equipe_id', UUID, 'N'], ['inicio_equipe_id', UUID, 'N']],
  [{ nome: 'uq_historico_inicio_equipe', cols: ['ticket_id', 'inicio_equipe_id'] }]);

// ---------------- chaves estrangeiras / ligações ----------------
const C = 'CASCADE', RS = 'RESTRICT', SN = 'SET NULL';
fk('usuarios', 'cargo', 'cargos', 'fk_usuarios_cargo', C, RS, 'R:0.5:L:0.27');
fk('usuarios', 'equipe_id', 'equipes', 'fk_usuarios_equipe', C, SN, 'L:0.85:R:0.05');
fk('usuarios', 'criado_por_id', 'usuarios', 'fk_usuarios_criado_por', C, SN, null);
fk('projetos', 'cliente_id', 'clientes', 'fk_projetos_cliente', C, RS, 'R:0.5:L:0.3');
fk('projetos', 'equipe_id', 'equipes', 'fk_projetos_equipe', C, RS, 'L:0.3:R:0.2');
fk('projetos', 'gestor_id', 'usuarios', 'fk_projetos_gestor', C, RS, 'T:0.3:B:0.3');
fk('tickets', 'prioridade', 'prioridades', 'fk_tickets_prioridade', C, RS, 'L:0.5:R:0.22');
fk('tickets', 'status', 'status_ticket', 'fk_tickets_status', RS, RS, 'L:0.5:R:0.62');
fk('tickets', 'projeto_id', 'projetos', 'fk_tickets_projeto', C, RS, 'R:0.85:T:0.25');
fk('tickets', 'aberto_por_id', 'usuarios', 'fk_tickets_aberto_por', C, RS, 'R:0.478:L:0.19');
fk('tickets', 'responsavel_id', 'usuarios', 'fk_tickets_responsavel', C, SN, 'R:0.735:L:0.443');
fk('ticket_equipes', 'ticket_id', 'tickets', 'fk_ticket_equipes_ticket', C, C, 'T:0.8:L:0.5');
fk('ticket_equipes', 'equipe_id', 'equipes', 'fk_ticket_equipes_equipe', C, C, 'B:0.5:T:0.5');
fk('relatorios', 'ticket_id', 'tickets', 'fk_relatorios_ticket', C, RS, 'L:0.93:T:0.9');
fk('relatorios', 'autor_id', 'usuarios', 'fk_relatorios_autor', C, RS, 'B:0.4:T:0.4');
fk('historico_ticket', 'ticket_id', 'tickets', 'fk_historico_ticket', C, RS, 'B:0.5:T:0.5');
fk('historico_ticket', 'usuario_id', 'usuarios', 'fk_historico_usuario', C, SN, 'R:0.95:L:0.25');
fk('historico_ticket', 'equipe_id', 'equipes', 'fk_historico_equipe', C, SN, 'R:0.4:R:0.4');
fk('historico_ticket', 'inicio_equipe_id', 'equipes', 'fk_historico_inicio_equipe', C, SN, 'R:0.8:R:0.75');
fk('atividades_conta', 'usuario_id', 'usuarios', 'fk_atividades_usuario', C, C, 'L:0.9:T:0.5');

// ---------------- XML ----------------
function xmlLogico() {
  const o = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>', `<DIAGRAMA ID="0" TIPO="tpLogico" UniversalUnicID="${uuid()}">`];
  const lst = (a) => '[' + a.join(', ') + ']';
  for (const t of tlist) {
    const campos = t.campos.map((c) =>
      `<Campo><Texto>${esc(c.n)}</Texto><Tipo>${esc(c.t)}</Tipo><Complemento>${c.nul ? 'NULL' : 'NOT NULL'}</Complemento>` +
      `<Dicionario>${esc(c.d)}</Dicionario><Observacao/><Key Valor="${c.k}"/><Fkey Valor="${c.fk}"/><Unique Valor="${c.u}"/></Campo>`).join('');
    const idx = (n) => t.campos.findIndex((c) => c.n === n);
    // ordem das constraints: PK (índice 0), UNIQUEs, FKs — as FKs apontam para "idTabela,0"
    const con = (nome, tipo, upd, del, lig, ori, co, cd) =>
      `<Constraint><Nome Valor="${nome}"/><Nomeada Valor="true"/><Tipo Valor="${tipo}"/><Dicionario/><Observacao/>` +
      `<DdlOnUpdate>${upd}</DdlOnUpdate><DdlOnDelete>${del}</DdlOnDelete><LigacaoParaOrigem ID="${lig}"/>` +
      `<ConstraintOrigem CamposDestino="${lst(cd)}" CamposOrigem="${lst(co)}" ID="${ori}"/></Constraint>`;
    const pks = t.campos.filter((c) => c.k).map((c) => idx(c.n));
    const cons = [con('pk_' + t.nome, 0, '', '', -1, '-1,-1', pks, pks.map(() => -1))];
    t.uniques.forEach((u) => cons.push(con(u.nome, 1, '', '', -1, '-1,-1', u.cols.map(idx), u.cols.map(() => -1))));
    t.fks.forEach((f) => {
      const pkIdx = f.P.campos.findIndex((c) => c.k);
      cons.push(con(f.nome, 2, f.upd, f.del, f.lin ? f.lin.id : -1, `${f.P.id},0`, [pkIdx], [idx(f.col)]));
    });
    o.push(
      `<Tabela ID="${t.id}"><Bounds Height="${t.h}" Left="${t.x}" Top="${t.y}" Width="${t.w}"/><DisablePainted Valor="false"/>` +
      `<Texto>${esc(t.nome)}</Texto><Observacao/><Dicionario/>${FONTE}<Ancorado Valor="false"/>` +
      `<Delimite Valor="true"/><Roundrect Valor="22"/><Gradiente Valor="true"/><GradienteStartColor Valor="0,0,0,255"/>` +
      `<GradienteEndColor Valor="204,204,204,255"/><CorBorda Valor="0,0,0,255"/><GDirecao Valor="0"/><Alfa Valor="25"/>` +
      `<Autosize Valor="true"/><ShowDDL Valor="false"/><ShowInPlain Valor="false"/><MostrarConstraints Valor="false"/><PlainIR Valor="true"/>` +
      `<Campos>${campos}</Campos><Constraints>${cons.join('')}</Constraints></Tabela>`
    );
  }
  const card = (cid, v) =>
    `<LogicoCardinalidade ID="${cid}"><DisablePainted Valor="false"/><Texto/><Observacao/><Dicionario/>${FONTE}<Ancorado Valor="false"/>` +
    `<TamanhoAutmatico Valor="true"/><Card Valor="${v}"/><MovimentacaoManual Valor="false"/><Papel Valor=""/></LogicoCardinalidade>`;
  const pt = (p) => `<Ponto Left="${Math.round(p[0]) - 3}" Top="${Math.round(p[1]) - 3}"/>`;
  for (const l of linhas) {
    o.push(
      `<LogicoLinha ID="${l.id}"><DisablePainted Valor="false"/><Tag LinhaMestre="-1"/><Dashed Valor="false"/><Ancorado Valor="false"/>` +
      `<TemSetaPontaA Valor="false"/><TemSetaPontaB Valor="false"/><SetaAberta Valor="false"/><SetaLargura Valor="10"/>` +
      `<Inteligente Valor="true"/><SetaAutomatica Valor="true"/><Largura Valor="1"/><Ligacoes PontaA="${l.A.id}" PontaB="${l.B.id}"/>` +
      `<Pontos>${pt(l.pA)}${pt(l.pB)}</Pontos>${card(l.cardAid, l.cardA)}${card(l.cardBid, l.cardB)}</LogicoLinha>`
    );
  }
  o.push('</DIAGRAMA>');
  return o.join('\n') + '\n';
}

// ---------------- preview SVG (aproximado) ----------------
function previewLogico() {
  let maxX = 0, maxY = 0;
  tlist.forEach((t) => { maxX = Math.max(maxX, t.x + t.w); maxY = Math.max(maxY, t.y + t.h); });
  const s = [`<svg xmlns="http://www.w3.org/2000/svg" width="${maxX + 200}" height="${maxY + 80}" font-family="Arial" font-size="12">`,
    '<rect width="100%" height="100%" fill="white"/>'];
  const CT = ['(1,1)', '(0,1)', '(1,n)', '(0,n)'];
  const onSide = (p, t) => Math.abs(p[0] - t.x) < 1 || Math.abs(p[0] - t.x - t.w) < 1;
  for (const l of linhas) {
    const [x1, y1] = l.pA, [x2, y2] = l.pB;
    const hA = onSide(l.pA, l.A), hB = onSide(l.pB, l.B);
    let pts;
    if (hA && hB) {
      const right = Math.abs(x1 - l.A.x - l.A.w) < 1 && Math.abs(x2 - l.B.x - l.B.w) < 1;
      const mx = right ? Math.max(x1, x2) + 50 * (1 + (y1 > 300)) : (x1 + x2) / 2;
      pts = `${x1},${y1} ${mx},${y1} ${mx},${y2} ${x2},${y2}`;
    } else if (!hA && !hB) {
      const my = (y1 + y2) / 2;
      pts = `${x1},${y1} ${x1},${my} ${x2},${my} ${x2},${y2}`;
    } else pts = `${x1},${y1} ${hA ? x2 : x1},${hA ? y1 : y2} ${x2},${y2}`;
    s.push(`<polyline points="${pts}" fill="none" stroke="black"/>`);
    s.push(`<text x="${x1 + 3}" y="${y1 - 3}" fill="#c00" font-size="10">${CT[l.cardA]}</text><text x="${x2 + 3}" y="${y2 - 3}" fill="#c00" font-size="10">${CT[l.cardB]}</text>`);
  }
  for (const t of tlist) {
    s.push(`<rect x="${t.x}" y="${t.y}" width="${t.w}" height="${t.h}" rx="8" fill="#f4f4f4" stroke="black"/>`);
    s.push(`<text x="${t.x + t.w / 2}" y="${t.y + 17}" text-anchor="middle" font-weight="bold">${t.nome}</text>`);
    t.campos.forEach((c, i) => {
      const y = t.y + 26 + i * 22 + 15;
      const ic = c.k ? 'PK' : c.fk ? 'FK' : c.u ? 'UN' : '';
      s.push(`<text x="${t.x + 3}" y="${y}" font-size="9" fill="#06c">${ic}</text><text x="${t.x + 22}" y="${y}">${c.n}: ${c.t}</text>`);
    });
  }
  s.push('</svg>');
  return s.join('\n');
}

fs.writeFileSync(path.join(OUT, 'modelo-logico.xml'), xmlLogico(), 'utf8');
if (process.env.PREVIEW) fs.writeFileSync(path.join(OUT, 'preview-logico.svg'), previewLogico(), 'utf8');
console.log('logico:', tlist.length, 'tabelas,', linhas.length, 'ligacoes, maxId', nextId);
