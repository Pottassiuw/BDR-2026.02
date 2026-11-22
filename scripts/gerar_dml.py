#!/usr/bin/env python3
"""Gera sql/02_dml.sql com dados fictícios consistentes (semente fixa).

Uso: python3 scripts/gerar_dml.py > sql/02_dml.sql
"""
import random
import uuid
from datetime import datetime, timedelta

random.seed(20261123)

AGORA = datetime(2026, 11, 22, 12, 0, 0)   # referência dos dados
INICIO = datetime(2026, 7, 1, 8, 0, 0)

out = []
def emit(s=""):
    out.append(s)

def uid():
    return str(uuid.UUID(int=random.getrandbits(128), version=4))

def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, datetime):
        return "'" + v.strftime("%Y-%m-%d %H:%M:%S.") + f"{v.microsecond // 1000:03d}'"
    return "'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'"

def insert(tabela, cols, vals):
    emit(f"INSERT INTO {tabela} ({', '.join(cols)}) VALUES ({', '.join(q(v) for v in vals)});")

def rnd_dt(a, b):
    return a + timedelta(seconds=random.randint(0, int((b - a).total_seconds())))

def fake_hash():
    al = "./ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "$2b$10$" + "".join(random.choice(al) for _ in range(53))

emit("-- =====================================================================")
emit("-- BDR 2026.02 - 3ª Avaliação | Parte 3 - DML (dados fictícios)")
emit("-- Gerado por scripts/gerar_dml.py (semente fixa: o resultado é sempre o mesmo).")
emit("-- Executar depois de 01_ddl.sql e ANTES de 06_triggers.sql.")
emit("-- =====================================================================")
emit("USE bdr_api;")
emit("SET NAMES utf8mb4;")
emit("START TRANSACTION;")
emit()

# ---------------------------------------------------------------- domínio
emit("-- ---------------- cargos (tabela de domínio)")
cargos = [
    ("TECNICO", "Técnico", "Executa os atendimentos de campo e registra relatórios.", False, False),
    ("GESTOR", "Gestor", "Gerencia uma equipe, prioriza tickets e aprova encerramentos.", True, True),
    ("SUPORTE", "Analista de Suporte Externo", "Abre tickets de manutenção vinculados a projetos.", True, False),
    ("SUPORTE_INTERNO", "Analista de Suporte Interno", "Administra as contas de usuário da plataforma.", False, False),
    ("COMERCIAL", "Analista Comercial", "Cadastra projetos e abre o ticket de instalação.", True, False),
]
for c in cargos:
    insert("cargos", ["codigo", "nome", "descricao", "pode_abrir_ticket", "pode_aprovar_encerramento"], c)
emit()
emit("-- ---------------- prioridades (tabela de domínio)")
PRIOR = {"BAIXA": (1, 72, 12), "MEDIA": (2, 48, 8), "ALTA": (3, 24, 4), "CRITICA": (4, 8, 2)}
nomes_p = {"BAIXA": "Baixa", "MEDIA": "Média", "ALTA": "Alta", "CRITICA": "Crítica"}
for k, (peso, sla, alerta) in PRIOR.items():
    insert("prioridades", ["codigo", "nome", "peso", "sla_horas", "alerta_horas"], [k, nomes_p[k], peso, sla, alerta])
emit()
emit("-- ---------------- status_ticket (tabela de domínio)")
status_d = [
    ("NAO_INICIADO", "Não iniciado", "Ticket aberto, nenhuma equipe iniciou o trabalho.", False, 1),
    ("EM_ANDAMENTO", "Em andamento", "Ao menos uma equipe está trabalhando no ticket.", False, 2),
    ("SOLICITACAO_ENCERRAMENTO", "Solicitação de encerramento", "Técnico pediu o encerramento; aguarda o gestor.", False, 3),
    ("EM_REVISAO", "Em revisão", "Encerramento negado pelo gestor; precisa de ajustes.", False, 4),
    ("ENCERRADO", "Encerrado", "Encerramento aprovado pelo gestor.", True, 5),
]
for s in status_d:
    insert("status_ticket", ["codigo", "nome", "descricao", "finalizado", "ordem"], s)
emit()

# ---------------------------------------------------------------- equipes
areas = ["Instalação", "Manutenção", "Redes", "Elétrica", "Automação",
         "Telemetria", "CFTV", "Drones", "Torres", "Campo"]
