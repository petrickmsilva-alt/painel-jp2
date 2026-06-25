import csv
import os
import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, Response, jsonify, redirect, render_template, request, session, url_for

from database import get_db_connection


bp_eventos = Blueprint("eventos", __name__)

EVENTOS_SCHEMA_VERIFICADO = False
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_EVENTOS = os.path.join(BASE_DIR, "data", "dados_eventos.csv")
CSV_MUNICIPIOS = os.path.join(BASE_DIR, "data", "municipios.csv")
MUNICIPIOS_CACHE = None

STATUS_OPCOES = ["Autorizado", "Em Andamento", "Pendente", "Em AnÃ¡lise", "Encerrado"]
ORIGEM_OPCOES = ["Emenda Direta", "Fomento", "Emenda PÃ³s", "Privado"]
MESES = {
    1: "janeiro",
    2: "fevereiro",
    3: "marÃ§o",
    4: "abril",
    5: "maio",
    6: "junho",
    7: "julho",
    8: "agosto",
    9: "setembro",
    10: "outubro",
    11: "novembro",
    12: "dezembro",
}


def login_obrigatorio_json():
    if "usuario_logado" not in session:
        return jsonify({"status": "erro", "msg": "NÃ£o autorizado"}), 401
    return None


def reparar_texto(valor):
    texto = str(valor or "").strip()
    if not texto:
        return ""
    if any(marca in texto for marca in ("Ãƒ", "Ã‚", "Ã¢")):
        try:
            texto = texto.encode("latin1").decode("utf-8")
        except UnicodeError:
            pass
    texto = texto.replace("dezember", "dezembro").replace("Dezember", "Dezembro")
    return re.sub(r"\s+", " ", texto).strip()


def normalizar_busca(valor):
    texto = reparar_texto(valor).upper()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(ch for ch in texto if not unicodedata.combining(ch))


def normalizar_status_evento(valor):
    texto = reparar_texto(valor)
    if texto.lower() in {"", "undefined", "null", "none"}:
        return "Pendente"
    texto_normalizado = normalizar_busca(texto)
    for opcao in STATUS_OPCOES:
        if normalizar_busca(opcao) == texto_normalizado:
            return opcao
    return "Pendente"


def decimal_ou_zero(valor):
    if isinstance(valor, Decimal):
        return valor
    texto = str(valor or "").strip()
    texto = texto.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def data_ou_none(valor):
    texto = str(valor or "").strip()
    if not texto:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto[:10], formato).date()
        except ValueError:
            continue
    return None


def dinheiro(valor):
    numero = decimal_ou_zero(valor)
    return f"R$ {numero:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def dias_evento(inicio, fim):
    if not inicio or not fim:
        return 0
    return max((fim - inicio).days + 1, 1)


def normalizar_evento(row):
    return {
        "id": row.get("id"),
        "cidade": row.get("cidade") or "",
        "uf": row.get("uf") or "",
        "regiao": row.get("regiao") or "",
        "nome_evento": row.get("nome_evento") or "",
        "data_inicio": row.get("data_inicio").isoformat() if row.get("data_inicio") else "",
        "data_fim": row.get("data_fim").isoformat() if row.get("data_fim") else "",
        "mes": row.get("mes") or "",
        "dias_evento": int(row.get("dias_evento") or 0),
        "valor_verba": float(decimal_ou_zero(row.get("valor_verba"))),
        "valor_verba_formatado": dinheiro(row.get("valor_verba")),
        "origem": row.get("origem") or "",
        "status": normalizar_status_evento(row.get("status")),
        "observacoes": row.get("observacoes") or "",
        "criado_por": row.get("criado_por") or "",
    }


def criar_indice(cur, tabela, nome, colunas):
    cur.execute(
        """
        SELECT COUNT(1) AS total
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND INDEX_NAME = %s
        """,
        (tabela, nome),
    )
    if not (cur.fetchone() or {}).get("total"):
        cur.execute(f"CREATE INDEX {nome} ON {tabela} ({colunas})")


