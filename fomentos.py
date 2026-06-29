import json
import os
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from database import get_db_connection


bp_fomentos = Blueprint("fomentos", __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELO_PT8_TEXTO = os.path.join(BASE_DIR, "data", "fomentos", "PT_8_conteudo.txt")
MODELO_PT8_PDF = "/static/documentos/fomentos/PT_8.pdf"
FOMENTOS_SCHEMA_VERIFICADO = False


def login_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "usuario_logado" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"status": "erro", "mensagem": "Sessao expirada."}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapper


def decimal_ou_zero(valor):
    if isinstance(valor, Decimal):
        return valor
    texto = str(valor or "").strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto or "0")
    except (InvalidOperation, ValueError):
        return Decimal("0")


def dinheiro(valor):
    numero = decimal_ou_zero(valor)
    return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def data_br(valor):
    if not valor:
        return "-"
    if isinstance(valor, str):
        valor = data_ou_none(valor)
    return valor.strftime("%d-%m-%Y") if valor else "-"


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


def json_seguro(valor, padrao=None):
    if isinstance(valor, (list, dict)):
        return valor
    try:
        return json.loads(valor or "")
    except (TypeError, ValueError):
        return [] if padrao is None else padrao


def texto_json(valor):
    return json.dumps(valor if isinstance(valor, (list, dict)) else [], ensure_ascii=False)


def limpar_cabecalhos(texto):
    linhas_ignoradas = (
        "GOVERNO DO DISTRITO FEDERAL",
        "SECRETARIA DE ESTADO DE CULTURA E ECONOMIA CRIATIVA DO DISTRITO FEDERAL",
        "TERMO DE FOMENTO TF-8-SECEC/2026",
        "Gerado em 01-04-2026",
        "MROSC: 0006-01-900000002184/2026-76",
    )
    linhas = []
    for linha in str(texto or "").splitlines():
        limpa = linha.strip()
        if not limpa or limpa.startswith("PAG:") or limpa.startswith("PÁG:"):
            continue
        if any(limpa.startswith(prefixo) for prefixo in linhas_ignoradas):
            continue
        linhas.append(limpa)
    return "\n".join(linhas).strip()


def extrair_secao(texto, inicio, fim):
    padrao = re.compile(
        rf"(?:^|\n){re.escape(inicio)}\s*\n(.*?)(?=\n{re.escape(fim)}\s*(?:\n|$))",
        re.DOTALL,
    )
    encontrado = padrao.search(texto or "")
    return limpar_cabecalhos(encontrado.group(1)) if encontrado else ""


def colunas_tabela(cur, tabela):
    cur.execute(f"SHOW COLUMNS FROM {tabela}")
    return {linha["Field"] for linha in cur.fetchall()}


