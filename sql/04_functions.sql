-- =====================================================================
-- BDR 2026.02 - 3ª Avaliação | Parte 3 - Functions (6)
-- =====================================================================
USE bdr_api;

DROP FUNCTION IF EXISTS fn_calcular_sla_em;
DROP FUNCTION IF EXISTS fn_situacao_sla;
DROP FUNCTION IF EXISTS fn_percentual_sla_consumido;
DROP FUNCTION IF EXISTS fn_tempo_medio_resolucao_equipe;
DROP FUNCTION IF EXISTS fn_taxa_cumprimento_sla_equipe;
DROP FUNCTION IF EXISTS fn_sugerir_tecnico;

DELIMITER $$

-- ---------------------------------------------------------------------
-- F1. fn_calcular_sla_em(prioridade, data_base)
-- Problema: na API o prazo do SLA é escolhido "na mão" no formulário.
-- O banco passa a ter o SLA padrão de cada prioridade (tabela
-- prioridades) e esta função devolve a data-limite a partir de uma data
-- base (abertura do ticket). Usada pelo trigger de INSERT de tickets e
-- pela procedure de abertura.
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_calcular_sla_em(p_prioridade VARCHAR(10), p_base DATETIME(3))
RETURNS DATETIME(3)
READS SQL DATA
BEGIN
  DECLARE v_horas SMALLINT;
  DECLARE CONTINUE HANDLER FOR NOT FOUND BEGIN END;  -- SELECT INTO sem linha => NULL

  SELECT sla_horas INTO v_horas
    FROM prioridades
   WHERE codigo = p_prioridade;

  IF v_horas IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Prioridade inválida: não há SLA cadastrado.';
  END IF;

  RETURN DATE_ADD(COALESCE(p_base, NOW(3)), INTERVAL v_horas HOUR);
END$$

-- ---------------------------------------------------------------------
-- F2. fn_situacao_sla(ticket_id)            >>> pensada para a API (Parte 5)
-- Problema: a US 5 pede um indicador visual do SLA em cada ticket. A
-- função classifica o ticket em:
--   CUMPRIDO / VIOLADO  -> ticket encerrado dentro / fora do prazo
--   VENCIDO             -> aberto e já passou do prazo
--   EM_ALERTA           -> aberto e faltam menos que "alerta_horas" da
--                          prioridade (subconsulta na tabela prioridades)
--   NO_PRAZO            -> aberto e com folga
-- Retorna NULL se o ticket não existe.
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_situacao_sla(p_ticket_id CHAR(36))
RETURNS VARCHAR(20)
READS SQL DATA
BEGIN
  DECLARE v_status   VARCHAR(30);
  DECLARE v_sla      DATETIME(3);
  DECLARE v_fim      DATETIME(3);
  DECLARE v_alerta   SMALLINT;
  DECLARE CONTINUE HANDLER FOR NOT FOUND BEGIN END;  -- SELECT INTO sem linha => NULL

  SELECT t.status, t.sla_em, t.encerrado_em,
         (SELECT p.alerta_horas FROM prioridades p WHERE p.codigo = t.prioridade)
    INTO v_status, v_sla, v_fim, v_alerta
    FROM tickets t
   WHERE t.id = p_ticket_id;

  IF v_status IS NULL THEN
    RETURN NULL;
  END IF;

  IF v_status = 'ENCERRADO' THEN
    RETURN IF(v_fim <= v_sla, 'CUMPRIDO', 'VIOLADO');
  ELSEIF NOW(3) > v_sla THEN
    RETURN 'VENCIDO';
  ELSEIF TIMESTAMPDIFF(MINUTE, NOW(3), v_sla) <= v_alerta * 60 THEN
    RETURN 'EM_ALERTA';
  END IF;
  RETURN 'NO_PRAZO';
END$$

-- ---------------------------------------------------------------------
-- F3. fn_percentual_sla_consumido(ticket_id)
-- Problema: para a barra de progresso do SLA na tela é preciso saber
-- quanto do prazo já foi consumido (0 % na abertura, 100 % no prazo,
-- > 100 % quando estourou). Para tickets encerrados, mede até o
-- encerramento.
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_percentual_sla_consumido(p_ticket_id CHAR(36))
RETURNS DECIMAL(7,1)
READS SQL DATA
BEGIN
  DECLARE v_criado DATETIME(3);
  DECLARE v_sla    DATETIME(3);
  DECLARE v_ref    DATETIME(3);
  DECLARE CONTINUE HANDLER FOR NOT FOUND BEGIN END;  -- SELECT INTO sem linha => NULL

  SELECT criado_em, sla_em, COALESCE(encerrado_em, NOW(3))
    INTO v_criado, v_sla, v_ref
    FROM tickets
   WHERE id = p_ticket_id;

  IF v_criado IS NULL THEN
    RETURN NULL;
  END IF;

  RETURN ROUND(100 * TIMESTAMPDIFF(SECOND, v_criado, v_ref)
                   / GREATEST(TIMESTAMPDIFF(SECOND, v_criado, v_sla), 1), 1);
