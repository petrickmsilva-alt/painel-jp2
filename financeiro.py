from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import get_db_connection

bp_financeiro = Blueprint("financeiro", __name__)

FINANCEIRO_SCHEMA_VERIFICADO = False


def coluna_existe(cur, tabela, coluna):
    cur.execute(f"SHOW COLUMNS FROM `{tabela}` LIKE %s", (coluna,))
    return cur.fetchone() is not None


def garantir_schema_financeiro():
    global FINANCEIRO_SCHEMA_VERIFICADO
    if FINANCEIRO_SCHEMA_VERIFICADO:
        return

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if not coluna_existe(cur, "investimentos", "empresa_id"):
                cur.execute("ALTER TABLE investimentos ADD COLUMN empresa_id INT NULL AFTER id")
            if not coluna_existe(cur, "investimentos", "tipo_recurso"):
                cur.execute("ALTER TABLE investimentos ADD COLUMN tipo_recurso VARCHAR(80) NULL")
        conn.commit()
        FINANCEIRO_SCHEMA_VERIFICADO = True
    finally:
        conn.close()


@bp_financeiro.route("/financeiro")
def pagina_financeiro():
    if "usuario_logado" not in session:
        return redirect(url_for("tela_login"))
    garantir_schema_financeiro()
    return render_template("financeiro.html")


@bp_financeiro.route("/api/empresas", methods=["GET"])
def listar_empresas():
    if "usuario_logado" not in session:
        return jsonify({"status": "erro", "mensagem": "Nao autorizado"}), 401

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, nome, cnpj, ramo_atividade FROM empresas ORDER BY nome ASC")
            dados = cur.fetchall()
        return jsonify({"status": "sucesso", "dados": dados})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
    finally:
        if conn:
            conn.close()


@bp_financeiro.route("/api/adicionar-empresa", methods=["POST"])
def adicionar_empresa():
    if "usuario_logado" not in session:
        return jsonify({"status": "erro", "mensagem": "Nao autorizado"}), 401

    nome = request.form.get("nome", "").strip()
    if not nome:
        return jsonify({"status": "erro", "mensagem": "Informe o nome da empresa"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO empresas (nome, cnpj, ramo_atividade) VALUES (%s, %s, %s)",
                (
                    nome,
                    request.form.get("cnpj", "").strip(),
                    request.form.get("ramo_atividade", "").strip(),
                ),
            )
        conn.commit()
        return jsonify({"status": "sucesso"})
    finally:
        conn.close()


@bp_financeiro.route("/api/excluir-empresa/<id>", methods=["DELETE"])
def excluir_empresa(id):
    if "usuario_logado" not in session:
        return jsonify({"status": "erro", "mensagem": "Nao autorizado"}), 401

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM empresas WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"status": "sucesso"})
    finally:
        conn.close()


@bp_financeiro.route("/api/resumo-investimentos", methods=["GET"])
def resumo_investimentos():
    if "usuario_logado" not in session:
        return jsonify({"status": "erro", "msg": "Nao autorizado"}), 401

    try:
        garantir_schema_financeiro()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT i.id, i.empresa_id, e.nome AS empresa_nome, i.nome_investidor,
                       i.valor_inicial, i.juros_mensais, i.data_inicio, i.captador,
                       i.tipo_recurso, i.finalidade, i.data_pgto
                FROM investimentos i
                LEFT JOIN empresas e ON e.id = i.empresa_id
                ORDER BY COALESCE(i.data_pgto, i.data_inicio) ASC, i.id DESC
                """
            )
            dados = cur.fetchall()
        conn.close()
        return jsonify({"status": "sucesso", "dados": dados})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)}), 500


@bp_financeiro.route("/api/adicionar-investimento", methods=["POST"])
def adicionar_investimento():
    if "usuario_logado" not in session:
        return jsonify({"status": "erro", "msg": "Nao autorizado"}), 401

    try:
        garantir_schema_financeiro()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO investimentos
                (empresa_id, nome_investidor, valor_inicial, juros_mensais, data_inicio,
                 captador, tipo_recurso, finalidade, data_pgto)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    request.form.get("empresa_id") or None,
                    request.form.get("quem", "").strip(),
                    request.form.get("valor") or 0,
                    request.form.get("juros") or 0,
                    request.form.get("data_recurso") or None,
                    request.form.get("captador", "").strip(),
                    request.form.get("tipo_recurso", "").strip(),
                    request.form.get("finalidade", "").strip(),
                    request.form.get("data_pgto") or None,
                ),
            )
        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso"})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)}), 500


@bp_financeiro.route("/api/excluir-investimento/<int:id>", methods=["DELETE"])
def excluir_investimento(id):
    if "usuario_logado" not in session:
        return jsonify({"status": "erro", "msg": "Nao autorizado"}), 401

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM investimentos WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso"})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)}), 500
