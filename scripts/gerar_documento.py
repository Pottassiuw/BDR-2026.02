#!/usr/bin/env python3
"""Monta docs/documento.md: texto fixo + código de cada rotina (extraído dos .sql)
+ retorno obtido (docs/prints/*.txt e .png). Uso: python3 scripts/gerar_documento.py"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SQL = RAIZ / "sql"
PRINTS = RAIZ / "docs" / "prints"


def blocos(arquivo):
    """Devolve {nome: (comentario_problema, codigo)} para cada CREATE ... $$ do arquivo."""
    txt = (SQL / arquivo).read_text(encoding="utf-8")
    res = {}
    padrao = re.compile(r"((?:-- [^\n]*\n|--\n)+)(CREATE (?:FUNCTION|PROCEDURE|TRIGGER) (\w+).*?END\$\$)", re.S)
    for m in padrao.finditer(txt):
        coment, codigo, nome = m.group(1), m.group(2), m.group(3)
        linhas = [l[3:] if l.startswith("-- ") else "" for l in coment.splitlines()]
        linhas = [l for l in linhas if not set(l.strip()) <= set("-")]
        res[nome] = ("\n".join(linhas).strip(), codigo.replace("END$$", "END"))
    return res


def problema(coment):
    """Título (1ª linha) e texto do problema; linhas com "->" viram itens de lista."""
    partes = coment.split("\n", 1)
    titulo = partes[0].replace(">>> pensada para a API (Parte 5)", "").strip()
    api = ">>> pensada para a API" in coment
    corpo = partes[1] if len(partes) > 1 else ""
    corpo = corpo.replace(">>> pensada para a API (Parte 5)", "").replace("Problema: ", "")
    paragrafo, itens, cont = [], [], None
    for l in corpo.splitlines():
        if "->" in l:
            itens.append(l.strip())
            cont = itens
        elif itens and l.startswith("    ") and l.strip():
            itens[-1] += " " + l.strip()
        elif l.strip():
            if itens:
                paragrafo.append("\n" + "\n".join("- `" + i.split("->")[0].strip() + "` → " +
                                                    i.split("->", 1)[1].strip() for i in itens) + "\n\n")
                itens = []
            paragrafo.append(l.strip())
    if itens:
        paragrafo.append("\n" + "\n".join("- `" + i.split("->")[0].strip() + "` → " +
                                            i.split("->", 1)[1].strip() for i in itens) + "\n\n")
    texto = " ".join(paragrafo).replace(" \n", "\n").replace("\n ", "\n")
    texto = texto[0].upper() + texto[1:]
    if api:
        titulo += " — *pensada para a API (Parte 5)*"
    return titulo, texto


RESUMO = {
    "fn_calcular_sla_em": "Calcula a data-limite do SLA pela prioridade (SLA padrão na tabela `prioridades`).",
    "fn_situacao_sla": "Indicador de SLA do ticket: NO_PRAZO, EM_ALERTA, VENCIDO, CUMPRIDO ou VIOLADO (US 5). **API**",
    "fn_percentual_sla_consumido": "% do prazo do SLA já consumido (barra de progresso).",
    "fn_tempo_medio_resolucao_equipe": "Tempo médio (h) de resolução dos tickets de uma equipe.",
    "fn_taxa_cumprimento_sla_equipe": "% de tickets encerrados dentro do SLA por equipe e período.",
    "fn_sugerir_tecnico": "Sugere o técnico ativo menos carregado da equipe.",
    "sp_abrir_ticket": "Abre ticket de forma atômica com validações, SLA, equipe, técnico, histórico e auditoria (US 1/8). **API**",
    "sp_decidir_encerramento": "Gestor aprova/nega o encerramento com parecer, com trava de linha. **API**",
    "sp_desativar_tecnico_redistribuir": "Desativa técnico e redistribui seus tickets abertos (cursor) (US 23).",
    "sp_gerar_alertas_sla": "Gera alertas de SLA para os gestores, sem repetir em 24 h (cursor) (US 19).",
    "sp_relatorio_sla_equipes": "Relatório gerencial de SLA e tempo de resolução por equipe no período.",
    "sp_ranking_tecnicos": "Ranking de produtividade dos técnicos vs. média da equipe.",
    "trg_tickets_bi_validar": "Valida abertura (projeto/cliente/usuário ativos) e calcula SLA se não informado.",
    "trg_tickets_bu_fluxo_status": "Bloqueia alteração de ticket encerrado e transições de status inválidas; preenche `encerrado_em`.",
    "trg_tickets_au_historico": "Registra no histórico mudanças de status, responsável e SLA.",
    "trg_relatorios_bi_validar_autor": "Só técnico ativo de equipe alocada registra relatório; nunca em ticket encerrado.",
    "trg_relatorios_ai_inicio_atividade": "1º relatório da equipe registra o início da atividade e põe o ticket EM_ANDAMENTO.",
    "trg_usuarios_au_auditoria": "Audita ativação, cargo, equipe e senha das contas (US 20/23/24).",
}


def secao(prefixo, nome, info, exemplo_sql):
    titulo, prob = problema(info[0])
    p = next(PRINTS.glob(f"{prefixo}_{nome}.txt"))
    saida = p.read_text(encoding="utf-8").rstrip()
    return f"""### {titulo}

