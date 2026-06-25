from datetime import datetime
import csv
import io
from flask import Blueprint, jsonify, make_response, render_template, request, session
from database import get_db_connection

bp_eventos = Blueprint("eventos", __name__)


def login_ok():
    return "usuario_logado" in session


def n(valor):
    texto = str(valor or "0").strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except Exception:
        return 0.0


def data_ok(valor):
    try:
        if not valor:
            return None
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        return None


def garantir_tabelas_eventos():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS eventos_cadastro (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    cidade VARCHAR(140) NOT NULL,
                    uf VARCHAR(2) NOT NULL,
                    regiao VARCHAR(80) NULL,
                    nome_evento VARCHAR(220) NOT NULL,
                    data_inicio DATE NOT NULL,
                    data_fim DATE NOT NULL,
                    mes VARCHAR(30) NULL,
                    dias_evento INT DEFAULT 1,
                    valor_verba DECIMAL(18,2) DEFAULT 0,
                    origem VARCHAR(80) NULL,
                    status VARCHAR(60) DEFAULT 'Pendente',
                    observacoes TEXT NULL,
                    criado_por VARCHAR(120) NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS eventos_financeiro (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    evento_id INT NOT NULL UNIQUE,
                    percentual_parlamentar DECIMAL(10,4) DEFAULT 0,
                    observacoes TEXT NULL,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS eventos_custos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    evento_id INT NOT NULL,
                    categoria VARCHAR(80) NOT NULL,
                    descricao VARCHAR(220) NULL,
                    fornecedor VARCHAR(180) NULL,
                    valor DECIMAL(18,2) DEFAULT 0,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)
        conn.commit()
    finally:
        conn.close()


def mes_nome(data_iso):
    nomes = ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    try:
        return nomes[datetime.strptime(data_iso, "%Y-%m-%d").month - 1]
    except Exception:
        return ""


def dias_evento(inicio, fim):
    try:
        di = datetime.strptime(inicio, "%Y-%m-%d")
        df = datetime.strptime(fim, "%Y-%m-%d")
        return max(1, (df - di).days + 1)
    except Exception:
        return 1


def evento_dict(row):
    item = dict(row)
    for campo in ("data_inicio", "data_fim"):
        item[campo] = str(item.get(campo) or "")[:10]
    item["valor_verba"] = float(item.get("valor_verba") or 0)
    item["dias_evento"] = int(item.get("dias_evento") or dias_evento(item.get("data_inicio"), item.get("data_fim")))
    return item


@bp_eventos.route("/eventos")
def tela_eventos():
    if not login_ok():
        return make_response("Nao autorizado", 401)
    garantir_tabelas_eventos()
    return render_template("eventos.html")


@bp_eventos.route("/api/eventos", methods=["GET", "POST"])
def api_eventos():
    if not login_ok():
        return jsonify({"status": "erro"}), 401
    garantir_tabelas_eventos()
    if request.method == "POST":
        return salvar_evento(None)

    filtros = {
        "uf": request.args.get("uf"),
        "regiao": request.args.get("regiao"),
        "mes": request.args.get("mes"),
        "origem": request.args.get("origem"),
        "status": request.args.get("status"),
        "q": request.args.get("q"),
        "inicio": data_ok(request.args.get("inicio")),
        "fim": data_ok(request.args.get("fim")),
    }
    where, params = [], []
    for campo in ("uf", "regiao", "mes", "origem", "status"):
        if filtros[campo]:
            where.append(f"{campo}=%s")
            params.append(filtros[campo])
    if filtros["q"]:
        where.append("(nome_evento LIKE %s OR cidade LIKE %s OR observacoes LIKE %s)")
        termo = f"%{filtros['q']}%"
        params.extend([termo, termo, termo])
    if filtros["inicio"]:
        where.append("data_inicio >= %s")
        params.append(filtros["inicio"])
    if filtros["fim"]:
        where.append("data_fim <= %s")
        params.append(filtros["fim"])
    sql = "SELECT * FROM eventos_cadastro"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY data_inicio ASC, cidade ASC, nome_evento ASC"
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            dados = [evento_dict(r) for r in cur.fetchall()]
        return jsonify({"status": "sucesso", "dados": dados})
    finally:
        conn.close()


@bp_eventos.route("/api/eventos/<int:evento_id>", methods=["POST", "DELETE"])
def api_evento_id(evento_id):
    if not login_ok():
        return jsonify({"status": "erro"}), 401
    garantir_tabelas_eventos()
    if request.method == "DELETE":
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM eventos_custos WHERE evento_id=%s", (evento_id,))
                cur.execute("DELETE FROM eventos_financeiro WHERE evento_id=%s", (evento_id,))
                cur.execute("DELETE FROM eventos_cadastro WHERE id=%s", (evento_id,))
            conn.commit()
            return jsonify({"status": "sucesso"})
        finally:
            conn.close()
    return salvar_evento(evento_id)


def salvar_evento(evento_id):
    cidade = (request.form.get("cidade") or "").strip()
    uf = (request.form.get("uf") or "").strip().upper()[:2]
    regiao = (request.form.get("regiao") or "").strip()
    nome_evento = (request.form.get("nome_evento") or "").strip()
    data_inicio = data_ok(request.form.get("data_inicio"))
    data_fim = data_ok(request.form.get("data_fim")) or data_inicio
    if not cidade or not uf or not nome_evento or not data_inicio:
        return jsonify({"status": "erro", "msg": "Preencha cidade, UF, evento e data."}), 400
    if data_fim < data_inicio:
        return jsonify({"status": "erro", "msg": "Data final nao pode ser anterior a inicial."}), 400
    payload = (
        cidade,
        uf,
        regiao,
        nome_evento,
        data_inicio,
        data_fim,
        mes_nome(data_inicio),
        dias_evento(data_inicio, data_fim),
        n(request.form.get("valor_verba")),
        request.form.get("origem") or "",
        request.form.get("status") or "Pendente",
        request.form.get("observacoes") or "",
    )
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if evento_id:
                cur.execute("""
                    UPDATE eventos_cadastro
                    SET cidade=%s, uf=%s, regiao=%s, nome_evento=%s, data_inicio=%s, data_fim=%s,
                        mes=%s, dias_evento=%s, valor_verba=%s, origem=%s, status=%s, observacoes=%s
                    WHERE id=%s
                """, payload + (evento_id,))
            else:
                cur.execute("""
                    INSERT INTO eventos_cadastro
                    (cidade, uf, regiao, nome_evento, data_inicio, data_fim, mes, dias_evento, valor_verba, origem, status, observacoes, criado_por)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, payload + (session.get("nome_exibicao") or session.get("usuario_logado") or "Sistema",))
                evento_id = cur.lastrowid
        conn.commit()
        return jsonify({"status": "sucesso", "id": evento_id})
    finally:
        conn.close()


@bp_eventos.route("/api/eventos/municipios")
def api_eventos_municipios():
    q = (request.args.get("q") or "").strip().upper()
    base = [
        ("GO", "CENTRO-OESTE", "GOIANIA"),
        ("GO", "CENTRO-OESTE", "ITAPURANGA"),
        ("GO", "CENTRO-OESTE", "AVELINOPOLIS"),
        ("GO", "CENTRO-OESTE", "TURVANIA"),
        ("GO", "CENTRO-OESTE", "URUAÇU"),
        ("MG", "SUDESTE", "CHAPADA GAUCHA"),
    ]
    dados = []
    for uf, regiao, cidade in base:
        if not q or q in cidade or q in uf:
            dados.append({"uf": uf, "regiao": regiao, "cidade": cidade.title(), "label": f"{cidade.title()} - {uf}"})
    return jsonify({"status": "sucesso", "dados": dados[:30]})


@bp_eventos.route("/api/eventos/financeiro/<int:evento_id>", methods=["GET", "POST"])
def api_evento_financeiro(evento_id):
    if not login_ok():
        return jsonify({"status": "erro"}), 401
    garantir_tabelas_eventos()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if request.method == "POST":
                cur.execute("""
                    INSERT INTO eventos_financeiro (evento_id, percentual_parlamentar, observacoes)
                    VALUES (%s,%s,%s)
                    ON DUPLICATE KEY UPDATE percentual_parlamentar=VALUES(percentual_parlamentar), observacoes=VALUES(observacoes)
                """, (evento_id, n(request.form.get("percentual_parlamentar")), request.form.get("observacoes") or ""))
                conn.commit()
            cur.execute("SELECT * FROM eventos_cadastro WHERE id=%s", (evento_id,))
            evento = cur.fetchone()
            if not evento:
                return jsonify({"status": "erro", "msg": "Evento nao encontrado"}), 404
            cur.execute("SELECT * FROM eventos_financeiro WHERE evento_id=%s", (evento_id,))
            financeiro = cur.fetchone() or {}
            cur.execute("SELECT * FROM eventos_custos WHERE evento_id=%s ORDER BY categoria, descricao", (evento_id,))
            custos = [dict(c) for c in cur.fetchall()]
        valor = float(evento.get("valor_verba") or 0)
        percentual = float(financeiro.get("percentual_parlamentar") or 0)
        total_custos = sum(float(c.get("valor") or 0) for c in custos)
        valor_parlamentar = valor * percentual / 100
        dados = {
            "evento": evento_dict(evento),
            "percentual_parlamentar": percentual,
            "observacoes": financeiro.get("observacoes") or "",
            "custos": custos,
            "total_custos": total_custos,
            "valor_parlamentar": valor_parlamentar,
            "resultado_instituto": valor - valor_parlamentar - total_custos,
        }
        return jsonify({"status": "sucesso", "dados": dados})
    finally:
        conn.close()


@bp_eventos.route("/api/eventos/financeiro/<int:evento_id>/custos", methods=["POST"])
def api_evento_custo_novo(evento_id):
    return salvar_custo(evento_id, None)


@bp_eventos.route("/api/eventos/financeiro/custos/<int:custo_id>", methods=["POST", "DELETE"])
def api_evento_custo_id(custo_id):
    if not login_ok():
        return jsonify({"status": "erro"}), 401
    garantir_tabelas_eventos()
    if request.method == "DELETE":
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM eventos_custos WHERE id=%s", (custo_id,))
            conn.commit()
            return jsonify({"status": "sucesso"})
        finally:
            conn.close()
    return salvar_custo(None, custo_id)


def salvar_custo(evento_id, custo_id):
    if not login_ok():
        return jsonify({"status": "erro"}), 401
    garantir_tabelas_eventos()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if custo_id:
                cur.execute("""
                    UPDATE eventos_custos
                    SET categoria=%s, descricao=%s, fornecedor=%s, valor=%s
                    WHERE id=%s
                """, (request.form.get("categoria") or "Outros", request.form.get("descricao") or "", request.form.get("fornecedor") or "", n(request.form.get("valor")), custo_id))
            else:
                cur.execute("""
                    INSERT INTO eventos_custos (evento_id, categoria, descricao, fornecedor, valor)
                    VALUES (%s,%s,%s,%s,%s)
                """, (evento_id, request.form.get("categoria") or "Outros", request.form.get("descricao") or "", request.form.get("fornecedor") or "", n(request.form.get("valor"))))
        conn.commit()
        return jsonify({"status": "sucesso"})
    finally:
        conn.close()


@bp_eventos.route("/eventos/exportar")
def exportar_eventos():
    if not login_ok():
        return make_response("Nao autorizado", 401)
    garantir_tabelas_eventos()
    filtros = {
        "uf": request.args.get("uf"),
        "regiao": request.args.get("regiao"),
        "mes": request.args.get("mes"),
        "origem": request.args.get("origem"),
        "status": request.args.get("status"),
        "q": request.args.get("q"),
        "inicio": data_ok(request.args.get("inicio")),
        "fim": data_ok(request.args.get("fim")),
    }
    where, params = [], []
    for campo in ("uf", "regiao", "mes", "origem", "status"):
        if filtros[campo]:
            where.append(f"{campo}=%s")
            params.append(filtros[campo])
    if filtros["q"]:
        where.append("(nome_evento LIKE %s OR cidade LIKE %s OR observacoes LIKE %s)")
        termo = f"%{filtros['q']}%"
        params.extend([termo, termo, termo])
    if filtros["inicio"]:
        where.append("data_inicio >= %s")
        params.append(filtros["inicio"])
    if filtros["fim"]:
        where.append("data_fim <= %s")
        params.append(filtros["fim"])
    sql = "SELECT * FROM eventos_cadastro"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY data_inicio ASC, cidade ASC, nome_evento ASC"
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            dados = [evento_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    saida = io.StringIO()
    writer = csv.writer(saida, delimiter=";")
    writer.writerow(["Evento", "Cidade", "UF", "Regiao", "Inicio", "Fim", "Dias", "Valor", "Origem", "Status", "Observacoes"])
    for e in dados:
        writer.writerow([e.get("nome_evento"), e.get("cidade"), e.get("uf"), e.get("regiao"), e.get("data_inicio"), e.get("data_fim"), e.get("dias_evento"), f"R$ {float(e.get('valor_verba') or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), e.get("origem"), e.get("status"), e.get("observacoes")])
    res = make_response("\ufeff" + saida.getvalue())
    res.headers["Content-Type"] = "text/csv; charset=utf-8"
    res.headers["Content-Disposition"] = "attachment; filename=eventos-jp2.csv"
    return res


@bp_eventos.route("/api/eventos/sincronizar-csv", methods=["POST"])
def sincronizar_csv():
    return jsonify({"status": "sucesso", "importados": 0})
