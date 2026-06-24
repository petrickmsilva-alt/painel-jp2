from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
import json
import os
import time
import urllib.error
import urllib.request
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from jinja2 import ChoiceLoader, DictLoader
from database import get_db_connection

bp_carteira = Blueprint(
    "carteira",
    __name__,
    url_prefix="/carteira",
    template_folder="templates",
)
CARTEIRA_TEMPLATE_FALLBACKS = {}

@bp_carteira.record_once
def registrar_templates_fallback(state):
    fallback_loader = DictLoader(CARTEIRA_TEMPLATE_FALLBACKS)
    if state.app.jinja_loader:
        state.app.jinja_loader = ChoiceLoader([state.app.jinja_loader, fallback_loader])
    else:
        state.app.jinja_loader = fallback_loader

TABELAS_OK = False
CLASSES = ["Reserva de emergencia", "Renda fixa", "Acoes Brasil", "FIIs", "Stocks", "REITs", "ETFs", "Caixa oportunidade"]
POLITICA_PADRAO = [
    ("Reserva de emergencia", 15, 100, 1, "Liquidez e seguranca para curto prazo."),
    ("Renda fixa", 25, 100, 2, "Selic, IPCA+ e protecao de medio prazo."),
    ("Acoes Brasil", 20, 12, 3, "Empresas brasileiras com lucro, margem e ROIC."),
    ("FIIs", 15, 10, 4, "Renda imobiliaria e geracao de caixa."),
    ("Stocks", 12, 10, 5, "Empresas globais e moeda forte."),
    ("REITs", 8, 8, 6, "Imoveis internacionais em dolar."),
    ("ETFs", 5, 15, 7, "Diversificacao ampla."),
]
CRITERIOS_PADRAO = [
    ("Acoes Brasil", "roic_min", 10, 15, 18, "ROIC minimo para empresa produtiva"),
    ("Acoes Brasil", "margem_ebit_min", 8, 12, 10, "Margem EBIT minima"),
    ("Acoes Brasil", "margem_liquida_min", 8, 12, 16, "Margem liquida minima"),
    ("Acoes Brasil", "divida_ebitda_max", 3.5, 2.5, 18, "Bloqueio de divida elevada"),
    ("Acoes Brasil", "liquidez_diaria_min", 6000000, 10000000, 10, "Liquidez media diaria"),
    ("Acoes Brasil", "patrimonio_liquido_min", 900000000, 3000000000, 10, "Patrimonio liquido minimo"),
    ("Acoes Brasil", "tag_along_min", 1, 1, 10, "Protecao ao acionista minoritario"),
    ("Acoes Brasil", "free_float_min", 0.15, 0.30, 8, "Acoes em circulacao no mercado"),
    ("Acoes Brasil", "anos_lucro_min", 5, 10, 8, "Historico consistente de lucro"),
    ("Acoes Brasil", "governo_majoritario_bloqueio", 1, 0, 20, "Evitar governo como majoritario"),
    ("Stocks", "roic_min", 10, 15, 18, "ROIC minimo para empresas globais"),
    ("Stocks", "margem_liquida_min", 8, 12, 16, "Margem liquida minima"),
    ("Stocks", "divida_ebitda_max", 3.5, 2.5, 18, "Divida controlada"),
    ("FIIs", "dividend_yield_min", 6, 8, 10, "Renda passiva minima"),
    ("REITs", "dividend_yield_min", 4, 6, 8, "Renda em dolar"),
    ("ETFs", "liquidez_diaria_min", 1000000, 5000000, 8, "Liquidez do ETF"),
]

BASE_ACOES_ARQUIVO = os.path.join(os.path.dirname(__file__), "data", "planilha_ouro_acoes_junho_2026.json")


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "usuario_logado" not in session:
            return redirect(url_for("tela_login"))
        garantir_tabelas()
        return view(*args, **kwargs)
    return wrapper


def num(valor, padrao=0):
    if valor is None:
        return Decimal(str(padrao))
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if not texto:
        return Decimal(str(padrao))
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation:
        return Decimal(str(padrao))


def fnum(valor):
    try:
        return float(valor or 0)
    except Exception:
        return 0.0