def garantir_schema_eventos():
    global EVENTOS_SCHEMA_VERIFICADO
    if EVENTOS_SCHEMA_VERIFICADO:
        return

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS eventos_cadastro (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    cidade VARCHAR(140) NOT NULL,
                    uf VARCHAR(2) NOT NULL,
                    regiao VARCHAR(80) NULL,
                    nome_evento VARCHAR(220) NOT NULL,
                    data_inicio DATE NOT NULL,
                    data_fim DATE NOT NULL,
                    mes VARCHAR(30) NULL,
                    dias_evento INT NOT NULL DEFAULT 1,
                    valor_verba DECIMAL(15,2) NOT NULL DEFAULT 0,
                    origem VARCHAR(80) NOT NULL,
                    status VARCHAR(40) NOT NULL DEFAULT 'Pendente',
                    observacoes TEXT NULL,
                    criado_por VARCHAR(120) NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS eventos_financeiro (
                    evento_id INT PRIMARY KEY,
                    percentual_parlamentar DECIMAL(8,2) NOT NULL DEFAULT 0,
                    observacoes TEXT NULL,
                    atualizado_por VARCHAR(120) NULL,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS eventos_custos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    evento_id INT NOT NULL,
                    categoria VARCHAR(90) NOT NULL,
                    descricao VARCHAR(220) NULL,
                    fornecedor VARCHAR(160) NULL,
                    valor DECIMAL(15,2) NOT NULL DEFAULT 0,
                    criado_por VARCHAR(120) NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
            criar_indice(cur, "eventos_cadastro", "idx_eventos_periodo", "data_inicio, data_fim")
            criar_indice(cur, "eventos_cadastro", "idx_eventos_filtros", "uf, regiao(40), status, origem")
            criar_indice(cur, "eventos_custos", "idx_eventos_custos_evento", "evento_id")
            importar_eventos_csv(cur)
        conn.commit()
        EVENTOS_SCHEMA_VERIFICADO = True
    finally:
        conn.close()


def evento_csv_existe(cur, cidade, uf, nome, inicio, fim):
    cur.execute(
        """
        SELECT id
        FROM eventos_cadastro
        WHERE cidade = %s
          AND uf = %s
          AND nome_evento = %s
          AND data_inicio = %s
          AND data_fim = %s
        LIMIT 1
        """,
        (cidade, uf, nome, inicio, fim),
    )
    return cur.fetchone()


def importar_eventos_csv(cur):
    if not os.path.exists(CSV_EVENTOS):
        return 0

    importados = 0
    with open(CSV_EVENTOS, "r", encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.reader(arquivo)
        next(leitor, None)
        for row in leitor:
            if len(row) < 12:
                continue
            cidade = reparar_texto(row[0]).upper()
            uf = reparar_texto(row[1]).upper()[:2]
            regiao = reparar_texto(row[2]).upper()
            nome = reparar_texto(row[3]).upper()
            inicio = data_ou_none(row[4])
            fim = data_ou_none(row[5])
            if not cidade or not uf or not nome or not inicio or not fim:
                continue
            if fim < inicio:
                fim = inicio
            mes = MESES.get(inicio.month, "")

            if evento_csv_existe(cur, cidade, uf, nome, inicio, fim):
                continue

            cur.execute(
                """
                INSERT INTO eventos_cadastro
                (cidade, uf, regiao, nome_evento, data_inicio, data_fim, mes, dias_evento,
                 valor_verba, origem, status, observacoes, criado_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    cidade,
                    uf,
                    regiao,
                    nome,
                    inicio,
                    fim,
                    mes,
                    dias_evento(inicio, fim),
                    decimal_ou_zero(row[8]),
                    reparar_texto(row[9]) or "Emenda Direta",
                    reparar_texto(row[10]) or "Pendente",
                    reparar_texto(row[11]),
                    "Carga inicial CSV",
                ),
            )
            importados += 1

    return importados


def carregar_municipios():
    global MUNICIPIOS_CACHE
    if MUNICIPIOS_CACHE is not None:
        return MUNICIPIOS_CACHE

    municipios = []
    if os.path.exists(CSV_MUNICIPIOS):
        with open(CSV_MUNICIPIOS, "r", encoding="utf-8-sig", newline="") as arquivo:
            leitor = csv.DictReader(arquivo)
            for row in leitor:
                cidade = reparar_texto(row.get("CIDADE")).upper()
                uf = reparar_texto(row.get("UF")).upper()[:2]
                regiao = reparar_texto(row.get("REGIAO") or row.get("REGIÃƒO")).upper()
                if cidade and uf:
                    municipios.append({
                        "label": f"{cidade} - {uf}",
                        "cidade": cidade,
                        "uf": uf,
                        "regiao": regiao,
                        "busca": normalizar_busca(f"{cidade} {uf} {regiao}"),
                    })
    MUNICIPIOS_CACHE = sorted(municipios, key=lambda item: item["label"])
    return MUNICIPIOS_CACHE


def montar_where(args):
    filtros = []
    params = []
    mapa = {
        "uf": "uf",
        "regiao": "regiao",
        "mes": "mes",
        "origem": "origem",
        "status": "status",
        "cidade": "cidade",
    }
    for arg, coluna in mapa.items():
        valor = args.get(arg, "").strip()
        if valor:
            filtros.append(f"{coluna} = %s")
            params.append(valor)

    busca = args.get("q", "").strip()
    if busca:
        filtros.append("(nome_evento LIKE %s OR cidade LIKE %s OR observacoes LIKE %s)")
        termo = f"%{busca}%"
        params.extend([termo, termo, termo])

    inicio = data_ou_none(args.get("inicio"))
    fim = data_ou_none(args.get("fim"))
    if inicio:
        filtros.append("data_fim >= %s")
        params.append(inicio)
    if fim:
        filtros.append("data_inicio <= %s")
        params.append(fim)

    return (" WHERE " + " AND ".join(filtros)) if filtros else "", params


def listar_eventos(args):
    garantir_schema_eventos()
    where_sql, params = montar_where(args)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, cidade, uf, regiao, nome_evento, data_inicio, data_fim, mes,
                       dias_evento, valor_verba, origem, status, observacoes, criado_por
                FROM eventos_cadastro
                {where_sql}
                ORDER BY data_inicio ASC, cidade ASC, nome_evento ASC
                """,
                tuple(params),
            )
            return cur.fetchall()
    finally:
        conn.close()


def normalizar_financeiro_evento(evento, financeiro=None, custos=None):
    financeiro = financeiro or {}
    custos = custos or []
    valor_verba = decimal_ou_zero(evento.get("valor_verba"))
    percentual = decimal_ou_zero(financeiro.get("percentual_parlamentar"))
    valor_parlamentar = valor_verba * percentual / Decimal("100")
    total_custos = sum((decimal_ou_zero(item.get("valor")) for item in custos), Decimal("0"))
    sobra = valor_verba - valor_parlamentar - total_custos
    return {
        "evento": normalizar_evento(evento),
        "percentual_parlamentar": float(percentual),
        "valor_parlamentar": float(valor_parlamentar),
        "valor_parlamentar_formatado": dinheiro(valor_parlamentar),
        "total_custos": float(total_custos),
        "total_custos_formatado": dinheiro(total_custos),
        "resultado_instituto": float(sobra),
        "resultado_instituto_formatado": dinheiro(sobra),
        "observacoes": financeiro.get("observacoes") or "",
        "custos": [
            {
                "id": item.get("id"),
                "categoria": item.get("categoria") or "",
                "descricao": item.get("descricao") or "",
                "fornecedor": item.get("fornecedor") or "",
                "valor": float(decimal_ou_zero(item.get("valor"))),
                "valor_formatado": dinheiro(item.get("valor")),
                "criado_por": item.get("criado_por") or "",
            }
            for item in custos
        ],
    }


@bp_eventos.route("/eventos")
def pagina_eventos():
    if "usuario_logado" not in session:
        return redirect(url_for("tela_login"))
    garantir_schema_eventos()
    return render_template("eventos.html", nome_socio=session.get("nome_exibicao", "SÃ³cio"))


@bp_eventos.route("/api/eventos", methods=["GET"])
def api_eventos():
    erro = login_obrigatorio_json()
    if erro:
        return erro
    dados = [normalizar_evento(row) for row in listar_eventos(request.args)]
    return jsonify({"status": "sucesso", "dados": dados})


@bp_eventos.route("/api/eventos/sincronizar-csv", methods=["POST"])
def api_sincronizar_eventos_csv():
    erro = login_obrigatorio_json()
    if erro:
        return erro
    garantir_schema_eventos()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            importados = importar_eventos_csv(cur)
        conn.commit()
        return jsonify({"status": "sucesso", "importados": importados})
    finally:
        conn.close()


@bp_eventos.route("/api/eventos", methods=["POST"])
def api_criar_evento():
    erro = login_obrigatorio_json()
    if erro:
        return erro
    return salvar_evento()


@bp_eventos.route("/api/eventos/<int:evento_id>", methods=["POST"])
def api_editar_evento(evento_id):
    erro = login_obrigatorio_json()
    if erro:
        return erro
    return salvar_evento(evento_id)


def salvar_evento(evento_id=None):
    garantir_schema_eventos()
    cidade = reparar_texto(request.form.get("cidade")).upper()
    uf = reparar_texto(request.form.get("uf")).upper()[:2]
    regiao = reparar_texto(request.form.get("regiao")).upper()
    nome = reparar_texto(request.form.get("nome_evento")).upper()
    inicio = data_ou_none(request.form.get("data_inicio"))
    fim = data_ou_none(request.form.get("data_fim"))
    valor = decimal_ou_zero(request.form.get("valor_verba"))
    origem = reparar_texto(request.form.get("origem"))
    status = normalizar_status_evento(request.form.get("status"))
    observacoes = reparar_texto(request.form.get("observacoes"))

    if not all([cidade, uf, nome, inicio, fim, origem, status]) or valor <= 0:
        return jsonify({"status": "erro", "msg": "Preencha todos os campos obrigatÃ³rios."}), 400
    if fim < inicio:
        return jsonify({"status": "erro", "msg": "A data final precisa ser igual ou posterior Ã  data inicial."}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            payload = (
                cidade,
                uf,
                regiao,
                nome,
                inicio,
                fim,
                MESES.get(inicio.month, ""),
                dias_evento(inicio, fim),
                valor,
                origem,
                status,
                observacoes,
            )
            if evento_id:
                cur.execute(
                    """
                    UPDATE eventos_cadastro
                    SET cidade=%s, uf=%s, regiao=%s, nome_evento=%s, data_inicio=%s,
                        data_fim=%s, mes=%s, dias_evento=%s, valor_verba=%s,
                        origem=%s, status=%s, observacoes=%s
                    WHERE id=%s
                    """,
                    payload + (evento_id,),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO eventos_cadastro
                    (cidade, uf, regiao, nome_evento, data_inicio, data_fim, mes,
                     dias_evento, valor_verba, origem, status, observacoes, criado_por)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    payload + (session.get("nome_exibicao", "Sistema"),),
                )
        conn.commit()
        return jsonify({"status": "sucesso"})
    finally:
        conn.close()


@bp_eventos.route("/api/eventos/<int:evento_id>", methods=["DELETE"])
def api_excluir_evento(evento_id):
    erro = login_obrigatorio_json()
    if erro:
        return erro
    garantir_schema_eventos()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM eventos_custos WHERE evento_id = %s", (evento_id,))
            cur.execute("DELETE FROM eventos_financeiro WHERE evento_id = %s", (evento_id,))
            cur.execute("DELETE FROM eventos_cadastro WHERE id = %s", (evento_id,))
        conn.commit()
        return jsonify({"status": "sucesso"})
    finally:
        conn.close()


@bp_eventos.route("/api/eventos/municipios")
def api_municipios_eventos():
    erro = login_obrigatorio_json()
    if erro:
        return erro
    termo = normalizar_busca(request.args.get("q", ""))
    dados = carregar_municipios()
    if termo:
        dados = [item for item in dados if termo in item["busca"]]
    return jsonify({"status": "sucesso", "dados": dados[:60]})


@bp_eventos.route("/api/eventos/financeiro/<int:evento_id>", methods=["GET"])
def api_evento_financeiro(evento_id):
    erro = login_obrigatorio_json()
    if erro:
        return erro
    garantir_schema_eventos()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, cidade, uf, regiao, nome_evento, data_inicio, data_fim, mes,
                       dias_evento, valor_verba, origem, status, observacoes, criado_por
                FROM eventos_cadastro
                WHERE id = %s
                LIMIT 1
                """,
                (evento_id,),
            )
            evento = cur.fetchone()
            if not evento:
                return jsonify({"status": "erro", "msg": "Evento nÃ£o encontrado."}), 404
            cur.execute("SELECT percentual_parlamentar, observacoes FROM eventos_financeiro WHERE evento_id = %s", (evento_id,))
            financeiro = cur.fetchone() or {}
            cur.execute(
                """
                SELECT id, categoria, descricao, fornecedor, valor, criado_por
                FROM eventos_custos
                WHERE evento_id = %s
                ORDER BY criado_em DESC, id DESC
                """,
                (evento_id,),
            )
            custos = cur.fetchall()
        return jsonify({"status": "sucesso", "dados": normalizar_financeiro_evento(evento, financeiro, custos)})
    finally:
        conn.close()


@bp_eventos.route("/api/eventos/financeiro/<int:evento_id>", methods=["POST"])
def api_salvar_evento_financeiro(evento_id):
    erro = login_obrigatorio_json()
    if erro:
        return erro
    percentual = decimal_ou_zero(request.form.get("percentual_parlamentar"))
    observacoes = reparar_texto(request.form.get("observacoes"))
    if percentual < 0 or percentual > 100:
        return jsonify({"status": "erro", "msg": "Informe um percentual entre 0 e 100."}), 400
    garantir_schema_eventos()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM eventos_cadastro WHERE id = %s", (evento_id,))
            if not cur.fetchone():
                return jsonify({"status": "erro", "msg": "Evento nÃ£o encontrado."}), 404
            cur.execute(
                """
                INSERT INTO eventos_financeiro
                (evento_id, percentual_parlamentar, observacoes, atualizado_por)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    percentual_parlamentar = VALUES(percentual_parlamentar),
                    observacoes = VALUES(observacoes),
                    atualizado_por = VALUES(atualizado_por)
                """,
                (evento_id, percentual, observacoes, session.get("nome_exibicao", "Sistema")),
            )
        conn.commit()
        return jsonify({"status": "sucesso"})
    finally:
        conn.close()


@bp_eventos.route("/api/eventos/financeiro/<int:evento_id>/custos", methods=["POST"])
def api_adicionar_custo_evento(evento_id):
    erro = login_obrigatorio_json()
    if erro:
        return erro
    categoria = reparar_texto(request.form.get("categoria"))
    descricao = reparar_texto(request.form.get("descricao"))
    fornecedor = reparar_texto(request.form.get("fornecedor"))
    valor = decimal_ou_zero(request.form.get("valor"))
    if not categoria or valor <= 0:
        return jsonify({"status": "erro", "msg": "Informe a categoria e um valor maior que zero."}), 400
    garantir_schema_eventos()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM eventos_cadastro WHERE id = %s", (evento_id,))
            if not cur.fetchone():
                return jsonify({"status": "erro", "msg": "Evento nÃ£o encontrado."}), 404
            cur.execute(
                """
                INSERT INTO eventos_custos
                (evento_id, categoria, descricao, fornecedor, valor, criado_por)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (evento_id, categoria, descricao, fornecedor, valor, session.get("nome_exibicao", "Sistema")),
            )
        conn.commit()
        return jsonify({"status": "sucesso"})
    finally:
        conn.close()


@bp_eventos.route("/api/eventos/financeiro/custos/<int:custo_id>", methods=["DELETE"])
def api_excluir_custo_evento(custo_id):
    erro = login_obrigatorio_json()
    if erro:
        return erro
    garantir_schema_eventos()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM eventos_custos WHERE id = %s", (custo_id,))
        conn.commit()
        return jsonify({"status": "sucesso"})
    finally:
        conn.close()


@bp_eventos.route("/api/eventos/financeiro/custos/<int:custo_id>", methods=["POST"])
def api_editar_custo_evento(custo_id):
    erro = login_obrigatorio_json()
    if erro:
        return erro
    categoria = reparar_texto(request.form.get("categoria"))
    descricao = reparar_texto(request.form.get("descricao"))
    fornecedor = reparar_texto(request.form.get("fornecedor"))
    valor = decimal_ou_zero(request.form.get("valor"))
    if not categoria or valor < 0:
        return jsonify({"status": "erro", "msg": "Informe a categoria e um valor vÃ¡lido."}), 400
    garantir_schema_eventos()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE eventos_custos
                SET categoria = %s, descricao = %s, fornecedor = %s, valor = %s
                WHERE id = %s
                """,
                (categoria, descricao, fornecedor, valor, custo_id),
            )
        conn.commit()
        return jsonify({"status": "sucesso"})
    finally:
        conn.close()


@bp_eventos.route("/eventos/exportar")
def exportar_eventos():
    if "usuario_logado" not in session:
        return redirect(url_for("tela_login"))
    rows = [normalizar_evento(row) for row in listar_eventos(request.args)]
    output = []
    output.append(["Cidade", "UF", "RegiÃ£o", "Evento", "InÃ­cio", "Fim", "MÃªs", "Dias", "Valor", "Origem", "Status", "ObservaÃ§Ãµes"])
    for item in rows:
        output.append([
            item["cidade"],
            item["uf"],
            item["regiao"],
            item["nome_evento"],
            item["data_inicio"],
            item["data_fim"],
            item["mes"],
            item["dias_evento"],
            item["valor_verba_formatado"],
            item["origem"],
            item["status"],
            item["observacoes"],
        ])

    linhas = []
    for row in output:
        linhas.append(";".join(f'"{str(col).replace(chr(34), chr(34) + chr(34))}"' for col in row))
    conteudo = "\ufeff" + "\n".join(linhas)
    return Response(
        conteudo,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=eventos_jp2.csv"},
    )