regioes = ["SJC", "Campinas", "São Paulo", "Santos", "Taubaté"]
desc_area = {
    "Instalação": "Instalação de equipamentos e sistemas em novos projetos",
    "Manutenção": "Manutenção preventiva e corretiva de equipamentos",
    "Redes": "Infraestrutura de redes e conectividade",
    "Elétrica": "Instalações e reparos elétricos",
    "Automação": "Automação industrial e CLPs",
    "Telemetria": "Sensores e telemetria remota",
    "CFTV": "Câmeras e monitoramento por vídeo",
    "Drones": "Operação e manutenção de drones de inspeção",
    "Torres": "Montagem e manutenção de torres e mastros",
    "Campo": "Atendimento geral de campo",
}
equipes = []
emit("-- ---------------- equipes (50)")
for a in areas:
    for r in regioes:
        e = {"id": uid(), "nome": f"{a} {r}", "criado": rnd_dt(INICIO - timedelta(days=60), INICIO - timedelta(days=30))}
        e["ativo"] = random.random() > 0.04
        equipes.append(e)
        insert("equipes", ["id", "nome", "descricao", "ativo", "criado_em", "atualizado_em"],
               [e["id"], e["nome"], f"{desc_area[a]} - regional {r}.", e["ativo"], e["criado"], e["criado"]])
emit()

# ---------------------------------------------------------------- usuarios
primeiros = ["Ana", "Bruno", "Carla", "Diego", "Eduarda", "Felipe", "Gabriela", "Henrique", "Isabela", "João",
             "Karina", "Lucas", "Mariana", "Nicolas", "Otávio", "Paula", "Rafael", "Sabrina", "Thiago", "Vanessa",
             "William", "Yasmin", "André", "Beatriz", "Caio", "Débora", "Enzo", "Fernanda", "Gustavo", "Helena",
             "Igor", "Juliana", "Leonardo", "Larissa", "Matheus", "Natália", "Pedro", "Renata", "Samuel", "Tatiane"]
sobrenomes = ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Ferreira", "Costa", "Rodrigues", "Almeida",
              "Nascimento", "Carvalho", "Araújo", "Ribeiro", "Gomes", "Martins", "Rocha", "Barbosa", "Moreira", "Cardoso",
              "Teixeira", "Mendes", "Freitas", "Vieira", "Monteiro", "Castro", "Campos", "Duarte", "Pinto", "Moura"]
def ascii_(s):
    tr = str.maketrans("áàâãéêíóôõúçÁÉÍÓÚÂÊÔÃÕÇ", "aaaaeeiooouc" + "AEIOUAEOAOC")
    return s.translate(tr).lower()

emails = set()
usuarios = []
def novo_usuario(cargo, equipe=None, criado_por=None, criado=None, ativo=True):
    while True:
        n, s1, s2 = random.choice(primeiros), random.choice(sobrenomes), random.choice(sobrenomes)
        if s1 == s2:
            continue
        nome = f"{n} {s1} {s2}"
        email = f"{ascii_(n)}.{ascii_(s2)}@altave.com.br"
        if email in emails:
            email = f"{ascii_(n)}.{ascii_(s1)}.{ascii_(s2)}@altave.com.br"
        if email not in emails:
            break
    emails.add(email)
    u = {"id": uid(), "nome": nome, "email": email, "cargo": cargo, "equipe": equipe,
         "criado_por": criado_por, "criado": criado or rnd_dt(INICIO - timedelta(days=30), INICIO),
         "ativo": ativo, "provisoria": random.random() < 0.15}
    usuarios.append(u)
    return u

admin = novo_usuario("SUPORTE_INTERNO", criado=INICIO - timedelta(days=90))
admin["provisoria"] = False
sup_int = [admin] + [novo_usuario("SUPORTE_INTERNO", criado_por=admin["id"]) for _ in range(2)]
gestores = {}
tecnicos = {}
for e in equipes:
    g = novo_usuario("GESTOR", equipe=e["id"], criado_por=random.choice(sup_int)["id"])
    gestores[e["id"]] = g
    tecnicos[e["id"]] = []
    for _ in range(3):
        t = novo_usuario("TECNICO", equipe=e["id"], criado_por=random.choice(sup_int)["id"],
                         ativo=random.random() > 0.05)
        tecnicos[e["id"]].append(t)
# alguns técnicos recém-contratados, ainda sem equipe
for _ in range(4):
    novo_usuario("TECNICO", criado_por=admin["id"])