**Problema.** {prob}

**Código SQL** (`sql/{ARQ[prefixo[0]]}`):

```sql
{info[1]}
```

**Execução de exemplo** (bloco `-- @print {prefixo}_{nome}` de `sql/07_exemplos.sql`):

```sql
{exemplo_sql.strip()}
```

**Retorno obtido** — print: [`docs/prints/{p.stem}.png`](prints/{p.stem}.png)

![{p.stem}](prints/{p.stem}.png)

<details><summary>Saída em texto</summary>

```text
{saida}
```
</details>

"""


ARQ = {"F": "04_functions.sql", "P": "05_procedures.sql", "T": "06_triggers.sql"}
ex_txt = (SQL / "07_exemplos.sql").read_text(encoding="utf-8")
ex = dict(zip(*[iter(re.split(r"^-- @print (\S+)\s*$", ex_txt, flags=re.M)[1:])] * 2))
ex = {k: re.sub(r"^USE bdr_api;\n", "", v) for k, v in ex.items()}

funcs = blocos("04_functions.sql")
procs = blocos("05_procedures.sql")
trigs = blocos("06_triggers.sql")
views = (SQL / "03_views.sql").read_text(encoding="utf-8")


def rotinas(prefixo_letra, dic):
    out = []
    for i, (nome, info) in enumerate(dic.items(), 1):
        pref = f"{prefixo_letra}{i}"
        out.append(secao(pref, nome, info, ex[f"{pref}_{nome}"]))
    return "".join(out)


def resumo(dic, letra):
    linhas = []
    for i, (nome, info) in enumerate(dic.items(), 1):
        linhas.append(f"| {letra}{i} | `{nome}` | {RESUMO[nome]} |")
    return "\n".join(linhas)


PARTE5 = (RAIZ / "docs" / "parte5.md").read_text(encoding="utf-8").rstrip("\n")

doc = f"""# 3ª Avaliação de Banco de Dados Relacional — Sistema de Tickets (Projeto API)

**FATEC São José dos Campos · BDR · 2º semestre de 2026** · Entrega: 23/11/2026

| | |
|---|---|
| **Tema** | Projeto API 2026.02 (FawkesCode / parceiro Altave): plataforma unificada de tickets / ordens de serviço |
| **SGBD** | MySQL 8.0 (validado no 8.0.40) |
| **Banco** | `bdr_api` |
| **Integrantes** | _preencher_ |

## Arquivos da entrega

