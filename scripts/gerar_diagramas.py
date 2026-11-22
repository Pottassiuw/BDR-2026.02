#!/usr/bin/env python3
"""Desenha modelos/modelo-conceitual.png (notação de Peter Chen, estilo brModelo)
e modelos/modelo-logico.png (tabelas com PK/FK). Uso: python3 scripts/gerar_diagramas.py"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
F = "/usr/share/fonts/TTF/DejaVuSans.ttf"
FB = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
FM = "/usr/share/fonts/TTF/DejaVuSansMono.ttf"
font = ImageFont.truetype(F, 15)
font_s = ImageFont.truetype(F, 13)
font_b = ImageFont.truetype(FB, 16)
font_m = ImageFont.truetype(FM, 13)
font_t = ImageFont.truetype(FB, 26)

PRETO = (20, 20, 20)
AZUL = (40, 90, 160)


def clip(rect, p_from):
    """Ponto na borda do retângulo na direção de p_from."""
    x0, y0, x1, y1 = rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = p_from[0] - cx, p_from[1] - cy
    if dx == 0 and dy == 0:
        return cx, cy
    hw, hh = (x1 - x0) / 2, (y1 - y0) / 2
    t = min(hw / abs(dx) if dx else 1e9, hh / abs(dy) if dy else 1e9)
    return cx + dx * t, cy + dy * t


def lerp(a, b, t):
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


# =====================================================================
# MODELO CONCEITUAL
# =====================================================================
ENT = {
    # nome: (cx, cy, [atributos]) ; "*" = identificador
    "CARGO": (1080, 150, ["*codigo", "nome", "descricao", "pode_abrir_ticket", "pode_aprovar_encerramento"]),
    "USUARIO": (1080, 470, ["*id", "nome", "email (único)", "senha_hash", "ativo", "senha_provisoria",
                            "criado_em", "atualizado_em"]),
    "ATIVIDADE_CONTA": (1700, 470, ["*id", "tipo", "descricao", "criado_em"]),
    "EQUIPE": (560, 470, ["*id", "nome (único)", "descricao", "ativo", "criado_em", "atualizado_em"]),
    "PROJETO": (220, 900, ["*id", "nome", "local_instalacao", "descricao", "ativo", "criado_em",
                           "atualizado_em"]),
    "CLIENTE": (220, 1300, ["*id", "nome (único)", "ativo", "criado_em", "atualizado_em"]),
    "TICKET": (1080, 1100, ["*id", "titulo", "descricao", "categoria", "sla_em", "encerrado_em",
                            "criado_em", "atualizado_em"]),
    "PRIORIDADE": (1700, 880, ["*codigo", "nome", "peso", "sla_horas", "alerta_horas"]),
    "STATUS_TICKET": (1700, 1160, ["*codigo", "nome", "descricao", "finalizado", "ordem"]),
    "RELATORIO": (1700, 1450, ["*id", "trabalho_realizado", "materiais_utilizados", "outros_detalhes",
                               "criado_em", "atualizado_em"]),
    "HISTORICO_TICKET": (1080, 1600, ["*id", "evento", "descricao", "criado_em"]),
}

# (entA, entB, verbo, cardA, cardB, losango (x,y) ou None, atributos, pontos A->losango, pontos losango->B)
REL = [
    ("USUARIO", "CARGO", "possui", "(0,n)", "(1,1)", None, [], [], []),
    ("USUARIO", "ATIVIDADE_CONTA", "realiza", "(1,1)", "(0,n)", None, [], [], []),
    ("USUARIO", "EQUIPE", "pertence", "(0,n)", "(0,1)", None, [], [], []),
    ("EQUIPE", "PROJETO", "atende", "(1,1)", "(0,n)", (220, 620), [], [], []),
    ("CLIENTE", "PROJETO", "contrata", "(1,1)", "(0,n)", None, [], [], []),
    ("USUARIO", "PROJETO", "gerencia", "(1,1)", "(0,n)", (560, 720), [], [], []),
    ("PROJETO", "TICKET", "gera", "(1,1)", "(0,n)", (640, 1010), [], [], []),
    ("USUARIO", "TICKET", "abre", "(1,1)", "(0,n)", (970, 790), [], [], []),
    ("USUARIO", "TICKET", "responsável", "(0,1)", "(0,n)", (1210, 790), [], [], []),
    ("TICKET", "EQUIPE", "alocada", "(1,n)", "(0,n)", (800, 840), ["criado_em"], [], []),
    ("TICKET", "PRIORIDADE", "classifica", "(0,n)", "(1,1)", (1410, 990), [], [], []),
    ("TICKET", "STATUS_TICKET", "está em", "(0,n)", "(1,1)", (1410, 1130), [], [], []),
    ("TICKET", "RELATORIO", "possui", "(1,1)", "(0,n)", (1410, 1290), [], [], []),
    ("USUARIO", "RELATORIO", "escreve", "(1,1)", "(0,n)", (1980, 1000), [], [(1980, 610)], []),
    ("TICKET", "HISTORICO_TICKET", "registra", "(1,1)", "(0,n)", None, [], [], []),
    ("USUARIO", "HISTORICO_TICKET", "é autor", "(0,1)", "(0,n)", (900, 1420), [], [], []),
    ("EQUIPE", "HISTORICO_TICKET", "equipe do autor", "(0,1)", "(0,n)", (480, 1560),
     [], [(60, 462), (60, 1560)], []),
    ("EQUIPE", "HISTORICO_TICKET", "inicia atividade", "(0,1)", "(0,n)", (600, 1700),
     [], [(40, 478), (40, 1700)], [(1040, 1700)]),
]


def conceitual():
    W, H = 2720, 1820
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 25), "Modelo Conceitual — bdr_api (Sistema de Tickets / Ordens de Serviço)", font=font_t, fill=PRETO)
    d.text((40, 62), "Notação de Chen (brModelo): retângulo = entidade, losango = relacionamento, "
                     "cardinalidade (mín,máx). Atributos no quadro à direita (● = identificador).",
           font=font_s, fill=(90, 90, 90))

    rects = {}
    for nome, (cx, cy, attrs) in ENT.items():
        w = max(d.textlength(nome, font=font_b) + 40, 190)
        h = 40
        rects[nome] = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

    def losango(c, txt):
        w = d.textlength(txt, font=font) + 46
        h = 46
        cx, cy = c
        pts = [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)]
        return pts, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

    def desenha_losango(c, txt):
        pts, lr = losango(c, txt)
        d.polygon(pts, outline=PRETO, fill=(255, 250, 225))
        d.text(c, txt, font=font, fill=PRETO, anchor="mm")
        return lr

    # autorrelacionamento USUARIO cria USUARIO
    ux0, uy0, ux1, uy1 = rects["USUARIO"]
    cria = (1330, 330)
    _, lr = losango(cria, "cria")
    d.line([(ux1 - 60, uy0), (ux1 - 60, cria[1]), (lr[0], cria[1])], fill=PRETO, width=2)
    d.line([(lr[2], cria[1]), (1440, cria[1]), (1440, 405), (ux1 - 15, 405), (ux1 - 15, uy0)], fill=PRETO, width=2)
    desenha_losango(cria, "cria")
    d.text((ux1 - 54, cria[1] + 30), "(0,1) criador", font=font_s, fill=AZUL)
    d.text((1300, 410), "(0,n) criado", font=font_s, fill=AZUL)

    lrs = []
    for a, b, verbo, ca, cb, pos, rattrs, via_a, via_b in REL:
        ra, rb = rects[a], rects[b]
        ca_c = ((ra[0] + ra[2]) / 2, (ra[1] + ra[3]) / 2)
        cb_c = ((rb[0] + rb[2]) / 2, (rb[1] + rb[3]) / 2)
        c = pos or lerp(ca_c, cb_c, 0.5)
        _, lr = losango(c, verbo)
        ca_alvo = via_a[0] if via_a else c
        cb_alvo = via_b[-1] if via_b else c
        if via_a and ra[1] <= via_a[0][1] <= ra[3]:  # saída horizontal pela lateral
            pa = (ra[0], via_a[0][1]) if via_a[0][0] < ra[0] else (ra[2], via_a[0][1])
        else:
            pa = clip(ra, ca_alvo)
        pb = clip(rb, cb_alvo)
        cam_a = [pa] + via_a
        cam_b = via_b + [pb]
        da = clip(lr, cam_a[-1])
        db = clip(lr, cam_b[0])
        d.line(cam_a + [da], fill=PRETO, width=2)
        d.line([db] + cam_b, fill=PRETO, width=2)
        lrs.append((c, verbo, lr, rattrs))
        for p, other, card in ((pa, (cam_a + [da])[1], ca), (pb, ([db] + cam_b)[-2], cb)):
            q = lerp(p, other, 0.18 if abs(other[0] - p[0]) + abs(other[1] - p[1]) > 200 else 0.35)
            d.text((q[0] + 6, q[1] - 16), card, font=font_s, fill=AZUL)
    for c, verbo, lr, rattrs in lrs:
        desenha_losango(c, verbo)
        for i, at in enumerate(rattrs):
            ax, ay = c[0] + 10, lr[3] + 14 + i * 18
            d.line([(c[0], lr[3]), (ax, ay)], fill=PRETO)
            d.ellipse([ax - 5, ay - 5, ax + 5, ay + 5], outline=PRETO, fill="white")
            d.text((ax + 9, ay), at, font=font_s, fill=PRETO, anchor="lm")

    for nome, (cx, cy, attrs) in ENT.items():
        d.rectangle(rects[nome], outline=PRETO, width=2, fill=(230, 240, 255))
        d.text((cx, cy), nome, font=font_b, fill=PRETO, anchor="mm")

    # quadro de atributos
    px, py = 2130, 110
    d.rectangle([px - 20, py - 15, W - 30, H - 40], outline=(150, 150, 150), fill=(250, 250, 250))
    d.text((px, py), "Atributos das entidades", font=font_b, fill=PRETO)
    py += 30
    for nome, (cx, cy, attrs) in ENT.items():
        d.text((px, py), nome, font=font_b, fill=(40, 70, 120))
        py += 21
        for at in attrs:
            ident = at.startswith("*")
            y = py + 8
            if ident:
                d.ellipse([px + 8, y - 5, px + 18, y + 5], fill=PRETO)
            else:
                d.ellipse([px + 8, y - 5, px + 18, y + 5], outline=PRETO, fill="white")
            d.text((px + 26, y), at.lstrip("*"), font=font_s, fill=PRETO, anchor="lm")
            py += 17
        py += 8
    img.save(RAIZ / "modelos" / "modelo-conceitual.png")


# =====================================================================
# MODELO LÓGICO
# =====================================================================
TAB = {
    "cargos": (60, 120, [("codigo", "ENUM", "PK"), ("nome", "VARCHAR(60)", "UQ"), ("descricao", "VARCHAR(255)", ""),
                         ("pode_abrir_ticket", "BOOLEAN", ""), ("pode_aprovar_encerramento", "BOOLEAN", "")]),
    "usuarios": (560, 120, [("id", "CHAR(36)", "PK"), ("nome", "VARCHAR(120)", ""), ("email", "VARCHAR(254)", "UQ"),
                            ("senha_hash", "VARCHAR(255)", ""), ("cargo", "ENUM", "FK"), ("ativo", "BOOLEAN", ""),
                            ("senha_provisoria", "BOOLEAN", ""), ("criado_em", "DATETIME(3)", ""),
                            ("atualizado_em", "DATETIME(3)", ""), ("equipe_id", "CHAR(36)", "FK"),
                            ("criado_por_id", "CHAR(36)", "FK")]),
    "atividades_conta": (1100, 120, [("id", "CHAR(36)", "PK"), ("tipo", "VARCHAR(20)", ""), ("descricao", "TEXT", ""),
                                     ("criado_em", "DATETIME(3)", ""), ("usuario_id", "CHAR(36)", "FK")]),
    "equipes": (60, 520, [("id", "CHAR(36)", "PK"), ("nome", "VARCHAR(100)", "UQ"), ("descricao", "VARCHAR(255)", ""),
                          ("ativo", "BOOLEAN", ""), ("criado_em", "DATETIME(3)", ""), ("atualizado_em", "DATETIME(3)", "")]),
    "clientes": (60, 1220, [("id", "CHAR(36)", "PK"), ("nome", "VARCHAR(150)", "UQ"), ("ativo", "BOOLEAN", ""),
                            ("criado_em", "DATETIME(3)", ""), ("atualizado_em", "DATETIME(3)", "")]),
    "projetos": (60, 840, [("id", "CHAR(36)", "PK"), ("nome", "VARCHAR(150)", "UQ*"), ("local_instalacao", "VARCHAR(255)", ""),
                           ("descricao", "TEXT", ""), ("ativo", "BOOLEAN", ""), ("criado_em", "DATETIME(3)", ""),
                           ("atualizado_em", "DATETIME(3)", ""), ("cliente_id", "CHAR(36)", "FK,UQ*"),
                           ("equipe_id", "CHAR(36)", "FK"), ("gestor_id", "CHAR(36)", "FK")]),
    "ticket_equipes": (560, 640, [("id", "CHAR(36)", "PK"), ("criado_em", "DATETIME(3)", ""),
                                  ("ticket_id", "CHAR(36)", "FK,UQ*"), ("equipe_id", "CHAR(36)", "FK,UQ*")]),
    "tickets": (560, 880, [("id", "CHAR(36)", "PK"), ("titulo", "VARCHAR(180)", ""), ("descricao", "TEXT", ""),
                           ("categoria", "ENUM", ""), ("prioridade", "ENUM", "FK"), ("status", "ENUM", "FK"),
                           ("sla_em", "DATETIME(3)", ""), ("encerrado_em", "DATETIME(3)", "NULL"),
                           ("criado_em", "DATETIME(3)", ""), ("atualizado_em", "DATETIME(3)", ""),
                           ("projeto_id", "CHAR(36)", "FK"), ("aberto_por_id", "CHAR(36)", "FK"),
                           ("responsavel_id", "CHAR(36)", "FK")]),
    "prioridades": (1100, 560, [("codigo", "ENUM", "PK"), ("nome", "VARCHAR(30)", ""), ("peso", "TINYINT", "UQ"),
                                ("sla_horas", "SMALLINT", ""), ("alerta_horas", "SMALLINT", "")]),
    "status_ticket": (1100, 820, [("codigo", "ENUM", "PK"), ("nome", "VARCHAR(40)", ""), ("descricao", "VARCHAR(255)", ""),
                                  ("finalizado", "BOOLEAN", ""), ("ordem", "TINYINT", "UQ")]),
    "relatorios": (1100, 1080, [("id", "CHAR(36)", "PK"), ("trabalho_realizado", "TEXT", ""),
                                ("materiais_utilizados", "TEXT", ""), ("outros_detalhes", "TEXT", ""),
                                ("criado_em", "DATETIME(3)", ""), ("atualizado_em", "DATETIME(3)", ""),
                                ("ticket_id", "CHAR(36)", "FK"), ("autor_id", "CHAR(36)", "FK")]),
    "historico_ticket": (560, 1300, [("id", "CHAR(36)", "PK"), ("evento", "VARCHAR(50)", ""), ("descricao", "TEXT", ""),
                                     ("criado_em", "DATETIME(3)", ""), ("ticket_id", "CHAR(36)", "FK,UQ*"),
                                     ("usuario_id", "CHAR(36)", "FK"), ("equipe_id", "CHAR(36)", "FK"),
                                     ("inicio_equipe_id", "CHAR(36)", "FK,UQ*")]),
}
# (tabela_filha, coluna, tabela_pai)
FKS = [
    ("usuarios", "cargo", "cargos"), ("usuarios", "equipe_id", "equipes"), ("usuarios", "criado_por_id", "usuarios"),
    ("atividades_conta", "usuario_id", "usuarios"),
    ("projetos", "cliente_id", "clientes"), ("projetos", "equipe_id", "equipes"), ("projetos", "gestor_id", "usuarios"),
    ("tickets", "prioridade", "prioridades"), ("tickets", "status", "status_ticket"),
    ("tickets", "projeto_id", "projetos"), ("tickets", "aberto_por_id", "usuarios"),
    ("tickets", "responsavel_id", "usuarios"),
    ("ticket_equipes", "ticket_id", "tickets"), ("ticket_equipes", "equipe_id", "equipes"),
    ("relatorios", "ticket_id", "tickets"), ("relatorios", "autor_id", "usuarios"),
    ("historico_ticket", "ticket_id", "tickets"), ("historico_ticket", "usuario_id", "usuarios"),
    ("historico_ticket", "equipe_id", "equipes"), ("historico_ticket", "inicio_equipe_id", "equipes"),
]
CORES = [(200, 60, 60), (40, 120, 200), (40, 150, 80), (160, 90, 200), (220, 130, 30), (30, 150, 160),
         (120, 120, 40), (200, 80, 150)]


def logico():
    W, H = 1560, 1560
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 25), "Modelo Lógico Relacional — bdr_api (MySQL 8)", font=font_t, fill=PRETO)
    d.text((40, 62), "PK = chave primária · FK = chave estrangeira · UQ = único · UQ* = único composto · "
                     "linhas: FK (filha, lado N) → PK (pai, lado 1)", font=font_s, fill=(90, 90, 90))
    LW, RH = 400, 20
    geo = {}
    for nome, (x, y, cols) in TAB.items():
        h = 30 + RH * len(cols) + 6
        geo[nome] = (x, y, x + LW, y + h)
    # linhas primeiro
    for i, (filha, col, pai) in enumerate(FKS):
        x0, y0, x1, y1 = geo[filha]
        cols = [c[0] for c in TAB[filha][2]]
        yr = y0 + 30 + RH * cols.index(col) + RH / 2
        px0, py0, px1, py1 = geo[pai]
        ypk = py0 + 30 + RH / 2
        cor = CORES[i % len(CORES)]
        if filha == pai:
            d.line([(x1, yr), (x1 + 25, yr), (x1 + 25, ypk), (x1, ypk)], fill=cor, width=2)
            d.text((x1 + 28, (yr + ypk) / 2), "N:1", font=font_s, fill=cor)
            continue
        # sai pelo lado mais próximo
        if px0 >= x1:
            a, b = (x1, yr), (px0, ypk)
        elif px1 <= x0:
            a, b = (x0, yr), (px1, ypk)
        else:
            a, b = (x1, yr), (px1, ypk)
            mx = max(x1, px1) + 30 + 8 * (i % 4)
            d.line([a, (mx, a[1]), (mx, b[1]), b], fill=cor, width=2)
            d.text((a[0] + 4, a[1] - 16), "N", font=font_s, fill=cor)
            d.text((b[0] + 4, b[1] - 16), "1", font=font_s, fill=cor)
            continue
        mx = (a[0] + b[0]) / 2 + (i % 5 - 2) * 9
        d.line([a, (mx, a[1]), (mx, b[1]), b], fill=cor, width=2)
        d.text((a[0] + (6 if a[0] < mx else -16), a[1] - 16), "N", font=font_s, fill=cor)
        d.text((b[0] + (-16 if b[0] > mx else 6), b[1] - 16), "1", font=font_s, fill=cor)
    for nome, (x, y, cols) in TAB.items():
        x0, y0, x1, y1 = geo[nome]
        d.rectangle([x0, y0, x1, y1], outline=PRETO, width=2, fill="white")
        d.rectangle([x0, y0, x1, y0 + 28], fill=(40, 70, 120))
        d.text((x0 + 10, y0 + 14), nome, font=font_b, fill="white", anchor="lm")
        for i, (c, t, k) in enumerate(cols):
            yy = y0 + 30 + RH * i + RH / 2
            cor = (170, 20, 20) if "PK" in k else (20, 80, 170) if "FK" in k else PRETO
            d.text((x0 + 10, yy), ("🔑 " if False else "") + c, font=font_m, fill=cor, anchor="lm")
            d.text((x0 + 215, yy), t, font=font_m, fill=(80, 80, 80), anchor="lm")
            d.text((x1 - 8, yy), k, font=font_m, fill=cor, anchor="rm")
    img.save(RAIZ / "modelos" / "modelo-logico.png")


if __name__ == "__main__":
    (RAIZ / "modelos").mkdir(exist_ok=True)
    conceitual()
    logico()
    print("ok")