END$$

-- ---------------------------------------------------------------------
-- F4. fn_tempo_medio_resolucao_equipe(equipe_id)
-- Problema: a liderança não tem visibilidade de quanto tempo cada equipe
-- leva para resolver um ticket. Calcula a média (AVG) em horas entre a
-- abertura e o encerramento dos tickets ENCERRADOS em que a equipe foi
-- alocada (INNER JOIN tickets x ticket_equipes).
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_tempo_medio_resolucao_equipe(p_equipe_id CHAR(36))
RETURNS DECIMAL(10,2)
READS SQL DATA
BEGIN
  DECLARE v_media DECIMAL(10,2);

  SELECT ROUND(AVG(TIMESTAMPDIFF(MINUTE, t.criado_em, t.encerrado_em)) / 60, 2)
    INTO v_media
    FROM tickets t
   INNER JOIN ticket_equipes te ON te.ticket_id = t.id
   WHERE te.equipe_id = p_equipe_id
     AND t.status = 'ENCERRADO';

  RETURN v_media;   -- NULL quando a equipe ainda não encerrou tickets
END$$

-- ---------------------------------------------------------------------
-- F5. fn_taxa_cumprimento_sla_equipe(equipe_id, inicio, fim)
-- Problema: medir o indicador "% de tickets encerrados dentro do SLA" de
-- uma equipe num período (tickets abertos entre inicio e fim). Usa duas
-- subconsultas com funções de grupo (COUNT) sobre os tickets da equipe.
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_taxa_cumprimento_sla_equipe(p_equipe_id CHAR(36), p_inicio DATE, p_fim DATE)
RETURNS DECIMAL(5,2)
READS SQL DATA
BEGIN
  DECLARE v_total   INT;
  DECLARE v_no_prazo INT;

  SELECT COUNT(*),
         COALESCE(SUM(t.encerrado_em <= t.sla_em), 0)
    INTO v_total, v_no_prazo
    FROM tickets t
   WHERE t.status = 'ENCERRADO'
     AND t.criado_em >= p_inicio
     AND t.criado_em <  DATE_ADD(p_fim, INTERVAL 1 DAY)
     AND t.id IN (SELECT te.ticket_id FROM ticket_equipes te WHERE te.equipe_id = p_equipe_id);

  IF v_total = 0 THEN
    RETURN NULL;
  END IF;
  RETURN ROUND(100 * v_no_prazo / v_total, 2);
END$$

-- ---------------------------------------------------------------------
-- F6. fn_sugerir_tecnico(equipe_id)
-- Problema: ao abrir/redistribuir um ticket o gestor precisa escolher um
-- técnico; a função sugere o técnico ATIVO da equipe com menos tickets
-- abertos sob sua responsabilidade (LEFT JOIN para contar zero, GROUP BY
-- + COUNT). Empate: quem tem menos relatórios nos últimos 7 dias
-- (subconsulta correlacionada). NULL se a equipe não tem técnico ativo.
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_sugerir_tecnico(p_equipe_id CHAR(36))
RETURNS CHAR(36)
READS SQL DATA
BEGIN
  DECLARE v_tecnico CHAR(36);
  DECLARE CONTINUE HANDLER FOR NOT FOUND BEGIN END;  -- SELECT INTO sem linha => NULL

  SELECT u.id INTO v_tecnico
    FROM usuarios u
    LEFT JOIN tickets t
           ON t.responsavel_id = u.id
          AND t.status <> 'ENCERRADO'
   WHERE u.equipe_id = p_equipe_id
     AND u.cargo = 'TECNICO'
     AND u.ativo = TRUE
   GROUP BY u.id
   ORDER BY COUNT(t.id),
            (SELECT COUNT(*) FROM relatorios r
              WHERE r.autor_id = u.id
                AND r.criado_em >= NOW(3) - INTERVAL 7 DAY),
            u.id
   LIMIT 1;

  RETURN v_tecnico;
END$$

DELIMITER ;
