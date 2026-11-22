-- =====================================================================
-- BDR 2026.02 - 3ª Avaliação | Exemplos de execução (base dos "prints")
-- Rodar logo após 01..06 (banco recém-carregado). Cada bloco começa com
-- "-- @print <nome>"; scripts/gerar_prints.py separa os blocos, executa
-- cada um e salva a saída em docs/prints/<nome>.txt e .png.
-- Os erros esperados (SIGNAL) aparecem na saída: o mysql roda com --force.
-- =====================================================================

-- @print F1_fn_calcular_sla_em
USE bdr_api;
SELECT codigo AS prioridade, sla_horas,
       fn_calcular_sla_em(codigo, '2026-11-23 08:00:00') AS sla_para_abertura_23_11_08h
  FROM prioridades ORDER BY peso;
SELECT fn_calcular_sla_em('URGENTE', NOW());

-- @print F2_fn_situacao_sla
USE bdr_api;
SELECT fn_situacao_sla(id) AS situacao_sla, COUNT(*) AS tickets
  FROM tickets GROUP BY situacao_sla ORDER BY tickets DESC;
SELECT LEFT(titulo, 45) AS titulo, status, prioridade, sla_em, fn_situacao_sla(id) AS situacao_sla
  FROM tickets WHERE status <> 'ENCERRADO' ORDER BY sla_em LIMIT 8;

-- @print F3_fn_percentual_sla_consumido
USE bdr_api;
SELECT LEFT(titulo, 45) AS titulo, status, criado_em, sla_em,
       fn_percentual_sla_consumido(id) AS pct_consumido, fn_situacao_sla(id) AS situacao
  FROM tickets WHERE status <> 'ENCERRADO'
 ORDER BY pct_consumido DESC LIMIT 10;

-- @print F4_fn_tempo_medio_resolucao_equipe
USE bdr_api;
SELECT equipe, tickets_encerrados,
       fn_tempo_medio_resolucao_equipe(equipe_id) AS horas_medias_resolucao
  FROM vw_carga_equipes
 WHERE tickets_encerrados > 0
 ORDER BY horas_medias_resolucao LIMIT 10;

-- @print F5_fn_taxa_cumprimento_sla_equipe
USE bdr_api;
SELECT equipe,
       fn_taxa_cumprimento_sla_equipe(equipe_id, '2026-07-01', '2026-09-30') AS pct_sla_3T,
       fn_taxa_cumprimento_sla_equipe(equipe_id, '2026-10-01', '2026-11-30') AS pct_sla_out_nov
  FROM vw_carga_equipes
 ORDER BY pct_sla_out_nov DESC, equipe LIMIT 12;

-- @print F6_fn_sugerir_tecnico
USE bdr_api;
SELECT c.equipe, c.tecnicos_ativos, u.nome AS tecnico_sugerido,
       (SELECT COUNT(*) FROM tickets t
         WHERE t.responsavel_id = u.id AND t.status <> 'ENCERRADO') AS abertos_do_sugerido
  FROM vw_carga_equipes c
  LEFT JOIN usuarios u ON u.id = fn_sugerir_tecnico(c.equipe_id)
 ORDER BY c.tickets_abertos DESC LIMIT 10;

-- @print P1_sp_abrir_ticket
USE bdr_api;
SET @projeto = (SELECT p.id FROM projetos p JOIN clientes c ON c.id = p.cliente_id
                 WHERE p.ativo AND c.ativo ORDER BY p.nome, p.id LIMIT 1);
SET @suporte = (SELECT id FROM usuarios WHERE cargo = 'SUPORTE' AND ativo ORDER BY nome LIMIT 1);
CALL sp_abrir_ticket(@projeto, @suporte, 'Câmera da portaria sem imagem',
     'Câmera 03 da portaria principal sem imagem desde as 7h.', 'MANUTENCAO', 'ALTA', NULL, @novo);
