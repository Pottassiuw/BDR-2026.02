# BDR-2026.02 — 3ª Avaliação de Banco de Dados Relacional

Projeto da 3ª avaliação de BDR (FATEC SJC, 2º sem. 2026), baseado no tema do Projeto API (`API-2026.02`).

Entrega no Teams: **23/11/2026**. Apresentações: 23/11, 26/11 e 30/11.

## Partes
1. Modelos: conceitual (BRModelo) e lógico → `modelos/`
2. DDL (criação das tabelas) → `sql/01_ddl.sql`
3. DML: ≥ 50 registros por tabela (exceto tabelas de domínio) → `sql/02_dml.sql`
4. Programação: 6 procedures, 6 functions, 6 triggers (cursor, view, INNER/LEFT/RIGHT JOIN, GROUP BY, funções de grupo, subconsultas) — cada uma com problema, código e print do resultado → `sql/03_*.sql`
5. Dicionário de dados (arquivo separado) → `docs/dicionario-de-dados.*`
6. Conexão com a API: uma funcionalidade usando ≥ 1 function e ≥ 1 procedure

Documento final referencia os scripts e o dicionário → `docs/`

## Estrutura entregue

| Caminho | Conteúdo |
|---|---|
| `docs/documento.md` | **Documento da entrega** (partes 1–5, problema + código + retorno de cada rotina) |
| `docs/dicionario-de-dados.md` | Dicionário de dados (arquivo separado) |
| `docs/prints/` | Retorno de cada function/procedure/trigger (`.txt` e `.png`) |
| `docs/parte5.md`, `docs/prints/parte5/` | Parte 5 (fonte da seção no documento) e evidências da API ligada ao `bdr_api` |
| `modelos/` | Modelo conceitual e lógico: arquivos do brModelo (`.brM3` e `.xml`), imagens `.png` exportadas pelo brModelo e `.md` |
| `sql/01_ddl.sql` … `06_triggers.sql` | Scripts, na ordem de execução |
| `sql/07_exemplos.sql` | Chamadas de exemplo usadas nos prints |
| `scripts/` | Geradores (DML, prints, diagramas, dicionário, documento), `rodar_tudo.sh` e `demo_parte5.sh` (demonstração da API) |

## Como rodar (MySQL 8)

```sh
MYSQL="mysql -uroot -p -h127.0.0.1 -P3306" ./scripts/rodar_tudo.sh   # cria bdr_api do zero, 01→06
mysql -uroot -p --force -t < sql/07_exemplos.sql                        # opcional: exemplos
```

Para regenerar os artefatos (requer Python 3 + Pillow), com o banco recém-criado:
`python3 scripts/gerar_dml.py > sql/02_dml.sql`, `MYSQL=... python3 scripts/gerar_dicionario.py`,
`MYSQL=... python3 scripts/gerar_prints.py`, `python3 scripts/gerar_diagramas.py`, `python3 scripts/gerar_documento.py`.
Arquivos do brModelo (Node): `node scripts/brmodelo_logico.js modelos` (gera o conceitual e o lógico).
Os PNG em `modelos/` são os exportados pelo brModelo; `gerar_diagramas.py` os sobrescreveria com a versão antiga.

## Arquivos para o Teams (`docs/entrega/`)

`Documento-BDR-3a-avaliacao.pdf/.docx` (documento completo, com capa, sumário, modelos e todos os prints) e
`Dicionario-de-Dados.pdf/.docx` (dicionário em arquivo separado). Gerados por `scripts/gerar_entrega.py`
(pandoc ≥ 3 + python-docx + weasyprint): `PANDOC=/caminho/pandoc python3 scripts/gerar_entrega.py`.
No .docx, o sumário é um campo do Word: ao abrir, confirme "atualizar campos" (ou F9) para preencher as páginas.
