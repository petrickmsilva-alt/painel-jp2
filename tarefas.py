import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for, Response

from database import get_db_connection
from atas import garantir_schema_atas


bp_tarefas = Blueprint("tarefas", __name__)
STATUS = ("A fazer", "Em andamento", "Aguardando", "Concluída")
PRIORIDADES = ("Urgente", "Alta", "Média", "Baixa")


def login_obrigatorio():
    if "usuario_logado" not in session:
        return redirect(url_for("tela_login"))
    return None


def usuario_atual():
    return session.get("usuario_logado") or "sistema"


def garantir_schema():
    garantir_schema_atas()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tarefas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    titulo VARCHAR(220) NOT NULL,
                    descricao LONGTEXT NULL,
                    responsavel_usuario VARCHAR(120) NULL,
                    participantes TEXT NULL,
                    ata_id INT NULL,
                    prioridade VARCHAR(20) NOT NULL DEFAULT 'Média',
                    status VARCHAR(30) NOT NULL DEFAULT 'A fazer',
                    data_inicio DATE NULL,
                    prazo DATE NULL,
                    checklist_json LONGTEXT NULL,
                    criado_por VARCHAR(120) NULL,
                    atualizado_por VARCHAR(120) NULL,
                    concluida_em DATETIME NULL,
                    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_tarefas_status_prazo (status, prazo),
                    INDEX idx_tarefas_responsavel (responsavel_usuario, status),
                    INDEX idx_tarefas_ata (ata_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tarefa_comentarios (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tarefa_id INT NOT NULL,
                    comentario TEXT NOT NULL,
                    usuario VARCHAR(120) NULL,
                    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_comentarios_tarefa (tarefa_id, criado_em)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tarefa_historico (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    tarefa_id INT NOT NULL,
                    acao VARCHAR(220) NOT NULL,
                    usuario VARCHAR(120) NULL,
                    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_historico_tarefa (tarefa_id, criado_em)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notificacoes_painel (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    usuario VARCHAR(120) NOT NULL,
                    titulo VARCHAR(220) NOT NULL,
                    mensagem TEXT NULL,
                    url VARCHAR(500) NULL,
                    lida TINYINT(1) NOT NULL DEFAULT 0,
                    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_notificacoes_usuario (usuario, lida, criado_em)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
    finally:
        conn.close()


def normalizar_checklist(texto):
    return [{"texto": linha.strip(), "feito": False} for linha in (texto or "").splitlines() if linha.strip()]


def checklist_texto(valor):
    try:
        return "\n".join(item.get("texto", "") for item in json.loads(valor or "[]") if item.get("texto"))
    except Exception:
        return ""


def usuarios_sistema():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT usuario, nome_exibicao FROM usuarios ORDER BY nome_exibicao, usuario")
            return cur.fetchall()
    finally:
        conn.close()


def registrar_historico(cur, tarefa_id, acao):
    cur.execute("INSERT INTO tarefa_historico (tarefa_id, acao, usuario) VALUES (%s,%s,%s)", (tarefa_id, acao, usuario_atual()))


def criar_notificacao(cur, destinatario, titulo, mensagem, url):
    if destinatario:
        cur.execute("INSERT INTO notificacoes_painel (usuario, titulo, mensagem, url) VALUES (%s,%s,%s,%s)", (destinatario, titulo, mensagem, url))


def enviar_push(destinatario, titulo, mensagem, url):
    app_id = os.environ.get("ONESIGNAL_APP_ID", "").strip()
    api_key = os.environ.get("ONESIGNAL_REST_API_KEY", "").strip()
    if not app_id or not api_key or not destinatario:
        return False
    payload = json.dumps({
        "app_id": app_id,
        "include_aliases": {"external_id": [destinatario]},
        "target_channel": "push",
        "headings": {"pt": titulo, "en": titulo},
        "contents": {"pt": mensagem, "en": mensagem},
        "url": url,
    }).encode("utf-8")
    req = urllib.request.Request("https://api.onesignal.com/notifications", data=payload, method="POST", headers={"Authorization": f"Key {api_key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resposta:
            return 200 <= resposta.status < 300
    except Exception as exc:
        print(f"AVISO ONESIGNAL: {type(exc).__name__}: {exc}", flush=True)
        return False


def dados_formulario():
    status = request.form.get("status", "A fazer")
    prioridade = request.form.get("prioridade", "Média")
    return {
        "titulo": request.form.get("titulo", "").strip(),
        "descricao": request.form.get("descricao", "").strip(),
        "responsavel_usuario": request.form.get("responsavel_usuario", "").strip() or None,
        "participantes": request.form.get("participantes", "").strip(),
        "ata_id": request.form.get("ata_id") or None,
        "prioridade": prioridade if prioridade in PRIORIDADES else "Média",
        "status": status if status in STATUS else "A fazer",
        "data_inicio": request.form.get("data_inicio") or None,
        "prazo": request.form.get("prazo") or None,
        "checklist_json": json.dumps(normalizar_checklist(request.form.get("checklist")), ensure_ascii=False),
    }


def buscar_tarefa(tarefa_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT t.*, a.numero_ata, a.titulo AS ata_titulo FROM tarefas t LEFT JOIN atas_reuniao a ON a.id=t.ata_id WHERE t.id=%s", (tarefa_id,))
            return cur.fetchone()
    finally:
        conn.close()


@bp_tarefas.route("/tarefas")
def kanban():
    bloqueio = login_obrigatorio()
    if bloqueio: return bloqueio
    garantir_schema()
    busca = request.args.get("q", "").strip()
    responsavel = request.args.get("responsavel", "").strip()
    prioridade = request.args.get("prioridade", "").strip()
    filtros, params = [], []
    if busca:
        filtros.append("(t.titulo LIKE %s OR t.descricao LIKE %s)")
        params.extend([f"%{busca}%", f"%{busca}%"])
    if responsavel:
        filtros.append("t.responsavel_usuario=%s"); params.append(responsavel)
    if prioridade in PRIORIDADES:
        filtros.append("t.prioridade=%s"); params.append(prioridade)
    where = " WHERE " + " AND ".join(filtros) if filtros else ""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT t.*, a.numero_ata FROM tarefas t LEFT JOIN atas_reuniao a ON a.id=t.ata_id{where} ORDER BY FIELD(t.prioridade,'Urgente','Alta','Média','Baixa'), t.prazo IS NULL, t.prazo, t.id DESC", tuple(params))
            tarefas = cur.fetchall()
    finally:
        conn.close()
    hoje = date.today()
    for tarefa in tarefas:
        tarefa["atrasada"] = bool(tarefa.get("prazo") and tarefa["prazo"] < hoje and tarefa.get("status") != "Concluída")
        try: tarefa["checklist"] = json.loads(tarefa.get("checklist_json") or "[]")
        except Exception: tarefa["checklist"] = []
    return render_template("tarefas_kanban.html", tarefas=tarefas, colunas=STATUS, prioridades=PRIORIDADES, usuarios=usuarios_sistema(), busca=busca, responsavel_atual=responsavel, prioridade_atual=prioridade)


@bp_tarefas.route("/tarefas/nova", methods=["GET", "POST"])
def nova():
    bloqueio = login_obrigatorio()
    if bloqueio: return bloqueio
    garantir_schema()
    ata_id = request.args.get("ata_id")
    ata = None
    if ata_id:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, numero_ata, titulo, encaminhamentos, responsaveis, prazo FROM atas_reuniao WHERE id=%s", (ata_id,))
                ata = cur.fetchone()
        finally: conn.close()
    if request.method == "POST":
        dados = dados_formulario()
        if not dados["titulo"]:
            flash("Informe o título da tarefa.")
            return render_template("tarefa_form.html", tarefa=dados, usuarios=usuarios_sistema(), prioridades=PRIORIDADES, status_validos=STATUS, ata=ata, hoje=date.today().isoformat())
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO tarefas (titulo,descricao,responsavel_usuario,participantes,ata_id,prioridade,status,data_inicio,prazo,checklist_json,criado_por,atualizado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (dados["titulo"],dados["descricao"],dados["responsavel_usuario"],dados["participantes"],dados["ata_id"],dados["prioridade"],dados["status"],dados["data_inicio"],dados["prazo"],dados["checklist_json"],usuario_atual(),usuario_atual()))
                tarefa_id = cur.lastrowid
                registrar_historico(cur, tarefa_id, "Tarefa criada")
                criar_notificacao(cur, dados["responsavel_usuario"], "Nova tarefa JP2", dados["titulo"], f"/tarefas/{tarefa_id}")
            conn.commit()
        finally: conn.close()
        enviar_push(dados["responsavel_usuario"], "Nova tarefa JP2", f"{dados['titulo']} • Prazo: {dados['prazo'] or 'não informado'}", request.url_root.rstrip("/") + f"/tarefas/{tarefa_id}")
        flash("Tarefa criada com sucesso.")
        return redirect(url_for("tarefas.detalhe", tarefa_id=tarefa_id))
    inicial = {"ata_id": ata_id, "titulo": ata.get("titulo") if ata else "", "descricao": ata.get("encaminhamentos") if ata else "", "participantes": ata.get("responsaveis") if ata else "", "prazo": ata.get("prazo") if ata else None}
    return render_template("tarefa_form.html", tarefa=inicial, usuarios=usuarios_sistema(), prioridades=PRIORIDADES, status_validos=STATUS, ata=ata, hoje=date.today().isoformat())


@bp_tarefas.route("/tarefas/<int:tarefa_id>")
def detalhe(tarefa_id):
    bloqueio = login_obrigatorio()
    if bloqueio: return bloqueio
    garantir_schema()
    tarefa = buscar_tarefa(tarefa_id)
    if not tarefa: return redirect(url_for("tarefas.kanban"))
    try: tarefa["checklist"] = json.loads(tarefa.get("checklist_json") or "[]")
    except Exception: tarefa["checklist"] = []
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM tarefa_comentarios WHERE tarefa_id=%s ORDER BY criado_em DESC", (tarefa_id,)); comentarios=cur.fetchall()
            cur.execute("SELECT * FROM tarefa_historico WHERE tarefa_id=%s ORDER BY criado_em DESC LIMIT 30", (tarefa_id,)); historico=cur.fetchall()
    finally: conn.close()
    return render_template("tarefa_detalhe.html", tarefa=tarefa, comentarios=comentarios, historico=historico, status_validos=STATUS)


@bp_tarefas.route("/tarefas/<int:tarefa_id>/editar", methods=["GET", "POST"])
def editar(tarefa_id):
    bloqueio = login_obrigatorio()
    if bloqueio: return bloqueio
    garantir_schema(); tarefa=buscar_tarefa(tarefa_id)
    if not tarefa: return redirect(url_for("tarefas.kanban"))
    if request.method == "POST":
        dados=dados_formulario(); anterior=tarefa.get("responsavel_usuario")
        conn=get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""UPDATE tarefas SET titulo=%s,descricao=%s,responsavel_usuario=%s,participantes=%s,ata_id=%s,prioridade=%s,status=%s,data_inicio=%s,prazo=%s,checklist_json=%s,atualizado_por=%s,concluida_em=IF(%s='Concluída',COALESCE(concluida_em,NOW()),NULL) WHERE id=%s""", (dados["titulo"],dados["descricao"],dados["responsavel_usuario"],dados["participantes"],dados["ata_id"],dados["prioridade"],dados["status"],dados["data_inicio"],dados["prazo"],dados["checklist_json"],usuario_atual(),dados["status"],tarefa_id))
                registrar_historico(cur,tarefa_id,"Tarefa atualizada")
                if dados["responsavel_usuario"] and dados["responsavel_usuario"] != anterior: criar_notificacao(cur,dados["responsavel_usuario"],"Tarefa atribuída a você",dados["titulo"],f"/tarefas/{tarefa_id}")
            conn.commit()
        finally: conn.close()
        if dados["responsavel_usuario"] and dados["responsavel_usuario"] != anterior: enviar_push(dados["responsavel_usuario"],"Tarefa atribuída a você",dados["titulo"],request.url_root.rstrip("/")+f"/tarefas/{tarefa_id}")
        flash("Tarefa atualizada."); return redirect(url_for("tarefas.detalhe",tarefa_id=tarefa_id))
    tarefa["checklist"] = checklist_texto(tarefa.get("checklist_json"))
    return render_template("tarefa_form.html",tarefa=tarefa,usuarios=usuarios_sistema(),prioridades=PRIORIDADES,status_validos=STATUS,ata=None,hoje=date.today().isoformat())


@bp_tarefas.route("/api/tarefas/<int:tarefa_id>/status", methods=["POST"])
def atualizar_status(tarefa_id):
    if "usuario_logado" not in session: return jsonify({"status":"erro"}),401
    novo=(request.get_json(silent=True) or {}).get("status") or request.form.get("status")
    if novo not in STATUS: return jsonify({"status":"erro","mensagem":"Status inválido"}),400
    conn=get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE tarefas SET status=%s, atualizado_por=%s, concluida_em=IF(%s='Concluída',COALESCE(concluida_em,NOW()),NULL) WHERE id=%s",(novo,usuario_atual(),novo,tarefa_id)); registrar_historico(cur,tarefa_id,f"Status alterado para {novo}")
        conn.commit()
    finally: conn.close()
    return jsonify({"status":"sucesso"})


@bp_tarefas.route("/tarefas/<int:tarefa_id>/comentar", methods=["POST"])
def comentar(tarefa_id):
    bloqueio=login_obrigatorio()
    if bloqueio:return bloqueio
    texto=request.form.get("comentario","").strip()
    if texto:
        conn=get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO tarefa_comentarios (tarefa_id,comentario,usuario) VALUES (%s,%s,%s)",(tarefa_id,texto,usuario_atual())); registrar_historico(cur,tarefa_id,"Novo comentário")
            conn.commit()
        finally:conn.close()
    return redirect(url_for("tarefas.detalhe",tarefa_id=tarefa_id))


@bp_tarefas.route("/api/tarefas/<int:tarefa_id>/checklist/<int:indice>", methods=["POST"])
def alternar_checklist(tarefa_id, indice):
    if "usuario_logado" not in session: return jsonify({"status":"erro"}),401
    conn=get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT checklist_json FROM tarefas WHERE id=%s",(tarefa_id,));row=cur.fetchone()
            if not row:return jsonify({"status":"erro","mensagem":"Tarefa não encontrada"}),404
            itens=json.loads(row.get("checklist_json") or "[]")
            if indice<0 or indice>=len(itens):return jsonify({"status":"erro","mensagem":"Item inválido"}),400
            itens[indice]["feito"]=not bool(itens[indice].get("feito"))
            cur.execute("UPDATE tarefas SET checklist_json=%s, atualizado_por=%s WHERE id=%s",(json.dumps(itens,ensure_ascii=False),usuario_atual(),tarefa_id));registrar_historico(cur,tarefa_id,f"Checklist atualizado: {itens[indice].get('texto','')}")
        conn.commit()
    finally:conn.close()
    return jsonify({"status":"sucesso"})


@bp_tarefas.route("/tarefas/<int:tarefa_id>/excluir",methods=["POST"])
def excluir(tarefa_id):
    bloqueio=login_obrigatorio()
    if bloqueio:return bloqueio
    conn=get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tarefa_comentarios WHERE tarefa_id=%s",(tarefa_id,));cur.execute("DELETE FROM tarefa_historico WHERE tarefa_id=%s",(tarefa_id,));cur.execute("DELETE FROM tarefas WHERE id=%s",(tarefa_id,))
        conn.commit()
    finally:conn.close()
    flash("Tarefa excluída.");return redirect(url_for("tarefas.kanban"))


@bp_tarefas.route("/api/notificacoes")
def notificacoes():
    if "usuario_logado" not in session:return jsonify({"dados":[]}),401
    garantir_schema();conn=get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM notificacoes_painel WHERE usuario=%s ORDER BY criado_em DESC LIMIT 30",(usuario_atual(),));dados=cur.fetchall()
    finally:conn.close()
    for item in dados:
        if isinstance(item.get("criado_em"),datetime):item["criado_em"]=item["criado_em"].isoformat()
    return jsonify({"dados":dados,"nao_lidas":sum(1 for i in dados if not i.get("lida"))})


@bp_tarefas.route("/api/notificacoes/ler",methods=["POST"])
def ler_notificacoes():
    if "usuario_logado" not in session:return jsonify({"status":"erro"}),401
    conn=get_db_connection()
    try:
        with conn.cursor() as cur:cur.execute("UPDATE notificacoes_painel SET lida=1 WHERE usuario=%s",(usuario_atual(),))
        conn.commit()
    finally:conn.close()
    return jsonify({"status":"sucesso"})


@bp_tarefas.route("/tarefas/push-config")
def push_config():
    if "usuario_logado" not in session:return jsonify({"ativo":False}),401
    return jsonify({"ativo":bool(os.environ.get("ONESIGNAL_APP_ID")),"app_id":os.environ.get("ONESIGNAL_APP_ID", ""),"external_id":usuario_atual()})


@bp_tarefas.route("/OneSignalSDKWorker.js")
def onesignal_worker():
    return Response('importScripts("https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.sw.js");',mimetype="application/javascript")
