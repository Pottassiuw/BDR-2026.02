#!/usr/bin/env python3
"""Gera os arquivos para entregar no Teams, em docs/entrega/:
  Documento-BDR-3a-avaliacao.docx / .pdf   (a partir de docs/documento.md)
  Dicionario-de-Dados.docx / .pdf          (a partir de docs/dicionario-de-dados.md)

Requer: pandoc (>= 3), python-docx e weasyprint.
Uso: PANDOC=/caminho/pandoc python3 scripts/gerar_entrega.py
"""
import os
import re
import subprocess
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from weasyprint import HTML

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
SAIDA = DOCS / "entrega"
PANDOC = os.environ.get("PANDOC", "pandoc")
TMP = Path(tempfile.mkdtemp(prefix="entrega_"))

CAPA = {
    "instituicao": "Faculdade de Tecnologia de São José dos Campos — Prof. Jessen Vidal",
    "sigla": "FATEC SJC",
    "disciplina": "Banco de Dados Relacional",
    "avaliacao": "3ª Avaliação — 2º semestre de 2026",
    "local": "São José dos Campos, 23 de novembro de 2026",
}


# ---------------------------------------------------------------- markdown
def preparar_md(origem: Path, tirar_titulo: bool) -> str:
    md = origem.read_text(encoding="utf-8")
    # saída em texto duplicada dos prints (o PNG já está embutido)
    md = re.sub(r"<details>.*?</details>\n?", "", md, flags=re.S)
    if tirar_titulo:
        md = re.sub(r"\A# .*\n", "", md)
    # links para arquivos do repositório viram texto (o caminho continua visível)
    md = re.sub(r"(?<!!)\[([^\]]+)\]\((?!https?:)[^)]+\.(?:sql|md|py|sh|txt)\)", r"\1", md)
    md = re.sub(r"(?<!!)\[([^\]]+)\]\((?!https?:)[^)]+/\)", r"\1", md)
    md = re.sub(r"(?<!!)\[([^\]]+)\]\((?!https?:)[^)]+\.png\)", r"\1", md)
    md = re.sub(r"(?<!!)\[([^\]]+)\]\(#[^)]+\)", r"\1", md)
    md = md.replace("| **Integrantes** | _preencher_ |\n", "")
    return md


def caminhos_imagens(md: str, base: Path) -> str:
    def troca(m):
        alt, p = m.group(1), m.group(2)
        return f"![{alt}]({(base / p).resolve().as_uri()})"
    return re.sub(r"!\[([^\]]*)\]\(([^)]+\.png)\)", troca, md)


