-- =====================================================================
-- BDR 2026.02 - 3ª Avaliação | Parte 3 - Stored Procedures (6)
-- Depende de 03_views.sql e 04_functions.sql.
-- =====================================================================
USE bdr_api;

DROP PROCEDURE IF EXISTS sp_abrir_ticket;
DROP PROCEDURE IF EXISTS sp_decidir_encerramento;
DROP PROCEDURE IF EXISTS sp_desativar_tecnico_redistribuir;
DROP PROCEDURE IF EXISTS sp_gerar_alertas_sla;
DROP PROCEDURE IF EXISTS sp_relatorio_sla_equipes;
DROP PROCEDURE IF EXISTS sp_ranking_tecnicos;

DELIMITER $$

-- ---------------------------------------------------------------------
-- P1. sp_abrir_ticket(...)                    >>> pensada para a API (Parte 5)
-- Problema: abrir um ticket envolve várias gravações que precisam ser
-- atômicas (US 1 e 8): o ticket, a alocação da equipe do projeto, o
-- histórico e a atividade da conta. A procedure valida as regras de
-- negócio (usuário ativo e com cargo que pode abrir ticket, projeto e
-- cliente ativos, categoria/prioridade válidas), calcula o SLA pela
-- prioridade quando não é informado (fn_calcular_sla_em), sugere o
-- técnico responsável (fn_sugerir_tecnico) e grava tudo numa transação.
-- Devolve o id no parâmetro OUT e o ticket criado (vw_tickets_detalhados).
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_abrir_ticket(
  IN  p_projeto_id   CHAR(36),
  IN  p_usuario_id   CHAR(36),
  IN  p_titulo       VARCHAR(180),
  IN  p_descricao    TEXT,
  IN  p_categoria    VARCHAR(20),
  IN  p_prioridade   VARCHAR(10),
  IN  p_sla_horas    SMALLINT,      -- NULL = SLA padrão da prioridade
  OUT p_ticket_id    CHAR(36))
BEGIN
  DECLARE v_pode_abrir BOOLEAN;
  DECLARE v_ativo      BOOLEAN;
  DECLARE v_eq_usuario CHAR(36);
  DECLARE v_nome_proj  VARCHAR(150);
  DECLARE v_eq_proj    CHAR(36);
  DECLARE v_proj_ok    BOOLEAN;
  DECLARE v_agora      DATETIME(3) DEFAULT NOW(3);
  DECLARE v_sla        DATETIME(3);

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  -- usuário + permissão do cargo (INNER JOIN com a tabela de domínio)
  SELECT u.ativo, c.pode_abrir_ticket, u.equipe_id
    INTO v_ativo, v_pode_abrir, v_eq_usuario
    FROM usuarios u
   INNER JOIN cargos c ON c.codigo = u.cargo
   WHERE u.id = p_usuario_id;

  IF v_ativo IS NULL OR v_ativo = FALSE THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Usuário inexistente ou inativo.';
  END IF;
  IF v_pode_abrir = FALSE THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'O cargo do usuário não permite abrir tickets.';
  END IF;

  -- projeto e cliente precisam estar ativos
  SELECT p.nome, p.equipe_id, (p.ativo AND c.ativo)
    INTO v_nome_proj, v_eq_proj, v_proj_ok
    FROM projetos p
   INNER JOIN clientes c ON c.id = p.cliente_id
   WHERE p.id = p_projeto_id;

  IF v_proj_ok IS NULL OR v_proj_ok = FALSE THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Projeto inexistente, inativo ou de cliente inativo.';
  END IF;
  IF p_categoria NOT IN ('MANUTENCAO', 'INSTALACAO') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Categoria inválida (MANUTENCAO ou INSTALACAO).';
  END IF;

  SET p_prioridade = COALESCE(p_prioridade, 'MEDIA');
  SET v_sla = IF(p_sla_horas IS NULL,
                 fn_calcular_sla_em(p_prioridade, v_agora),
                 DATE_ADD(v_agora, INTERVAL p_sla_horas HOUR));

  START TRANSACTION;
    SET p_ticket_id = UUID();

    INSERT INTO tickets (id, titulo, descricao, categoria, prioridade, status, sla_em,
                         criado_em, projeto_id, aberto_por_id, responsavel_id)
    VALUES (p_ticket_id, p_titulo, p_descricao, p_categoria, p_prioridade, 'EM_ANDAMENTO', v_sla,
            v_agora, p_projeto_id, p_usuario_id, fn_sugerir_tecnico(v_eq_proj));

    INSERT INTO ticket_equipes (ticket_id, equipe_id, criado_em)
    VALUES (p_ticket_id, v_eq_proj, v_agora);

    INSERT INTO historico_ticket (evento, descricao, criado_em, ticket_id, usuario_id, equipe_id)
    VALUES ('TICKET_CRIADO',
            CONCAT('Ticket aberto com prioridade ', p_prioridade, ' e SLA até ',
                   DATE_FORMAT(v_sla, '%d/%m/%Y %H:%i'), '.'),
            v_agora, p_ticket_id, p_usuario_id, v_eq_usuario);

    INSERT INTO atividades_conta (tipo, descricao, criado_em, usuario_id)
    VALUES ('TICKET | ABERTURA',
            CONCAT('Abriu o ticket ', p_titulo, ' vinculado ao projeto ', v_nome_proj, '.'),
            v_agora, p_usuario_id);
  COMMIT;

  SELECT ticket_id, titulo, prioridade, status, sla_em, equipe_projeto, responsavel,
         fn_situacao_sla(ticket_id) AS situacao_sla
    FROM vw_tickets_detalhados
   WHERE ticket_id = p_ticket_id;
