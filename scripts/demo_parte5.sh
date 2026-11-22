#!/usr/bin/env bash
# Parte 5 — demonstração ponta a ponta: API (Next.js) apontando para o bdr_api.
# Pré-requisitos: banco recém-criado (scripts/rodar_tudo.sh) e a API rodando com
# USAR_ROTINAS_BDR=true (ver docs/documento.md, Parte 5).
# Uso: API=http://127.0.0.1:3055 MYSQL="mysql -uroot -h127.0.0.1 -P3399" ./scripts/demo_parte5.sh
# Saída: docs/prints/parte5/*.txt
set -euo pipefail
API=${API:-http://127.0.0.1:3000}
MYSQL=${MYSQL:-"mysql -uroot -p"}
SAIDA="$(dirname "$0")/../docs/prints/parte5"
mkdir -p "$SAIDA"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
sql() { $MYSQL --default-character-set=utf8mb4 -N bdr_api -e "$1"; }

# Dados do cenário: o 1º usuário SUPORTE ativo, o 1º projeto ativo (cliente ativo),
# uma equipe extra e um técnico da equipe do projeto.
SUPORTE=$(sql "SELECT id FROM usuarios WHERE cargo='SUPORTE' AND ativo ORDER BY nome LIMIT 1")
read -r PROJETO EQ_PROJ < <(sql "SELECT p.id, p.equipe_id FROM projetos p JOIN clientes c ON c.id=p.cliente_id
                                   WHERE p.ativo AND c.ativo ORDER BY p.nome, p.id LIMIT 1")
EQ_EXTRA=$(sql "SELECT id FROM equipes WHERE ativo AND id<>'$EQ_PROJ' ORDER BY nome LIMIT 1")
TECNICO=$(sql "SELECT id FROM usuarios WHERE cargo='TECNICO' AND ativo AND equipe_id='$EQ_PROJ' ORDER BY nome LIMIT 1")
SLA=$(date -u -d '+3 hours' +%Y-%m-%dT%H:%M:%S.000Z)

{
  echo "### 1) Sessão do usuário SUPORTE — POST $API/api/dev/sessao"
  curl -s -c "$TMP/cj" -X POST "$API/api/dev/sessao" -H 'Content-Type: application/json' \
       -d "{\"usuarioId\":\"$SUPORTE\"}" -w '\nHTTP %{http_code}\n'
  echo
  echo "### 2) Criar ticket — POST $API/api/tickets   (API -> CALL sp_abrir_ticket)"
  CORPO="{\"titulo\":\"Câmera da doca 2 sem imagem\",\"descricao\":\"Câmera da doca 2 sem imagem desde as 14h.\",\"categoria\":\"MANUTENCAO\",\"prioridade\":\"ALTA\",\"slaEm\":\"$SLA\",\"projetoId\":\"$PROJETO\",\"abertoPorId\":\"$SUPORTE\",\"equipeIds\":[\"$EQ_EXTRA\"]}"
  echo "Corpo: $CORPO"
  curl -s -b "$TMP/cj" -X POST "$API/api/tickets" -H 'Content-Type: application/json' \
       -d "$CORPO" -w '\nHTTP %{http_code}\n' | tee "$TMP/criado"
} > "$SAIDA/01_criar_ticket.txt"
ID=$(head -1 "$TMP/criado" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

{
  echo "### 3) Consultar o ticket — GET $API/api/tickets/$ID   (API -> SELECT fn_situacao_sla(id))"
  curl -s -b "$TMP/cj" "$API/api/tickets/$ID" -w '\nHTTP %{http_code}\n'
  echo
  echo "### 4) Listagem — GET $API/api/tickets   (situacaoSla em cada item; resumo)"
  curl -s -b "$TMP/cj" "$API/api/tickets" | python3 -c "
import sys, json, collections
l = json.load(sys.stdin)
print('total de tickets:', len(l))
print('por situacaoSla:', dict(collections.Counter(t.get('situacaoSla') for t in l)))
print('5 primeiros (mais recentes):')
for t in l[:5]:
    print('  ', t['id'], '|', t['title'][:40].ljust(40), '|', t['status'].ljust(16), '|', t['situacaoSla'])"
} > "$SAIDA/02_consultar_ticket.txt"

{
  echo "### 5) Regra validada pela procedure — TÉCNICO da equipe do projeto tenta abrir ticket"
  curl -s -c "$TMP/cj2" -X POST "$API/api/dev/sessao" -H 'Content-Type: application/json' \
       -d "{\"usuarioId\":\"$TECNICO\"}" -w '\nHTTP %{http_code}\n'
  curl -s -b "$TMP/cj2" -X POST "$API/api/tickets" -H 'Content-Type: application/json' \
       -d "{\"titulo\":\"Teste de permissão do cargo\",\"descricao\":\"Técnico tentando abrir ticket.\",\"categoria\":\"MANUTENCAO\",\"prioridade\":\"BAIXA\",\"slaEm\":\"$SLA\",\"projetoId\":\"$PROJETO\",\"abertoPorId\":\"$TECNICO\"}" \
       -w '\nHTTP %{http_code}\n'
} > "$SAIDA/03_erro_regra_procedure.txt"

# A API usa sessão em UTC (MYSQL_SESSION_TIME_ZONE=+00:00), como o Prisma grava as datas.
$MYSQL --default-character-set=utf8mb4 -t -vvv bdr_api > "$SAIDA/04_select_banco.txt" 2>&1 <<SQL
SET time_zone = '+00:00';
SELECT id, titulo, prioridade, status, criado_em, sla_em, fn_situacao_sla(id) AS situacao_sla
  FROM tickets WHERE id = '$ID';
SELECT titulo, equipe_projeto, responsavel, aberto_por FROM vw_tickets_detalhados WHERE ticket_id = '$ID';
SELECT e.nome AS equipe_alocada FROM ticket_equipes te JOIN equipes e ON e.id = te.equipe_id
 WHERE te.ticket_id = '$ID' ORDER BY e.nome;
SELECT evento, descricao FROM historico_ticket WHERE ticket_id = '$ID';
SELECT tipo, descricao FROM atividades_conta WHERE usuario_id = '$SUPORTE' ORDER BY criado_em DESC LIMIT 1;
SELECT COUNT(*) AS tickets_do_tecnico FROM tickets WHERE aberto_por_id = '$TECNICO';
SQL
echo "ok: ticket $ID — evidências em $SAIDA"
