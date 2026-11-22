-- =====================================================================
-- BDR 2026.02 - 3ª Avaliação | Parte 3 - Triggers (6)
-- Criados DEPOIS da carga (02_dml.sql) para não interferir nos dados
-- históricos. Depende de 04_functions.sql.
-- =====================================================================
USE bdr_api;

DROP TRIGGER IF EXISTS trg_tickets_bi_validar;
DROP TRIGGER IF EXISTS trg_tickets_bu_fluxo_status;
DROP TRIGGER IF EXISTS trg_tickets_au_historico;
DROP TRIGGER IF EXISTS trg_relatorios_bi_validar_autor;
DROP TRIGGER IF EXISTS trg_relatorios_ai_inicio_atividade;
DROP TRIGGER IF EXISTS trg_usuarios_au_auditoria;

DELIMITER $$

-- ---------------------------------------------------------------------
-- T1. trg_tickets_bi_validar  (BEFORE INSERT ON tickets)
-- Problema: qualquer caminho de inserção (API, carga, outro sistema)
-- precisa respeitar as regras de abertura: projeto e cliente ativos,
-- quem abre deve estar ativo, ticket nasce aberto (nunca ENCERRADO) e,
-- se o SLA não for informado (NULL), é calculado pela prioridade com
-- fn_calcular_sla_em.
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_tickets_bi_validar
BEFORE INSERT ON tickets
FOR EACH ROW
BEGIN
  DECLARE v_ok BOOLEAN;

  SET NEW.criado_em = COALESCE(NEW.criado_em, NOW(3));

  SELECT (p.ativo AND c.ativo) INTO v_ok
    FROM projetos p
   INNER JOIN clientes c ON c.id = p.cliente_id
   WHERE p.id = NEW.projeto_id;
  IF v_ok IS NULL OR v_ok = FALSE THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Não é possível abrir ticket: projeto ou cliente inativo/inexistente.';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM usuarios WHERE id = NEW.aberto_por_id AND ativo) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Usuário que abre o ticket está inativo ou não existe.';
  END IF;

  IF NEW.status = 'ENCERRADO' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Um ticket não pode ser criado já encerrado.';
  END IF;
  SET NEW.encerrado_em = NULL;

  IF NEW.sla_em IS NULL THEN
    SET NEW.sla_em = fn_calcular_sla_em(NEW.prioridade, NEW.criado_em);
  END IF;
END$$

-- ---------------------------------------------------------------------
-- T2. trg_tickets_bu_fluxo_status  (BEFORE UPDATE ON tickets)
-- Problema: a API sofreu bugs de "alterar ticket encerrado" e de
-- transições inválidas (ver commits do projeto). O trigger garante no
-- banco: (a) ticket ENCERRADO não pode mais ser alterado; (b) só são
-- aceitas as transições do fluxo:
--     NAO_INICIADO -> EM_ANDAMENTO
--     EM_ANDAMENTO / EM_REVISAO -> SOLICITACAO_ENCERRAMENTO
--     EM_REVISAO -> EM_ANDAMENTO
--     SOLICITACAO_ENCERRAMENTO -> ENCERRADO | EM_REVISAO
-- (c) preenche encerrado_em automaticamente ao encerrar.
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_tickets_bu_fluxo_status
BEFORE UPDATE ON tickets
FOR EACH ROW
BEGIN
  IF OLD.status = 'ENCERRADO' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ticket encerrado não pode ser alterado.';
  END IF;

  IF NEW.status <> OLD.status AND NOT (
       (OLD.status = 'NAO_INICIADO'  AND NEW.status = 'EM_ANDAMENTO') OR
       (OLD.status IN ('EM_ANDAMENTO', 'EM_REVISAO') AND NEW.status = 'SOLICITACAO_ENCERRAMENTO') OR
       (OLD.status = 'EM_REVISAO'    AND NEW.status = 'EM_ANDAMENTO') OR
       (OLD.status = 'SOLICITACAO_ENCERRAMENTO' AND NEW.status IN ('ENCERRADO', 'EM_REVISAO'))
     ) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Transição de status não permitida.';
  END IF;

  IF NEW.status = 'ENCERRADO' THEN
    SET NEW.encerrado_em = NOW(3);
  ELSE
    SET NEW.encerrado_em = NULL;
  END IF;