SELECT @novo AS ticket_criado;
SELECT evento, descricao FROM historico_ticket WHERE ticket_id = @novo;
SELECT e.nome AS equipe_alocada FROM ticket_equipes te JOIN equipes e ON e.id = te.equipe_id WHERE te.ticket_id = @novo;
-- prazo escolhido na tela (como a API envia o slaEm): 3 h para um ticket ALTA
CALL sp_abrir_ticket(@projeto, @suporte, 'Leitor de crachá travado',
     'Leitor de crachá da catraca 2 não libera a passagem.', 'MANUTENCAO', 'ALTA',
     NOW(3) + INTERVAL 3 HOUR, @novo2);
-- erro esperado: prazo no passado
CALL sp_abrir_ticket(@projeto, @suporte, 'Teste de prazo inválido', 'x', 'MANUTENCAO', 'BAIXA',
     NOW(3) - INTERVAL 1 HOUR, @x);
-- erro esperado: técnico não pode abrir ticket
SET @tecnico = (SELECT id FROM usuarios WHERE cargo = 'TECNICO' AND ativo ORDER BY nome LIMIT 1);
CALL sp_abrir_ticket(@projeto, @tecnico, 'Teste de permissão', 'x', 'MANUTENCAO', 'BAIXA', NULL, @x);

-- @print P2_sp_decidir_encerramento
USE bdr_api;
SELECT t.id, p.gestor_id INTO @tk1, @gestor1 FROM tickets t JOIN projetos p ON p.id = t.projeto_id
 WHERE t.status = 'SOLICITACAO_ENCERRAMENTO' ORDER BY t.criado_em LIMIT 1;
SELECT t.id, p.gestor_id INTO @tk2, @gestor2 FROM tickets t JOIN projetos p ON p.id = t.projeto_id
 WHERE t.status = 'SOLICITACAO_ENCERRAMENTO' ORDER BY t.criado_em LIMIT 1 OFFSET 1;
CALL sp_decidir_encerramento(@tk1, @gestor1, TRUE, 'Serviço conferido com o cliente, aprovado.');
CALL sp_decidir_encerramento(@tk2, @gestor2, FALSE, 'Falta o relatório de testes finais.');
SELECT LEFT(h.evento, 22) AS evento, LEFT(h.descricao, 60) AS descricao, u.nome AS autor
  FROM historico_ticket h LEFT JOIN usuarios u ON u.id = h.usuario_id
 WHERE h.ticket_id IN (@tk1, @tk2) AND h.criado_em >= NOW() - INTERVAL 1 MINUTE;
-- erro esperado: o ticket já foi encerrado
CALL sp_decidir_encerramento(@tk1, @gestor1, TRUE, 'Aprovando de novo.');

-- @print P3_sp_desativar_tecnico_redistribuir
USE bdr_api;
SET @tec = (SELECT responsavel_id FROM tickets WHERE status <> 'ENCERRADO' AND responsavel_id IS NOT NULL
             GROUP BY responsavel_id ORDER BY COUNT(*) DESC, responsavel_id LIMIT 1);
SET @admin = (SELECT id FROM usuarios WHERE cargo = 'SUPORTE_INTERNO' ORDER BY criado_em LIMIT 1);
SELECT nome, ativo, (SELECT COUNT(*) FROM tickets WHERE responsavel_id = @tec AND status <> 'ENCERRADO') AS abertos
  FROM usuarios WHERE id = @tec;
CALL sp_desativar_tecnico_redistribuir(@tec, @admin);
SELECT nome, ativo FROM usuarios WHERE id = @tec;
SELECT tipo, descricao FROM atividades_conta WHERE usuario_id = @tec ORDER BY criado_em DESC LIMIT 1;

-- @print P4_sp_gerar_alertas_sla
USE bdr_api;
CALL sp_gerar_alertas_sla();
SELECT COUNT(*) AS eventos_alerta_gravados FROM historico_ticket WHERE evento = 'ALERTA_SLA';
-- segunda execução logo em seguida: nenhum e-mail novo (anti-spam de 24 h)
CALL sp_gerar_alertas_sla();

-- @print P5_sp_relatorio_sla_equipes
USE bdr_api;
CALL sp_relatorio_sla_equipes('2026-10-01', '2026-11-30');