END$$

-- ---------------------------------------------------------------------
-- P2. sp_decidir_encerramento(ticket, gestor, aprovar, parecer)
--                                             >>> pensada para a API (Parte 5)
-- Problema: o fluxo de aprovação de encerramento com parecer (solução da
-- API). Só um GESTOR ativo de uma equipe alocada ao ticket pode decidir,
-- e só quando o ticket está em SOLICITACAO_ENCERRAMENTO. A linha do
-- ticket é travada (SELECT ... FOR UPDATE) para evitar decisão em
-- corrida. Aprovar -> ENCERRADO; negar -> EM_REVISAO. O parecer vai para
-- o histórico; o encerrado_em é preenchido pelo trigger de tickets.
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_decidir_encerramento(
  IN p_ticket_id CHAR(36),
  IN p_gestor_id CHAR(36),
  IN p_aprovar   BOOLEAN,
  IN p_parecer   TEXT)
BEGIN
  DECLARE v_status   VARCHAR(30);
  DECLARE v_cargo    VARCHAR(20);
  DECLARE v_ativo    BOOLEAN;
  DECLARE v_equipe   CHAR(36);

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  IF p_parecer IS NULL OR CHAR_LENGTH(TRIM(p_parecer)) < 5 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Informe um parecer (mínimo 5 caracteres).';
  END IF;

  START TRANSACTION;
    SELECT status INTO v_status FROM tickets WHERE id = p_ticket_id FOR UPDATE;
    IF v_status IS NULL THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ticket não encontrado.';
    END IF;
    IF v_status <> 'SOLICITACAO_ENCERRAMENTO' THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'O ticket não está aguardando decisão de encerramento.';
    END IF;

    SELECT cargo, ativo, equipe_id INTO v_cargo, v_ativo, v_equipe
      FROM usuarios WHERE id = p_gestor_id;
    IF v_cargo IS NULL OR v_cargo <> 'GESTOR' OR v_ativo = FALSE THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Apenas um gestor ativo pode decidir o encerramento.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM ticket_equipes te
                    WHERE te.ticket_id = p_ticket_id AND te.equipe_id = v_equipe) THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'A equipe do gestor não está alocada neste ticket.';
    END IF;

    UPDATE tickets
       SET status = IF(p_aprovar, 'ENCERRADO', 'EM_REVISAO')
     WHERE id = p_ticket_id;

    INSERT INTO historico_ticket (evento, descricao, ticket_id, usuario_id, equipe_id)
    VALUES (IF(p_aprovar, 'ENCERRAMENTO_APROVADO', 'ENCERRAMENTO_NEGADO'),
            p_parecer, p_ticket_id, p_gestor_id, v_equipe);
  COMMIT;

  SELECT t.id, t.status, t.encerrado_em, fn_situacao_sla(t.id) AS situacao_sla,
         fn_percentual_sla_consumido(t.id) AS pct_sla_consumido
    FROM tickets t WHERE t.id = p_ticket_id;