comerciais = [novo_usuario("COMERCIAL", criado_por=random.choice(sup_int)["id"]) for _ in range(8)]
suportes = [novo_usuario("SUPORTE", criado_por=random.choice(sup_int)["id"]) for _ in range(8)]

emit(f"-- ---------------- usuarios ({len(usuarios)})")
for u in usuarios:
    insert("usuarios", ["id", "nome", "email", "senha_hash", "cargo", "ativo", "senha_provisoria",
                        "criado_em", "atualizado_em", "equipe_id", "criado_por_id"],
           [u["id"], u["nome"], u["email"], fake_hash(), u["cargo"], u["ativo"], u["provisoria"],
            u["criado"], u["criado"], u["equipe"], u["criado_por"]])
emit()

# ---------------------------------------------------------------- clientes
pref = ["Metalúrgica", "Agro", "Logística", "Portos", "Mineração", "Energia", "Química", "Construtora",
        "Transportes", "Siderúrgica"]
mid = ["Vale Azul", "Serra Verde", "Horizonte", "Paraíba", "Mantiqueira", "Litoral Norte", "Bandeirantes",
       "Tietê", "Atlântico", "Planalto", "Jacareí", "Ipiranga", "Aurora", "Santa Clara", "Rio Claro"]
suf = ["Ltda", "S.A.", "Indústria e Comércio", "Ltda ME"]
clientes = []
nomes_cli = set()
while len(clientes) < 50:
    nome = f"{random.choice(pref)} {random.choice(mid)} {random.choice(suf)}"
    if nome in nomes_cli:
        continue
    nomes_cli.add(nome)
    c = {"id": uid(), "nome": nome, "criado": rnd_dt(INICIO - timedelta(days=20), INICIO + timedelta(days=60)),
         "ativo": random.random() > 0.06}
    clientes.append(c)
emit("-- ---------------- clientes (50)")
for c in clientes:
    insert("clientes", ["id", "nome", "ativo", "criado_em", "atualizado_em"],
           [c["id"], c["nome"], c["ativo"], c["criado"], c["criado"]])
emit()

# ---------------------------------------------------------------- projetos
tipos_proj = ["Monitoramento por câmeras", "Rede de sensores", "Torre de telecom", "Automação de linha",
              "Subestação elétrica", "Inspeção com drones", "Rede Wi-Fi industrial", "Telemetria de tanques",
              "Controle de acesso", "Painel solar"]
cidades = ["São José dos Campos/SP", "Jacareí/SP", "Taubaté/SP", "Campinas/SP", "Santos/SP", "São Paulo/SP",
           "Caçapava/SP", "Pindamonhangaba/SP", "Guarulhos/SP", "Sorocaba/SP"]
locais = ["Galpão", "Pátio", "Planta", "Unidade", "Terminal", "Centro de Distribuição"]
projetos = []
emit("-- ---------------- projetos (60)")
ativos_eq = [e for e in equipes if e["ativo"]]
for i in range(60):
    c = clientes[i % 50] if i < 50 else random.choice(clientes)
    e = random.choice(ativos_eq)
    nome = f"{random.choice(tipos_proj)} {random.choice(locais)} {random.randint(1, 9)}"
    while any(p["cliente"] == c["id"] and p["nome"] == nome for p in projetos):
        nome = f"{random.choice(tipos_proj)} {random.choice(locais)} {random.randint(1, 9)}"
    criado = max(c["criado"], INICIO) + timedelta(hours=random.randint(1, 72))
    p = {"id": uid(), "nome": nome, "cliente": c["id"], "equipe": e["id"], "gestor": gestores[e["id"]]["id"],
         "criado": criado, "ativo": random.random() > 0.05, "local": f"{random.choice(locais)} {random.randint(1, 30)} - {random.choice(cidades)}"}
    projetos.append(p)
    insert("projetos", ["id", "nome", "local_instalacao", "descricao", "ativo", "criado_em", "atualizado_em",
                        "cliente_id", "equipe_id", "gestor_id"],
           [p["id"], p["nome"], p["local"], f"Projeto de {p['nome'].lower()} para o cliente {c['nome']}.",
            p["ativo"], p["criado"], p["criado"], p["cliente"], p["equipe"], p["gestor"]])
emit()

