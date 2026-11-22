# Dicionário de Dados — banco `bdr_api`

BDR 2026.02 — 3ª Avaliação · Parte 4. Gerado a partir do `information_schema` do MySQL 8 (script `scripts/gerar_dicionario.py`) após rodar `sql/01_ddl.sql`.

Legenda: **PK** chave primária · **FK** chave estrangeira · **UQ** único · **NN** NOT NULL · **CK** regra CHECK. Todos os `id` são UUID (CHAR(36)), como na API.

## Tabelas

- [`cargos`](#cargos) — Domínio dos cargos (perfis de acesso) dos usuários e suas permissões.
- [`prioridades`](#prioridades) — Domínio das prioridades de ticket, com o SLA padrão de cada uma.
- [`status_ticket`](#status_ticket) — Domínio dos status do ciclo de vida do ticket.
- [`equipes`](#equipes) — Equipes técnicas que atendem projetos e tickets.
- [`usuarios`](#usuarios) — Contas dos funcionários (técnicos, gestores, analistas).
- [`clientes`](#clientes) — Clientes da Altave donos dos projetos.
- [`projetos`](#projetos) — Projetos (instalações) contratados por clientes e atendidos por uma equipe.
- [`tickets`](#tickets) — Tickets / ordens de serviço de instalação ou manutenção.
- [`ticket_equipes`](#ticket_equipes) — Associativa N:N: equipes alocadas em cada ticket.
- [`relatorios`](#relatorios) — Relatórios de atendimento registrados pelos técnicos.
- [`historico_ticket`](#historico_ticket) — Linha do tempo (log) de eventos de cada ticket.
- [`atividades_conta`](#atividades_conta) — Auditoria das ações feitas por/sobre cada conta de usuário.

## cargos

Domínio dos cargos (perfis de acesso) dos usuários e suas permissões. Registros na carga (02_dml.sql): **5**.

| Campo | Descrição | Tipo | Nulo | Default | Chave | Restrições |
|---|---|---|---|---|---|---|
| `codigo` | Código do cargo (mesmo ENUM `Cargo` da API). | enum('TECNICO','GESTOR','SUPORTE','SUPORTE_INTERNO','COMERCIAL') | Não |  | PK | NN |
| `nome` | Nome do cargo para exibição. | varchar(60) | Não |  | UQ | NN; `uq_cargos_nome` |
| `descricao` | O que o cargo faz no sistema. | varchar(255) | Não |  |  | NN |
| `pode_abrir_ticket` | Indica se o cargo pode abrir tickets. | tinyint(1) | Não | `0` |  | NN |
| `pode_aprovar_encerramento` | Indica se o cargo pode aprovar/negar encerramentos. | tinyint(1) | Não | `0` |  | NN |

## prioridades

Domínio das prioridades de ticket, com o SLA padrão de cada uma. Registros na carga (02_dml.sql): **4**.

| Campo | Descrição | Tipo | Nulo | Default | Chave | Restrições |
|---|---|---|---|---|---|---|
| `codigo` | Código da prioridade (mesmo ENUM `Prioridade` da API). | enum('BAIXA','MEDIA','ALTA','CRITICA') | Não |  | PK | NN |
| `nome` | Nome para exibição. | varchar(30) | Não |  |  | NN |
| `peso` | Peso para ordenar a fila (maior = mais urgente). | tinyint unsigned | Não |  | UQ | NN; `uq_prioridades_peso`; CK `ck_prioridades_peso` |
| `sla_horas` | Prazo padrão do SLA, em horas, a partir da abertura. | smallint unsigned | Não |  |  | NN; CK `ck_prioridades_sla`; CK `ck_prioridades_alerta` |
| `alerta_horas` | Antecedência (h) para o ticket ser considerado EM_ALERTA. | smallint unsigned | Não | `2` |  | NN; CK `ck_prioridades_alerta` |

**Regras CHECK:**

- `ck_prioridades_peso`: `(`peso` between 1 and 10)`
- `ck_prioridades_sla`: `(`sla_horas` between 1 and 720)`
- `ck_prioridades_alerta`: `(`alerta_horas` < `sla_horas`)`

## status_ticket

Domínio dos status do ciclo de vida do ticket. Registros na carga (02_dml.sql): **5**.

| Campo | Descrição | Tipo | Nulo | Default | Chave | Restrições |
|---|---|---|---|---|---|---|
| `codigo` | Código do status (mesmo ENUM `StatusTicket` da API). | enum('NAO_INICIADO','EM_ANDAMENTO','SOLICITACAO_ENCERRAMENTO','ENCERRADO','EM_REVISAO') | Não |  | PK | NN |
| `nome` | Nome para exibição. | varchar(40) | Não |  |  | NN |
| `descricao` | Significado do status. | varchar(255) | Não |  |  | NN |
| `finalizado` | Indica status final (ticket encerrado). | tinyint(1) | Não | `0` |  | NN |
| `ordem` | Ordem do status no fluxo. | tinyint unsigned | Não |  | UQ | NN; `uq_status_ticket_ordem` |

## equipes

Equipes técnicas que atendem projetos e tickets. Registros na carga (02_dml.sql): **50**.

| Campo | Descrição | Tipo | Nulo | Default | Chave | Restrições |
|---|---|---|---|---|---|---|
| `id` | Identificador (UUID). | char(36) | Não | `uuid()` | PK | NN |
| `nome` | Nome da equipe. | varchar(100) | Não |  | UQ | NN; `uq_equipes_nome`; CK `ck_equipes_nome` |
| `descricao` | Área de atuação da equipe. | varchar(255) | Sim |  |  |  |
| `ativo` | Equipe ativa (TRUE) ou desativada. | tinyint(1) | Não | `1` |  | NN |
| `criado_em` | Data/hora de criação. | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN |
| `atualizado_em` | Data/hora da última alteração (automática). | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN; ON UPDATE CURRENT_TIMESTAMP(3) |

**Regras CHECK:**

- `ck_equipes_nome`: `(char_length(trim(`nome`)) >= 3)`

## usuarios

Contas dos funcionários (técnicos, gestores, analistas). Registros na carga (02_dml.sql): **223**.

| Campo | Descrição | Tipo | Nulo | Default | Chave | Restrições |
|---|---|---|---|---|---|---|
| `id` | Identificador (UUID). | char(36) | Não | `uuid()` | PK | NN |
| `nome` | Nome completo. | varchar(120) | Não |  |  | NN |
| `email` | E-mail de login (único). | varchar(254) | Não |  | UQ | NN; `uq_usuarios_email`; CK `ck_usuarios_email` |
| `senha_hash` | Hash bcrypt da senha. | varchar(255) | Não |  |  | NN |
| `cargo` | Cargo/perfil de acesso. | enum('TECNICO','GESTOR','SUPORTE','SUPORTE_INTERNO','COMERCIAL') | Não |  | FK → `cargos.codigo` | NN; ON DELETE RESTRICT |
| `ativo` | Conta ativa (pode logar) ou desativada. | tinyint(1) | Não | `1` |  | NN |
| `senha_provisoria` | TRUE enquanto o usuário não trocar a senha provisória. | tinyint(1) | Não | `1` |  | NN |
| `criado_em` | Data/hora de criação. | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN |
| `atualizado_em` | Data/hora da última alteração (automática). | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN; ON UPDATE CURRENT_TIMESTAMP(3) |
| `equipe_id` | Equipe à qual o usuário pertence (opcional). | char(36) | Sim |  | FK → `equipes.id` | ON DELETE SET NULL |
| `criado_por_id` | Usuário (Suporte Interno) que criou a conta. | char(36) | Sim |  | FK → `usuarios.id` | ON DELETE SET NULL |

**Regras CHECK:**

- `ck_usuarios_email`: `(`email` like _utf8mb4\\'_%@_%._%\\')`

## clientes

Clientes da Altave donos dos projetos. Registros na carga (02_dml.sql): **50**.

| Campo | Descrição | Tipo | Nulo | Default | Chave | Restrições |
|---|---|---|---|---|---|---|
| `id` | Identificador (UUID). | char(36) | Não | `uuid()` | PK | NN |
| `nome` | Razão social / nome do cliente. | varchar(150) | Não |  | UQ | NN; `uq_clientes_nome` |
| `ativo` | Cliente ativo. | tinyint(1) | Não | `1` |  | NN |
| `criado_em` | Data/hora de criação. | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN |
| `atualizado_em` | Data/hora da última alteração (automática). | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN; ON UPDATE CURRENT_TIMESTAMP(3) |

## projetos

Projetos (instalações) contratados por clientes e atendidos por uma equipe. Registros na carga (02_dml.sql): **60**.

| Campo | Descrição | Tipo | Nulo | Default | Chave | Restrições |
|---|---|---|---|---|---|---|
| `id` | Identificador (UUID). | char(36) | Não | `uuid()` | PK | NN |
| `nome` | Nome do projeto (único por cliente). | varchar(150) | Não |  | UQ | NN; `uq_projetos_cliente_nome (composta)` |
| `local_instalacao` | Endereço/local da instalação. | varchar(255) | Não |  |  | NN |
| `descricao` | Descrição do projeto. | text | Sim |  |  |  |
| `ativo` | Projeto ativo (aceita novos tickets). | tinyint(1) | Não | `1` |  | NN |
| `criado_em` | Data/hora de criação. | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN |
| `atualizado_em` | Data/hora da última alteração (automática). | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN; ON UPDATE CURRENT_TIMESTAMP(3) |
| `cliente_id` | Cliente dono do projeto. | char(36) | Não |  | FK → `clientes.id`, UQ | NN; `uq_projetos_cliente_nome (composta)`; ON DELETE RESTRICT |
| `equipe_id` | Equipe responsável pelo projeto. | char(36) | Não |  | FK → `equipes.id` | NN; ON DELETE RESTRICT |
| `gestor_id` | Gestor responsável pelo projeto. | char(36) | Não |  | FK → `usuarios.id` | NN; ON DELETE RESTRICT |

## tickets

Tickets / ordens de serviço de instalação ou manutenção. Registros na carga (02_dml.sql): **220**.

| Campo | Descrição | Tipo | Nulo | Default | Chave | Restrições |
|---|---|---|---|---|---|---|
| `id` | Identificador (UUID). | char(36) | Não | `uuid()` | PK | NN |
| `titulo` | Título curto do chamado. | varchar(180) | Não |  |  | NN; CK `ck_tickets_titulo` |
| `descricao` | Descrição detalhada do problema/serviço. | text | Não |  |  | NN |
| `categoria` | MANUTENCAO ou INSTALACAO. | enum('MANUTENCAO','INSTALACAO') | Não |  |  | NN |
| `prioridade` | Prioridade do ticket. | enum('BAIXA','MEDIA','ALTA','CRITICA') | Não | `MEDIA` | FK → `prioridades.codigo` | NN; ON DELETE RESTRICT |
| `status` | Status atual no fluxo. | enum('NAO_INICIADO','EM_ANDAMENTO','SOLICITACAO_ENCERRAMENTO','ENCERRADO','EM_REVISAO') | Não | `EM_ANDAMENTO` | FK → `status_ticket.codigo` | NN; ON DELETE RESTRICT; CK `ck_tickets_encerramento` |
| `sla_em` | Data-limite do SLA. | datetime(3) | Não |  |  | NN; CK `ck_tickets_sla` |
| `encerrado_em` | Data/hora do encerramento (só quando ENCERRADO). | datetime(3) | Sim |  |  | CK `ck_tickets_encerramento` |
| `criado_em` | Data/hora de abertura. | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN; CK `ck_tickets_sla`; CK `ck_tickets_encerramento` |
| `atualizado_em` | Data/hora da última alteração (automática). | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN; ON UPDATE CURRENT_TIMESTAMP(3) |
| `projeto_id` | Projeto ao qual o ticket pertence. | char(36) | Não |  | FK → `projetos.id` | NN; ON DELETE RESTRICT |
| `aberto_por_id` | Usuário que abriu o ticket. | char(36) | Não |  | FK → `usuarios.id` | NN; ON DELETE RESTRICT |
| `responsavel_id` | Técnico responsável (opcional). | char(36) | Sim |  | FK → `usuarios.id` | ON DELETE SET NULL |

**Regras CHECK:**

- `ck_tickets_titulo`: `(char_length(trim(`titulo`)) >= 5)`
- `ck_tickets_sla`: `(`sla_em` > `criado_em`)`
- `ck_tickets_encerramento`: `(((`status` = _utf8mb4\\'ENCERRADO\\') and (`encerrado_em` is not null) and (`encerrado_em` >= `criado_em`)) or ((`status` <> _utf8mb4\\'ENCERRADO\\') and (`encerrado_em` is null)))`

## ticket_equipes

Associativa N:N: equipes alocadas em cada ticket. Registros na carga (02_dml.sql): **304**.

| Campo | Descrição | Tipo | Nulo | Default | Chave | Restrições |
|---|---|---|---|---|---|---|
| `id` | Identificador (UUID). | char(36) | Não | `uuid()` | PK | NN |
| `criado_em` | Quando a equipe foi alocada. | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN |
| `ticket_id` | Ticket. | char(36) | Não |  | FK → `tickets.id`, UQ | NN; `uq_ticket_equipes_ticket_equipe (composta)`; ON DELETE CASCADE |
| `equipe_id` | Equipe alocada. | char(36) | Não |  | FK → `equipes.id`, UQ | NN; `uq_ticket_equipes_ticket_equipe (composta)`; ON DELETE CASCADE |

## relatorios

Relatórios de atendimento registrados pelos técnicos. Registros na carga (02_dml.sql): **426**.

| Campo | Descrição | Tipo | Nulo | Default | Chave | Restrições |
|---|---|---|---|---|---|---|
| `id` | Identificador (UUID). | char(36) | Não | `uuid()` | PK | NN |
| `trabalho_realizado` | Descrição do reparo/serviço feito. | text | Não |  |  | NN; CK `ck_relatorios_trabalho` |
| `materiais_utilizados` | Materiais usados no atendimento. | text | Não |  |  | NN |
| `outros_detalhes` | Observações gerais. | text | Não |  |  | NN |
| `criado_em` | Data/hora do registro. | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN |
| `atualizado_em` | Data/hora da última alteração (automática). | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN; ON UPDATE CURRENT_TIMESTAMP(3) |
| `ticket_id` | Ticket atendido. | char(36) | Não |  | FK → `tickets.id` | NN; ON DELETE RESTRICT |
| `autor_id` | Técnico autor do relatório. | char(36) | Não |  | FK → `usuarios.id` | NN; ON DELETE RESTRICT |

**Regras CHECK:**

- `ck_relatorios_trabalho`: `(char_length(trim(`trabalho_realizado`)) >= 10)`

## historico_ticket

Linha do tempo (log) de eventos de cada ticket. Registros na carga (02_dml.sql): **1374**.

| Campo | Descrição | Tipo | Nulo | Default | Chave | Restrições |
|---|---|---|---|---|---|---|
| `id` | Identificador (UUID). | char(36) | Não | `uuid()` | PK | NN |
| `evento` | Tipo do evento (TICKET_CRIADO, ATIVIDADE_INICIADA, LOG, ENCERRAMENTO_*, STATUS_ALTERADO, ALERTA_SLA...). | varchar(50) | Não |  |  | NN; CK `ck_historico_evento` |
| `descricao` | Texto do evento / parecer. | text | Não |  |  | NN |
| `criado_em` | Data/hora do evento. | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN |
| `ticket_id` | Ticket do evento. | char(36) | Não |  | FK → `tickets.id`, UQ | NN; `uq_historico_inicio_equipe (composta)`; ON DELETE RESTRICT |
| `usuario_id` | Autor do evento (NULL = evento automático do sistema). | char(36) | Sim |  | FK → `usuarios.id` | ON DELETE SET NULL |
| `equipe_id` | Equipe do autor no momento do evento. | char(36) | Sim |  | FK → `equipes.id` | ON DELETE SET NULL |
| `inicio_equipe_id` | Preenchido só em ATIVIDADE_INICIADA: garante um início por equipe (UNIQUE com ticket_id). | char(36) | Sim |  | FK → `equipes.id`, UQ | `uq_historico_inicio_equipe (composta)`; ON DELETE SET NULL |

**Regras CHECK:**

- `ck_historico_evento`: `((`evento` = upper(`evento`)) and (char_length(`evento`) >= 3))`

## atividades_conta

Auditoria das ações feitas por/sobre cada conta de usuário. Registros na carga (02_dml.sql): **702**.

| Campo | Descrição | Tipo | Nulo | Default | Chave | Restrições |
|---|---|---|---|---|---|---|
| `id` | Identificador (UUID). | char(36) | Não | `uuid()` | PK | NN |
| `tipo` | Categoria da atividade (CADASTRO, EQUIPE, LOG, PROJETO, TICKET, TICKET | ABERTURA, CONTA). | varchar(20) | Não |  |  | NN; CK `ck_atividades_tipo` |
| `descricao` | Descrição da atividade. | text | Não |  |  | NN |
| `criado_em` | Data/hora da atividade. | datetime(3) | Não | `CURRENT_TIMESTAMP(3)` |  | NN |
| `usuario_id` | Usuário da atividade. | char(36) | Não |  | FK → `usuarios.id` | NN; ON DELETE CASCADE |

**Regras CHECK:**

- `ck_atividades_tipo`: `(`tipo` in (_utf8mb4\\'CADASTRO\\',_utf8mb4\\'EQUIPE\\',_utf8mb4\\'LOG\\',_utf8mb4\\'PROJETO\\',_utf8mb4\\'TICKET\\',_utf8mb4\\'TICKET ¦ ABERTURA\\',_utf8mb4\\'CONTA\\'))`

## Objetos programados

| Tipo | Nome | Arquivo |
|---|---|---|
| VIEW | `vw_carga_equipes` | `sql/03_views.sql` |
| VIEW | `vw_produtividade_tecnicos` | `sql/03_views.sql` |
| VIEW | `vw_tickets_detalhados` | `sql/03_views.sql` |
| FUNCTION | `fn_calcular_sla_em` | `sql/04_functions.sql` |
| FUNCTION | `fn_percentual_sla_consumido` | `sql/04_functions.sql` |
| FUNCTION | `fn_situacao_sla` | `sql/04_functions.sql` |
| FUNCTION | `fn_sugerir_tecnico` | `sql/04_functions.sql` |
| FUNCTION | `fn_taxa_cumprimento_sla_equipe` | `sql/04_functions.sql` |
| FUNCTION | `fn_tempo_medio_resolucao_equipe` | `sql/04_functions.sql` |
| PROCEDURE | `sp_abrir_ticket` | `sql/05_procedures.sql` |
| PROCEDURE | `sp_decidir_encerramento` | `sql/05_procedures.sql` |
| PROCEDURE | `sp_desativar_tecnico_redistribuir` | `sql/05_procedures.sql` |
| PROCEDURE | `sp_gerar_alertas_sla` | `sql/05_procedures.sql` |
| PROCEDURE | `sp_ranking_tecnicos` | `sql/05_procedures.sql` |
| PROCEDURE | `sp_relatorio_sla_equipes` | `sql/05_procedures.sql` |
| TRIGGER (AFTER INSERT relatorios) | `trg_relatorios_ai_inicio_atividade` | `sql/06_triggers.sql` |
| TRIGGER (BEFORE INSERT relatorios) | `trg_relatorios_bi_validar_autor` | `sql/06_triggers.sql` |
| TRIGGER (AFTER UPDATE tickets) | `trg_tickets_au_historico` | `sql/06_triggers.sql` |
| TRIGGER (BEFORE INSERT tickets) | `trg_tickets_bi_validar` | `sql/06_triggers.sql` |
| TRIGGER (BEFORE UPDATE tickets) | `trg_tickets_bu_fluxo_status` | `sql/06_triggers.sql` |
| TRIGGER (AFTER UPDATE usuarios) | `trg_usuarios_au_auditoria` | `sql/06_triggers.sql` |
