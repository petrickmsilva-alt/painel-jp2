from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from database import get_db_connection


bp_consultoria = Blueprint("consultoria", __name__, url_prefix="/consultoria")

FASES = (
    "Diagnóstico", "Mapa/SISMAPA", "Captação", "Proposta", "Plano de Trabalho",
    "Diligências", "Formalização", "Execução", "Prestação de Contas",
)
STATUS_PROJETO = ("Em preparação", "Aguardando Prefeitura", "Em análise", "Com pendência", "Aprovado", "Em execução", "Concluído", "Arquivado")
STATUS_ITEM = ("Pendente", "Em andamento", "Concluído", "Não se aplica")
RISCOS = ("Baixo", "Médio", "Alto", "Crítico")

CHECKLIST_PADRAO = (
    ("Diagnóstico", "Confirmar CNPJ, gestor e unidade responsável da Prefeitura", 1),
    ("Diagnóstico", "Formalizar autorização e escopo da consultoria", 1),
    ("Diagnóstico", "Validar regularidade e capacidade técnica do proponente", 1),
    ("Mapa/SISMAPA", "Normativo da estrutura municipal com órgão responsável pelo turismo", 1),
    ("Mapa/SISMAPA", "LOA e QDD vigentes com dotação destinada ao turismo", 1),
    ("Mapa/SISMAPA", "Ao menos um prestador obrigatório regular no Cadastur", 1),
    ("Mapa/SISMAPA", "Ato de criação do Conselho ou Fórum Municipal de Turismo", 1),
    ("Mapa/SISMAPA", "Ata de posse da diretoria atual do Conselho ou Fórum", 1),
    ("Mapa/SISMAPA", "Duas atas de reunião dos últimos 12 meses", 1),
    ("Mapa/SISMAPA", "Plano de trabalho vigente do Conselho ou Fórum", 1),
    ("Mapa/SISMAPA", "Termo de compromisso vigente assinado pelas três autoridades", 1),
    ("Mapa/SISMAPA", "Critérios adicionais do Estado e declaração da IGR para renovação", 1),
    ("Captação", "Identificar emenda, parlamentar, programa e janela vigente", 1),
    ("Captação", "Confirmar que o objeto e o proponente são elegíveis no programa", 1),
    ("Proposta", "Comprovar tradição, interesse turístico e histórico do evento", 1),
    ("Proposta", "Definir objeto, justificativa, público, resultados e indicadores", 1),
    ("Proposta", "Validar gratuidade e restrições do instrumento vigente", 1),
    ("Plano de Trabalho", "Cadastrar metas, etapas, cronograma físico e desembolso", 1),
    ("Plano de Trabalho", "Anexar pesquisa de preços, memória de cálculo e documentos", 1),
    ("Plano de Trabalho", "Parecer técnico e jurídico da Prefeitura", 1),
    ("Diligências", "Responder diligências dentro do prazo com evidências", 1),
    ("Formalização", "Validar condições, conta, publicação e instrumento assinado", 1),
    ("Formalização", "Definir rota legal da execução: direta, contratação ou parceria", 1),
    ("Formalização", "Registrar análise de conflito de interesse e segregação de funções", 1),
    ("Execução", "Executar compras/parcerias e pagamentos conforme o plano aprovado", 1),
    ("Execução", "Guardar notas, contratos, fotos, listas e comprovação das metas", 1),
    ("Prestação de Contas", "Conciliação financeira, relatório de objeto e devoluções", 1),
    ("Prestação de Contas", "Enviar prestação de contas e acompanhar parecer final", 1),
)