# ---------------------------------------------------------------- tickets
problemas_m = ["Câmera sem imagem", "Sensor de temperatura sem leitura", "Queda de link de rádio",
               "Disjuntor desarmando", "CLP reiniciando sozinho", "Drone não sincroniza com base",
               "Ruído no sinal da antena", "Nobreak em alarme", "Switch com portas desligadas",
               "Falha na gravação do NVR", "Bateria do sensor fraca", "Cabo rompido na torre",
               "Painel solar com baixa geração", "Leitor de crachá sem resposta", "Firmware desatualizado"]
problemas_i = ["Instalação inicial do sistema", "Instalação de novos pontos de câmera",
               "Instalação de gateway de telemetria", "Montagem da torre principal",
               "Instalação de rede de fibra", "Instalação de quadro elétrico", "Instalação de estação de drones"]
HORAS_SLA = [4, 8, 24, 48, 72, 168]
users_by_id = {u["id"]: u for u in usuarios}
abridores = comerciais + suportes

tickets = []
ticket_equipes = []
historico = []
relatorios = []
atividades = []

def add_hist(t, evento, desc, quando, usuario=None, equipe=None, inicio=None):
    historico.append([uid(), evento, desc, quando, t["id"], usuario, equipe, inicio])

for i in range(220):
    p = random.choice(projetos)
    if random.random() < 0.6:
        criado = rnd_dt(max(p["criado"], INICIO), AGORA - timedelta(hours=2))
    else:  # parte dos tickets é recente, para haver fila aberta e SLAs correndo
        criado = rnd_dt(max(p["criado"], AGORA - timedelta(days=12)), AGORA - timedelta(hours=2))
    if i < 60:  # primeiro ticket de vários projetos = instalação
        categoria = "INSTALACAO"
        titulo = f"{random.choice(problemas_i)} - {p['nome']}"
        abridor = random.choice(comerciais)
    else:
        categoria = random.choice(["MANUTENCAO"] * 4 + ["INSTALACAO"])
        titulo = f"{random.choice(problemas_m if categoria == 'MANUTENCAO' else problemas_i)} - {p['nome']}"
        abridor = random.choice(abridores + [gestores[p["equipe"]]])
    prioridade = random.choices(["BAIXA", "MEDIA", "ALTA", "CRITICA"], [20, 40, 28, 12])[0]
    if random.random() < 0.75:
        horas = PRIOR[prioridade][1]
    else:
        horas = random.choice(HORAS_SLA)
    sla = criado + timedelta(hours=horas)
    idade_h = (AGORA - criado).total_seconds() / 3600
    # status coerente com a idade do ticket
    if idade_h > 24 * 20:
        status = random.choices(["ENCERRADO", "EM_REVISAO", "EM_ANDAMENTO"], [88, 5, 7])[0]
    elif idade_h > 24 * 5:
        status = random.choices(["ENCERRADO", "SOLICITACAO_ENCERRAMENTO", "EM_REVISAO", "EM_ANDAMENTO"],
                                [60, 12, 8, 20])[0]
    else:
        status = random.choices(["NAO_INICIADO", "EM_ANDAMENTO", "SOLICITACAO_ENCERRAMENTO", "ENCERRADO"],
                                [25, 50, 10, 15])[0]
    if status != "ENCERRADO" and random.random() < 0.55:
        # metade da fila aberta ainda está dentro do SLA
        horas = random.choice(HORAS_SLA[2:])
        criado = max(p["criado"] + timedelta(minutes=5),
                     AGORA - timedelta(seconds=random.randint(3600, int(horas * 3600 * 0.9))))
        sla = criado + timedelta(hours=horas)
    equipes_t = [p["equipe"]]
    r = random.random()
    if r < 0.35:
        extra = random.sample([e["id"] for e in ativos_eq if e["id"] != p["equipe"]], 1 if r < 0.27 else 2)
        equipes_t += extra
    techs_proj = [t for t in tecnicos[p["equipe"]] if t["ativo"]] or tecnicos[p["equipe"]]
    responsavel = None if (status == "NAO_INICIADO" and random.random() < 0.7) else random.choice(techs_proj)["id"]

    # linha do tempo
    fim = AGORA - timedelta(minutes=5)
    encerrado = None
    if status == "ENCERRADO":
        # ~78% dentro do SLA
        if random.random() < 0.78:
            encerrado = criado + timedelta(seconds=random.randint(1800, int(horas * 3600 * 0.95)))
        else:
            encerrado = criado + timedelta(seconds=int(horas * 3600 * random.uniform(1.05, 2.5)))
        if encerrado > fim:
            encerrado = fim
        fim = encerrado
    t = {"id": uid(), "titulo": titulo, "categoria": categoria, "prioridade": prioridade, "status": status,
         "sla": sla, "encerrado": encerrado, "criado": criado, "projeto": p["id"], "abridor": abridor["id"],
         "responsavel": responsavel, "equipes": equipes_t}
    tickets.append(t)
    desc = (f"{titulo.split(' - ')[0]} no local {p['local']}. Chamado aberto por {abridor['nome']} "
            f"para atendimento da equipe responsável pelo projeto.")
    t["descricao"] = desc

    # ticket_equipes
    for k, eq in enumerate(equipes_t):
        ticket_equipes.append([uid(), criado + timedelta(seconds=k * 30 + 1), t["id"], eq])

    # histórico + relatórios
    add_hist(t, "TICKET_CRIADO", f"Ticket aberto com prioridade {prioridade} e SLA de {horas}h.",
             criado, abridor["id"], abridor["equipe"])
    atividades.append([uid(), "TICKET | ABERTURA",
                       f"Abriu o ticket {titulo} vinculado ao projeto {p['nome']}.", criado, abridor["id"]])
    for k, eq in enumerate(equipes_t[1:]):
        add_hist(t, "EQUIPE_ADICIONADA", f"Equipe {next(e['nome'] for e in equipes if e['id'] == eq)} alocada ao ticket.",
                 criado + timedelta(seconds=k * 30 + 31), abridor["id"], abridor["equipe"])
    if status == "NAO_INICIADO":
        continue
    span = (fim - criado).total_seconds()
    cur = criado + timedelta(seconds=span * random.uniform(0.02, 0.12))
    iniciadas = equipes_t if status in ("ENCERRADO", "SOLICITACAO_ENCERRAMENTO", "EM_REVISAO") or random.random() < 0.6 else equipes_t[:1]
    for eq in iniciadas:
        tec = random.choice(tecnicos[eq])
        add_hist(t, "ATIVIDADE_INICIADA", f"Equipe iniciou os trabalhos no local.", cur, tec["id"], eq, eq)
        cur += timedelta(seconds=span * random.uniform(0.02, 0.08))
    nrel = random.randint(1, 3)
    for _ in range(nrel):
        eq = random.choice(iniciadas)
        tec = random.choice(tecnicos[eq])
        relatorios.append({"id": uid(), "ticket": t["id"], "autor": tec["id"], "criado": cur, "cat": categoria})
        add_hist(t, "LOG", "Relatório de atendimento registrado.", cur + timedelta(seconds=2), tec["id"], eq)
        cur += timedelta(seconds=span * random.uniform(0.05, 0.15))
    if status in ("SOLICITACAO_ENCERRAMENTO", "EM_REVISAO", "ENCERRADO"):
        tec = users_by_id[responsavel] if responsavel else random.choice(tecnicos[p["equipe"]])
        if status in ("EM_REVISAO",) or (status == "ENCERRADO" and random.random() < 0.15):
            add_hist(t, "ENCERRAMENTO_SOLICITADO", "Serviço concluído, solicito encerramento.", cur, tec["id"], tec["equipe"])
            cur += timedelta(seconds=span * 0.05)
            g = gestores[p["equipe"]]
            add_hist(t, "ENCERRAMENTO_NEGADO", "Faltou anexar o relatório de testes. Revisar.", cur, g["id"], g["equipe"])
            cur += timedelta(seconds=span * 0.05)
        if status != "EM_REVISAO":
            sol = min(cur, fim - timedelta(minutes=30)) if status == "ENCERRADO" else cur
            add_hist(t, "ENCERRAMENTO_SOLICITADO", "Atendimento finalizado, aguardando aprovação.", sol, tec["id"], tec["equipe"])
        if status == "ENCERRADO":
            g = gestores[p["equipe"]]
            add_hist(t, "ENCERRAMENTO_APROVADO", "Encerramento aprovado. Serviço conferido.", encerrado, g["id"], g["equipe"])