END$$

-- ---------------------------------------------------------------------
-- P3. sp_desativar_tecnico_redistribuir(tecnico, executor)
-- Problema: quando o Suporte Interno desativa a conta de um técnico
-- (US 23), os tickets abertos dele ficariam sem dono. A procedure
-- desativa a conta e percorre com um CURSOR cada ticket aberto do
-- técnico, repassando-o para o técnico menos carregado da equipe do
-- projeto (fn_sugerir_tecnico). Se não houver ninguém disponível o
-- ticket fica sem responsável. Retorna o resumo da redistribuição.
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_desativar_tecnico_redistribuir(
  IN p_tecnico_id  CHAR(36),
  IN p_executor_id CHAR(36))
BEGIN
  DECLARE v_fim       BOOLEAN DEFAULT FALSE;
  DECLARE v_ticket    CHAR(36);
  DECLARE v_equipe    CHAR(36);
  DECLARE v_novo      CHAR(36);
  DECLARE v_cargo     VARCHAR(20);
  DECLARE v_exec      VARCHAR(20);

  DECLARE cur_tickets CURSOR FOR
    SELECT t.id, p.equipe_id
      FROM tickets t
     INNER JOIN projetos p ON p.id = t.projeto_id
     WHERE t.responsavel_id = p_tecnico_id
       AND t.status <> 'ENCERRADO'
     ORDER BY t.sla_em;
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_fim = TRUE;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SELECT cargo INTO v_cargo FROM usuarios WHERE id = p_tecnico_id;
  SELECT cargo INTO v_exec  FROM usuarios WHERE id = p_executor_id AND ativo;
  SET v_fim = FALSE;  -- os SELECT INTO acima podem ter acionado o NOT FOUND
  IF v_cargo IS NULL OR v_cargo <> 'TECNICO' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Usuário informado não é um técnico.';
  END IF;
  IF v_exec IS NULL OR v_exec <> 'SUPORTE_INTERNO' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Somente o Suporte Interno pode desativar contas.';
  END IF;

  DROP TEMPORARY TABLE IF EXISTS tmp_redistribuicao;
  CREATE TEMPORARY TABLE tmp_redistribuicao (
    ticket_id      CHAR(36),
    novo_tecnico   CHAR(36)
  );

  START TRANSACTION;
    -- desativa primeiro: assim fn_sugerir_tecnico já não o considera
    UPDATE usuarios SET ativo = FALSE WHERE id = p_tecnico_id;

    OPEN cur_tickets;
    laco: LOOP
      FETCH cur_tickets INTO v_ticket, v_equipe;
      IF v_fim THEN
        LEAVE laco;
      END IF;

      SET v_novo = fn_sugerir_tecnico(v_equipe);
      UPDATE tickets SET responsavel_id = v_novo WHERE id = v_ticket;
      INSERT INTO tmp_redistribuicao VALUES (v_ticket, v_novo);
    END LOOP laco;
    CLOSE cur_tickets;
  COMMIT;

  SELECT r.ticket_id, t.titulo, t.prioridade,
         COALESCE(u.nome, '(sem técnico disponível)') AS novo_responsavel
    FROM tmp_redistribuicao r
   INNER JOIN tickets  t ON t.id = r.ticket_id
   LEFT  JOIN usuarios u ON u.id = r.novo_tecnico;
END$$

