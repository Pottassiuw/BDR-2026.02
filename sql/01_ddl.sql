-- =====================================================================
-- BDR 2026.02 - 3ª Avaliação | Parte 2 - DDL
-- Tema: Sistema de Ordens de Serviço / Tickets (Projeto API - FawkesCode/Altave)
-- SGBD: MySQL 8.0
--
-- O schema segue as tabelas reais da API (src/prisma/schema.prisma), com os
-- mesmos nomes de tabelas/colunas e tipos, para que a API possa apontar para
-- este banco na Parte 5. Complementos do BDR:
--   * 3 tabelas de domínio (cargos, prioridades, status_ticket) que
--     normalizam os ENUMs da API e guardam regras (SLA padrão, peso etc.);
--   * CHECKs e DEFAULTs que a API só validava no código.
-- =====================================================================

DROP DATABASE IF EXISTS bdr_api;
CREATE DATABASE bdr_api
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE bdr_api;

-- ---------------------------------------------------------------------
-- Tabelas de domínio
-- ---------------------------------------------------------------------

-- Cargos (perfis de acesso) dos usuários.
CREATE TABLE cargos (
  codigo        ENUM('TECNICO','GESTOR','SUPORTE','SUPORTE_INTERNO','COMERCIAL') NOT NULL,
  nome          VARCHAR(60)  NOT NULL,
  descricao     VARCHAR(255) NOT NULL,
  pode_abrir_ticket  BOOLEAN NOT NULL DEFAULT FALSE,
  pode_aprovar_encerramento BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT pk_cargos PRIMARY KEY (codigo),
  CONSTRAINT uq_cargos_nome UNIQUE (nome)
) ENGINE=InnoDB;

-- Prioridades dos tickets, com o SLA padrão de cada uma.
CREATE TABLE prioridades (
  codigo        ENUM('BAIXA','MEDIA','ALTA','CRITICA') NOT NULL,
  nome          VARCHAR(30) NOT NULL,
  peso          TINYINT UNSIGNED NOT NULL,
  sla_horas     SMALLINT UNSIGNED NOT NULL,
  alerta_horas  SMALLINT UNSIGNED NOT NULL DEFAULT 2,
  CONSTRAINT pk_prioridades PRIMARY KEY (codigo),
  CONSTRAINT uq_prioridades_peso UNIQUE (peso),
  CONSTRAINT ck_prioridades_peso CHECK (peso BETWEEN 1 AND 10),
  CONSTRAINT ck_prioridades_sla CHECK (sla_horas BETWEEN 1 AND 720),
  CONSTRAINT ck_prioridades_alerta CHECK (alerta_horas < sla_horas)
) ENGINE=InnoDB;

