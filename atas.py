from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from database import get_db_connection


bp_atas = Blueprint("atas", __name__, url_prefix="/atas")
STATUS_VALIDOS = ("Rascunho", "Em revisão", "Aprovada")


def login_obrigatorio():
    if "usuario_logado" not in session:
        return redirect(url_for("tela_login"))
    return None


def garantir_schema_atas():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS atas_reuniao (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    numero_ata VARCHAR(30) NULL UNIQUE,
                    titulo VARCHAR(220) NOT NULL,
                    data_reuniao DATE NOT NULL,
                    horario_inicio TIME NULL,
                    horario_fim TIME NULL,
                    local_reuniao VARCHAR(220) NULL,
                    participantes TEXT NULL,
                    pauta LONGTEXT NULL,
                    resumo LONGTEXT NULL,
                    deliberacoes LONGTEXT NULL,
                    encaminhamentos LONGTEXT NULL,
                    responsaveis TEXT NULL,
                    prazo DATE NULL,
                    status VARCHAR(30) NOT NULL DEFAULT 'Rascunho',
                    criado_por VARCHAR(120) NULL,
                    atualizado_por VARCHAR(120) NULL,
                    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_atas_data (data_reuniao),
                    INDEX idx_atas_status (status, data_reuniao)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
    finally:
        conn.close()


def dados_formulario():
    status = request.form.get("status", "Rascunho").strip()
    if status not in STATUS_VALIDOS:
        status = "Rascunho"
    return {
        "titulo": request.form.get("titulo", "").strip(),
        "data_reuniao": request.form.get("data_reuniao", "").strip(),
        "horario_inicio": request.form.get("horario_inicio") or None,
        "horario_fim": request.form.get("horario_fim") or None,
        "local_reuniao": request.form.get("local_reuniao", "").strip(),
        "participantes": request.form.get("participantes", "").strip(),
        "pauta": request.form.get("pauta", "").strip(),
        "resumo": request.form.get("resumo", "").strip(),
        "deliberacoes": request.form.get("deliberacoes", "").strip(),
        "encaminhamentos": request.form.get("encaminhamentos", "").strip(),
        "responsaveis": request.form.get("responsaveis", "").strip(),
        "prazo": request.form.get("prazo") or None,
        "status": status,
    }


@bp_atas.route("")
def lista():
    bloqueio = login_obrigatorio()
    if bloqueio:
        return bloqueio
    garantir_schema_atas()
    busca = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    filtros, params = [], []
    if busca:
        termo = f"%{busca}%"
        filtros.append("(numero_ata LIKE %s OR titulo LIKE %s OR participantes LIKE %s OR deliberacoes LIKE %s)")
        params.extend([termo, termo, termo, termo])
    if status in STATUS_VALIDOS:
        filtros.append("status = %s")
        params.append(status)
    where = " WHERE " + " AND ".join(filtros) if filtros else ""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM atas_reuniao{where} ORDER BY data_reuniao DESC, id DESC", tuple(params))
            atas = cur.fetchall()
            cur.execute("SELECT status, COUNT(*) quantidade FROM atas_reuniao GROUP BY status")
            contagens = {row["status"]: row["quantidade"] for row in cur.fetchall()}
    finally:
        conn.close()
    return render_template("atas_lista.html", atas=atas, busca=busca, status_atual=status, status_validos=STATUS_VALIDOS, contagens=contagens)


@bp_atas.route("/nova", methods=["GET", "POST"])
def nova():
    bloqueio = login_obrigatorio()
    if bloqueio:
        return bloqueio
    garantir_schema_atas()
    if request.method == "POST":
        dados = dados_formulario()
        if not dados["titulo"] or not dados["data_reuniao"]:
            flash("Informe o título e a data da reunião.")
            return render_template("ata_form.html", ata=dados, status_validos=STATUS_VALIDOS, hoje=date.today().isoformat())
        usuario = session.get("nome_exibicao") or session.get("usuario_logado") or "Sistema"
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO atas_reuniao
                    (titulo, data_reuniao, horario_inicio, horario_fim, local_reuniao, participantes,
                     pauta, resumo, deliberacoes, encaminhamentos, responsaveis, prazo, status,
                     criado_por, atualizado_por)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (dados["titulo"], dados["data_reuniao"], dados["horario_inicio"], dados["horario_fim"], dados["local_reuniao"], dados["participantes"], dados["pauta"], dados["resumo"], dados["deliberacoes"], dados["encaminhamentos"], dados["responsaveis"], dados["prazo"], dados["status"], usuario, usuario),
                )
                ata_id = cur.lastrowid
                numero = f"ATA-{str(dados['data_reuniao'])[:4]}-{ata_id:04d}"
                cur.execute("UPDATE atas_reuniao SET numero_ata=%s WHERE id=%s", (numero, ata_id))
            conn.commit()
        except Exception as exc:
            print(f"ERRO AO SALVAR ATA: {type(exc).__name__}: {exc}", flush=True)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"status": "erro", "mensagem": "Não foi possível salvar a ata no banco de dados."}), 500
            flash("Não foi possível salvar a ata. Tente novamente.")
            return render_template("ata_form.html", ata=dados, status_validos=STATUS_VALIDOS, hoje=date.today().isoformat()), 500
        finally:
            if conn:
                conn.close()
        flash("Ata criada com sucesso.")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"status": "sucesso", "url": url_for("atas.detalhe", ata_id=ata_id)})
        return redirect(url_for("atas.detalhe", ata_id=ata_id))
    return render_template("ata_form.html", ata={}, status_validos=STATUS_VALIDOS, hoje=date.today().isoformat())