def br_money(valor):
    return f"R$ {fnum(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def importar_universo_acoes(cur):
    if not os.path.exists(BASE_ACOES_ARQUIVO):
        return
    with open(BASE_ACOES_ARQUIVO, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    itens = dados.get("items") or []
    if not itens:
        return
    sql = """
        INSERT INTO carteira_universo_acoes (
            ticker, empresa, setor, tipo_acao, tag_along, free_float, segmento_listagem,
            segmento_ordem, governo_majoritario, patrimonio_liquido, liquidez_media_diaria,
            margem_ebit, margem_liquida, roic, roe, anos_ipo, anos_lucro,
            dividend_yield, cagr_lucro_5a, soma_div_cagr, divida_liquida_ebitda
        ) VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        ) ON DUPLICATE KEY UPDATE
            empresa=VALUES(empresa), setor=VALUES(setor), tipo_acao=VALUES(tipo_acao),
            tag_along=VALUES(tag_along), free_float=VALUES(free_float),
            segmento_listagem=VALUES(segmento_listagem), segmento_ordem=VALUES(segmento_ordem),
            governo_majoritario=VALUES(governo_majoritario), patrimonio_liquido=VALUES(patrimonio_liquido),
            liquidez_media_diaria=VALUES(liquidez_media_diaria), margem_ebit=VALUES(margem_ebit),
            margem_liquida=VALUES(margem_liquida), roic=VALUES(roic), roe=VALUES(roe),
            anos_ipo=VALUES(anos_ipo), anos_lucro=VALUES(anos_lucro),
            dividend_yield=VALUES(dividend_yield), cagr_lucro_5a=VALUES(cagr_lucro_5a),
            soma_div_cagr=VALUES(soma_div_cagr), divida_liquida_ebitda=VALUES(divida_liquida_ebitda)
    """
    valores = [
        (
            i.get("ticker"), i.get("empresa"), i.get("setor"), i.get("tipo_acao"),
            num(i.get("tag_along")), num(i.get("free_float")), i.get("segmento_listagem"),
            int(fnum(i.get("segmento_ordem")) or 99), i.get("governo_majoritario"),
            num(i.get("patrimonio_liquido")), num(i.get("liquidez_media_diaria")),
            num(i.get("margem_ebit")), num(i.get("margem_liquida")), num(i.get("roic")),
            num(i.get("roe")), num(i.get("anos_ipo")), num(i.get("anos_lucro")),
            num(i.get("dividend_yield")), num(i.get("cagr_lucro_5a")), num(i.get("soma_div_cagr")),
            num(i.get("divida_liquida_ebitda")),
        )
        for i in itens
        if i.get("ticker") and i.get("empresa")
    ]
    cur.executemany(sql, valores)


def score_acao_universo(a):
    score = 0
    motivos, bloqueios = [], []
    if str(a.get("governo_majoritario") or "").strip().lower() in ("sim", "yes", "1"):
        bloqueios.append("governo majoritario")
        score -= 30
    if fnum(a.get("tag_along")) >= 1:
        score += 10; motivos.append("tag along forte")
    if fnum(a.get("free_float")) >= 0.15:
        score += 8; motivos.append("free float adequado")
    segmento = str(a.get("segmento_listagem") or "").lower()
    if "novo mercado" in segmento:
        score += 12; motivos.append("governanca Novo Mercado")
    elif fnum(a.get("segmento_ordem")) <= 3:
        score += 7; motivos.append("boa listagem")
    if fnum(a.get("patrimonio_liquido")) >= 900000000:
        score += 10; motivos.append("patrimonio liquido robusto")
    else:
        bloqueios.append("patrimonio liquido baixo")
    if fnum(a.get("liquidez_media_diaria")) >= 6000000:
        score += 10; motivos.append("liquidez diaria adequada")
    else:
        bloqueios.append("liquidez fraca")
    if fnum(a.get("margem_ebit")) >= 0.08:
        score += 8; motivos.append("margem EBIT acima de 8%")
    else:
        bloqueios.append("margem EBIT baixa")
    if fnum(a.get("margem_liquida")) >= 0.08:
        score += 10; motivos.append("margem liquida acima de 8%")
    else:
        bloqueios.append("margem liquida baixa")
    if fnum(a.get("roic")) >= 0.10:
        score += 14; motivos.append("ROIC acima de 10%")
    else:
        bloqueios.append("ROIC baixo")
    if fnum(a.get("roe")) >= 0.12:
        score += 6; motivos.append("ROE saudavel")
    if fnum(a.get("anos_lucro")) >= 5:
        score += 8; motivos.append("historico de lucro")
    else:
        bloqueios.append("poucos anos de lucro")
    if fnum(a.get("soma_div_cagr")) >= 0.10:
        score += 7; motivos.append("dividendos mais crescimento")
    divida = fnum(a.get("divida_liquida_ebitda"))
    if divida <= 3.5:
        score += 7; motivos.append("divida controlada")
    else:
        score -= 12; bloqueios.append("divida elevada")
    score = max(0, min(100, int(round(score))))
    decisao = "Aportar" if score >= 75 and len(bloqueios) <= 1 else "Observar" if score >= 58 else "Nao aportar"
    return score, decisao, motivos[:6], bloqueios[:6]


def garantir_coluna(cur, tabela, coluna, definicao):
    cur.execute(f"SHOW COLUMNS FROM {tabela} LIKE %s", (coluna,))
    if not cur.fetchone():
        cur.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def garantir_tabelas():
    global TABELAS_OK
    if TABELAS_OK:
        return
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS carteira_ativos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(32) NOT NULL UNIQUE,
                nome VARCHAR(160) NOT NULL,
                classe VARCHAR(60) NOT NULL,
                pais VARCHAR(60) DEFAULT 'Brasil',
                setor VARCHAR(100) NULL,
                moeda VARCHAR(12) DEFAULT 'BRL',
                quantidade DECIMAL(18,6) DEFAULT 0,
                preco_medio DECIMAL(18,4) DEFAULT 0,
                valor_atual DECIMAL(18,2) DEFAULT 0,
                dividend_yield DECIMAL(10,4) DEFAULT 0,
                roic DECIMAL(10,4) DEFAULT 0,
                margem_liquida DECIMAL(10,4) DEFAULT 0,
                divida_ebitda DECIMAL(10,4) DEFAULT 0,
                liquidez_diaria DECIMAL(18,2) DEFAULT 0,
                governanca VARCHAR(80) NULL,
                status VARCHAR(20) DEFAULT 'observar',
                observacoes TEXT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS carteira_aportes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ativo_id INT NULL,
                classe VARCHAR(60) NOT NULL,
                tipo VARCHAR(40) DEFAULT 'compra',
                valor DECIMAL(18,2) NOT NULL DEFAULT 0,
                data_aporte DATE NOT NULL,
                observacoes TEXT NULL,
                criado_por VARCHAR(120) NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_carteira_aportes_data (data_aporte),
                INDEX idx_carteira_aportes_classe (classe)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS carteira_politica (
                id INT AUTO_INCREMENT PRIMARY KEY,
                classe VARCHAR(60) NOT NULL UNIQUE,
                percentual_alvo DECIMAL(10,2) NOT NULL DEFAULT 0,
                limite_por_ativo DECIMAL(10,2) NOT NULL DEFAULT 10,
                prioridade INT DEFAULT 10,
                descricao TEXT NULL
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS carteira_inteligencia_criterios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                classe VARCHAR(60) NOT NULL,
                criterio VARCHAR(80) NOT NULL,
                minimo DECIMAL(18,4) DEFAULT 0,
                ideal DECIMAL(18,4) DEFAULT 0,
                peso INT DEFAULT 0,
                descricao TEXT NULL,
                ativo TINYINT(1) DEFAULT 1,
                UNIQUE KEY uq_carteira_criterio (classe, criterio)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS carteira_dados_mercado (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(32) NOT NULL UNIQUE,
                preco DECIMAL(18,4) DEFAULT 0,
                variacao_dia DECIMAL(10,4) DEFAULT 0,
                variacao_52s DECIMAL(10,4) DEFAULT 0,
                fonte VARCHAR(80) DEFAULT 'manual',
                dados_json TEXT NULL,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS carteira_universo_acoes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(32) NOT NULL UNIQUE,
                empresa VARCHAR(180) NOT NULL,
                setor VARCHAR(140) NULL,
                tipo_acao VARCHAR(20) NULL,
                tag_along DECIMAL(10,6) DEFAULT 0,
                free_float DECIMAL(10,6) DEFAULT 0,
                segmento_listagem VARCHAR(80) NULL,
                segmento_ordem INT DEFAULT 99,
                governo_majoritario VARCHAR(20) NULL,
                patrimonio_liquido DECIMAL(20,2) DEFAULT 0,
                liquidez_media_diaria DECIMAL(20,2) DEFAULT 0,
                margem_ebit DECIMAL(12,6) DEFAULT 0,
                margem_liquida DECIMAL(12,6) DEFAULT 0,
                roic DECIMAL(12,6) DEFAULT 0,
                roe DECIMAL(12,6) DEFAULT 0,
                anos_ipo DECIMAL(10,2) DEFAULT 0,
                anos_lucro DECIMAL(10,2) DEFAULT 0,
                dividend_yield DECIMAL(12,6) DEFAULT 0,
                cagr_lucro_5a DECIMAL(12,6) DEFAULT 0,
                soma_div_cagr DECIMAL(12,6) DEFAULT 0,
                divida_liquida_ebitda DECIMAL(12,6) DEFAULT 0,
                fonte VARCHAR(120) DEFAULT 'Planilha de Ouro Acoes',
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """)
        garantir_coluna(cur, "carteira_ativos", "pl", "DECIMAL(18,4) DEFAULT 0")
        garantir_coluna(cur, "carteira_ativos", "pvp", "DECIMAL(18,4) DEFAULT 0")
        garantir_coluna(cur, "carteira_ativos", "roe", "DECIMAL(10,4) DEFAULT 0")
        garantir_coluna(cur, "carteira_ativos", "lucro_cagr", "DECIMAL(10,4) DEFAULT 0")
        garantir_coluna(cur, "carteira_ativos", "preco_teto", "DECIMAL(18,4) DEFAULT 0")
        garantir_coluna(cur, "carteira_aportes", "quantidade", "DECIMAL(18,6) DEFAULT 0")
        cur.execute("SELECT COUNT(*) AS total FROM carteira_politica")
        if int(cur.fetchone()["total"] or 0) == 0:
            cur.executemany("INSERT INTO carteira_politica (classe, percentual_alvo, limite_por_ativo, prioridade, descricao) VALUES (%s,%s,%s,%s,%s)", POLITICA_PADRAO)
        cur.execute("SELECT COUNT(*) AS total FROM carteira_inteligencia_criterios")
        if int(cur.fetchone()["total"] or 0) == 0:
            cur.executemany("INSERT INTO carteira_inteligencia_criterios (classe, criterio, minimo, ideal, peso, descricao) VALUES (%s,%s,%s,%s,%s,%s)", CRITERIOS_PADRAO)
        cur.executemany(
            "INSERT IGNORE INTO carteira_inteligencia_criterios (classe, criterio, minimo, ideal, peso, descricao) VALUES (%s,%s,%s,%s,%s,%s)",
            CRITERIOS_PADRAO,
        )
        cur.execute("SELECT COUNT(*) AS total FROM carteira_universo_acoes")
        if int(cur.fetchone()["total"] or 0) == 0:
            importar_universo_acoes(cur)
    conn.close()
    TABELAS_OK = True


def criterios_por_classe():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM carteira_inteligencia_criterios WHERE ativo=1")
        rows = cur.fetchall()
    conn.close()
    mapa = {}
    for r in rows:
        mapa.setdefault(r["classe"], {})[r["criterio"]] = r
    return mapa


def dados_mercado_map():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM carteira_dados_mercado")
        rows = cur.fetchall()
    conn.close()
    return {r["ticker"].upper(): r for r in rows}


def score_ativo(a, criterios=None, mercado=None):
    criterios = criterios or {}
    mercado = mercado or {}
    classe = a.get("classe") or ""
    regras = criterios.get(classe, {})
    status = (a.get("status") or "observar").lower()
    score = 50
    motivos = []
    bloqueios = []

    roic = fnum(a.get("roic")); margem = fnum(a.get("margem_liquida")); divida = fnum(a.get("divida_ebitda"))
    liquidez = fnum(a.get("liquidez_diaria")); dy = fnum(a.get("dividend_yield")); pl = fnum(a.get("pl")); pvp = fnum(a.get("pvp")); roe = fnum(a.get("roe")); lucro_cagr = fnum(a.get("lucro_cagr")); preco_teto = fnum(a.get("preco_teto"))
    ticker = (a.get("ticker") or "").upper(); dado = mercado.get(ticker) or {}; preco = fnum(dado.get("preco")) or fnum(a.get("preco_medio"))
    gov = (a.get("governanca") or "").lower()

    roic_min = fnum((regras.get("roic_min") or {}).get("minimo")) or 10
    roic_ideal = fnum((regras.get("roic_min") or {}).get("ideal")) or 15
    margem_min = fnum((regras.get("margem_liquida_min") or {}).get("minimo")) or 8
    margem_ideal = fnum((regras.get("margem_liquida_min") or {}).get("ideal")) or 12
    divida_max = fnum((regras.get("divida_ebitda_max") or {}).get("minimo")) or 3.5
    divida_ideal = fnum((regras.get("divida_ebitda_max") or {}).get("ideal")) or 2.5
    liquidez_min = fnum((regras.get("liquidez_diaria_min") or {}).get("minimo")) or 6000000
    dy_min = fnum((regras.get("dividend_yield_min") or {}).get("minimo")) or 6

    if classe in ("Acoes Brasil", "Stocks"):
        if roic >= roic_ideal: score += 18; motivos.append("ROIC forte")
        elif roic >= roic_min: score += 12; motivos.append("ROIC adequado")
        else: score -= 14; bloqueios.append("ROIC abaixo do filtro")
        if margem >= margem_ideal: score += 16; motivos.append("margem confortavel")
        elif margem >= margem_min: score += 9; motivos.append("margem minima atendida")
        else: score -= 16; bloqueios.append("margem abaixo de 8%")
        if roe >= 12: score += 6; motivos.append("ROE saudavel")
        if lucro_cagr >= 8: score += 6; motivos.append("crescimento de lucro")
        if pl and pl <= 18: score += 5; motivos.append("valuation aceitavel")
        elif pl > 28: score -= 8; bloqueios.append("valuation caro")
    if classe in ("FIIs", "REITs"):
        if dy >= dy_min: score += 12; motivos.append("renda passiva atrativa")
        else: score -= 8; bloqueios.append("renda passiva baixa")
        if pvp and pvp <= 1.05: score += 6; motivos.append("P/VP controlado")
        elif pvp > 1.20: score -= 6; bloqueios.append("P/VP esticado")
    if classe in ("ETFs",):
        if liquidez >= max(1000000, liquidez_min): score += 8; motivos.append("ETF com liquidez")
    if divida and divida <= divida_ideal: score += 10; motivos.append("divida controlada")
    elif divida > divida_max: score -= 18; bloqueios.append("divida elevada")
    if liquidez >= liquidez_min: score += 10; motivos.append("liquidez adequada")
    elif classe in ("Acoes Brasil", "FIIs", "Stocks", "REITs") and liquidez > 0: score -= 8; bloqueios.append("liquidez fraca")
    if any(x in gov for x in ("novo", "nivel", "nivel", "adr", "etf", "reit")): score += 8; motivos.append("governanca favoravel")
    if preco_teto and preco and preco <= preco_teto: score += 8; motivos.append("preco dentro do teto")
    elif preco_teto and preco > preco_teto: score -= 10; bloqueios.append("preco acima do teto")
    if status == "aportar": score += 8
    if status == "pausar": score = min(score, 35); bloqueios.append("marcado para pausar")
    score = max(0, min(100, int(round(score))))
    decisao = "Aportar" if score >= 75 and not bloqueios else "Observar" if score >= 55 else "Nao aportar"
    if status == "pausar": decisao = "Nao aportar"
    return score, decisao, motivos[:5], bloqueios[:5]


def listar_ativos():
    criterios = criterios_por_classe(); mercado = dados_mercado_map()
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM carteira_ativos ORDER BY classe,ticker")
        rows = cur.fetchall()
    conn.close(); out=[]
    for a in rows:
        a=dict(a); s,d,m,b=score_ativo(a, criterios, mercado); dado=mercado.get((a.get("ticker") or "").upper()) or {}
        a.update({"score":s,"decisao":d,"motivos":m,"bloqueios":b,"preco_mercado":dado.get("preco"),"mercado_atualizado_em":dado.get("atualizado_em")})
        out.append(a)
    return out


def listar_universo_acoes(limite=40):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM carteira_universo_acoes")
        rows = cur.fetchall()
    conn.close()
    itens = []
    for row in rows:
        a = dict(row)
        score, decisao, motivos, bloqueios = score_acao_universo(a)
        a.update({
            "score": score,
            "decisao": decisao,
            "motivos": motivos,
            "bloqueios": bloqueios,
            "classe": "Acoes Brasil",
            "nome": a.get("empresa"),
            "valor_atual": 0,
            "preco_medio": 0,
            "origem": "Planilha de Ouro",
        })
        itens.append(a)
    itens.sort(key=lambda x: (-x["score"], x.get("setor") or "", x.get("ticker") or ""))
    return itens[:limite]


def listar_politica():
    conn=get_db_connection()
    with conn.cursor() as cur: cur.execute("SELECT * FROM carteira_politica ORDER BY prioridade,classe"); rows=cur.fetchall()
    conn.close(); return rows


def resumo_classes(ativos=None, politica=None):
    ativos=ativos if ativos is not None else listar_ativos(); politica=politica if politica is not None else listar_politica(); total=sum(fnum(a.get("valor_atual")) for a in ativos); mapa={}
    for p in politica: mapa[p["classe"]]={"classe":p["classe"],"alvo":fnum(p["percentual_alvo"]),"limite":fnum(p["limite_por_ativo"]),"descricao":p.get("descricao") or "","valor":0,"atual":0,"gap":0,"ativos":0}
    for a in ativos:
        c=a.get("classe") or "Outros"; mapa.setdefault(c,{"classe":c,"alvo":0,"limite":10,"descricao":"","valor":0,"atual":0,"gap":0,"ativos":0}); mapa[c]["valor"]+=fnum(a.get("valor_atual")); mapa[c]["ativos"]+=1
    for g in mapa.values(): g["atual"]=(g["valor"]/total*100) if total else 0; g["gap"]=g["alvo"]-g["atual"]
    return sorted(mapa.values(), key=lambda x:(x["gap"]<=0,-x["gap"],x["classe"])), total


def recomendacoes(valor=Decimal("100000")):
    ativos=listar_ativos(); grupos,total=resumo_classes(ativos); universo_acoes=listar_universo_acoes(60)
    candidatos=sorted([a for a in ativos if a["decisao"]=="Aportar"] + [a for a in universo_acoes if a["decisao"]=="Aportar"], key=lambda a:-a["score"])
    prios=[g for g in grupos if g["gap"]>0] or grupos[:3]; soma=sum(max(0,g["gap"]) for g in prios) or len(prios) or 1; al=[]; v=fnum(valor)
    for g in prios:
        valor_classe=v*((max(0,g["gap"])/soma) if soma else 0); ativos_classe=[a for a in candidatos if a.get("classe")==g["classe"]]
        if not ativos_classe: al.append({"classe":g["classe"],"valor":valor_classe,"ativo":None,"motivo":"classe abaixo da meta; cadastre ativo elegivel"}); continue
        fatia=valor_classe/min(3,len(ativos_classe)) if valor_classe else 0
        for a in ativos_classe[:3]: al.append({"classe":g["classe"],"valor":fatia,"ativo":a,"motivo":", ".join(a["motivos"] or ["melhor score da classe"])})
    return al,candidatos,grupos,total


def listar_historico(limite=500):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT a.*, c.ticker, c.nome
            FROM carteira_aportes a
            LEFT JOIN carteira_ativos c ON c.id = a.ativo_id
            ORDER BY a.data_aporte DESC, a.id DESC
            LIMIT %s
        """, (limite,))
        rows = cur.fetchall()
    conn.close()
    return rows


def resumo_renda_passiva(periodo="mes"):
    hoje = date.today()
    meses_atras = {"mes": 1, "6m": 6, "12m": 12, "24m": 24}.get(periodo, 1)
    inicio = (hoje.replace(day=1) - timedelta(days=31 * (meses_atras - 1))).replace(day=1)
    passivos = []
    for item in listar_historico(1000):
        tipo = str(item.get("tipo") or "").lower()
        if tipo in ("dividendo", "jcp", "provento", "proventos"):
            passivos.append(dict(item))
    filtrados = [p for p in passivos if str(p.get("data_aporte") or "") >= inicio.isoformat()]
    total_periodo = sum(fnum(p.get("valor")) for p in filtrados)
    mes_atual = hoje.strftime("%Y-%m")
    total_mes = sum(fnum(p.get("valor")) for p in filtrados if str(p.get("data_aporte") or "").startswith(mes_atual))
    por = {}
    por_mes = {}
    for p in filtrados:
        chave = p.get("ticker") or p.get("classe") or "Sem ativo"
        por[chave] = por.get(chave, 0) + fnum(p.get("valor"))
        mes = str(p.get("data_aporte") or "")[:7] or mes_atual
        por_mes[mes] = por_mes.get(mes, 0) + fnum(p.get("valor"))
    maior = max(por_mes.values()) if por_mes else 0
    meses = []
    for i in range(max(1, meses_atras)):
        ref = (inicio + timedelta(days=31 * i)).strftime("%Y-%m")
        valor = por_mes.get(ref, 0)
        meses.append({"label": ref[5:] + "/" + ref[2:4], "valor": valor, "altura": (valor / maior * 100) if maior else 4})
    por_ativo = [{"ticker": k, "total": v} for k, v in sorted(por.items(), key=lambda x: -x[1])]
    return total_periodo, total_mes, por_ativo, meses, maior


def aplicar_movimento_ativo(cur, ativo_id, tipo, valor, quantidade, sentido=1):
    if not ativo_id:
        return
    tipo_normalizado = (tipo or "").strip().lower()
    if tipo_normalizado not in ("compra", "venda"):
        return
    cur.execute("SELECT quantidade, valor_atual FROM carteira_ativos WHERE id=%s", (ativo_id,))
    ativo = cur.fetchone()
    if not ativo:
        return
    valor = num(valor)
    quantidade = num(quantidade)
    sinal = Decimal(str(sentido))
    if tipo_normalizado == "venda":
        sinal *= Decimal("-1")
    nova_quantidade = max(Decimal("0"), num(ativo.get("quantidade")) + (quantidade * sinal))
    novo_valor = max(Decimal("0"), num(ativo.get("valor_atual")) + (valor * sinal))
    preco_medio = (novo_valor / nova_quantidade) if nova_quantidade > 0 else Decimal("0")
    cur.execute(
        "UPDATE carteira_ativos SET quantidade=%s, valor_atual=%s, preco_medio=%s WHERE id=%s",
        (nova_quantidade, novo_valor, preco_medio, ativo_id),
    )


def ticker_yahoo(ticker, classe, pais):
    t=(ticker or "").upper().strip()
    if pais == "Brasil" and classe in ("Acoes Brasil", "FIIs") and not t.endswith(".SA"):
        return t + ".SA"
    return t


def buscar_preco_yahoo(ticker, classe, pais):
    simbolo=ticker_yahoo(ticker, classe, pais)
    url=f"https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}?range=1d&interval=1d"
    req=urllib.request.Request(url, headers={"User-Agent":"JP2Business/1.0"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        data=json.loads(resp.read().decode("utf-8"))
    result=(data.get("chart",{}).get("result") or [None])[0]
    if not result: return None
    meta=result.get("meta",{})
    preco=meta.get("regularMarketPrice") or meta.get("previousClose")
    prev=meta.get("previousClose") or preco
    variacao=((float(preco)-float(prev))/float(prev)*100) if preco and prev else 0
    return {"preco": preco or 0, "variacao_dia": variacao, "fonte": "Yahoo Finance", "dados_json": json.dumps({"symbol": simbolo, "meta": meta})[:6000]}


@bp_carteira.route("/")
@login_required
def dashboard():
    ativos=listar_ativos(); grupos,total=resumo_classes(ativos); al,cand,_,_=recomendacoes(); score=round(sum(a["score"] for a in ativos)/len(ativos),1) if ativos else 0
    return render_template("carteira_dashboard.html", ativos=ativos, grupos=grupos, total=total, score_medio=score, candidatos=cand, alocacoes=al, br_money=br_money)


@bp_carteira.route("/ativos", methods=["GET","POST"])
@login_required
def ativos():
    if request.method=="POST":
        d=request.form; ativo_id=d.get("id"); payload=((d.get("ticker") or "").upper().strip(), d.get("nome") or "", d.get("classe") or "Acoes Brasil", d.get("pais") or "Brasil", d.get("setor") or "", d.get("moeda") or "BRL", num(d.get("quantidade")), num(d.get("preco_medio")), num(d.get("valor_atual")), num(d.get("dividend_yield")), num(d.get("roic")), num(d.get("margem_liquida")), num(d.get("divida_ebitda")), num(d.get("liquidez_diaria")), d.get("governanca") or "", d.get("status") or "observar", d.get("observacoes") or "", num(d.get("pl")), num(d.get("pvp")), num(d.get("roe")), num(d.get("lucro_cagr")), num(d.get("preco_teto")))
        conn=get_db_connection()
        with conn.cursor() as cur:
            if ativo_id:
                cur.execute("UPDATE carteira_ativos SET ticker=%s,nome=%s,classe=%s,pais=%s,setor=%s,moeda=%s,quantidade=%s,preco_medio=%s,valor_atual=%s,dividend_yield=%s,roic=%s,margem_liquida=%s,divida_ebitda=%s,liquidez_diaria=%s,governanca=%s,status=%s,observacoes=%s,pl=%s,pvp=%s,roe=%s,lucro_cagr=%s,preco_teto=%s WHERE id=%s", payload+(ativo_id,)); flash("Ativo atualizado.")
            else:
                cur.execute("INSERT INTO carteira_ativos (ticker,nome,classe,pais,setor,moeda,quantidade,preco_medio,valor_atual,dividend_yield,roic,margem_liquida,divida_ebitda,liquidez_diaria,governanca,status,observacoes,pl,pvp,roe,lucro_cagr,preco_teto) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE nome=VALUES(nome),classe=VALUES(classe),pais=VALUES(pais),setor=VALUES(setor),moeda=VALUES(moeda),quantidade=VALUES(quantidade),preco_medio=VALUES(preco_medio),valor_atual=VALUES(valor_atual),dividend_yield=VALUES(dividend_yield),roic=VALUES(roic),margem_liquida=VALUES(margem_liquida),divida_ebitda=VALUES(divida_ebitda),liquidez_diaria=VALUES(liquidez_diaria),governanca=VALUES(governanca),status=VALUES(status),observacoes=VALUES(observacoes),pl=VALUES(pl),pvp=VALUES(pvp),roe=VALUES(roe),lucro_cagr=VALUES(lucro_cagr),preco_teto=VALUES(preco_teto)", payload); flash("Ativo salvo.")
        conn.close(); return redirect(url_for("carteira.ativos"))
    return render_template("carteira_ativos.html", ativos=listar_ativos(), classes=CLASSES, br_money=br_money)


@bp_carteira.route("/ativos/excluir/<int:ativo_id>", methods=["POST"])
@login_required
def excluir_ativo(ativo_id):
    conn=get_db_connection()
    with conn.cursor() as cur: cur.execute("DELETE FROM carteira_ativos WHERE id=%s",(ativo_id,))
    conn.close(); flash("Ativo excluido."); return redirect(url_for("carteira.ativos"))


@bp_carteira.route("/aportes", methods=["GET","POST"])
@login_required
def aportes():
    if request.method=="POST":
        conn=get_db_connection(); aid=request.form.get("ativo_id") or None; classe=request.form.get("classe") or "Caixa oportunidade"
        tipo = request.form.get("tipo") or "compra"
        valor = num(request.form.get("valor"))
        quantidade = num(request.form.get("quantidade"))
        if aid:
            with conn.cursor() as cur: cur.execute("SELECT classe FROM carteira_ativos WHERE id=%s",(aid,)); a=cur.fetchone(); classe=a["classe"] if a else classe
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO carteira_aportes (ativo_id,classe,tipo,valor,quantidade,data_aporte,observacoes,criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (aid, classe, tipo, valor, quantidade, request.form.get("data_aporte") or date.today().isoformat(), request.form.get("observacoes") or "", session.get("nome_exibicao") or session.get("usuario_logado")),
            )
            aplicar_movimento_ativo(cur, aid, tipo, valor, quantidade, sentido=1)
        conn.close(); flash("Movimentacao registrada."); return redirect(url_for("carteira.aportes"))
    return render_template(
        "carteira_aportes.html",
        ativos=listar_ativos(),
        aportes=listar_historico(),
        classes=CLASSES,
        hoje=date.today().isoformat(),
        tipo=request.args.get("tipo") or "compra",
        ativo_id=request.args.get("ativo_id"),
        br_money=br_money,
    )


@bp_carteira.route("/aportes/excluir/<int:aporte_id>", methods=["POST"])
@login_required
def excluir_aporte(aporte_id):
    conn=get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT ativo_id,tipo,valor,quantidade FROM carteira_aportes WHERE id=%s",(aporte_id,))
        aporte = cur.fetchone()
        if aporte:
            aplicar_movimento_ativo(cur, aporte.get("ativo_id"), aporte.get("tipo"), aporte.get("valor"), aporte.get("quantidade"), sentido=-1)
        cur.execute("DELETE FROM carteira_aportes WHERE id=%s",(aporte_id,))
    conn.close(); flash("Movimentacao excluida."); return redirect(url_for("carteira.aportes"))


@bp_carteira.route("/onde-aportar", methods=["GET","POST"])
@login_required
def onde_aportar():
    valor=num(request.form.get("valor_aporte"),100000) if request.method=="POST" else Decimal("100000"); al,cand,grupos,total=recomendacoes(valor)
    return render_template("carteira_onde_aportar.html", valor=valor, alocacoes=al, candidatos=cand, grupos=grupos, total=total, br_money=br_money)


@bp_carteira.route("/resumo")
@login_required
def resumo():
    ativos=listar_ativos(); grupos,total=resumo_classes(ativos)
    renda_total, renda_mes, _, _, maior_renda = resumo_renda_passiva("24m")
    return render_template("carteira_resumo.html", ativos=ativos, grupos=grupos, total=total, renda_total=renda_total, renda_mes=renda_mes, maior_renda=maior_renda, br_money=br_money)


@bp_carteira.route("/configuracoes", methods=["GET","POST"])
@login_required
def configuracoes():
    if request.method=="POST":
        conn=get_db_connection()
        with conn.cursor() as cur:
            for classe in request.form.getlist("classe"):
                cur.execute("UPDATE carteira_politica SET percentual_alvo=%s, limite_por_ativo=%s, descricao=%s WHERE classe=%s", (num(request.form.get(f"alvo_{classe}")), num(request.form.get(f"limite_{classe}"),10), request.form.get(f"descricao_{classe}") or "", classe))
        conn.close(); flash("Politica atualizada."); return redirect(url_for("carteira.configuracoes"))
    politica = listar_politica()
    mapa = {p["classe"]: fnum(p["percentual_alvo"]) for p in politica}
    renda_variavel = 100 - mapa.get("Renda fixa", 0) - mapa.get("Reserva de emergencia", 0)
    brasil = mapa.get("Acoes Brasil", 0) + mapa.get("FIIs", 0)
    exterior = mapa.get("Stocks", 0) + mapa.get("REITs", 0) + mapa.get("ETFs", 0)
    return render_template("carteira_configuracoes.html", politica=politica, mapa=mapa, renda_variavel=renda_variavel, brasil=brasil, exterior=exterior)


@bp_carteira.route("/historico")
@login_required
def historico():
    return render_template("carteira_historico.html", historico=listar_historico(), br_money=br_money)


@bp_carteira.route("/renda-passiva")
@login_required
def renda_passiva():
    periodo = request.args.get("periodo") or "mes"
    total_periodo, total_mes, por_ativo, meses, _ = resumo_renda_passiva(periodo)
    return render_template("carteira_renda_passiva.html", periodo=periodo, total_periodo=total_periodo, total_mes=total_mes, por_ativo=por_ativo, meses=meses, br_money=br_money)


@bp_carteira.route("/reserva", methods=["GET", "POST"])
@login_required
def reserva():
    custo = Decimal("0")
    meses = 8
    if request.method == "POST":
        custo = num(request.form.get("custo_mensal"))
        soma = sum(num(request.form.get(c)) for c in ("moradia", "contas", "internet", "transporte", "compras", "saude"))
        if soma > 0:
            custo = soma
        meses = int(fnum(request.form.get("meses")) or 8)
    valor = custo * Decimal(str(meses))
    return render_template("carteira_reserva.html", custo_mensal=custo, meses_recomendados=meses, valor_reserva=valor, br_money=br_money)


@bp_carteira.route("/api/resumo")
@login_required
def api_resumo():
    ativos=listar_ativos(); grupos,total=resumo_classes(ativos); return jsonify({"total":total,"classes":grupos,"ativos":ativos})


@bp_carteira.route("/api/ranking-acoes")
@login_required
def api_ranking_acoes():
    limite = int(fnum(request.args.get("limite")) or 30)
    ranking = listar_universo_acoes(max(5, min(limite, 100)))
    return jsonify({
        "fonte": "Planilha de Ouro Acoes Filtrada - Junho 2026",
        "criterios": {
            "sociedade": ["tag along", "free float", "governanca", "governo majoritario"],
            "lucro": ["margem EBIT", "margem liquida", "ROIC", "ROE", "anos gerando lucro"],
            "negocio": ["setor", "patrimonio liquido", "liquidez media diaria", "divida liquida/EBITDA"],
            "retorno": ["dividend yield", "CAGR do lucro em 5 anos", "soma dividendos + CAGR"],
        },
        "ranking": ranking,
    })


@bp_carteira.route("/api/sincronizar-mercado", methods=["POST"])
@login_required
def api_sincronizar_mercado():
    ativos = listar_ativos(); atualizados = 0; falhas = []
    conn = get_db_connection()
    with conn.cursor() as cur:
        for ativo in ativos[:40]:
            try:
                dado = buscar_preco_yahoo(ativo["ticker"], ativo["classe"], ativo.get("pais") or "Brasil")
                if not dado: continue
                cur.execute("""
                    INSERT INTO carteira_dados_mercado (ticker, preco, variacao_dia, fonte, dados_json)
                    VALUES (%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE preco=VALUES(preco), variacao_dia=VALUES(variacao_dia), fonte=VALUES(fonte), dados_json=VALUES(dados_json)
                """, (ativo["ticker"], dado["preco"], dado["variacao_dia"], dado["fonte"], dado["dados_json"]))
                atualizados += 1; time.sleep(0.15)
            except Exception as exc:
                falhas.append(f"{ativo['ticker']}: {str(exc)[:80]}")
    conn.close()
    return jsonify({"status":"sucesso", "atualizados":atualizados, "falhas":falhas[:8]})