| Parte | Conteúdo | Arquivo |
|---|---|---|
| 1 | Modelo conceitual | [`modelos/modelo-conceitual.md`](../modelos/modelo-conceitual.md), [`modelos/modelo-conceitual.png`](../modelos/modelo-conceitual.png) |
| 1 | Modelo lógico | [`modelos/modelo-logico.md`](../modelos/modelo-logico.md), [`modelos/modelo-logico.png`](../modelos/modelo-logico.png) |
| 2 | **Script de criação das tabelas (DDL)** | [`sql/01_ddl.sql`](../sql/01_ddl.sql) |
| 3 | **Script de inserção de dados (DML)** | [`sql/02_dml.sql`](../sql/02_dml.sql) (gerado por [`scripts/gerar_dml.py`](../scripts/gerar_dml.py)) |
| 3 | Views | [`sql/03_views.sql`](../sql/03_views.sql) |
| 3 | 6 functions | [`sql/04_functions.sql`](../sql/04_functions.sql) |
| 3 | 6 stored procedures | [`sql/05_procedures.sql`](../sql/05_procedures.sql) |
| 3 | 6 triggers | [`sql/06_triggers.sql`](../sql/06_triggers.sql) |
| 3 | Execuções de exemplo (prints) | [`sql/07_exemplos.sql`](../sql/07_exemplos.sql), [`docs/prints/`](prints/) |
| 4 | **Dicionário de dados** | [`docs/dicionario-de-dados.md`](dicionario-de-dados.md) |
| 5 | Conexão com a API (sp_abrir_ticket + fn_situacao_sla) | [`docs/parte5.md`](parte5.md), [`scripts/demo_parte5.sh`](../scripts/demo_parte5.sh), [`docs/prints/parte5/`](prints/parte5/) |

### Como executar

```sh
# na pasta do repositório; ajuste usuário/host/porta do seu MySQL 8
MYSQL="mysql -uroot -p -h127.0.0.1 -P3306" ./scripts/rodar_tudo.sh
# equivalente manual, na ordem:
# mysql -uroot -p < sql/01_ddl.sql   (... até 06_triggers.sql)
# depois, opcionalmente, os exemplos:  mysql -uroot -p --force -t < sql/07_exemplos.sql
```

A ordem importa: os triggers (06) são criados **depois** da carga (02) para não interferirem nos dados
históricos. Os scripts recriam o banco do zero (`DROP DATABASE IF EXISTS bdr_api`).

---

## Parte 1 — Modelos de banco de dados

O modelo foi levantado a partir das entidades reais da API (`src/prisma/schema.prisma` e migrations):
`usuarios`, `equipes`, `clientes`, `projetos`, `tickets`, `ticket_equipes`, `relatorios`,
`historico_ticket` e `atividades_conta`. Para o BDR ele foi complementado com três tabelas de domínio
(`cargos`, `prioridades`, `status_ticket`) que normalizam os ENUMs da API e guardam regras de negócio
(SLA padrão por prioridade, permissões por cargo), além de CHECKs e DEFAULTs. Nomes e tipos foram
mantidos idênticos aos da API para a Parte 5.

### 1.1 Modelo conceitual (brModelo / notação de Chen)

![Modelo conceitual](../modelos/modelo-conceitual.png)

Entidades, atributos, cardinalidades e o passo a passo para redesenhar no brModelo:
[`modelos/modelo-conceitual.md`](../modelos/modelo-conceitual.md).

### 1.2 Modelo lógico

![Modelo lógico](../modelos/modelo-logico.png)

Esquema relacional e decisões de mapeamento: [`modelos/modelo-logico.md`](../modelos/modelo-logico.md).

---

## Parte 2 — Criação das tabelas (DDL)

Script: [`sql/01_ddl.sql`](../sql/01_ddl.sql). Cria o banco `bdr_api` com 12 tabelas, todas com PK,
e com 20 FKs, UNIQUEs (`email`, nome de equipe/cliente, projeto por cliente, equipe por ticket, um início
de atividade por equipe), CHECKs (ex.: `encerrado_em` só existe quando o ticket está ENCERRADO; o SLA
precisa ser posterior à abertura) e DEFAULTs (UUID, datas automáticas, status/prioridade padrão).

| Tabela | Tipo | Registros |
|---|---|---|
| `cargos` | domínio | 5 |
| `prioridades` | domínio | 4 |
| `status_ticket` | domínio | 5 |
| `equipes` | | 50 |
| `usuarios` | | 223 |
| `clientes` | | 50 |
| `projetos` | | 60 |
| `tickets` | | 220 |
| `ticket_equipes` | associativa N:N | 326 |
| `relatorios` | | 413 |
| `historico_ticket` | | 1461 |
| `atividades_conta` | | 702 |

## Parte 3 — Inserção das linhas (DML)