def garantir_schema_fomentos():
    global FOMENTOS_SCHEMA_VERIFICADO
    if FOMENTOS_SCHEMA_VERIFICADO:
        return

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS eventos_fomentos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    evento_id INT NULL,
                    termo_numero VARCHAR(90) NOT NULL,
                    plano_trabalho_numero VARCHAR(60) NULL,
                    mrsc_numero VARCHAR(100) NULL,
                    nome_parceria VARCHAR(255) NULL,
                    titulo_projeto VARCHAR(255) NOT NULL,
                    osc_nome VARCHAR(255) NULL,
                    osc_cnpj VARCHAR(30) NULL,
                    osc_endereco VARCHAR(500) NULL,
                    osc_ra VARCHAR(120) NULL,
                    osc_uf VARCHAR(2) NULL,
                    osc_cep VARCHAR(15) NULL,
                    osc_site VARCHAR(255) NULL,
                    representante_nome VARCHAR(180) NULL,
                    representante_cargo VARCHAR(120) NULL,
                    representante_rg VARCHAR(80) NULL,
                    representante_orgao VARCHAR(50) NULL,
                    representante_cpf VARCHAR(30) NULL,
                    acompanhamento_nome VARCHAR(180) NULL,
                    acompanhamento_funcao VARCHAR(120) NULL,
                    acompanhamento_cpf VARCHAR(30) NULL,
                    acompanhamento_rg VARCHAR(80) NULL,
                    acompanhamento_orgao VARCHAR(50) NULL,
                    acompanhamento_telefone VARCHAR(80) NULL,
                    acompanhamento_email VARCHAR(180) NULL,
                    valor_total DECIMAL(16,2) NOT NULL DEFAULT 0,
                    vigencia_inicio DATE NULL,
                    vigencia_fim DATE NULL,
                    objeto LONGTEXT NULL,
                    apresentacao LONGTEXT NULL,
                    justificativa LONGTEXT NULL,
                    descricao_projeto LONGTEXT NULL,
                    analise_cenario LONGTEXT NULL,
                    eixos_atuacao LONGTEXT NULL,
                    alinhamento_politicas LONGTEXT NULL,
                    publico_alvo LONGTEXT NULL,
                    contrapartida LONGTEXT NULL,
                    metodologia LONGTEXT NULL,
                    resultados_esperados LONGTEXT NULL,
                    metas_json LONGTEXT NULL,
                    orcamento_json LONGTEXT NULL,
                    equipe_json LONGTEXT NULL,
                    receitas_json LONGTEXT NULL,
                    parcelas_json LONGTEXT NULL,
                    desembolso_json LONGTEXT NULL,
                    conteudo_integral LONGTEXT NULL,
                    documento_original VARCHAR(500) NULL,
                    status VARCHAR(40) NOT NULL DEFAULT 'Em elaboracao',
                    criado_por VARCHAR(120) NULL,
                    atualizado_por VARCHAR(120) NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_eventos_fomentos_termo (termo_numero)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
            existentes = colunas_tabela(cur, "eventos_fomentos")
            colunas_novas = {
                "conteudo_integral": "LONGTEXT NULL",
                "documento_original": "VARCHAR(500) NULL",
                "status": "VARCHAR(40) NOT NULL DEFAULT 'Em elaboracao'",
            }
            for coluna, definicao in colunas_novas.items():
                if coluna not in existentes:
                    cur.execute(f"ALTER TABLE eventos_fomentos ADD COLUMN {coluna} {definicao}")
            semear_pt8(cur)
        conn.commit()
        FOMENTOS_SCHEMA_VERIFICADO = True
    finally:
        conn.close()


