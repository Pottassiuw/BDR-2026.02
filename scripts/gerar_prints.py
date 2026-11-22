#!/usr/bin/env python3
"""Executa cada bloco "-- @print <nome>" de sql/07_exemplos.sql e salva a saída
do cliente mysql em docs/prints/<nome>.txt e docs/prints/<nome>.png.

Uso: MYSQL="mysql -uroot -h127.0.0.1 -P3399" python3 scripts/gerar_prints.py
(o banco deve ter acabado de ser criado com scripts/rodar_tudo.sh)
"""
import os
import re
import shlex
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
MYSQL = shlex.split(os.environ.get("MYSQL", "mysql -uroot -p"))
FONTE = "/usr/share/fonts/TTF/DejaVuSansMono.ttf"
SAIDA = RAIZ / "docs" / "prints"
SAIDA.mkdir(parents=True, exist_ok=True)

texto = (RAIZ / "sql" / "07_exemplos.sql").read_text(encoding="utf-8")
blocos = re.split(r"^-- @print (\S+)\s*$", texto, flags=re.M)[1:]


def png(nome, conteudo):
    fonte = ImageFont.truetype(FONTE, 14)
    titulo = ImageFont.truetype(FONTE, 16)
    linhas = conteudo.rstrip("\n").split("\n")
    larg_c = fonte.getlength("M")
    alt_l = 18
    w = int(max(900, 40 + larg_c * max(len(l) for l in linhas)))
    h = 60 + alt_l * len(linhas) + 20
    img = Image.new("RGB", (w, h), (30, 30, 36))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 36], fill=(52, 52, 62))
    for i, cor in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([14 + i * 22, 11, 28 + i * 22, 25], fill=cor)
    d.text((90, 9), f"mysql 8.0 — bdr_api — {nome}", font=titulo, fill=(220, 220, 220))
    y = 50
    for l in linhas:
        cor = (230, 230, 230)
        if l.startswith("ERROR"):
            cor = (255, 120, 120)
        elif l.startswith("--------------") or l.startswith("CALL") or l.startswith("SELECT") \
                or l.startswith("INSERT") or l.startswith("UPDATE") or l.startswith("SET"):
            cor = (140, 200, 255)
        d.text((20, y), l, font=fonte, fill=cor)
        y += alt_l
    img.save(SAIDA / f"{nome}.png")


for nome, sql in zip(blocos[0::2], blocos[1::2]):
    # remove linhas de comentário para a saída ficar limpa
    sql_exec = "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--"))
    # --unbuffered + stderr no stdout: cada ERROR aparece logo após o comando que o gerou
    r = subprocess.run(MYSQL + ["--force", "--unbuffered", "-t", "-vvv", "--default-character-set=utf8mb4"],
                       input=sql_exec, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    erros = [l for l in r.stdout.splitlines() if l.startswith("ERROR")]
    saida_final = r.stdout.replace("\nBye\n", "\n").rstrip() + "\n"
    (SAIDA / f"{nome}.txt").write_text(saida_final, encoding="utf-8")
    png(nome, saida_final)
    print(f"{nome}: {len(saida_final.splitlines())} linhas, {len(erros)} erro(s) esperado(s)")