emit(f"-- ---------------- tickets ({len(tickets)})")
for t in tickets:
    insert("tickets", ["id", "titulo", "descricao", "categoria", "prioridade", "status", "sla_em", "encerrado_em",
                       "criado_em", "atualizado_em", "projeto_id", "aberto_por_id", "responsavel_id"],
           [t["id"], t["titulo"], t["descricao"], t["categoria"], t["prioridade"], t["status"], t["sla"],
            t["encerrado"], t["criado"], t["encerrado"] or t["criado"], t["projeto"], t["abridor"], t["responsavel"]])
emit()
emit(f"-- ---------------- ticket_equipes ({len(ticket_equipes)})")
for te in ticket_equipes:
    insert("ticket_equipes", ["id", "criado_em", "ticket_id", "equipe_id"], te)
emit()

trab = {"MANUTENCAO": ["Substituído o módulo defeituoso e realizados testes de funcionamento.",
                       "Refeita a conexão do cabeamento e reconfigurado o equipamento.",
                       "Atualizado o firmware e ajustados os parâmetros de comunicação.",
                       "Limpeza preventiva, reaperto de conexões e medição de tensões.",
                       "Diagnóstico realizado; peça solicitada ao almoxarifado."],
        "INSTALACAO": ["Fixação dos suportes e passagem de cabos concluídas.",
                       "Equipamentos instalados e energizados; comissionamento iniciado.",
                       "Configuração de rede e integração com a central de monitoramento.",
                       "Montagem mecânica concluída e aterramento verificado.",
                       "Testes de aceitação realizados junto ao cliente."]}