-- ---------------------------------------------------------------------
-- P4. sp_gerar_alertas_sla()
-- Problema: a US 19 pede um alerta ao gestor quando o SLA de um ticket
-- estiver perto do fim. A procedure percorre com CURSOR os tickets
-- abertos classificados como EM_ALERTA ou VENCIDO (fn_situacao_sla),
-- registra um evento ALERTA_SLA no histórico - só se não houve alerta
-- para o mesmo ticket nas últimas 24 h (subconsulta NOT EXISTS, evita
-- spam) - e devolve a lista de e-mails a enviar (gestor do projeto).
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_gerar_alertas_sla()
BEGIN
  DECLARE v_fim      BOOLEAN DEFAULT FALSE;
  DECLARE v_ticket   CHAR(36);
  DECLARE v_situacao VARCHAR(20);
  DECLARE v_horas    DECIMAL(10,1);
  DECLARE v_gestor   VARCHAR(120);
  DECLARE v_email    VARCHAR(254);
  DECLARE v_titulo   VARCHAR(180);

  DECLARE cur_alerta CURSOR FOR
    SELECT v.ticket_id, fn_situacao_sla(v.ticket_id), v.horas_para_sla,
           v.gestor, v.email_gestor, v.titulo
      FROM vw_tickets_detalhados v
     WHERE v.finalizado = FALSE
       AND fn_situacao_sla(v.ticket_id) IN ('EM_ALERTA', 'VENCIDO')
     ORDER BY v.sla_em;
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_fim = TRUE;

  DROP TEMPORARY TABLE IF EXISTS tmp_alertas;
  CREATE TEMPORARY TABLE tmp_alertas (
    ticket_id   CHAR(36),
    situacao    VARCHAR(20),
    gestor      VARCHAR(120),
    email       VARCHAR(254),
    mensagem    VARCHAR(400),
    novo_alerta BOOLEAN
  );

  OPEN cur_alerta;
  laco: LOOP
    FETCH cur_alerta INTO v_ticket, v_situacao, v_horas, v_gestor, v_email, v_titulo;
    IF v_fim THEN
      LEAVE laco;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM historico_ticket h
                    WHERE h.ticket_id = v_ticket
                      AND h.evento = 'ALERTA_SLA'
                      AND h.criado_em >= NOW(3) - INTERVAL 24 HOUR) THEN
      INSERT INTO historico_ticket (evento, descricao, ticket_id)
      VALUES ('ALERTA_SLA', CONCAT('Alerta automático: SLA ', v_situacao, '.'), v_ticket);

      INSERT INTO tmp_alertas VALUES
        (v_ticket, v_situacao, v_gestor, v_email,
         CONCAT('[', v_situacao, '] "', LEFT(v_titulo, 40), '" - ',
                IF(v_horas < 0, CONCAT('vencido há ', -v_horas, ' h'),
                                CONCAT('vence em ', v_horas, ' h'))),
         TRUE);
    ELSE
      INSERT INTO tmp_alertas VALUES (v_ticket, v_situacao, v_gestor, v_email,
                                      'Já alertado nas últimas 24 h', FALSE);
    END IF;
  END LOOP laco;
  CLOSE cur_alerta;

  -- e-mails a enviar agora, agrupados por gestor
  SELECT email, gestor, COUNT(*) AS qtd_tickets,
         SUM(situacao = 'VENCIDO') AS vencidos,
         LEFT(GROUP_CONCAT(mensagem ORDER BY situacao DESC SEPARATOR ' | '), 110) AS mensagens
    FROM tmp_alertas
   WHERE novo_alerta
   GROUP BY email, gestor
   ORDER BY vencidos DESC, qtd_tickets DESC;
END$$

