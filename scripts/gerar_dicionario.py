#!/usr/bin/env python3
"""Gera docs/dicionario-de-dados.md a partir do information_schema do banco bdr_api
(tipos, nulos, defaults, PK/FK/UNIQUE/CHECK) + descrições escritas abaixo.
Uso: MYSQL="mysql -uroot -h127.0.0.1 -P3399" python3 scripts/gerar_dicionario.py"""
import os
import shlex
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MYSQL = shlex.split(os.environ.get("MYSQL", "mysql -uroot -p"))

TABELAS = {
    "cargos": ("Domínio dos cargos (perfis de acesso) dos usuários e suas permissões.", {
        "codigo": "Código do cargo (mesmo ENUM `Cargo` da API).",
        "nome": "Nome do cargo para exibição.",
        "descricao": "O que o cargo faz no sistema.",
        "pode_abrir_ticket": "Indica se o cargo pode abrir tickets.",
        "pode_aprovar_encerramento": "Indica se o cargo pode aprovar/negar encerramentos.",
    }),
    "prioridades": ("Domínio das prioridades de ticket, com o SLA padrão de cada uma.", {
        "codigo": "Código da prioridade (mesmo ENUM `Prioridade` da API).",
        "nome": "Nome para exibição.",
        "peso": "Peso para ordenar a fila (maior = mais urgente).",
        "sla_horas": "Prazo padrão do SLA, em horas, a partir da abertura.",
        "alerta_horas": "Antecedência (h) para o ticket ser considerado EM_ALERTA.",
    }),
    "status_ticket": ("Domínio dos status do ciclo de vida do ticket.", {
        "codigo": "Código do status (mesmo ENUM `StatusTicket` da API).",
        "nome": "Nome para exibição.",
        "descricao": "Significado do status.",
        "finalizado": "Indica status final (ticket encerrado).",
        "ordem": "Ordem do status no fluxo.",
    }),
    "equipes": ("Equipes técnicas que atendem projetos e tickets.", {
        "id": "Identificador (UUID).",
        "nome": "Nome da equipe.",
        "descricao": "Área de atuação da equipe.",
        "ativo": "Equipe ativa (TRUE) ou desativada.",
        "criado_em": "Data/hora de criação.",
        "atualizado_em": "Data/hora da última alteração (automática).",
    }),
    "usuarios": ("Contas dos funcionários (técnicos, gestores, analistas).", {
        "id": "Identificador (UUID).",
        "nome": "Nome completo.",
        "email": "E-mail de login (único).",
        "senha_hash": "Hash bcrypt da senha.",
        "cargo": "Cargo/perfil de acesso.",
        "ativo": "Conta ativa (pode logar) ou desativada.",
        "senha_provisoria": "TRUE enquanto o usuário não trocar a senha provisória.",
        "criado_em": "Data/hora de criação.",
        "atualizado_em": "Data/hora da última alteração (automática).",
        "equipe_id": "Equipe à qual o usuário pertence (opcional).",
        "criado_por_id": "Usuário (Suporte Interno) que criou a conta.",
    }),
    "clientes": ("Clientes da Altave donos dos projetos.", {
        "id": "Identificador (UUID).",
        "nome": "Razão social / nome do cliente.",
        "ativo": "Cliente ativo.",
        "criado_em": "Data/hora de criação.",
        "atualizado_em": "Data/hora da última alteração (automática).",
    }),
    "projetos": ("Projetos (instalações) contratados por clientes e atendidos por uma equipe.", {
        "id": "Identificador (UUID).",
        "nome": "Nome do projeto (único por cliente).",
        "local_instalacao": "Endereço/local da instalação.",
        "descricao": "Descrição do projeto.",
        "ativo": "Projeto ativo (aceita novos tickets).",
        "criado_em": "Data/hora de criação.",
        "atualizado_em": "Data/hora da última alteração (automática).",
        "cliente_id": "Cliente dono do projeto.",
        "equipe_id": "Equipe responsável pelo projeto.",
        "gestor_id": "Gestor responsável pelo projeto.",
    }),
    "tickets": ("Tickets / ordens de serviço de instalação ou manutenção.", {
        "id": "Identificador (UUID).",
        "titulo": "Título curto do chamado.",
        "descricao": "Descrição detalhada do problema/serviço.",
        "categoria": "MANUTENCAO ou INSTALACAO.",
        "prioridade": "Prioridade do ticket.",
        "status": "Status atual no fluxo.",
        "sla_em": "Data-limite do SLA.",
        "encerrado_em": "Data/hora do encerramento (só quando ENCERRADO).",
        "criado_em": "Data/hora de abertura.",
        "atualizado_em": "Data/hora da última alteração (automática).",
        "projeto_id": "Projeto ao qual o ticket pertence.",
        "aberto_por_id": "Usuário que abriu o ticket.",
        "responsavel_id": "Técnico responsável (opcional).",
    }),
    "ticket_equipes": ("Associativa N:N: equipes alocadas em cada ticket.", {
        "id": "Identificador (UUID).",
        "criado_em": "Quando a equipe foi alocada.",
        "ticket_id": "Ticket.",
        "equipe_id": "Equipe alocada.",
    }),
    "relatorios": ("Relatórios de atendimento registrados pelos técnicos.", {
        "id": "Identificador (UUID).",
        "trabalho_realizado": "Descrição do reparo/serviço feito.",
        "materiais_utilizados": "Materiais usados no atendimento.",
        "outros_detalhes": "Observações gerais.",
        "criado_em": "Data/hora do registro.",
        "atualizado_em": "Data/hora da última alteração (automática).",
        "ticket_id": "Ticket atendido.",
        "autor_id": "Técnico autor do relatório.",
    }),
    "historico_ticket": ("Linha do tempo (log) de eventos de cada ticket.", {
        "id": "Identificador (UUID).",
        "evento": "Tipo do evento (TICKET_CRIADO, ATIVIDADE_INICIADA, LOG, ENCERRAMENTO_*, STATUS_ALTERADO, ALERTA_SLA...).",
        "descricao": "Texto do evento / parecer.",
        "criado_em": "Data/hora do evento.",
        "ticket_id": "Ticket do evento.",
        "usuario_id": "Autor do evento (NULL = evento automático do sistema).",
        "equipe_id": "Equipe do autor no momento do evento.",
        "inicio_equipe_id": "Preenchido só em ATIVIDADE_INICIADA: garante um início por equipe (UNIQUE com ticket_id).",
    }),
    "atividades_conta": ("Auditoria das ações feitas por/sobre cada conta de usuário.", {
        "id": "Identificador (UUID).",
        "tipo": "Categoria da atividade (CADASTRO, EQUIPE, LOG, PROJETO, TICKET, TICKET | ABERTURA, CONTA).",
        "descricao": "Descrição da atividade.",
        "criado_em": "Data/hora da atividade.",
        "usuario_id": "Usuário da atividade.",
    }),
}