LINKS_OFICIAIS = (
    ("SISMAPA", "Cadastro e atualização do Mapa do Turismo", "https://sistema.mapa.turismo.gov.br/"),
    ("Mapa do Turismo", "Consulta pública de municípios e regiões", "https://www.mapa.turismo.gov.br/mapa/init.html"),
    ("Transferegov", "Propostas, instrumentos, execução e prestação de contas", "https://idp.transferegov.sistema.gov.br/idp/"),
    ("Programas Transferegov", "Consulta pública de programas disponíveis", "https://especiais.transferegov.sistema.gov.br/"),
    ("Cadastur", "Consulta de prestadores de serviços turísticos", "https://cadastur.turismo.gov.br/"),
    ("CAUC", "Consulta de requisitos fiscais para transferências", "https://sti.tesouro.gov.br/cauc/"),
    ("Manuais Transferegov", "Tutoriais oficiais de transferências discricionárias", "https://www.gov.br/transferegov/pt-br/manuais/transferegov/discricionarias"),
    ("Normas do MTur", "Atos normativos oficiais do Ministério do Turismo", "https://www.gov.br/turismo/pt-br/centrais-de-conteudo-/publicacoes/atos-normativos-2"),
)


def usuario_atual():
    return session.get("nome_exibicao") or session.get("usuario_logado") or "Sistema"


def login_obrigatorio():
    if "usuario_logado" not in session:
        return redirect(url_for("tela_login"))