# ---------------------------------------------------------------- PDF
CSS = """
@page { size: A4; margin: 2cm 1.7cm 2cm 1.7cm;
        @bottom-right { content: counter(page); font: 9pt 'DejaVu Sans'; color: #555; } }
@page capa { @bottom-right { content: none; } }
@page paisagem { size: A4 landscape; margin: 1.5cm;
        @bottom-right { content: counter(page); font: 9pt 'DejaVu Sans'; color: #555; } }
.pg-paisagem { page: paisagem; break-after: page; }
.pg-paisagem img { max-height: 16.5cm; }
html { font-family: 'DejaVu Sans', sans-serif; font-size: 10pt; line-height: 1.4; color: #111; }
body.paisagem { page: paisagem; }
h1 { font-size: 17pt; color: #1f3d6b; border-bottom: 2px solid #1f3d6b; padding-bottom: 3px;
     break-before: page; margin-top: 0; }
h2 { font-size: 14pt; color: #1f3d6b; margin-top: 1.4em; }
h3 { font-size: 11.5pt; color: #24497d; margin-top: 1.3em; break-after: avoid; }
h2, h3 { break-after: avoid; }
p { text-align: left; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 8.6pt; background: #f2f4f7; padding: 0 2px; }
pre { font-family: 'DejaVu Sans Mono', monospace; font-size: 7.8pt; line-height: 1.3;
      background: #f6f8fa; border: 1px solid #d5dbe3; border-left: 3px solid #1f3d6b;
      padding: 6px 8px; white-space: pre-wrap; word-break: break-word; }
pre code { background: none; padding: 0; font-size: inherit; }
table { border-collapse: collapse; width: 100%; font-size: 8.6pt; margin: 0.6em 0; }
th, td { border: 1px solid #c4ccd6; padding: 3px 5px; vertical-align: top; text-align: left; }
th { background: #e6ecf4; }
td, th { overflow-wrap: break-word; }
body.paisagem td, body.paisagem th { overflow-wrap: anywhere; }
td code { word-break: break-word; }
/* dicionário: 7 colunas com larguras fixas para nunca passar da margem */
body.paisagem table { table-layout: fixed; }
body.paisagem th:nth-child(1) { width: 13%; } body.paisagem th:nth-child(2) { width: 21%; }
body.paisagem th:nth-child(3) { width: 17%; } body.paisagem th:nth-child(4) { width: 5%; }
body.paisagem th:nth-child(5) { width: 11%; } body.paisagem th:nth-child(6) { width: 12%; }
body.paisagem th:nth-child(7) { width: 21%; }
body.paisagem ul table, body.paisagem li { table-layout: auto; }
img { max-width: 100%; max-height: 23cm; display: block; margin: 6px auto; border: 1px solid #ccc; }
figure { margin: 0.6em 0; break-inside: avoid; }
figcaption { text-align: center; font-size: 8.5pt; color: #555; }
.capa { page: capa; height: 25.5cm; display: flex; flex-direction: column; text-align: center; }
.capa .inst { font-size: 13pt; font-weight: bold; color: #1f3d6b; margin-top: 0.5cm; }
.capa .disc { font-size: 15pt; margin-top: 3cm; }
.capa .aval { font-size: 13pt; margin-top: 0.3cm; }
.capa .titulo { font-size: 22pt; font-weight: bold; color: #1f3d6b; margin-top: 3cm; }
.capa .sub { font-size: 12pt; margin-top: 0.4cm; color: #333; }
.capa .campos { margin: auto 1.5cm 0 1.5cm; text-align: left; font-size: 12pt; }
.capa .campos div { border-bottom: 1px solid #333; padding: 10px 0 2px 0; margin-bottom: 10px; }
.capa .local { margin-top: 1.4cm; font-size: 11pt; }
nav#TOC { break-before: page; }
nav#TOC h2 { font-size: 17pt; border-bottom: 2px solid #1f3d6b; }
nav#TOC ul { list-style: none; padding-left: 0; }
nav#TOC ul ul { padding-left: 1.2em; }
nav#TOC li { margin: 2px 0; }
nav#TOC a { color: #111; text-decoration: none; }
nav#TOC a::after { content: leader('.') target-counter(attr(href), page); }
a { color: #1f3d6b; }
"""


def capa_html(titulo, sub):
    return f"""<section class="capa">
<div class="inst">{CAPA['instituicao']}<br>({CAPA['sigla']})</div>
<div class="disc">{CAPA['disciplina']}</div>
<div class="aval">{CAPA['avaliacao']}</div>
<div class="titulo">{titulo}</div>
<div class="sub">{sub}</div>
<div class="campos"><div>Nome:</div><div>Nome:</div><div>Turma:</div><div>Professor:</div></div>
<div class="local">{CAPA['local']}</div>
</section>"""