def sql(q):
    r = subprocess.run(MYSQL + ["-N", "-B", "--default-character-set=utf8mb4", "information_schema", "-e", q],
                       capture_output=True, text=True, check=True)
    return [l.split("\t") for l in r.stdout.splitlines()]


out = ["# Dicionário de Dados — banco `bdr_api`", "",
       "BDR 2026.02 — 3ª Avaliação · Parte 4. Gerado a partir do `information_schema` do MySQL 8 "
       "(script `scripts/gerar_dicionario.py`) após rodar `sql/01_ddl.sql`.", "",
       "Legenda: **PK** chave primária · **FK** chave estrangeira · **UQ** único · **NN** NOT NULL · "
       "**CK** regra CHECK. Todos os `id` são UUID (CHAR(36)), como na API.", "",
       "## Tabelas", ""]
for t, (desc, _) in TABELAS.items():
    out.append(f"- [`{t}`](#{t.replace('_', '_')}) — {desc}")
out.append("")

for t, (desc, cols_desc) in TABELAS.items():
    cols = sql(f"SELECT column_name, column_type, is_nullable, IFNULL(column_default,'∅'), extra "
               f"FROM columns WHERE table_schema='bdr_api' AND table_name='{t}' ORDER BY ordinal_position")
    pk = {r[0] for r in sql(f"SELECT column_name FROM key_column_usage WHERE table_schema='bdr_api' "
                            f"AND table_name='{t}' AND constraint_name='PRIMARY'")}
    fks = {r[0]: (r[1], r[2], r[3]) for r in sql(
        f"SELECT k.column_name, k.referenced_table_name, k.referenced_column_name, "
        f"CONCAT('ON DELETE ', r.delete_rule) FROM key_column_usage k JOIN referential_constraints r "
        f"ON r.constraint_schema=k.constraint_schema AND r.constraint_name=k.constraint_name "
        f"WHERE k.table_schema='bdr_api' AND k.table_name='{t}' AND k.referenced_table_name IS NOT NULL")}
    uqs = sql(f"SELECT tc.constraint_name, GROUP_CONCAT(k.column_name ORDER BY k.ordinal_position) "
              f"FROM table_constraints tc JOIN key_column_usage k ON k.constraint_schema=tc.constraint_schema "
              f"AND k.table_name=tc.table_name AND k.constraint_name=tc.constraint_name "
              f"WHERE tc.table_schema='bdr_api' AND tc.table_name='{t}' AND tc.constraint_type='UNIQUE' "
              f"GROUP BY tc.constraint_name")
    cks = sql(f"SELECT cc.constraint_name, cc.check_clause FROM check_constraints cc JOIN table_constraints tc "
              f"ON tc.constraint_schema=cc.constraint_schema AND tc.constraint_name=cc.constraint_name "
              f"WHERE cc.constraint_schema='bdr_api' AND tc.table_name='{t}'")
    uq_cols = {}
    for nome, cs in uqs:
        for c in cs.split(","):
            uq_cols.setdefault(c, []).append(nome + (" (composta)" if "," in cs else ""))
    n = sql(f"SELECT COUNT(*) FROM bdr_api.{t}")[0][0]
    out += [f"## {t}", "", f"{desc} Registros na carga (02_dml.sql): **{n}**.", "",
            "| Campo | Descrição | Tipo | Nulo | Default | Chave | Restrições |",
            "|---|---|---|---|---|---|---|"]
    for c, tipo, nulo, default, extra in cols:
        chave = []
        if c in pk:
            chave.append("PK")
        if c in fks:
            chave.append(f"FK → `{fks[c][0]}.{fks[c][1]}`")
        if c in uq_cols:
            chave.append("UQ")
        restr = []
        if nulo == "NO":
            restr.append("NN")
        if c in uq_cols:
            restr += [f"`{u}`" for u in uq_cols[c]]
        if c in fks:
            restr.append(fks[c][2])
        for nome, clausula in cks:
            if f"`{c}`" in clausula:
                restr.append(f"CK `{nome}`")
        if "on update" in extra.lower():
            restr.append("ON UPDATE CURRENT_TIMESTAMP(3)")
        d = default.replace("_utf8mb4\\'", "'").replace("\\'", "'")
        if extra.upper().startswith("DEFAULT_GENERATED") and d not in ("∅",):
            d = d if "(" in d else d
        tipo_md = tipo.replace("|", "\\|").replace("','", "', '")
        out.append(f"| `{c}` | {cols_desc.get(c, '').replace('|', chr(92) + '|')} | {tipo_md} | {'Sim' if nulo == 'YES' else 'Não'} | "
                   f"{'' if d == '∅' else '`' + d + '`'} | {', '.join(chave)} | {'; '.join(restr)} |")
    if cks:
        out += ["", "**Regras CHECK:**", ""]
        for nome, clausula in cks:
            c = (clausula.replace("_utf8mb4\\\\'", "'").replace("\\\\'", "'").replace("`", "")
                 .replace(",'", ", '"))
            out.append(f"- `{nome}`: `{c}`")
    out.append("")

out += ["## Objetos programados", "",
        "| Tipo | Nome | Arquivo |", "|---|---|---|"]
for r in sql("SELECT 'VIEW', table_name, '03_views.sql' FROM views WHERE table_schema='bdr_api' "
             "UNION ALL SELECT routine_type, routine_name, IF(routine_type='FUNCTION','04_functions.sql','05_procedures.sql') "
             "FROM routines WHERE routine_schema='bdr_api' "
             "UNION ALL SELECT CONCAT('TRIGGER (', action_timing, ' ', event_manipulation, ' ', event_object_table, ')'), "
             "trigger_name, '06_triggers.sql' FROM triggers WHERE trigger_schema='bdr_api' ORDER BY 3, 2"):
    out.append(f"| {r[0]} | `{r[1]}` | `sql/{r[2]}` |")
out.append("")
(RAIZ / "docs" / "dicionario-de-dados.md").write_text("\n".join(out), encoding="utf-8")
print("ok")
