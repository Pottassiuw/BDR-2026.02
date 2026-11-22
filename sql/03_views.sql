-- =====================================================================
-- BDR 2026.02 - 3ª Avaliação | Parte 3 - Views
-- As views concentram junções usadas pelas functions/procedures e pelas
-- telas da API (fila de tickets, carga por equipe, produtividade).
-- =====================================================================
USE bdr_api;

-- ---------------------------------------------------------------------
-- vw_tickets_detalhados
-- Fila de tickets "pronta para tela": junta ticket, projeto, cliente,
-- equipe do projeto, quem abriu (INNER JOIN) e responsável (LEFT JOIN,
-- pois o ticket pode não ter responsável). Traz o peso da prioridade
-- (para ordenar a fila) e as horas que faltam para o SLA.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_tickets_detalhados AS
SELECT t.id                    AS ticket_id,
       t.titulo,
       t.categoria,
       t.prioridade,
       pr.peso                 AS peso_prioridade,
       t.status,
       st.finalizado,
       t.criado_em,
       t.sla_em,
       t.encerrado_em,
       ROUND(TIMESTAMPDIFF(MINUTE, NOW(), t.sla_em) / 60, 1) AS horas_para_sla,
       p.id                    AS projeto_id,
       p.nome                  AS projeto,
       c.nome                  AS cliente,
       e.id                    AS equipe_id,
       e.nome                  AS equipe_projeto,
       g.nome                  AS gestor,
       g.email                 AS email_gestor,
       ab.nome                 AS aberto_por,
       r.id                    AS responsavel_id,
       r.nome                  AS responsavel
FROM tickets t
INNER JOIN prioridades   pr ON pr.codigo = t.prioridade
INNER JOIN status_ticket st ON st.codigo = t.status
INNER JOIN projetos      p  ON p.id  = t.projeto_id
INNER JOIN clientes      c  ON c.id  = p.cliente_id
INNER JOIN equipes       e  ON e.id  = p.equipe_id
INNER JOIN usuarios      g  ON g.id  = p.gestor_id
INNER JOIN usuarios      ab ON ab.id = t.aberto_por_id
LEFT  JOIN usuarios      r  ON r.id  = t.responsavel_id;

-- ---------------------------------------------------------------------
-- vw_carga_equipes
-- Quantos tickets cada equipe tem alocados, por situação. Usa LEFT JOIN
-- para listar também equipes sem nenhum ticket, GROUP BY e funções de
-- grupo (COUNT/SUM) e uma subconsulta escalar para contar técnicos ativos.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_carga_equipes AS
SELECT e.id   AS equipe_id,
       e.nome AS equipe,
       e.ativo,
       (SELECT COUNT(*) FROM usuarios u
         WHERE u.equipe_id = e.id AND u.cargo = 'TECNICO' AND u.ativo) AS tecnicos_ativos,
       COUNT(t.id)                                          AS total_tickets,
       COALESCE(SUM(t.status <> 'ENCERRADO'), 0)            AS tickets_abertos,
       COALESCE(SUM(t.status <> 'ENCERRADO' AND t.sla_em < NOW()), 0) AS abertos_sla_vencido,
       COALESCE(SUM(t.status = 'ENCERRADO'), 0)             AS tickets_encerrados
FROM equipes e
LEFT JOIN ticket_equipes te ON te.equipe_id = e.id
LEFT JOIN tickets        t  ON t.id = te.ticket_id
GROUP BY e.id, e.nome, e.ativo;

-- ---------------------------------------------------------------------
-- vw_produtividade_tecnicos
-- Produção de cada técnico: relatórios escritos, tickets atendidos e
-- tickets dos quais é responsável. RIGHT JOIN a partir de usuarios para
-- manter técnicos que ainda não escreveram nenhum relatório.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_produtividade_tecnicos AS
SELECT u.id                               AS tecnico_id,
       u.nome                             AS tecnico,
       u.ativo,
       e.nome                             AS equipe,
       COUNT(rel.id)                      AS relatorios,
       COUNT(DISTINCT rel.ticket_id)      AS tickets_atendidos,
       MAX(rel.criado_em)                 AS ultimo_relatorio,
       (SELECT COUNT(*) FROM tickets t
         WHERE t.responsavel_id = u.id AND t.status <> 'ENCERRADO') AS tickets_abertos_responsavel
FROM relatorios rel
RIGHT JOIN usuarios u ON u.id = rel.autor_id
LEFT  JOIN equipes  e ON e.id = u.equipe_id
WHERE u.cargo = 'TECNICO'
GROUP BY u.id, u.nome, u.ativo, e.nome;
