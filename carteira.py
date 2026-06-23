from datetime import date
from decimal import Decimal, InvalidOperation
from functools import wraps
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from database import get_db_connection

bp_carteira = Blueprint("carteira", __name__, url_prefix="/carteira")
TABELAS_OK = False
CLASSES = ["Reserva de emergência", "Renda fixa", "Ações Brasil", "FIIs", "Stocks", "REITs", "ETFs", "Caixa oportunidade"]
POLITICA_PADRAO = [
    ("Reserva de emergência", 15, 100, 1, "Liquidez e segurança para curto prazo."),
    ("Renda fixa", 25, 100, 2, "Selic, IPCA+ e proteção de médio prazo."),
    ("Ações Brasil", 20, 12, 3, "Empresas brasileiras com lucro, margem e ROIC."),
    ("FIIs", 15, 10, 4, "Renda imobiliária e geração de caixa."),
    ("Stocks", 12, 10, 5, "Empresas globais e moeda forte."),
    ("REITs", 8, 8, 6, "Imóveis internacionais em dólar."),
    ("ETFs", 5, 15, 7, "Diversificação ampla."),
]

def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "usuario_logado" not in session:
            return redirect(url_for("tela_login"))
        garantir_tabelas()
        return view(*args, **kwargs)
    return wrapper

def num(valor, padrao=0):
    if valor is None: return Decimal(str(padrao))
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if not texto: return Decimal(str(padrao))
    if "," in texto: texto = texto.replace(".", "").replace(",", ".")
    try: return Decimal(texto)
    except InvalidOperation: return Decimal(str(padrao))

def fnum(valor):
    try: return float(valor or 0)
    except Exception: return 0.0

def br_money(valor):
    return f"R$ {fnum(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def garantir_tabelas():
    global TABELAS_OK
    if TABELAS_OK: return
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
        cur.execute("SELECT COUNT(*) AS total FROM carteira_politica")
        if int(cur.fetchone()["total"] or 0) == 0:
            cur.executemany("INSERT INTO carteira_politica (classe, percentual_alvo, limite_por_ativo, prioridade, descricao) VALUES (%s,%s,%s,%s,%s)", POLITICA_PADRAO)
    conn.close(); TABELAS_OK = True

def score_ativo(a):
    classe=(a.get("classe") or ""); status=(a.get("status") or "observar").lower(); score=50; motivos=[]; bloqueios=[]
    roic=fnum(a.get("roic")); margem=fnum(a.get("margem_liquida")); divida=fnum(a.get("divida_ebitda")); liquidez=fnum(a.get("liquidez_diaria")); dy=fnum(a.get("dividend_yield")); gov=(a.get("governanca") or "").lower()
    if roic >= 15: score += 18; motivos.append("ROIC forte")
    elif roic >= 10: score += 12; motivos.append("ROIC adequado")
    elif classe in ("Ações Brasil", "Stocks"): score -= 12; bloqueios.append("ROIC baixo")
    if margem >= 12: score += 16; motivos.append("margem confortável")
    elif margem >= 8: score += 9; motivos.append("margem mínima atendida")
    elif classe in ("Ações Brasil", "Stocks"): score -= 15; bloqueios.append("margem abaixo de 8%")
    if divida and divida <= 2.5: score += 10; motivos.append("dívida controlada")
    elif divida > 3.5: score -= 18; bloqueios.append("dívida elevada")
    if liquidez >= 6000000: score += 10; motivos.append("liquidez adequada")
    elif classe in ("Ações Brasil", "FIIs", "Stocks", "REITs") and liquidez > 0: score -= 8; bloqueios.append("liquidez fraca")
    if any(x in gov for x in ("novo", "nível", "nivel", "adr", "etf", "reit")): score += 8; motivos.append("governança favorável")
    if dy >= 6: score += 5; motivos.append("renda passiva")
    if status == "aportar": score += 8
    if status == "pausar": score = min(score, 35); bloqueios.append("marcado para pausar")
    score=max(0,min(100,int(round(score))))
    decisao="Aportar" if score >= 75 and not bloqueios else "Observar" if score >= 55 else "Não aportar"
    if status == "pausar": decisao="Não aportar"
    return score, decisao, motivos[:4], bloqueios[:4]