def gerar_pdf(md, destino, titulo, sub, paisagem=False):
    src = TMP / (destino.stem + ".md")
    src.write_text(md, encoding="utf-8")
    html = TMP / (destino.stem + ".html")
    subprocess.run([PANDOC, str(src), "-f", "gfm+attributes", "-t", "html5", "-s", "--toc",
                    "--toc-depth=3", "--metadata", f"title={titulo}", "--metadata", "toc-title=Sumário",
                    "-o", str(html)], check=True)
    h = html.read_text(encoding="utf-8")
    h = re.sub(r"<style>.*?</style>", "", h, flags=re.S)
    h = re.sub(r'<header id="title-block-header">.*?</header>', "", h, flags=re.S)
    h = h.replace("</head>", f"<style>{CSS}</style></head>")
    h = h.replace("<body>", f'<body class="{"paisagem" if paisagem else ""}">' + capa_html(titulo, sub), 1)
    # imagens largas (modelos e prints com muitas colunas) ganham uma página em paisagem
    from PIL import Image as PILImage
    from urllib.parse import unquote, urlparse

    def larga(m):
        tag = m.group(0)
        src = re.search(r'src="([^"]+)"', tag).group(1)
        caminho = unquote(urlparse(src).path) if src.startswith("file:") else src
        try:
            w = PILImage.open(caminho).size[0]
        except OSError:
            return tag
        if not paisagem and w > 1250:
            return f'<div class="pg-paisagem">{tag}</div>'
        return tag
    h = re.sub(r"<img\s[^>]+>", larga, h)
    # primeiro h1 do conteúdo já quebra página pelo CSS; o sumário também
    html.write_text(h, encoding="utf-8")
    doc = HTML(filename=str(html), base_url=str(RAIZ)).render()
    doc.write_pdf(str(destino))
    return len(doc.pages)


# ---------------------------------------------------------------- DOCX
def reference_docx():
    ref = TMP / "reference.docx"
    subprocess.run([PANDOC, "-o", str(ref), "--print-default-data-file", "reference.docx"], check=True)
    d = Document(str(ref))
    st = d.styles
    st["Normal"].font.name = "Calibri"
    st["Normal"].font.size = Pt(10.5)
    for nome, tam in (("Heading 1", 17), ("Heading 2", 14), ("Heading 3", 12)):
        s = st[nome]
        s.font.name = "Calibri"
        s.font.size = Pt(tam)
        s.font.color.rgb = RGBColor(0x1F, 0x3D, 0x6B)
        s.font.bold = True
    st["Heading 1"].paragraph_format.page_break_before = True
    from docx.enum.style import WD_STYLE_TYPE
    existentes = [x.name for x in st]
    if "Source Code" not in existentes:
        st.add_style("Source Code", WD_STYLE_TYPE.PARAGRAPH).base_style = st["Normal"]
    if "Verbatim Char" not in existentes:
        st.add_style("Verbatim Char", WD_STYLE_TYPE.CHARACTER)
    for nome in ("Source Code", "Verbatim Char"):
        if True:
            s = st[nome]
            s.font.name = "Consolas"
            s.font.size = Pt(8)
            rpr = s.element.get_or_add_rPr()
            fonts = rpr.find(qn("w:rFonts"))
            if fonts is None:
                fonts = OxmlElement("w:rFonts")
                rpr.append(fonts)
            for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                fonts.set(qn(a), "Consolas")
    sc = st["Source Code"]
    sc.paragraph_format.space_after = Pt(0)
    ppr = sc.element.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), "F3F5F8")
    ppr.append(shd)
    for sec in d.sections:
        sec.page_height, sec.page_width = Cm(29.7), Cm(21)
        sec.left_margin = sec.right_margin = Cm(2)
        sec.top_margin = sec.bottom_margin = Cm(2)
    d.save(str(ref))
    return ref


def capa_docx(d: Document, titulo, sub):
    corpo = d.element.body
    primeiro = corpo[0]
    novos = []

    def par(texto, tam=12, negrito=False, cor=None, antes=0, alinhamento=WD_ALIGN_PARAGRAPH.CENTER):
        p = d.add_paragraph()
        p.alignment = alinhamento
        p.paragraph_format.space_before = Pt(antes)
        if texto:
            r = p.add_run(texto)
            r.font.size = Pt(tam)
            r.bold = negrito
            if cor:
                r.font.color.rgb = cor
        novos.append(p)
        return p

    azul = RGBColor(0x1F, 0x3D, 0x6B)
    par(CAPA["instituicao"], 13, True, azul)
    par(f"({CAPA['sigla']})", 12, True, azul)
    par(CAPA["disciplina"], 15, antes=90)
    par(CAPA["avaliacao"], 13, antes=6)
    par(titulo, 22, True, azul, antes=90)
    par(sub, 12, antes=8)
    for i, campo in enumerate(("Nome:", "Nome:", "Turma:", "Professor:")):
        p = par(campo + " " + "_" * 60, 12, antes=70 if i == 0 else 14, alinhamento=WD_ALIGN_PARAGRAPH.LEFT)
    p = par(CAPA["local"], 11, antes=50)
    p.add_run().add_break(WD_BREAK.PAGE)
    for p in novos:
        primeiro.addprevious(p._p)