def garantir_schema():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS consultoria_municipios (
                id INT AUTO_INCREMENT PRIMARY KEY, nome VARCHAR(180) NOT NULL, uf CHAR(2) NOT NULL,
                codigo_ibge VARCHAR(10), cnpj VARCHAR(20), prefeito VARCHAR(180), orgao_turismo VARCHAR(220),
                gestor_nome VARCHAR(180), gestor_email VARCHAR(180), gestor_telefone VARCHAR(30),
                regiao_turistica VARCHAR(180), igr VARCHAR(180), situacao_mapa VARCHAR(50) DEFAULT 'Não verificado',
                validade_mapa DATE NULL, categoria_mapa VARCHAR(20), observacoes LONGTEXT,
                criado_por VARCHAR(120), atualizado_por VARCHAR(120), criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_consultoria_municipio (uf,nome), INDEX idx_consultoria_validade (validade_mapa)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
            cur.execute("""CREATE TABLE IF NOT EXISTS consultoria_projetos (
                id INT AUTO_INCREMENT PRIMARY KEY, municipio_id INT NOT NULL, titulo VARCHAR(220) NOT NULL,
                objeto LONGTEXT, data_evento_inicio DATE NULL, data_evento_fim DATE NULL, local_evento VARCHAR(220),
                fase VARCHAR(40) DEFAULT 'Diagnóstico', status VARCHAR(40) DEFAULT 'Em preparação', risco VARCHAR(20) DEFAULT 'Médio',
                responsavel VARCHAR(180), prazo_geral DATE NULL, parlamentar VARCHAR(180), numero_emenda VARCHAR(60),
                programa VARCHAR(180), numero_proposta VARCHAR(80), numero_instrumento VARCHAR(80),
                valor_repasse DECIMAL(15,2) DEFAULT 0, valor_contrapartida DECIMAL(15,2) DEFAULT 0,
                rota_execucao VARCHAR(80), parecer_juridico VARCHAR(30) DEFAULT 'Pendente', observacoes LONGTEXT,
                criado_por VARCHAR(120), atualizado_por VARCHAR(120), criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_consultoria_projeto (municipio_id,fase,status), INDEX idx_consultoria_prazo (prazo_geral)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
            cur.execute("""CREATE TABLE IF NOT EXISTS consultoria_itens (
                id INT AUTO_INCREMENT PRIMARY KEY, projeto_id INT NOT NULL, fase VARCHAR(40) NOT NULL,
                titulo VARCHAR(255) NOT NULL, obrigatorio TINYINT(1) DEFAULT 1, status VARCHAR(30) DEFAULT 'Pendente',
                responsavel VARCHAR(180), prazo DATE NULL, evidencia_url VARCHAR(700), observacao TEXT,
                atualizado_por VARCHAR(120), atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_consultoria_item (projeto_id,fase,status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
            cur.execute("""CREATE TABLE IF NOT EXISTS consultoria_documentos (
                id INT AUTO_INCREMENT PRIMARY KEY, projeto_id INT NOT NULL, tipo VARCHAR(100) NOT NULL,
                titulo VARCHAR(220) NOT NULL, url VARCHAR(700), validade DATE NULL, observacao TEXT,
                criado_por VARCHAR(120), criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_consultoria_documento (projeto_id,tipo)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
            cur.execute("""CREATE TABLE IF NOT EXISTS consultoria_historico (
                id INT AUTO_INCREMENT PRIMARY KEY, projeto_id INT NULL, municipio_id INT NULL,
                acao VARCHAR(255) NOT NULL, detalhes TEXT, usuario VARCHAR(120), criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_consultoria_hist_projeto (projeto_id,criado_em), INDEX idx_consultoria_hist_municipio (municipio_id,criado_em)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    finally:
        conn.close()


def registrar(cur, acao, projeto_id=None, municipio_id=None, detalhes=None):
    cur.execute("INSERT INTO consultoria_historico (projeto_id,municipio_id,acao,detalhes,usuario) VALUES (%s,%s,%s,%s,%s)",
                (projeto_id, municipio_id, acao, detalhes, usuario_atual()))


def moeda(valor):
    try:
        return float(str(valor or "0").replace(".", "").replace(",", "."))
    except ValueError:
        return 0


@bp_consultoria.route("")
def dashboard():
    bloqueio = login_obrigatorio()
    if bloqueio: return bloqueio
    garantir_schema()
    q, fase, status = request.args.get("q", "").strip(), request.args.get("fase", "").strip(), request.args.get("status", "").strip()
    filtros, params = [], []
    if q:
        filtros.append("(p.titulo LIKE %s OR m.nome LIKE %s OR p.numero_proposta LIKE %s OR p.numero_emenda LIKE %s)")
        params += [f"%{q}%"] * 4
    if fase in FASES: filtros.append("p.fase=%s"); params.append(fase)
    if status in STATUS_PROJETO: filtros.append("p.status=%s"); params.append(status)
    where = " WHERE " + " AND ".join(filtros) if filtros else ""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""SELECT p.*,m.nome municipio,m.uf,
                (SELECT COUNT(*) FROM consultoria_itens i WHERE i.projeto_id=p.id AND i.obrigatorio=1 AND i.status='Concluído') itens_ok,
                (SELECT COUNT(*) FROM consultoria_itens i WHERE i.projeto_id=p.id AND i.obrigatorio=1) itens_total
                FROM consultoria_projetos p JOIN consultoria_municipios m ON m.id=p.municipio_id {where}
                ORDER BY FIELD(p.risco,'Crítico','Alto','Médio','Baixo'),p.prazo_geral IS NULL,p.prazo_geral,p.id DESC""", params)
            projetos = cur.fetchall()
            cur.execute("SELECT * FROM consultoria_municipios ORDER BY nome")
            municipios = cur.fetchall()
            cur.execute("""SELECT COUNT(*) projetos,
                SUM(status IN ('Em preparação','Aguardando Prefeitura','Em análise','Com pendência','Aprovado','Em execução')) ativos,
                SUM(risco IN ('Alto','Crítico')) riscos,
                SUM(prazo_geral<CURDATE() AND status NOT IN ('Concluído','Arquivado')) atrasados FROM consultoria_projetos""")
            resumo = cur.fetchone()
    finally: conn.close()
    return render_template("consultoria_dashboard.html", projetos=projetos, municipios=municipios, resumo=resumo,
                           fases=FASES, status_projeto=STATUS_PROJETO, q=q, fase_atual=fase, status_atual=status, links=LINKS_OFICIAIS)


@bp_consultoria.route("/municipios/novo", methods=["GET", "POST"])
@bp_consultoria.route("/municipios/<int:municipio_id>/editar", methods=["GET", "POST"])
def municipio_form(municipio_id=None):
    bloqueio = login_obrigatorio()
    if bloqueio: return bloqueio
    garantir_schema(); municipio = {}
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if municipio_id:
                cur.execute("SELECT * FROM consultoria_municipios WHERE id=%s", (municipio_id,)); municipio = cur.fetchone()
                if not municipio: flash("Prefeitura não encontrada."); return redirect(url_for("consultoria.dashboard"))
            if request.method == "POST":
                campos = ("nome","uf","codigo_ibge","cnpj","prefeito","orgao_turismo","gestor_nome","gestor_email","gestor_telefone","regiao_turistica","igr","situacao_mapa","validade_mapa","categoria_mapa","observacoes")
                d = {c: request.form.get(c, "").strip() or None for c in campos}; d["uf"] = (d["uf"] or "").upper()[:2]
                if not d["nome"] or len(d["uf"]) != 2: flash("Informe o município e a UF."); municipio=d
                elif municipio_id:
                    cur.execute("""UPDATE consultoria_municipios SET nome=%s,uf=%s,codigo_ibge=%s,cnpj=%s,prefeito=%s,orgao_turismo=%s,gestor_nome=%s,gestor_email=%s,gestor_telefone=%s,regiao_turistica=%s,igr=%s,situacao_mapa=%s,validade_mapa=%s,categoria_mapa=%s,observacoes=%s,atualizado_por=%s WHERE id=%s""", tuple(d[c] for c in campos)+(usuario_atual(),municipio_id))
                    registrar(cur,"Cadastro da Prefeitura atualizado",municipio_id=municipio_id); flash("Prefeitura atualizada."); return redirect(url_for("consultoria.municipio_detalhe",municipio_id=municipio_id))
                else:
                    cur.execute("""INSERT INTO consultoria_municipios (nome,uf,codigo_ibge,cnpj,prefeito,orgao_turismo,gestor_nome,gestor_email,gestor_telefone,regiao_turistica,igr,situacao_mapa,validade_mapa,categoria_mapa,observacoes,criado_por,atualizado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", tuple(d[c] for c in campos)+(usuario_atual(),usuario_atual()))
                    municipio_id=cur.lastrowid; registrar(cur,"Prefeitura cadastrada",municipio_id=municipio_id); flash("Prefeitura cadastrada."); return redirect(url_for("consultoria.municipio_detalhe",municipio_id=municipio_id))
    finally: conn.close()
    return render_template("consultoria_municipio_form.html", municipio=municipio or {})


@bp_consultoria.route("/municipios/<int:municipio_id>")
def municipio_detalhe(municipio_id):
    bloqueio=login_obrigatorio()
    if bloqueio:return bloqueio
    garantir_schema(); conn=get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM consultoria_municipios WHERE id=%s",(municipio_id,)); municipio=cur.fetchone()
            if not municipio: flash("Prefeitura não encontrada."); return redirect(url_for("consultoria.dashboard"))
            cur.execute("SELECT * FROM consultoria_projetos WHERE municipio_id=%s ORDER BY id DESC",(municipio_id,)); projetos=cur.fetchall()
            cur.execute("SELECT * FROM consultoria_historico WHERE municipio_id=%s ORDER BY criado_em DESC LIMIT 30",(municipio_id,)); historico=cur.fetchall()
    finally:conn.close()
    return render_template("consultoria_municipio_detalhe.html",municipio=municipio,projetos=projetos,historico=historico)


@bp_consultoria.route("/projetos/novo", methods=["GET", "POST"])
@bp_consultoria.route("/projetos/<int:projeto_id>/editar", methods=["GET", "POST"])
def projeto_form(projeto_id=None):
    bloqueio=login_obrigatorio()
    if bloqueio:return bloqueio
    garantir_schema(); conn=get_db_connection(); projeto={}
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,nome,uf FROM consultoria_municipios ORDER BY nome"); municipios=cur.fetchall()
            if projeto_id: cur.execute("SELECT * FROM consultoria_projetos WHERE id=%s",(projeto_id,)); projeto=cur.fetchone()
            if request.method=="POST":
                campos=("municipio_id","titulo","objeto","data_evento_inicio","data_evento_fim","local_evento","fase","status","risco","responsavel","prazo_geral","parlamentar","numero_emenda","programa","numero_proposta","numero_instrumento","rota_execucao","parecer_juridico","observacoes")
                d={c:request.form.get(c,"").strip() or None for c in campos}; d["valor_repasse"]=moeda(request.form.get("valor_repasse")); d["valor_contrapartida"]=moeda(request.form.get("valor_contrapartida"))
                if not d["municipio_id"] or not d["titulo"]: flash("Informe a Prefeitura e o título do projeto."); projeto=d
                elif projeto_id:
                    cur.execute("""UPDATE consultoria_projetos SET municipio_id=%s,titulo=%s,objeto=%s,data_evento_inicio=%s,data_evento_fim=%s,local_evento=%s,fase=%s,status=%s,risco=%s,responsavel=%s,prazo_geral=%s,parlamentar=%s,numero_emenda=%s,programa=%s,numero_proposta=%s,numero_instrumento=%s,rota_execucao=%s,parecer_juridico=%s,observacoes=%s,valor_repasse=%s,valor_contrapartida=%s,atualizado_por=%s WHERE id=%s""",tuple(d[c] for c in campos)+(d["valor_repasse"],d["valor_contrapartida"],usuario_atual(),projeto_id))
                    registrar(cur,"Projeto atualizado",projeto_id,int(d["municipio_id"]),f"{d['fase']} / {d['status']}"); flash("Projeto atualizado."); return redirect(url_for("consultoria.projeto_detalhe",projeto_id=projeto_id))
                else:
                    cur.execute("""INSERT INTO consultoria_projetos (municipio_id,titulo,objeto,data_evento_inicio,data_evento_fim,local_evento,fase,status,risco,responsavel,prazo_geral,parlamentar,numero_emenda,programa,numero_proposta,numero_instrumento,rota_execucao,parecer_juridico,observacoes,valor_repasse,valor_contrapartida,criado_por,atualizado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",tuple(d[c] for c in campos)+(d["valor_repasse"],d["valor_contrapartida"],usuario_atual(),usuario_atual()))
                    projeto_id=cur.lastrowid
                    cur.executemany("INSERT INTO consultoria_itens (projeto_id,fase,titulo,obrigatorio) VALUES (%s,%s,%s,%s)",[(projeto_id,*item) for item in CHECKLIST_PADRAO])
                    registrar(cur,"Projeto criado com checklist 2026",projeto_id,int(d["municipio_id"])); flash("Projeto criado com o checklist completo."); return redirect(url_for("consultoria.projeto_detalhe",projeto_id=projeto_id))
    finally:conn.close()
    return render_template("consultoria_projeto_form.html",projeto=projeto or {},municipios=municipios,fases=FASES,status_projeto=STATUS_PROJETO,riscos=RISCOS)


@bp_consultoria.route("/projetos/<int:projeto_id>")
def projeto_detalhe(projeto_id):
    bloqueio=login_obrigatorio()
    if bloqueio:return bloqueio
    garantir_schema(); conn=get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT p.*,m.nome municipio,m.uf,m.situacao_mapa,m.validade_mapa FROM consultoria_projetos p JOIN consultoria_municipios m ON m.id=p.municipio_id WHERE p.id=%s",(projeto_id,)); projeto=cur.fetchone()
            if not projeto: flash("Projeto não encontrado."); return redirect(url_for("consultoria.dashboard"))
            cur.execute("SELECT * FROM consultoria_itens WHERE projeto_id=%s ORDER BY FIELD(fase,"+",".join(["%s"]*len(FASES))+") ,id",(projeto_id,*FASES)); itens=cur.fetchall()
            cur.execute("SELECT * FROM consultoria_documentos WHERE projeto_id=%s ORDER BY criado_em DESC",(projeto_id,)); documentos=cur.fetchall()
            cur.execute("SELECT * FROM consultoria_historico WHERE projeto_id=%s ORDER BY criado_em DESC LIMIT 50",(projeto_id,)); historico=cur.fetchall()
    finally:conn.close()
    total=sum(1 for i in itens if i["obrigatorio"]); concluidos=sum(1 for i in itens if i["obrigatorio"] and i["status"]=="Concluído")
    bloqueios=[i for i in itens if i["obrigatorio"] and i["status"] not in ("Concluído","Não se aplica")]
    return render_template("consultoria_projeto_detalhe.html",projeto=projeto,itens=itens,documentos=documentos,historico=historico,fases=FASES,status_item=STATUS_ITEM,total=total,concluidos=concluidos,bloqueios=bloqueios,links=LINKS_OFICIAIS)


@bp_consultoria.route("/itens/<int:item_id>/atualizar",methods=["POST"])
def item_atualizar(item_id):
    bloqueio=login_obrigatorio()
    if bloqueio:return bloqueio
    garantir_schema(); status=request.form.get("status")
    if status not in STATUS_ITEM: flash("Status inválido."); return redirect(request.referrer or url_for("consultoria.dashboard"))
    conn=get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT projeto_id,titulo FROM consultoria_itens WHERE id=%s",(item_id,)); item=cur.fetchone()
            if not item: flash("Item não encontrado."); return redirect(url_for("consultoria.dashboard"))
            cur.execute("UPDATE consultoria_itens SET status=%s,responsavel=%s,prazo=%s,evidencia_url=%s,observacao=%s,atualizado_por=%s WHERE id=%s",(status,request.form.get("responsavel") or None,request.form.get("prazo") or None,request.form.get("evidencia_url") or None,request.form.get("observacao") or None,usuario_atual(),item_id))
            registrar(cur,f"Checklist: {item['titulo']} → {status}",item["projeto_id"])
    finally:conn.close()
    flash("Etapa atualizada."); return redirect(url_for("consultoria.projeto_detalhe",projeto_id=item["projeto_id"]) + f"#item-{item_id}")


@bp_consultoria.route("/projetos/<int:projeto_id>/documentos",methods=["POST"])
def documento_novo(projeto_id):
    bloqueio=login_obrigatorio()
    if bloqueio:return bloqueio
    titulo=request.form.get("titulo","").strip(); tipo=request.form.get("tipo","").strip()
    if not titulo or not tipo: flash("Informe o tipo e o título do documento."); return redirect(url_for("consultoria.projeto_detalhe",projeto_id=projeto_id))
    conn=get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO consultoria_documentos (projeto_id,tipo,titulo,url,validade,observacao,criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s)",(projeto_id,tipo,titulo,request.form.get("url") or None,request.form.get("validade") or None,request.form.get("observacao") or None,usuario_atual()))
            registrar(cur,f"Documento registrado: {titulo}",projeto_id)
    finally:conn.close()
    flash("Documento registrado."); return redirect(url_for("consultoria.projeto_detalhe",projeto_id=projeto_id)+"#documentos")


@bp_consultoria.route("/documentos/<int:documento_id>/excluir",methods=["POST"])
def documento_excluir(documento_id):
    bloqueio=login_obrigatorio()
    if bloqueio:return bloqueio
    conn=get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT projeto_id,titulo FROM consultoria_documentos WHERE id=%s",(documento_id,)); doc=cur.fetchone()
            if not doc: return redirect(url_for("consultoria.dashboard"))
            cur.execute("DELETE FROM consultoria_documentos WHERE id=%s",(documento_id,)); registrar(cur,f"Documento excluído: {doc['titulo']}",doc["projeto_id"])
    finally:conn.close()
    flash("Documento excluído."); return redirect(url_for("consultoria.projeto_detalhe",projeto_id=doc["projeto_id"])+"#documentos")