-- Status possíveis do ciclo de vida de um ticket.
CREATE TABLE status_ticket (
  codigo        ENUM('NAO_INICIADO','EM_ANDAMENTO','SOLICITACAO_ENCERRAMENTO','ENCERRADO','EM_REVISAO') NOT NULL,
  nome          VARCHAR(40)  NOT NULL,
  descricao     VARCHAR(255) NOT NULL,
  finalizado    BOOLEAN NOT NULL DEFAULT FALSE,
  ordem         TINYINT UNSIGNED NOT NULL,
  CONSTRAINT pk_status_ticket PRIMARY KEY (codigo),
  CONSTRAINT uq_status_ticket_ordem UNIQUE (ordem)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Tabelas do sistema (mesmas da API)
-- ---------------------------------------------------------------------

CREATE TABLE equipes (
  id            CHAR(36)     NOT NULL DEFAULT (UUID()),
  nome          VARCHAR(100) NOT NULL,
  descricao     VARCHAR(255) NULL,
  ativo         BOOLEAN      NOT NULL DEFAULT TRUE,
  criado_em     DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  atualizado_em DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  CONSTRAINT pk_equipes PRIMARY KEY (id),
  CONSTRAINT uq_equipes_nome UNIQUE (nome),
  CONSTRAINT ck_equipes_nome CHECK (CHAR_LENGTH(TRIM(nome)) >= 3)
) ENGINE=InnoDB;

CREATE TABLE usuarios (
  id               CHAR(36)     NOT NULL DEFAULT (UUID()),
  nome             VARCHAR(120) NOT NULL,
  email            VARCHAR(254) NOT NULL,
  senha_hash       VARCHAR(255) NOT NULL,
  cargo            ENUM('TECNICO','GESTOR','SUPORTE','SUPORTE_INTERNO','COMERCIAL') NOT NULL,
  ativo            BOOLEAN      NOT NULL DEFAULT TRUE,
  senha_provisoria BOOLEAN      NOT NULL DEFAULT TRUE,
  criado_em        DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  atualizado_em    DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  equipe_id        CHAR(36)     NULL,
  criado_por_id    CHAR(36)     NULL,
  CONSTRAINT pk_usuarios PRIMARY KEY (id),
  CONSTRAINT uq_usuarios_email UNIQUE (email),
  CONSTRAINT ck_usuarios_email CHECK (email LIKE '_%@_%._%'),
  CONSTRAINT fk_usuarios_cargo FOREIGN KEY (cargo) REFERENCES cargos (codigo)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_usuarios_equipe FOREIGN KEY (equipe_id) REFERENCES equipes (id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_usuarios_criado_por FOREIGN KEY (criado_por_id) REFERENCES usuarios (id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  INDEX ix_usuarios_equipe (equipe_id)
) ENGINE=InnoDB;

CREATE TABLE clientes (
  id            CHAR(36)     NOT NULL DEFAULT (UUID()),
  nome          VARCHAR(150) NOT NULL,
  ativo         BOOLEAN      NOT NULL DEFAULT TRUE,
  criado_em     DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  atualizado_em DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  CONSTRAINT pk_clientes PRIMARY KEY (id),
  CONSTRAINT uq_clientes_nome UNIQUE (nome)
) ENGINE=InnoDB;

CREATE TABLE projetos (
  id               CHAR(36)     NOT NULL DEFAULT (UUID()),
  nome             VARCHAR(150) NOT NULL,
  local_instalacao VARCHAR(255) NOT NULL,
  descricao        TEXT         NULL,
  ativo            BOOLEAN      NOT NULL DEFAULT TRUE,
  criado_em        DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  atualizado_em    DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  cliente_id       CHAR(36)     NOT NULL,
  equipe_id        CHAR(36)     NOT NULL,
  gestor_id        CHAR(36)     NOT NULL,
  CONSTRAINT pk_projetos PRIMARY KEY (id),
  CONSTRAINT uq_projetos_cliente_nome UNIQUE (cliente_id, nome),
  CONSTRAINT fk_projetos_cliente FOREIGN KEY (cliente_id) REFERENCES clientes (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_projetos_equipe FOREIGN KEY (equipe_id) REFERENCES equipes (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_projetos_gestor FOREIGN KEY (gestor_id) REFERENCES usuarios (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  INDEX ix_projetos_equipe (equipe_id),
  INDEX ix_projetos_gestor (gestor_id)
) ENGINE=InnoDB;

CREATE TABLE tickets (
  id             CHAR(36)     NOT NULL DEFAULT (UUID()),
  titulo         VARCHAR(180) NOT NULL,
  descricao      TEXT         NOT NULL,
  categoria      ENUM('MANUTENCAO','INSTALACAO') NOT NULL,
  prioridade     ENUM('BAIXA','MEDIA','ALTA','CRITICA') NOT NULL DEFAULT 'MEDIA',
  status         ENUM('NAO_INICIADO','EM_ANDAMENTO','SOLICITACAO_ENCERRAMENTO','ENCERRADO','EM_REVISAO')
                 NOT NULL DEFAULT 'EM_ANDAMENTO',
  sla_em         DATETIME(3)  NOT NULL,
  encerrado_em   DATETIME(3)  NULL,
  criado_em      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  atualizado_em  DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  projeto_id     CHAR(36)     NOT NULL,
  aberto_por_id  CHAR(36)     NOT NULL,
  responsavel_id CHAR(36)     NULL,
  CONSTRAINT pk_tickets PRIMARY KEY (id),
  CONSTRAINT ck_tickets_titulo CHECK (CHAR_LENGTH(TRIM(titulo)) >= 5),
  CONSTRAINT ck_tickets_sla CHECK (sla_em > criado_em),
  -- encerrado_em só existe (e é obrigatório) quando o status é ENCERRADO
  CONSTRAINT ck_tickets_encerramento CHECK (
    (status = 'ENCERRADO' AND encerrado_em IS NOT NULL AND encerrado_em >= criado_em)
    OR (status <> 'ENCERRADO' AND encerrado_em IS NULL)),
  CONSTRAINT fk_tickets_prioridade FOREIGN KEY (prioridade) REFERENCES prioridades (codigo)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  -- status participa de CHECK, por isso a FK não pode ter ação referencial (MySQL)
  CONSTRAINT fk_tickets_status FOREIGN KEY (status) REFERENCES status_ticket (codigo)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  CONSTRAINT fk_tickets_projeto FOREIGN KEY (projeto_id) REFERENCES projetos (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_tickets_aberto_por FOREIGN KEY (aberto_por_id) REFERENCES usuarios (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_tickets_responsavel FOREIGN KEY (responsavel_id) REFERENCES usuarios (id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  INDEX ix_tickets_fila (projeto_id, status, prioridade, criado_em),
  INDEX ix_tickets_sla (status, sla_em),
  INDEX ix_tickets_aberto_por (aberto_por_id),
  INDEX ix_tickets_responsavel (responsavel_id)
) ENGINE=InnoDB;

-- Associativa N:N - equipes alocadas em cada ticket.
CREATE TABLE ticket_equipes (
  id         CHAR(36)    NOT NULL DEFAULT (UUID()),
  criado_em  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  ticket_id  CHAR(36)    NOT NULL,
  equipe_id  CHAR(36)    NOT NULL,
  CONSTRAINT pk_ticket_equipes PRIMARY KEY (id),
  CONSTRAINT uq_ticket_equipes_ticket_equipe UNIQUE (ticket_id, equipe_id),
  CONSTRAINT fk_ticket_equipes_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_ticket_equipes_equipe FOREIGN KEY (equipe_id) REFERENCES equipes (id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  INDEX ix_ticket_equipes_equipe (equipe_id)
) ENGINE=InnoDB;

-- Relatórios de atendimento (trabalho realizado, materiais...).
CREATE TABLE relatorios (
  id                   CHAR(36)    NOT NULL DEFAULT (UUID()),
  trabalho_realizado   TEXT        NOT NULL,
  materiais_utilizados TEXT        NOT NULL,
  outros_detalhes      TEXT        NOT NULL,
  criado_em            DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  atualizado_em        DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  ticket_id            CHAR(36)    NOT NULL,
  autor_id             CHAR(36)    NOT NULL,
  CONSTRAINT pk_relatorios PRIMARY KEY (id),
  CONSTRAINT ck_relatorios_trabalho CHECK (CHAR_LENGTH(TRIM(trabalho_realizado)) >= 10),
  CONSTRAINT fk_relatorios_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_relatorios_autor FOREIGN KEY (autor_id) REFERENCES usuarios (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  INDEX ix_relatorios_ticket (ticket_id, criado_em),
  INDEX ix_relatorios_autor (autor_id)
) ENGINE=InnoDB;

-- Histórico (log) de eventos de cada ticket.
CREATE TABLE historico_ticket (
  id               CHAR(36)    NOT NULL DEFAULT (UUID()),
  evento           VARCHAR(50) NOT NULL,
  descricao        TEXT        NOT NULL,
  criado_em        DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  ticket_id        CHAR(36)    NOT NULL,
  usuario_id       CHAR(36)    NULL,  -- NULL = evento automático do sistema
  equipe_id        CHAR(36)    NULL,  -- equipe do autor no momento do registro
  inicio_equipe_id CHAR(36)    NULL,  -- só em ATIVIDADE_INICIADA
  CONSTRAINT pk_historico_ticket PRIMARY KEY (id),
  CONSTRAINT uq_historico_inicio_equipe UNIQUE (ticket_id, inicio_equipe_id),
  CONSTRAINT ck_historico_evento CHECK (evento = UPPER(evento) AND CHAR_LENGTH(evento) >= 3),
  CONSTRAINT fk_historico_ticket FOREIGN KEY (ticket_id) REFERENCES tickets (id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_historico_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_historico_equipe FOREIGN KEY (equipe_id) REFERENCES equipes (id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT fk_historico_inicio_equipe FOREIGN KEY (inicio_equipe_id) REFERENCES equipes (id)
    ON UPDATE CASCADE ON DELETE SET NULL,
  INDEX ix_historico_ticket_data (ticket_id, criado_em),
  INDEX ix_historico_usuario (usuario_id),
  INDEX ix_historico_equipe (equipe_id),
  INDEX ix_historico_inicio_equipe (inicio_equipe_id)
) ENGINE=InnoDB;

-- Registro de atividades feitas por cada conta (auditoria de usuário).
CREATE TABLE atividades_conta (
  id         CHAR(36)    NOT NULL DEFAULT (UUID()),
  tipo       VARCHAR(20) NOT NULL,
  descricao  TEXT        NOT NULL,
  criado_em  DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  usuario_id CHAR(36)    NOT NULL,
  CONSTRAINT pk_atividades_conta PRIMARY KEY (id),
  CONSTRAINT ck_atividades_tipo CHECK (tipo IN ('CADASTRO','EQUIPE','LOG','PROJETO','TICKET','TICKET | ABERTURA','CONTA')),
  CONSTRAINT fk_atividades_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  INDEX ix_atividades_conta_usuario_data (usuario_id, criado_em)
) ENGINE=InnoDB;