def listar_ativos():
    conn=get_db_connection()
    with conn.cursor() as cur: cur.execute("SELECT * FROM carteira_ativos ORDER BY classe,ticker"); rows=cur.fetchall()
    conn.close(); out=[]
    for a in rows:
        a=dict(a); s,d,m,b=score_ativo(a); a.update({"score":s,"decisao":d,"motivos":m,"bloqueios":b}); out.append(a)
    return out

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
    ativos=listar_ativos(); grupos,total=resumo_classes(ativos); candidatos=sorted([a for a in ativos if a["decisao"]=="Aportar"], key=lambda a:-a["score"]); prios=[g for g in grupos if g["gap"]>0] or grupos[:3]; soma=sum(max(0,g["gap"]) for g in prios) or len(prios) or 1; al=[]; v=fnum(valor)
    for g in prios:
        valor_classe=v*((max(0,g["gap"])/soma) if soma else 0); ativos_classe=[a for a in candidatos if a.get("classe")==g["classe"]]
        if not ativos_classe: al.append({"classe":g["classe"],"valor":valor_classe,"ativo":None,"motivo":"classe abaixo da meta; cadastre ativo elegível"}); continue
        fatia=valor_classe/min(3,len(ativos_classe)) if valor_classe else 0
        for a in ativos_classe[:3]: al.append({"classe":g["classe"],"valor":fatia,"ativo":a,"motivo":", ".join(a["motivos"] or ["melhor score da classe"])})
    return al,candidatos,grupos,total

@bp_carteira.route("/")
@login_required
def dashboard():
    ativos=listar_ativos(); grupos,total=resumo_classes(ativos); al,cand,_,_=recomendacoes(); score=round(sum(a["score"] for a in ativos)/len(ativos),1) if ativos else 0
    return render_template("carteira_dashboard.html", ativos=ativos, grupos=grupos, total=total, score_medio=score, candidatos=cand, alocacoes=al, br_money=br_money)

@bp_carteira.route("/ativos", methods=["GET","POST"])
@login_required
def ativos():
    if request.method=="POST":
        d=request.form; ativo_id=d.get("id"); payload=((d.get("ticker") or "").upper().strip(), d.get("nome") or "", d.get("classe") or "Ações Brasil", d.get("pais") or "Brasil", d.get("setor") or "", d.get("moeda") or "BRL", num(d.get("quantidade")), num(d.get("preco_medio")), num(d.get("valor_atual")), num(d.get("dividend_yield")), num(d.get("roic")), num(d.get("margem_liquida")), num(d.get("divida_ebitda")), num(d.get("liquidez_diaria")), d.get("governanca") or "", d.get("status") or "observar", d.get("observacoes") or "")
        conn=get_db_connection()
        with conn.cursor() as cur:
            if ativo_id:
                cur.execute("UPDATE carteira_ativos SET ticker=%s,nome=%s,classe=%s,pais=%s,setor=%s,moeda=%s,quantidade=%s,preco_medio=%s,valor_atual=%s,dividend_yield=%s,roic=%s,margem_liquida=%s,divida_ebitda=%s,liquidez_diaria=%s,governanca=%s,status=%s,observacoes=%s WHERE id=%s", payload+(ativo_id,)); flash("Ativo atualizado.")
            else:
                cur.execute("INSERT INTO carteira_ativos (ticker,nome,classe,pais,setor,moeda,quantidade,preco_medio,valor_atual,dividend_yield,roic,margem_liquida,divida_ebitda,liquidez_diaria,governanca,status,observacoes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE nome=VALUES(nome),classe=VALUES(classe),pais=VALUES(pais),setor=VALUES(setor),moeda=VALUES(moeda),quantidade=VALUES(quantidade),preco_medio=VALUES(preco_medio),valor_atual=VALUES(valor_atual),dividend_yield=VALUES(dividend_yield),roic=VALUES(roic),margem_liquida=VALUES(margem_liquida),divida_ebitda=VALUES(divida_ebitda),liquidez_diaria=VALUES(liquidez_diaria),governanca=VALUES(governanca),status=VALUES(status),observacoes=VALUES(observacoes)", payload); flash("Ativo salvo.")
        conn.close(); return redirect(url_for("carteira.ativos"))
    return render_template("carteira_ativos.html", ativos=listar_ativos(), classes=CLASSES, br_money=br_money)