def gerar_docx(md, destino, titulo, sub, paisagem=False):
    src = TMP / (destino.stem + "_docx.md")
    src.write_text(md, encoding="utf-8")
    subprocess.run([PANDOC, str(src), "-f", "gfm", "-t", "docx", "--toc", "--toc-depth=3",
                    "--metadata", "toc-title=Sumário", f"--reference-doc={reference_docx()}",
                    "-o", str(destino)], check=True)
    d = Document(str(destino))
    capa_docx(d, titulo, sub)
    # tabelas com bordas e fonte menor
    for t in d.tables:
        tblpr = t._tbl.tblPr
        bordas = OxmlElement("w:tblBorders")
        for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
            b = OxmlElement(f"w:{lado}")
            b.set(qn("w:val"), "single")
            b.set(qn("w:sz"), "4")
            b.set(qn("w:color"), "A0AAB8")
            bordas.append(b)
        tblpr.append(bordas)
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(8.5 if not paisagem else 8)
    if paisagem:
        for sec in d.sections:
            sec.orientation = WD_ORIENT.LANDSCAPE
            sec.page_width, sec.page_height = Cm(29.7), Cm(21)
            sec.left_margin = sec.right_margin = Cm(1.5)
    # pede ao Word para atualizar o sumário (campo TOC) ao abrir
    settings = d.settings.element
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    settings.append(uf)
    d.save(str(destino))


# ---------------------------------------------------------------- main
def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    tit = "Sistema de Tickets / Ordens de Serviço"
    sub_doc = "Projeto API 2026.02 — banco de dados bdr_api (MySQL 8)"

    md = caminhos_imagens(preparar_md(DOCS / "documento.md", tirar_titulo=True), DOCS)
    nota = ("> **Arquivos separados desta entrega:** script de criação das tabelas `sql/01_ddl.sql`, "
            "script de inserção de dados `sql/02_dml.sql` e dicionário de dados "
            "`docs/dicionario-de-dados.md` (também em `Dicionario-de-Dados.pdf` / `.docx`). "
            "Os demais scripts estão em `sql/` (03 a 07).\n\n")
    # sobe um nível os títulos: cada "Parte" vira capítulo (h1) e cada rotina aparece no sumário
    md = re.sub(r"^(#{2,6}) ", lambda m: m.group(1)[1:] + " ", md, flags=re.M)
    md = "# Apresentação\n\n" + nota + md
    pdf = SAIDA / "Documento-BDR-3a-avaliacao.pdf"
    n1 = gerar_pdf(md, pdf, tit, sub_doc)
    gerar_docx(md, SAIDA / "Documento-BDR-3a-avaliacao.docx", tit, sub_doc)

    dic = preparar_md(DOCS / "dicionario-de-dados.md", tirar_titulo=True)
    # cada tabela vira capítulo (h1) para o sumário e a quebra de página
    dic = re.sub(r"^## ", "# ", dic, flags=re.M)
    dic = "# Introdução\n\n" + dic
    pdf2 = SAIDA / "Dicionario-de-Dados.pdf"
    n2 = gerar_pdf(dic, pdf2, "Dicionário de Dados", "Banco de dados bdr_api (MySQL 8) — Parte 4", paisagem=True)
    gerar_docx(dic, SAIDA / "Dicionario-de-Dados.docx", "Dicionário de Dados",
               "Banco de dados bdr_api (MySQL 8) — Parte 4", paisagem=True)
    import shutil
    shutil.rmtree(TMP, ignore_errors=True)
    print(f"{pdf.name}: {n1} páginas\n{pdf2.name}: {n2} páginas")


if __name__ == "__main__":
    main()