-- @print P6_sp_ranking_tecnicos
USE bdr_api;
SET @eq = (SELECT u.equipe_id FROM relatorios r JOIN usuarios u ON u.id = r.autor_id
            WHERE u.equipe_id IS NOT NULL GROUP BY u.equipe_id ORDER BY COUNT(*) DESC LIMIT 1);
CALL sp_ranking_tecnicos(@eq, 60);
-- mesma equipe, só os últimos 7 dias
CALL sp_ranking_tecnicos(@eq, 7);

-- @print T1_trg_tickets_bi_validar
USE bdr_api;
SET @projeto = (SELECT p.id FROM projetos p JOIN clientes c ON c.id = p.cliente_id
                 WHERE p.ativo AND c.ativo ORDER BY p.nome DESC LIMIT 1);
SET @com = (SELECT id FROM usuarios WHERE cargo = 'COMERCIAL' AND ativo ORDER BY nome LIMIT 1);
-- sla_em = NULL: o trigger calcula pelo SLA padrão da prioridade CRITICA (8 h)
INSERT INTO tickets (id, titulo, descricao, categoria, prioridade, sla_em, projeto_id, aberto_por_id)
VALUES ('00000000-0000-4000-8000-000000000001', 'Queda total do link da torre', 'Sem comunicação com a torre 2.',
        'MANUTENCAO', 'CRITICA', NULL, @projeto, @com);
SELECT titulo, prioridade, status, criado_em, sla_em,
       TIMESTAMPDIFF(HOUR, criado_em, sla_em) AS horas_sla
  FROM tickets WHERE id = '00000000-0000-4000-8000-000000000001';
-- erro esperado: projeto inativo
SET @inativo = (SELECT id FROM projetos WHERE ativo = FALSE LIMIT 1);
INSERT INTO tickets (titulo, descricao, categoria, sla_em, projeto_id, aberto_por_id)
VALUES ('Ticket em projeto inativo', 'teste', 'MANUTENCAO', NULL, @inativo, @com);
-- erro esperado: ticket não nasce encerrado
INSERT INTO tickets (titulo, descricao, categoria, status, sla_em, projeto_id, aberto_por_id)
VALUES ('Ticket já encerrado', 'teste', 'MANUTENCAO', 'ENCERRADO', NULL, @projeto, @com);

-- @print T2_trg_tickets_bu_fluxo_status
USE bdr_api;
SET @enc = (SELECT id FROM tickets WHERE status = 'ENCERRADO' ORDER BY criado_em LIMIT 1);
SET @ni  = (SELECT id FROM tickets WHERE status = 'NAO_INICIADO' ORDER BY criado_em LIMIT 1);
SET @sol = (SELECT id FROM tickets WHERE status = 'SOLICITACAO_ENCERRAMENTO' ORDER BY criado_em LIMIT 1);
-- erro esperado: ticket encerrado não pode ser alterado
UPDATE tickets SET prioridade = 'CRITICA' WHERE id = @enc;
-- erro esperado: NAO_INICIADO -> ENCERRADO pula o fluxo
UPDATE tickets SET status = 'ENCERRADO' WHERE id = @ni;
-- transição válida: o trigger preenche encerrado_em
UPDATE tickets SET status = 'ENCERRADO' WHERE id = @sol;
SELECT status, encerrado_em, fn_situacao_sla(id) AS situacao_sla FROM tickets WHERE id = @sol;

-- @print T3_trg_tickets_au_historico
USE bdr_api;
SET @tk = (SELECT id FROM tickets WHERE status = 'EM_ANDAMENTO' ORDER BY criado_em DESC LIMIT 1);
SET @eq = (SELECT p.equipe_id FROM tickets t JOIN projetos p ON p.id = t.projeto_id WHERE t.id = @tk);
UPDATE tickets
   SET responsavel_id = fn_sugerir_tecnico(@eq),
       sla_em = sla_em + INTERVAL 24 HOUR
 WHERE id = @tk;