@bp_carteira.route("/ativos/excluir/<int:ativo_id>", methods=["POST"])
@login_required
def excluir_ativo(ativo_id):
    conn=get_db_connection();
    with conn.cursor() as cur: cur.execute("DELETE FROM carteira_ativos WHERE id=%s",(ativo_id,))
    conn.close(); flash("Ativo excluído."); return redirect(url_for("carteira.ativos"))

@bp_carteira.route("/aportes", methods=["GET","POST"])
@login_required
def aportes():
    if request.method=="POST":
        conn=get_db_connection(); aid=request.form.get("ativo_id") or None; classe=request.form.get("classe") or "Caixa oportunidade"
        if aid:
            with conn.cursor() as cur: cur.execute("SELECT classe FROM carteira_ativos WHERE id=%s",(aid,)); a=cur.fetchone(); classe=a["classe"] if a else classe
        with conn.cursor() as cur: cur.execute("INSERT INTO carteira_aportes (ativo_id,classe,tipo,valor,data_aporte,observacoes,criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s)",(aid,classe,request.form.get("tipo") or "compra",num(request.form.get("valor")),request.form.get("data_aporte") or date.today().isoformat(),request.form.get("observacoes") or "",session.get("nome_exibicao") or session.get("usuario_logado")))
        conn.close(); flash("Aporte registrado."); return redirect(url_for("carteira.aportes"))
    conn=get_db_connection();
    with conn.cursor() as cur: cur.execute("SELECT a.*, c.ticker, c.nome FROM carteira_aportes a LEFT JOIN carteira_ativos c ON c.id=a.ativo_id ORDER BY a.data_aporte DESC,a.id DESC LIMIT 500"); lista=cur.fetchall()
    conn.close(); return render_template("carteira_aportes.html", ativos=listar_ativos(), aportes=lista, classes=CLASSES, hoje=date.today().isoformat(), br_money=br_money)

@bp_carteira.route("/aportes/excluir/<int:aporte_id>", methods=["POST"])
@login_required
def excluir_aporte(aporte_id):
    conn=get_db_connection();
    with conn.cursor() as cur: cur.execute("DELETE FROM carteira_aportes WHERE id=%s",(aporte_id,))
    conn.close(); flash("Aporte excluído."); return redirect(url_for("carteira.aportes"))

@bp_carteira.route("/onde-aportar", methods=["GET","POST"])
@login_required
def onde_aportar():
    valor=num(request.form.get("valor_aporte"),100000) if request.method=="POST" else Decimal("100000"); al,cand,grupos,total=recomendacoes(valor)
    return render_template("carteira_onde_aportar.html", valor=valor, alocacoes=al, candidatos=cand, grupos=grupos, total=total, br_money=br_money)

@bp_carteira.route("/resumo")
@login_required
def resumo():
    ativos=listar_ativos(); grupos,total=resumo_classes(ativos); return render_template("carteira_resumo.html", ativos=ativos, grupos=grupos, total=total, br_money=br_money)

@bp_carteira.route("/configuracoes", methods=["GET","POST"])
@login_required
def configuracoes():
    if request.method=="POST":
        conn=get_db_connection();
        with conn.cursor() as cur:
            for classe in request.form.getlist("classe"):
                cur.execute("UPDATE carteira_politica SET percentual_alvo=%s, limite_por_ativo=%s, descricao=%s WHERE classe=%s", (num(request.form.get(f"alvo_{classe}")), num(request.form.get(f"limite_{classe}"),10), request.form.get(f"descricao_{classe}") or "", classe))
        conn.close(); flash("Política atualizada."); return redirect(url_for("carteira.configuracoes"))
    return render_template("carteira_configuracoes.html", politica=listar_politica())

@bp_carteira.route("/api/resumo")
@login_required
def api_resumo():
    ativos=listar_ativos(); grupos,total=resumo_classes(ativos); return jsonify({"total":total,"classes":grupos,"ativos":ativos})