-- ---------------------------------------------------------------------
-- P5. sp_relatorio_sla_equipes(inicio, fim)
-- Problema: falta à liderança visibilidade em tempo real do desempenho
-- das equipes (desafio do projeto). Relatório por equipe no período:
-- tickets recebidos, encerrados, abertos, % SLA cumprido
-- (fn_taxa_cumprimento_sla_equipe), tempo médio de resolução
-- (fn_tempo_medio_resolucao_equipe) e comparação com a média geral
-- (subconsulta). LEFT JOIN + GROUP BY + HAVING (só equipes com tickets).
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_relatorio_sla_equipes(IN p_inicio DATE, IN p_fim DATE)
BEGIN
  IF p_inicio IS NULL OR p_fim IS NULL OR p_inicio > p_fim THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Período inválido.';
  END IF;

  SELECT e.nome                                          AS equipe,
         COUNT(t.id)                                     AS recebidos,
         SUM(t.status = 'ENCERRADO')                     AS encerrados,
         SUM(t.status <> 'ENCERRADO')                    AS abertos,
         fn_taxa_cumprimento_sla_equipe(e.id, p_inicio, p_fim) AS pct_sla_cumprido,
         fn_tempo_medio_resolucao_equipe(e.id)           AS horas_medias_resolucao,
         CASE
           WHEN fn_taxa_cumprimento_sla_equipe(e.id, p_inicio, p_fim) >=
                (SELECT 100 * SUM(t2.encerrado_em <= t2.sla_em) / COUNT(*)
                   FROM tickets t2
                  WHERE t2.status = 'ENCERRADO'
                    AND t2.criado_em >= p_inicio
                    AND t2.criado_em < DATE_ADD(p_fim, INTERVAL 1 DAY))
           THEN 'ACIMA DA MEDIA' ELSE 'ABAIXO DA MEDIA'
         END                                             AS comparacao_geral
    FROM equipes e
    LEFT JOIN ticket_equipes te ON te.equipe_id = e.id
    LEFT JOIN tickets t
           ON t.id = te.ticket_id
          AND t.criado_em >= p_inicio
          AND t.criado_em <  DATE_ADD(p_fim, INTERVAL 1 DAY)
   GROUP BY e.id, e.nome
  HAVING COUNT(t.id) > 0
   ORDER BY pct_sla_cumprido DESC, recebidos DESC;
END$$

-- ---------------------------------------------------------------------
-- P6. sp_ranking_tecnicos(equipe, dias)
-- Problema: o gestor quer saber quais técnicos estão produzindo e quais
-- estão sobrecarregados para distribuir as demandas (US 13). Ranking dos
-- técnicos (de uma equipe ou de todas, se NULL) nos últimos N dias:
-- relatórios, tickets atendidos, tickets abertos sob responsabilidade
-- (vw_produtividade_tecnicos) e se está acima da média de relatórios da
-- própria equipe (subconsulta derivada). RIGHT JOIN mantém técnicos sem
-- nenhum relatório no período.
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_ranking_tecnicos(IN p_equipe_id CHAR(36), IN p_dias INT)
BEGIN
  SET p_dias = COALESCE(p_dias, 30);

  SELECT RANK() OVER (ORDER BY COUNT(r.id) DESC)       AS posicao,
         u.nome                                         AS tecnico,
         e.nome                                         AS equipe,
         COUNT(r.id)                                    AS relatorios_periodo,
         COUNT(DISTINCT r.ticket_id)                    AS tickets_atendidos,
         vp.tickets_abertos_responsavel                 AS abertos_responsavel,
         ROUND(media.media_equipe, 1)                   AS media_equipe,
         IF(COUNT(r.id) >= media.media_equipe, 'SIM', 'NAO') AS acima_media
    FROM relatorios r
   RIGHT JOIN usuarios u
           ON u.id = r.autor_id
          AND r.criado_em >= NOW(3) - INTERVAL p_dias DAY
   INNER JOIN equipes e ON e.id = u.equipe_id
   INNER JOIN vw_produtividade_tecnicos vp ON vp.tecnico_id = u.id
   INNER JOIN (SELECT u2.equipe_id, COUNT(r2.id) / COUNT(DISTINCT u2.id) AS media_equipe
                 FROM usuarios u2
                 LEFT JOIN relatorios r2
                        ON r2.autor_id = u2.id
                       AND r2.criado_em >= NOW(3) - INTERVAL p_dias DAY
                WHERE u2.cargo = 'TECNICO' AND u2.ativo
                GROUP BY u2.equipe_id) media ON media.equipe_id = u.equipe_id
   WHERE u.cargo = 'TECNICO'
     AND u.ativo
     AND (p_equipe_id IS NULL OR u.equipe_id = p_equipe_id)
   GROUP BY u.id, u.nome, e.nome, vp.tickets_abertos_responsavel, media.media_equipe
   ORDER BY posicao, tecnico;
END$$

DELIMITER ;