def buscar_ata(ata_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM atas_reuniao WHERE id=%s", (ata_id,))
            return cur.fetchone()
    finally:
        conn.close()


@bp_atas.route("/<int:ata_id>")
def detalhe(ata_id):
    bloqueio = login_obrigatorio()
    if bloqueio:
        return bloqueio
    garantir_schema_atas()
    ata = buscar_ata(ata_id)
    if not ata:
        flash("Ata não encontrada.")
        return redirect(url_for("atas.lista"))
    return render_template("ata_detalhe.html", ata=ata)


@bp_atas.route("/<int:ata_id>/editar", methods=["GET", "POST"])
def editar(ata_id):
    bloqueio = login_obrigatorio()
    if bloqueio:
        return bloqueio
    garantir_schema_atas()
    ata = buscar_ata(ata_id)
    if not ata:
        flash("Ata não encontrada.")
        return redirect(url_for("atas.lista"))
    if request.method == "POST":
        dados = dados_formulario()
        if not dados["titulo"] or not dados["data_reuniao"]:
            flash("Informe o título e a data da reunião.")
            dados["id"], dados["numero_ata"] = ata_id, ata.get("numero_ata")
            return render_template("ata_form.html", ata=dados, status_validos=STATUS_VALIDOS, hoje=date.today().isoformat())
        usuario = session.get("nome_exibicao") or session.get("usuario_logado") or "Sistema"
        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE atas_reuniao SET titulo=%s, data_reuniao=%s, horario_inicio=%s,
                    horario_fim=%s, local_reuniao=%s, participantes=%s, pauta=%s, resumo=%s,
                    deliberacoes=%s, encaminhamentos=%s, responsaveis=%s, prazo=%s, status=%s,
                    atualizado_por=%s WHERE id=%s
                    """,
                    (dados["titulo"], dados["data_reuniao"], dados["horario_inicio"], dados["horario_fim"], dados["local_reuniao"], dados["participantes"], dados["pauta"], dados["resumo"], dados["deliberacoes"], dados["encaminhamentos"], dados["responsaveis"], dados["prazo"], dados["status"], usuario, ata_id),
                )
            conn.commit()
        except Exception as exc:
            print(f"ERRO AO ATUALIZAR ATA {ata_id}: {type(exc).__name__}: {exc}", flush=True)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"status": "erro", "mensagem": "Não foi possível atualizar a ata no banco de dados."}), 500
            flash("Não foi possível atualizar a ata. Tente novamente.")
            dados["id"], dados["numero_ata"] = ata_id, ata.get("numero_ata")
            return render_template("ata_form.html", ata=dados, status_validos=STATUS_VALIDOS, hoje=date.today().isoformat()), 500
        finally:
            if conn:
                conn.close()
        flash("Ata atualizada com sucesso.")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"status": "sucesso", "url": url_for("atas.detalhe", ata_id=ata_id)})
        return redirect(url_for("atas.detalhe", ata_id=ata_id))
    return render_template("ata_form.html", ata=ata, status_validos=STATUS_VALIDOS, hoje=date.today().isoformat())


@bp_atas.route("/<int:ata_id>/excluir", methods=["POST"])
def excluir(ata_id):
    bloqueio = login_obrigatorio()
    if bloqueio:
        return bloqueio
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM atas_reuniao WHERE id=%s", (ata_id,))
    finally:
        conn.close()
    flash("Ata excluída.")
    return redirect(url_for("atas.lista"))