Script: [`sql/02_dml.sql`](../sql/02_dml.sql) — um `INSERT INTO` por linha, dentro de uma transação.
Os dados são fictícios e foram gerados por [`scripts/gerar_dml.py`](../scripts/gerar_dml.py) com semente
fixa, então o arquivo é sempre o mesmo. Os dados respeitam as FKs e as regras do negócio: cada equipe tem
1 gestor e 3 técnicos; projetos ligados a clientes, equipes e ao gestor da equipe; tickets com status
coerente com a idade (antigos encerrados, recentes em andamento); SLA pela prioridade; cerca de 22 %
dos encerramentos fora do SLA; histórico em ordem cronológica (abertura → início por equipe → relatórios
→ solicitação → aprovação/negação). Apenas as tabelas de domínio têm menos de 50 registros, como o
enunciado permite.

## Parte 3 — Programação em banco de dados

### Visão geral

| # | Rotina | Problema resolvido |
|---|---|---|
{resumo(funcs, 'F')}
{resumo(procs, 'P')}
{resumo(trigs, 'T')}

**Conceitos usados no conjunto:**

| Conceito | Onde |
|---|---|
| CURSOR | `sp_desativar_tecnico_redistribuir`, `sp_gerar_alertas_sla` |
| VIEW | `vw_tickets_detalhados`, `vw_carga_equipes`, `vw_produtividade_tecnicos` (usadas em `sp_abrir_ticket`, `sp_gerar_alertas_sla`, `sp_ranking_tecnicos` e nos exemplos) |
| INNER JOIN | views, `fn_tempo_medio_resolucao_equipe`, `sp_abrir_ticket`, `sp_desativar_tecnico_redistribuir`, `trg_tickets_bi_validar`, `trg_relatorios_bi_validar_autor` |
| LEFT JOIN | `vw_tickets_detalhados`, `vw_carga_equipes`, `fn_sugerir_tecnico`, `sp_relatorio_sla_equipes`, `sp_ranking_tecnicos` |
| RIGHT JOIN | `vw_produtividade_tecnicos`, `sp_ranking_tecnicos` |
| GROUP BY / HAVING | `vw_carga_equipes`, `vw_produtividade_tecnicos`, `fn_sugerir_tecnico`, `sp_gerar_alertas_sla`, `sp_relatorio_sla_equipes` (HAVING), `sp_ranking_tecnicos` |
| Funções de grupo | `COUNT`, `SUM`, `AVG`, `MAX`, `GROUP_CONCAT` (views, F4, F5, F6, P4, P5, P6) |
| Subconsultas | escalar (`fn_situacao_sla`, `vw_carga_equipes`, P5), `IN` (`fn_taxa_cumprimento_sla_equipe`), `EXISTS`/`NOT EXISTS` (P2, P4, T4, T5), correlacionada (`fn_sugerir_tecnico`), tabela derivada (P6) |
| Transação / tratamento de erro | `START TRANSACTION`/`COMMIT`, `EXIT HANDLER ... ROLLBACK; RESIGNAL`, `SIGNAL SQLSTATE '45000'`, `SELECT ... FOR UPDATE` |

**Pensadas para a Parte 5 (API):** a function `fn_situacao_sla` (indicador de SLA da US 5) e as procedures
`sp_abrir_ticket` (US 1/8) e `sp_decidir_encerramento` (fluxo de aprovação de encerramento).

### Views de apoio

```sql
{views.split("USE bdr_api;", 1)[1].strip()}
```

### 3.1 Functions

{rotinas('F', funcs)}
### 3.2 Stored procedures

{rotinas('P', procs)}
### 3.3 Triggers

{rotinas('T', trigs)}
---

## Parte 4 — Dicionário de dados

Arquivo separado: [`docs/dicionario-de-dados.md`](dicionario-de-dados.md). Para cada tabela, lista os campos
com descrição, tipo, nulidade, default, PK/FK/UNIQUE e as regras CHECK, além dos objetos programados
(views, functions, procedures e triggers). Foi gerado direto do `information_schema` do banco
([`scripts/gerar_dicionario.py`](../scripts/gerar_dicionario.py)), então reflete exatamente o DDL.

---

{PARTE5}
"""

(RAIZ / "docs" / "documento.md").write_text(doc, encoding="utf-8")
print("ok", len(doc.splitlines()), "linhas")