def semear_pt8(cur):
    cur.execute("SELECT id FROM eventos_fomentos WHERE termo_numero = %s LIMIT 1", ("TF-8-SECEC/2026",))
    if cur.fetchone() or not os.path.exists(MODELO_PT8_TEXTO):
        return

    with open(MODELO_PT8_TEXTO, "r", encoding="utf-8") as arquivo:
        conteudo = arquivo.read()

    objeto = extrair_secao(conteudo, "OBJETO", "APRESENTAÇÃO")
    apresentacao = extrair_secao(conteudo, "APRESENTAÇÃO", "JUSTIFICATIVA")
    justificativa = extrair_secao(conteudo, "JUSTIFICATIVA", "DESCRIÇÃO DO PROJETO")
    descricao = extrair_secao(conteudo, "DESCRIÇÃO DO PROJETO", "ANÁLISE DO CENÁRIO")
    cenario = extrair_secao(conteudo, "ANÁLISE DO CENÁRIO", "EIXOS DE ATUAÇÃO")
    eixos = extrair_secao(conteudo, "EIXOS DE ATUAÇÃO", "ALINHAMENTO COM AS POLÍTICAS PÚBLICAS")
    politicas = extrair_secao(conteudo, "ALINHAMENTO COM AS POLÍTICAS PÚBLICAS", "PÚBLICO ALVO BENEFICIADO")
    publico = extrair_secao(conteudo, "PÚBLICO ALVO BENEFICIADO", "CONTRAPARTIDA")
    contrapartida = extrair_secao(conteudo, "CONTRAPARTIDA", "METODOLOGIA DAS AÇÕES")
    metodologia = extrair_secao(conteudo, "METODOLOGIA DAS AÇÕES", "RESULTADOS ESPERADOS")
    resultados = extrair_secao(conteudo, "RESULTADOS ESPERADOS", "DETALHAMENTO DAS METAS E INDICADORES")

    metas = [
        {
            "numero": "1",
            "titulo": "Realizar a programacao de apresentacoes musicais e culturais do Festival",
            "publico": "Pessoas de ambos os sexos, todas as idades, em vulnerabilidade social",
            "regiao": "Planaltina (RA VI)",
            "quantidade": "15",
            "indicadores": "Minimo de 15 apresentacoes; qualidade tecnica e diversidade da programacao cultural.",
            "verificacao": "Programacao oficial, contratos artisticos, registros fotograficos e audiovisuais, relatorio tecnico e clipping.",
        },
        {
            "numero": "2",
            "titulo": "Realizar atividades culturais e de integracao comunitaria durante o periodo diurno do festival",
            "publico": "Pessoas de ambos os sexos, todas as idades, em vulnerabilidade social",
            "regiao": "Planaltina (RA VI)",
            "quantidade": "",
            "indicadores": "Execucao das atividades culturais e comunitarias planejadas.",
            "verificacao": "Relatorios de execucao, registros fotograficos e audiovisuais.",
        },
        {
            "numero": "3",
            "titulo": "Alcancar publico presencial durante a realizacao do Festival Expomix Brasil",
            "publico": "Pessoas de ambos os sexos, todas as idades, em vulnerabilidade social",
            "regiao": "Planaltina (RA VI)",
            "quantidade": "100000",
            "indicadores": "Participacao de 100 mil pessoas e ampla adesao do publico.",
            "verificacao": "Controle de acesso, registros fotograficos e audiovisuais, relatorios de publico e clipping.",
        },
    ]
    orcamento = [
        {"meta": "1", "classificacao": "Apoio administrativo, tecnico e operacional", "valor": 52600.00},
        {"meta": "1", "classificacao": "Apresentacoes e eventos - contratacoes artisticas", "valor": 3313000.00},
        {"meta": "2", "classificacao": "Locacao em geral (para eventos)", "valor": 3576520.00},
        {"meta": "2", "classificacao": "Servicos para eventos em geral", "valor": 222060.00},
        {"meta": "3", "classificacao": "Servicos de comunicacao visual e afins", "valor": 435728.61},
    ]
    equipe = [
        {"cargo": "Coordenador Geral - Eduardo Faad", "quantidade": 5, "unidade": "Semana", "valor_unitario": 2100, "valor_total": 10500},
        {"cargo": "Coordenacao Financeira", "quantidade": 5, "unidade": "Semana", "valor_unitario": 1600, "valor_total": 8000},
        {"cargo": "Produtor Executivo", "quantidade": 5, "unidade": "Semana", "valor_unitario": 2900, "valor_total": 14500},
    ]
    receitas = [{"fonte_recurso": "Tesouro - ordinario nao vinculado", "fonte": "100", "valor": 7599908.61}]
    parcelas = [
        {"parcela": "1", "data": "2026-04-02", "valor": 6000000.00},
        {"parcela": "2", "data": "2026-04-16", "valor": 1599908.61},
    ]
    desembolso = [dict(item, parcela="1") for item in orcamento]

    cur.execute(
        """
        INSERT INTO eventos_fomentos (
            termo_numero, plano_trabalho_numero, mrsc_numero, nome_parceria, titulo_projeto,
            osc_nome, osc_cnpj, osc_endereco, osc_ra, osc_uf, osc_cep, osc_site,
            representante_nome, representante_cargo, representante_rg, representante_orgao, representante_cpf,
            acompanhamento_nome, acompanhamento_funcao, acompanhamento_cpf, acompanhamento_rg,
            acompanhamento_orgao, acompanhamento_telefone, acompanhamento_email,
            valor_total, vigencia_inicio, vigencia_fim, objeto, apresentacao, justificativa,
            descricao_projeto, analise_cenario, eixos_atuacao, alinhamento_politicas, publico_alvo,
            contrapartida, metodologia, resultados_esperados, metas_json, orcamento_json,
            equipe_json, receitas_json, parcelas_json, desembolso_json, conteudo_integral,
            documento_original, status, criado_por, atualizado_por
        ) VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        )
        """,
        (
            "TF-8-SECEC/2026", "2184", "0006-01-900000002184/2026-76",
            "7a Edicao do Festival ExpoMix Brasil", "7a Edicao do Festival ExpoMix Brasil",
            "ASSOCIACAO SEMPER FIDELIS", "24.300.747/0001-23",
            "Quadra AR 11 Conjunto 7, Lote 01, Sala 01", "Setor Oeste (Sobradinho II)", "DF", "73.060-207",
            "https://institutosemperfidelis.org.br/", "EDUARDO FAAD", "PRESIDENTE", "██████", "███", "***.451.701-**",
            "EDUARDO FAAD", "DIRETOR", "***.451.701-**", "██████", "███", "(61) ███████████ 65", "se█████████████s@gmail.com",
            Decimal("7599908.61"), date(2026, 4, 2), date(2026, 5, 12), objeto, apresentacao, justificativa,
            descricao, cenario, eixos, politicas, publico, contrapartida, metodologia, resultados,
            texto_json(metas), texto_json(orcamento), texto_json(equipe), texto_json(receitas),
            texto_json(parcelas), texto_json(desembolso), conteudo, MODELO_PT8_PDF, "Vigente", "Sistema", "Sistema",
        ),
    )


