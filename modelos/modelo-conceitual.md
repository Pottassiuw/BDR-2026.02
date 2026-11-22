# Modelo Conceitual — bdr_api

![Modelo conceitual](modelo-conceitual.png)

Diagrama em notação de Peter Chen (a mesma do brModelo), gerado por `scripts/gerar_diagramas.py`.
A fonte de verdade das entidades é o schema real da API (`API-2026.02/src/prisma/schema.prisma`).

## Entidades

| Entidade | Identificador | Atributos | Observação |
|---|---|---|---|
| CARGO | codigo | nome, descricao, pode_abrir_ticket, pode_aprovar_encerramento | Domínio (ENUM `Cargo` da API normalizado) |
| PRIORIDADE | codigo | nome, peso, sla_horas, alerta_horas | Domínio (ENUM `Prioridade`) + regra de SLA |
| STATUS_TICKET | codigo | nome, descricao, finalizado, ordem | Domínio (ENUM `StatusTicket`) |
| USUARIO | id | nome, email (único), senha_hash, ativo, senha_provisoria, criado_em, atualizado_em | |
| EQUIPE | id | nome (único), descricao, ativo, criado_em, atualizado_em | |
| CLIENTE | id | nome (único), ativo, criado_em, atualizado_em | |
| PROJETO | id | nome, local_instalacao, descricao, ativo, criado_em, atualizado_em | nome único por cliente |
| TICKET | id | titulo, descricao, categoria, sla_em, encerrado_em, criado_em, atualizado_em | |
| RELATORIO | id | trabalho_realizado, materiais_utilizados, outros_detalhes, criado_em, atualizado_em | |
| HISTORICO_TICKET | id | evento, descricao, criado_em | |
| ATIVIDADE_CONTA | id | tipo, descricao, criado_em | |

## Relacionamentos

| Relacionamento | Entidades e cardinalidades | Leitura |
|---|---|---|
| possui | USUARIO (0,n) — (1,1) CARGO | Todo usuário tem um cargo; um cargo tem vários usuários |
| pertence | USUARIO (0,n) — (0,1) EQUIPE | Usuário pode pertencer a uma equipe |
| cria (auto) | USUARIO (0,1) criador — (0,n) criado | Suporte Interno cria contas |
| realiza | USUARIO (1,1) — (0,n) ATIVIDADE_CONTA | Auditoria da conta |
| contrata | CLIENTE (1,1) — (0,n) PROJETO | |
| atende | EQUIPE (1,1) — (0,n) PROJETO | Equipe responsável pelo projeto |
| gerencia | USUARIO/gestor (1,1) — (0,n) PROJETO | |
| gera | PROJETO (1,1) — (0,n) TICKET | |
| abre | USUARIO (1,1) — (0,n) TICKET | |
| responsável | USUARIO (0,1) — (0,n) TICKET | Técnico responsável (opcional) |
| alocada | TICKET (0,n) — (1,n) EQUIPE, atributo `criado_em` | **N:N** → tabela `ticket_equipes` |
| classifica | TICKET (0,n) — (1,1) PRIORIDADE | |
| está em | TICKET (0,n) — (1,1) STATUS_TICKET | |
| possui | TICKET (1,1) — (0,n) RELATORIO | |
| escreve | USUARIO (1,1) — (0,n) RELATORIO | |
| registra | TICKET (1,1) — (0,n) HISTORICO_TICKET | |
| é autor | USUARIO (0,1) — (0,n) HISTORICO_TICKET | NULL = evento do sistema |
| equipe do autor | EQUIPE (0,1) — (0,n) HISTORICO_TICKET | Equipe do autor no momento |
| inicia atividade | EQUIPE (0,1) — (0,n) HISTORICO_TICKET | Um início por equipe por ticket |

## Mesmo modelo em Mermaid (renderiza no GitHub/VS Code)

```mermaid
erDiagram
    CARGO ||--o{ USUARIO : possui
    EQUIPE |o--o{ USUARIO : pertence
    USUARIO |o--o{ USUARIO : cria
    USUARIO ||--o{ ATIVIDADE_CONTA : realiza
    CLIENTE ||--o{ PROJETO : contrata
    EQUIPE ||--o{ PROJETO : atende
    USUARIO ||--o{ PROJETO : gerencia
    PROJETO ||--o{ TICKET : gera
    USUARIO ||--o{ TICKET : abre
    USUARIO |o--o{ TICKET : responsavel
    TICKET }o--|{ EQUIPE : alocada
    PRIORIDADE ||--o{ TICKET : classifica
    STATUS_TICKET ||--o{ TICKET : esta_em
    TICKET ||--o{ RELATORIO : possui
    USUARIO ||--o{ RELATORIO : escreve
    TICKET ||--o{ HISTORICO_TICKET : registra
    USUARIO |o--o{ HISTORICO_TICKET : autor
    EQUIPE |o--o{ HISTORICO_TICKET : equipe_do_autor
    EQUIPE |o--o{ HISTORICO_TICKET : inicia_atividade
```

## Como redesenhar no brModelo (arquivo .brM3)

O arquivo `.brM3` não foi gerado automaticamente (formato do brModelo não documentado). Para entregar o
modelo no brModelo 3:

1. *Arquivo → Novo → Modelo Conceitual*.
2. Crie as 11 entidades da tabela "Entidades" (ferramenta **Entidade**). Em cada uma, adicione os atributos
   (ferramenta **Atributo**) e marque o identificador (`id` ou `codigo`) como **Atributo identificador**.
3. Crie cada relacionamento da tabela "Relacionamentos" (ferramenta **Relacionamento**), ligue às duas
   entidades e ajuste a cardinalidade de cada lado clicando na linha (ex.: `(0,n)` / `(1,1)`).
   - `cria` é um **autorrelacionamento**: ligue USUARIO duas vezes ao mesmo losango.
   - `alocada` é N:N com o atributo `criado_em` no próprio relacionamento.
4. Posicione como no PNG acima e salve em `modelos/modelo-conceitual.brM3`.
5. (Opcional) *Esquema → Converter para modelo lógico* e compare com `modelo-logico.md`.
