#!/usr/bin/env python3
"""Gera docs/prints/parte5/*.png a partir dos .txt produzidos por scripts/demo_parte5.sh
(mesmo visual dos prints da Parte 3; JSON das respostas é indentado para caber na imagem).

Uso: python3 scripts/gerar_prints_parte5.py   (requer Pillow)
"""
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "docs" / "prints" / "parte5"
FONTE = "/usr/share/fonts/TTF/DejaVuSansMono.ttf"
LARGURA_MAX = 170


def formatar(texto):
    saida = []
    for linha in texto.rstrip("\n").split("\n"):
        if linha.strip() == "--------------":
            continue
        bruto = linha[len("Corpo: "):] if linha.startswith("Corpo: ") else linha
        try:
            obj = json.loads(bruto)
            if isinstance(obj, (dict, list)):
                if linha.startswith("Corpo: "):
                    saida.append("Corpo:")
                saida.extend(json.dumps(obj, ensure_ascii=False, indent=2).split("\n"))
                continue
        except ValueError:
            pass
        saida.extend(textwrap.wrap(linha, LARGURA_MAX, drop_whitespace=False) or [""])
    return saida


def png(nome, linhas):
    fonte = ImageFont.truetype(FONTE, 14)
    titulo = ImageFont.truetype(FONTE, 16)
    larg_c = fonte.getlength("M")
    alt_l = 18
    w = int(max(900, 40 + larg_c * max(len(l) for l in linhas)))
    h = 60 + alt_l * len(linhas) + 20
    img = Image.new("RGB", (w, h), (30, 30, 36))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 36], fill=(52, 52, 62))
    for i, cor in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([14 + i * 22, 11, 28 + i * 22, 25], fill=cor)
    d.text((90, 9), f"API -> bdr_api — {nome}", font=titulo, fill=(220, 220, 220))
    y = 50
    for l in linhas:
        cor = (230, 230, 230)
        if l.startswith("###"):
            cor = (255, 210, 120)
        elif l.startswith("HTTP 4") or l.startswith("HTTP 5") or '"erro"' in l:
            cor = (255, 120, 120)
        elif l.startswith("HTTP 2") or "situacao" in l.lower():
            cor = (120, 230, 140)
        elif l.startswith(("SELECT", "SET", " WHERE", "  FROM")):
            cor = (140, 200, 255)
        d.text((20, y), l, font=fonte, fill=cor)
        y += alt_l
    img.save(PASTA / f"{nome}.png")


for txt in sorted(PASTA.glob("0*.txt")):
    png(txt.stem, formatar(txt.read_text(encoding="utf-8")))
    print("ok", txt.stem)