COLUNAS_EDITAVEIS = [
    "evento_id", "termo_numero", "plano_trabalho_numero", "mrsc_numero", "nome_parceria", "titulo_projeto",
    "osc_nome", "osc_cnpj", "osc_endereco", "osc_ra", "osc_uf", "osc_cep", "osc_site",
    "representante_nome", "representante_cargo", "representante_rg", "representante_orgao", "representante_cpf",
    "acompanhamento_nome", "acompanhamento_funcao", "acompanhamento_cpf", "acompanhamento_rg",
    "acompanhamento_orgao", "acompanhamento_telefone", "acompanhamento_email", "valor_total",
    "vigencia_inicio", "vigencia_fim", "objeto", "apresentacao", "justificativa", "descricao_projeto",
    "analise_cenario", "eixos_atuacao", "alinhamento_politicas", "publico_alvo", "contrapartida",
    "metodologia", "resultados_esperados", "metas_json", "orcamento_json", "equipe_json",
    "receitas_json", "parcelas_json", "desembolso_json", "conteudo_integral", "documento_original", "status",
]


def normalizar_payload(payload):
    dados = {}
    for coluna in COLUNAS_EDITAVEIS:
        valor = payload.get(coluna)
        if coluna in {"metas_json", "orcamento_json", "equipe_json", "receitas_json", "parcelas_json", "desembolso_json"}:
            dados[coluna] = texto_json(valor)
        elif coluna == "valor_total":
            dados[coluna] = decimal_ou_zero(valor)
        elif coluna in {"vigencia_inicio", "vigencia_fim"}:
            dados[coluna] = data_ou_none(valor)
        elif coluna == "evento_id":
            dados[coluna] = int(valor) if str(valor or "").isdigit() else None
        else:
            dados[coluna] = str(valor or "").strip()
    return dados


def serializar_registro(row, completo=True):
    if not row:
        return None
    dado = dict(row)
    for campo in ("valor_total",):
        dado[campo] = float(decimal_ou_zero(dado.get(campo)))
    for campo in ("vigencia_inicio", "vigencia_fim"):
        valor = dado.get(campo)
        dado[campo] = valor.isoformat() if valor else ""
    for campo in ("criado_em", "atualizado_em"):
        valor = dado.get(campo)
        dado[campo] = valor.isoformat() if valor else ""
    for campo in ("metas_json", "orcamento_json", "equipe_json", "receitas_json", "parcelas_json", "desembolso_json"):
        dado[campo] = json_seguro(dado.get(campo))
    if not completo:
        dado.pop("conteudo_integral", None)
        for campo in (
            "objeto", "apresentacao", "justificativa", "descricao_projeto", "analise_cenario",
            "eixos_atuacao", "alinhamento_politicas", "publico_alvo", "contrapartida",
            "metodologia", "resultados_esperados",
        ):
            dado.pop(campo, None)
    return dado