UPDATE tickets SET status = 'SOLICITACAO_ENCERRAMENTO' WHERE id = @tk;
SELECT evento, descricao FROM historico_ticket
 WHERE ticket_id = @tk AND usuario_id IS NULL ORDER BY criado_em, evento;

-- @print T4_trg_relatorios_bi_validar_autor
USE bdr_api;
SET @tk = (SELECT id FROM tickets WHERE status = 'EM_ANDAMENTO' ORDER BY criado_em LIMIT 1);
-- técnico ativo de uma equipe que NÃO está alocada no ticket
SET @fora = (SELECT u.id FROM usuarios u WHERE u.cargo = 'TECNICO' AND u.ativo AND u.equipe_id IS NOT NULL
               AND u.equipe_id NOT IN (SELECT equipe_id FROM ticket_equipes WHERE ticket_id = @tk)
             ORDER BY u.nome LIMIT 1);
INSERT INTO relatorios (trabalho_realizado, materiais_utilizados, outros_detalhes, ticket_id, autor_id)
VALUES ('Tentativa de relatório por técnico de fora.', '-', '-', @tk, @fora);
-- erro esperado: ticket encerrado
SET @enc = (SELECT t.id FROM tickets t WHERE t.status = 'ENCERRADO' ORDER BY t.criado_em LIMIT 1);
SET @dentro = (SELECT u.id FROM usuarios u JOIN ticket_equipes te ON te.equipe_id = u.equipe_id
                WHERE te.ticket_id = @enc AND u.ativo AND u.cargo = 'TECNICO' LIMIT 1);
INSERT INTO relatorios (trabalho_realizado, materiais_utilizados, outros_detalhes, ticket_id, autor_id)
VALUES ('Relatório em ticket já encerrado.', '-', '-', @enc, @dentro);
SELECT COUNT(*) AS relatorios_gravados_nos_testes FROM relatorios WHERE criado_em >= NOW() - INTERVAL 1 MINUTE;

-- @print T5_trg_relatorios_ai_inicio_atividade
USE bdr_api;
SELECT t.id, u.id INTO @tk, @tec
  FROM tickets t
  JOIN ticket_equipes te ON te.ticket_id = t.id
  JOIN usuarios u ON u.equipe_id = te.equipe_id AND u.cargo = 'TECNICO' AND u.ativo
 WHERE t.status = 'NAO_INICIADO' ORDER BY t.criado_em, u.nome LIMIT 1;
SELECT status FROM tickets WHERE id = @tk;
INSERT INTO relatorios (trabalho_realizado, materiais_utilizados, outros_detalhes, ticket_id, autor_id)
VALUES ('Diagnóstico inicial: fonte do equipamento queimada, substituída.', '1 fonte 12V 5A',
        'Retorno amanhã para teste final.', @tk, @tec);
SELECT status FROM tickets WHERE id = @tk;
SELECT evento, LEFT(descricao, 70) AS descricao FROM historico_ticket
 WHERE ticket_id = @tk AND criado_em >= NOW() - INTERVAL 1 MINUTE AND evento <> 'ALERTA_SLA'
 ORDER BY criado_em, evento;
SELECT tipo, descricao FROM atividades_conta WHERE usuario_id = @tec ORDER BY criado_em DESC LIMIT 1;

-- @print T6_trg_usuarios_au_auditoria
USE bdr_api;
SET @u = (SELECT id FROM usuarios WHERE cargo = 'TECNICO' AND equipe_id IS NULL ORDER BY nome LIMIT 1);
SET @eq = (SELECT id FROM equipes WHERE ativo ORDER BY nome LIMIT 1);
UPDATE usuarios SET equipe_id = @eq WHERE id = @u;
UPDATE usuarios SET senha_hash = '$2b$10$novaSenhaProvisoriaHashFicticio000000000000000000000', senha_provisoria = TRUE WHERE id = @u;
UPDATE usuarios SET ativo = FALSE WHERE id = @u;
UPDATE usuarios SET ativo = TRUE, cargo = 'GESTOR' WHERE id = @u;
SELECT tipo, descricao FROM atividades_conta WHERE usuario_id = @u ORDER BY criado_em, descricao;