END$$

-- ---------------------------------------------------------------------
-- T3. trg_tickets_au_historico  (AFTER UPDATE ON tickets)
-- Problema: rastreabilidade completa de cada ordem de serviço. Toda
-- mudança de status, responsável ou prazo de SLA gera automaticamente
-- um evento no histórico (usuario_id NULL = evento do sistema), mesmo
-- que a alteração não tenha passado pela API.
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_tickets_au_historico
AFTER UPDATE ON tickets
FOR EACH ROW
BEGIN
  IF NEW.status <> OLD.status THEN
    INSERT INTO historico_ticket (evento, descricao, ticket_id)
    VALUES ('STATUS_ALTERADO',
            CONCAT('Status alterado de ', OLD.status, ' para ', NEW.status, '.'), NEW.id);
  END IF;

  IF NOT (NEW.responsavel_id <=> OLD.responsavel_id) THEN
    INSERT INTO historico_ticket (evento, descricao, ticket_id)
    VALUES ('RESPONSAVEL_ALTERADO',
            CONCAT('Responsável alterado de ',
                   COALESCE((SELECT nome FROM usuarios WHERE id = OLD.responsavel_id), '(ninguém)'),
                   ' para ',
                   COALESCE((SELECT nome FROM usuarios WHERE id = NEW.responsavel_id), '(ninguém)'), '.'),
            NEW.id);
  END IF;

  IF NEW.sla_em <> OLD.sla_em THEN
    INSERT INTO historico_ticket (evento, descricao, ticket_id)
    VALUES ('SLA_ALTERADO',
            CONCAT('Prazo do SLA alterado de ', DATE_FORMAT(OLD.sla_em, '%d/%m/%Y %H:%i'),
                   ' para ', DATE_FORMAT(NEW.sla_em, '%d/%m/%Y %H:%i'), '.'), NEW.id);
  END IF;
END$$

-- ---------------------------------------------------------------------
-- T4. trg_relatorios_bi_validar_autor  (BEFORE INSERT ON relatorios)
-- Problema: só quem atua no ticket pode registrar relatório (US 4). O
-- autor tem de estar ativo e pertencer a uma das equipes alocadas ao
-- ticket (subconsulta EXISTS em ticket_equipes) e o ticket não pode
-- estar encerrado.
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_relatorios_bi_validar_autor
BEFORE INSERT ON relatorios
FOR EACH ROW
BEGIN
  IF (SELECT status FROM tickets WHERE id = NEW.ticket_id) = 'ENCERRADO' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ticket encerrado não recebe novos relatórios.';
  END IF;

  IF NOT EXISTS (
       SELECT 1
         FROM usuarios u
        INNER JOIN ticket_equipes te ON te.equipe_id = u.equipe_id
        WHERE u.id = NEW.autor_id
          AND u.ativo
          AND te.ticket_id = NEW.ticket_id) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Autor inativo ou sua equipe não está alocada neste ticket.';
  END IF;
END$$