def obter_fomento(fomento_id):
    garantir_schema_fomentos()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM eventos_fomentos WHERE id = %s", (fomento_id,))
            return cur.fetchone()
    finally:
        conn.close()


@bp_fomentos.route("/eventos/fomentos")
@login_obrigatorio
def pagina_fomentos():
    garantir_schema_fomentos()
    return render_template("eventos_fomentos.html")


@bp_fomentos.route("/api/eventos/fomentos", methods=["GET"])
@login_obrigatorio
def listar_fomentos():
    garantir_schema_fomentos()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, termo_numero, plano_trabalho_numero, titulo_projeto, osc_nome,
                       valor_total, vigencia_inicio, vigencia_fim, status, atualizado_em
                FROM eventos_fomentos
                ORDER BY atualizado_em DESC, id DESC
                """
            )
            return jsonify({"status": "ok", "dados": [serializar_registro(row, False) for row in cur.fetchall()]})
    finally:
        conn.close()


@bp_fomentos.route("/api/eventos/fomentos/<int:fomento_id>", methods=["GET"])
@login_obrigatorio
def detalhar_fomento(fomento_id):
    registro = obter_fomento(fomento_id)
    if not registro:
        return jsonify({"status": "erro", "mensagem": "Termo de fomento nao encontrado."}), 404
    return jsonify({"status": "ok", "dado": serializar_registro(registro)})


@bp_fomentos.route("/api/eventos/fomentos", methods=["POST"])
@bp_fomentos.route("/api/eventos/fomentos/<int:fomento_id>", methods=["POST"])
@login_obrigatorio
def salvar_fomento(fomento_id=None):
    garantir_schema_fomentos()
    payload = request.get_json(silent=True) or request.form.to_dict()
    dados = normalizar_payload(payload)
    if not dados["termo_numero"] or not dados["titulo_projeto"]:
        return jsonify({"status": "erro", "mensagem": "Informe o numero do termo e o titulo do projeto."}), 400

    usuario = session.get("nome_exibicao") or session.get("usuario_logado") or "Sistema"
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if fomento_id:
                atribuicoes = ", ".join(f"{coluna} = %s" for coluna in COLUNAS_EDITAVEIS)
                valores = [dados[coluna] for coluna in COLUNAS_EDITAVEIS]
                cur.execute(
                    f"UPDATE eventos_fomentos SET {atribuicoes}, atualizado_por = %s WHERE id = %s",
                    valores + [usuario, fomento_id],
                )
            else:
                colunas = ", ".join(COLUNAS_EDITAVEIS)
                marcadores = ", ".join(["%s"] * len(COLUNAS_EDITAVEIS))
                valores = [dados[coluna] for coluna in COLUNAS_EDITAVEIS]
                cur.execute(
                    f"INSERT INTO eventos_fomentos ({colunas}, criado_por, atualizado_por) VALUES ({marcadores}, %s, %s)",
                    valores + [usuario, usuario],
                )
                fomento_id = cur.lastrowid
        conn.commit()
        return jsonify({"status": "ok", "mensagem": "Termo de fomento salvo com sucesso.", "id": fomento_id})
    except Exception as erro:
        if "Duplicate entry" in str(erro):
            return jsonify({"status": "erro", "mensagem": "Ja existe um cadastro com este numero de termo."}), 409
        raise
    finally:
        conn.close()


@bp_fomentos.route("/api/eventos/fomentos/<int:fomento_id>", methods=["DELETE"])
@login_obrigatorio
def excluir_fomento(fomento_id):
    garantir_schema_fomentos()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM eventos_fomentos WHERE id = %s", (fomento_id,))
        conn.commit()
        return jsonify({"status": "ok", "mensagem": "Termo excluido."})
    finally:
        conn.close()


@bp_fomentos.route("/eventos/fomentos/<int:fomento_id>/imprimir")
@login_obrigatorio
def imprimir_fomento(fomento_id):
    registro = obter_fomento(fomento_id)
    if not registro:
        return redirect(url_for("fomentos.pagina_fomentos"))
    return render_template(
        "eventos_fomento_impressao.html",
        fomento=serializar_registro(registro),
        dinheiro=dinheiro,
        data_br=data_br,
    )