materiais = ["2 conectores RJ45, 10 m de cabo UTP cat6", "1 fonte 12V 5A, fita isolante",
             "Cabo PP 3x2,5mm (15 m), 4 abraçadeiras", "1 câmera IP 4MP, 1 suporte de parede",
             "1 sensor PT100, prensa-cabos", "Nenhum material utilizado", "2 baterias 12V 7Ah",
             "1 switch PoE 8 portas, patch cords", "Parafusos e buchas, 1 caixa hermética",
             "1 rádio 5 GHz, kit de fixação"]
detalhes = ["Cliente acompanhou o atendimento.", "Acesso liberado pela portaria às 8h.",
            "Necessário retorno para teste final.", "Equipamento em garantia.",
            "Local com acesso restrito; uso de EPI obrigatório.", "Sem observações adicionais."]
emit(f"-- ---------------- relatorios ({len(relatorios)})")
for r in relatorios:
    insert("relatorios", ["id", "trabalho_realizado", "materiais_utilizados", "outros_detalhes", "criado_em",
                          "atualizado_em", "ticket_id", "autor_id"],
           [r["id"], random.choice(trab[r["cat"]]), random.choice(materiais), random.choice(detalhes),
            r["criado"], r["criado"], r["ticket"], r["autor"]])
emit()
emit(f"-- ---------------- historico_ticket ({len(historico)})")
for h in historico:
    insert("historico_ticket", ["id", "evento", "descricao", "criado_em", "ticket_id", "usuario_id", "equipe_id",
                                "inicio_equipe_id"], h)
emit()

# ---------------------------------------------------------------- atividades_conta
ROT = {c[0]: c[1] for c in cargos}
for u in usuarios:
    if u["criado_por"]:
        atividades.append([uid(), "CADASTRO", f"Criou usuário {u['nome']} do tipo {ROT[u['cargo']]}.",
                           u["criado"], u["criado_por"]])
    if u["cargo"] == "GESTOR":
        e = next(e for e in equipes if e["id"] == u["equipe"])
        atividades.append([uid(), "EQUIPE", f"Equipe {e['nome']} criada automaticamente para sua conta.",
                           u["criado"], u["id"]])
for e in equipes:
    g = gestores[e["id"]]
    for t in tecnicos[e["id"]]:
        atividades.append([uid(), "EQUIPE", f"Adicionou usuário {t['nome']} à equipe {e['nome']}.",
                           max(t["criado"], g["criado"]) + timedelta(hours=2), g["id"]])
for p in projetos:
    c = next(c for c in clientes if c["id"] == p["cliente"])
    atividades.append([uid(), "PROJETO", f"Cadastrou o projeto {p['nome']} do cliente {c['nome']}.",
                       p["criado"], random.choice(comerciais)["id"]])
atividades.sort(key=lambda a: a[3])
emit(f"-- ---------------- atividades_conta ({len(atividades)})")
for a in atividades:
    insert("atividades_conta", ["id", "tipo", "descricao", "criado_em", "usuario_id"], a)
emit()
emit("COMMIT;")

print("\n".join(out))