-- ---------------------------------------------------------------------
-- T5. trg_relatorios_ai_inicio_atividade  (AFTER INSERT ON relatorios)
-- Problema: ao registrar o primeiro relatório de uma equipe, o técnico
-- obviamente já iniciou o trabalho. O trigger registra o evento
-- ATIVIDADE_INICIADA da equipe (se ainda não houver - o índice único
-- uq_historico_inicio_equipe garante um por equipe), move o ticket de
-- NAO_INICIADO/EM_REVISAO para EM_ANDAMENTO, grava o LOG no histórico
-- e a atividade na conta do técnico.
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_relatorios_ai_inicio_atividade
AFTER INSERT ON relatorios
FOR EACH ROW
BEGIN
  DECLARE v_equipe CHAR(36);
  DECLARE v_status VARCHAR(30);

  SELECT equipe_id INTO v_equipe FROM usuarios WHERE id = NEW.autor_id;
  SELECT status    INTO v_status FROM tickets  WHERE id = NEW.ticket_id;

  IF NOT EXISTS (SELECT 1 FROM historico_ticket
                  WHERE ticket_id = NEW.ticket_id AND inicio_equipe_id = v_equipe) THEN
    INSERT INTO historico_ticket (evento, descricao, ticket_id, usuario_id, equipe_id, inicio_equipe_id)
    VALUES ('ATIVIDADE_INICIADA', 'Início registrado automaticamente pelo primeiro relatório da equipe.',
            NEW.ticket_id, NEW.autor_id, v_equipe, v_equipe);
  END IF;

  IF v_status IN ('NAO_INICIADO', 'EM_REVISAO') THEN
    UPDATE tickets SET status = 'EM_ANDAMENTO' WHERE id = NEW.ticket_id;
  END IF;

  INSERT INTO historico_ticket (evento, descricao, ticket_id, usuario_id, equipe_id)
  VALUES ('LOG', CONCAT('Relatório registrado: ', LEFT(NEW.trabalho_realizado, 120)),
          NEW.ticket_id, NEW.autor_id, v_equipe);

  INSERT INTO atividades_conta (tipo, descricao, usuario_id)
  VALUES ('LOG', CONCAT('Registrou relatório no ticket ',
                        (SELECT titulo FROM tickets WHERE id = NEW.ticket_id), '.'),
          NEW.autor_id);
END$$

-- ---------------------------------------------------------------------
-- T6. trg_usuarios_au_auditoria  (AFTER UPDATE ON usuarios)
-- Problema: o Suporte Interno ativa/desativa, edita e redefine senhas
-- de contas (US 20, 23, 24) e isso precisa ficar auditado. Registra em
-- atividades_conta cada ativação/desativação, troca de cargo, troca de
-- equipe e redefinição de senha da conta alterada.
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_usuarios_au_auditoria
AFTER UPDATE ON usuarios
FOR EACH ROW
BEGIN
  IF NEW.ativo <> OLD.ativo THEN
    INSERT INTO atividades_conta (tipo, descricao, usuario_id)
    VALUES ('CONTA', IF(NEW.ativo, 'Conta reativada.', 'Conta desativada.'), NEW.id);
  END IF;

  IF NEW.cargo <> OLD.cargo THEN
    INSERT INTO atividades_conta (tipo, descricao, usuario_id)
    VALUES ('CONTA', CONCAT('Cargo alterado de ',
                            (SELECT nome FROM cargos WHERE codigo = OLD.cargo), ' para ',
                            (SELECT nome FROM cargos WHERE codigo = NEW.cargo), '.'), NEW.id);
  END IF;

  IF NOT (NEW.equipe_id <=> OLD.equipe_id) THEN
    INSERT INTO atividades_conta (tipo, descricao, usuario_id)
    VALUES ('EQUIPE', CONCAT('Equipe alterada de ',
                             COALESCE((SELECT nome FROM equipes WHERE id = OLD.equipe_id), '(nenhuma)'),
                             ' para ',
                             COALESCE((SELECT nome FROM equipes WHERE id = NEW.equipe_id), '(nenhuma)'), '.'),
            NEW.id);
  END IF;

  IF NEW.senha_hash <> OLD.senha_hash THEN
    INSERT INTO atividades_conta (tipo, descricao, usuario_id)
    VALUES ('CONTA', IF(NEW.senha_provisoria, 'Senha redefinida (provisória).', 'Senha alterada pelo usuário.'),
            NEW.id);
  END IF;
END$$

DELIMITER ;
