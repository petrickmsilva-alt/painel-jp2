import re
import unicodedata
import zipfile
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import get_db_connection

bp_financeiro = Blueprint("financeiro", __name__)

FINANCEIRO_SCHEMA_VERIFICADO = False
ORIGEM_IMPORTACAO_EXCEL = "excel_junho_2026"
ABA_IMPORTACAO_EXCEL = "RELACAO DE EMPRESTIMOS (2)"


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
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS investimento_pagamentos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    investimento_id INT NOT NULL,
                    data_pagamento DATE NOT NULL,
                    valor_pago DECIMAL(15,2) NOT NULL DEFAULT 0,
                    observacoes TEXT NULL,
                    criado_por VARCHAR(120) NULL,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
            if not coluna_existe(cur, "investimento_pagamentos", "criado_por"):
                cur.execute("ALTER TABLE investimento_pagamentos ADD COLUMN criado_por VARCHAR(120) NULL")
            colunas = {
                "empresa_id": "INT NULL AFTER id",
                "tipo_recurso": "VARCHAR(80) NULL",
                "observacoes": "TEXT NULL",
                "valor_juros_day": "DECIMAL(15,2) NULL",
                "valor_divida_day": "DECIMAL(15,2) NULL",
                "pgto_day": "DECIMAL(15,2) NULL",
                "valor_divida_futuro": "DECIMAL(15,2) NULL",
                "importacao_origem": "VARCHAR(80) NULL",
                "importacao_id": "VARCHAR(80) NULL",
            }
            for coluna, definicao in colunas.items():
                if not coluna_existe(cur, "investimentos", coluna):
                    cur.execute(f"ALTER TABLE investimentos ADD COLUMN {coluna} {definicao}")
        conn.commit()
        FINANCEIRO_SCHEMA_VERIFICADO = True
    finally:
        conn.close()


def decimal_ou_zero(valor):
    texto = str(valor or "").strip()
    if not texto:
        return Decimal("0")
    texto = texto.replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation:
        return Decimal("0")


def percentual_excel(valor):
    numero = decimal_ou_zero(valor)
    if numero > 0 and numero < 1:
        numero = numero * Decimal("100")
    return numero


def data_excel(valor):
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        serial = float(texto)
        if serial < 30000:
            return None
        return (datetime(1899, 12, 30) + timedelta(days=serial)).date().isoformat()
    except ValueError:
        pass
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto[:10], formato).date().isoformat()
        except ValueError:
            continue
    return None


def texto_limpo(valor):
    return str(valor or "").strip()


def local_name(tag):
    return tag.split("}", 1)[-1]


def normalizar_busca(texto):
    sem_acento = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", sem_acento).strip().upper()


def coluna_para_indice(referencia):
    letras = re.match(r"^[A-Z]+", referencia or "")
    if not letras:
        return 0
    indice = 0
    for letra in letras.group(0):
        indice = indice * 26 + ord(letra) - ord("A") + 1
    return indice


def carregar_shared_strings(zf):
    try:
        stream = zf.open("xl/sharedStrings.xml")
    except KeyError:
        return []

    strings = []
    with stream:
        for _, elem in ET.iterparse(stream, events=("end",)):
            if local_name(elem.tag) == "si":
                partes = []
                for texto in elem.iter():
                    if local_name(texto.tag) == "t" and texto.text:
                        partes.append(texto.text)
                strings.append("".join(partes))
                elem.clear()
    return strings


def caminho_aba(zf, nome_aba):
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    rel_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

    alvo = normalizar_busca(nome_aba)
    for sheet in workbook.iter():
        if local_name(sheet.tag) == "sheet" and normalizar_busca(sheet.attrib.get("name")) == alvo:
            target = rel_map[sheet.attrib[rel_ns]].lstrip("/")
            return target if target.startswith("xl/") else f"xl/{target}"
    raise ValueError(f"Aba '{nome_aba}' nao encontrada na planilha.")


def valor_celula(cell, shared_strings):
    tipo = cell.attrib.get("t")
    valor = ""
    for filho in cell:
        if local_name(filho.tag) in ("v", "t"):
            valor = filho.text or ""
            break
        if local_name(filho.tag) == "is":
            textos = [t.text or "" for t in filho.iter() if local_name(t.tag) == "t"]
            valor = "".join(textos)
            break
    if tipo == "s" and valor:
        indice = int(valor)
        return shared_strings[indice] if indice < len(shared_strings) else ""
    return valor


def extrair_registros_excel(arquivo):
    arquivo.seek(0)
    registros = []
    with zipfile.ZipFile(arquivo) as zf:
        shared_strings = carregar_shared_strings(zf)
        sheet_path = caminho_aba(zf, ABA_IMPORTACAO_EXCEL)
        empty_after_data = 0
        past_data = False

        with zf.open(sheet_path) as stream:
            for _, elem in ET.iterparse(stream, events=("end",)):
                if local_name(elem.tag) != "row":
                    continue

                row_num = int(elem.attrib.get("r", "0"))
                if row_num < 6:
                    elem.clear()
                    continue

                cells = {}
                for cell in elem:
                    if local_name(cell.tag) != "c":
                        continue
                    cells[coluna_para_indice(cell.attrib.get("r"))] = texto_limpo(valor_celula(cell, shared_strings))

                valor = decimal_ou_zero(cells.get(7))
                empresa = texto_limpo(cells.get(2))
                importacao_id = texto_limpo(cells.get(1))
                if importacao_id and empresa and valor > 0:
                    past_data = True
                    empty_after_data = 0
                    registros.append({
                        "importacao_id": importacao_id,
                        "empresa": empresa,
                        "credor": texto_limpo(cells.get(3)),
                        "captador": texto_limpo(cells.get(4)),
                        "tipo_recurso": texto_limpo(cells.get(5)),
                        "finalidade": texto_limpo(cells.get(6)),
                        "valor": valor,
                        "juros": percentual_excel(cells.get(8)),
                        "data_recurso": data_excel(cells.get(9)),
                        "data_pgto": data_excel(cells.get(10)),
                        "observacoes": texto_limpo(cells.get(11)),
                        "valor_juros_day": decimal_ou_zero(cells.get(12)),
                        "valor_divida_day": decimal_ou_zero(cells.get(13)),
                        "pgto_day": decimal_ou_zero(cells.get(14)),
                        "valor_divida_futuro": decimal_ou_zero(cells.get(15)),
                    })
                elif past_data:
                    empty_after_data += 1
                    if empty_after_data > 200:
                        break

                elem.clear()
    return registros


def dinheiro(valor):
    numero = decimal_ou_zero(valor)
    return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def normalizar_json(valor):
    if isinstance(valor, Decimal):
        return float(valor)
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return valor


def normalizar_lista_json(lista):
    return [{chave: normalizar_json(valor) for chave, valor in item.items()} for item in lista]


def resumo_registros(registros):
    empresas = {}
    tipos = {}
    finalidades = {}
    total = Decimal("0")
    total_day = Decimal("0")
    total_futuro = Decimal("0")
    for item in registros:
        total += item["valor"]
        total_day += item["valor_divida_day"]
        total_futuro += item["valor_divida_futuro"]
        for mapa, chave in ((empresas, item["empresa"]), (tipos, item["tipo_recurso"]), (finalidades, item["finalidade"])):
            if chave:
                mapa[chave] = mapa.get(chave, 0) + 1
    return {
        "qtd": len(registros),
        "total_valor": str(total),
        "total_valor_formatado": dinheiro(total),
        "total_day": str(total_day),
        "total_day_formatado": dinheiro(total_day),
        "total_futuro": str(total_futuro),
        "total_futuro_formatado": dinheiro(total_futuro),
        "empresas": empresas,
        "tipos": tipos,
        "finalidades": finalidades,
    }


def obter_ou_criar_empresa(cur, nome):
    cur.execute("SELECT id FROM empresas WHERE UPPER(nome) = UPPER(%s) LIMIT 1", (nome,))
    empresa = cur.fetchone()
    if empresa:
        return empresa["id"]
    cur.execute(
        "INSERT INTO empresas (nome, cnpj, ramo_atividade) VALUES (%s, %s, %s)",
        (nome, "", "Importado da planilha financeira"),
    )
    return cur.lastrowid


def juros_sobre_saldo(valor, taxa_percentual, data_inicio, data_fim):
    principal = decimal_ou_zero(valor)
    taxa = decimal_ou_zero(taxa_percentual) / Decimal("100")
    if not data_inicio or not data_fim or principal <= 0 or taxa <= 0:
        return Decimal("0")
    try:
        inicio = datetime.strptime(str(data_inicio)[:10], "%Y-%m-%d").date()
        fim = datetime.strptime(str(data_fim)[:10], "%Y-%m-%d").date()
    except ValueError:
        return Decimal("0")
    dias = max(0, (fim - inicio).days)
    meses = Decimal(dias) / Decimal("30")
    return principal * taxa * meses


def listar_investimentos_com_pagamentos(cur):
    cur.execute(
        """
        SELECT i.id, i.empresa_id, e.nome AS empresa_nome, i.nome_investidor,
               i.valor_inicial, i.juros_mensais, i.data_inicio, i.captador,
               i.tipo_recurso, i.finalidade, i.data_pgto, i.observacoes,
               i.valor_juros_day, i.valor_divida_day, i.pgto_day,
               i.valor_divida_futuro, i.importacao_origem, i.importacao_id,
               COALESCE(SUM(p.valor_pago), 0) AS total_pago,
               MAX(p.data_pagamento) AS ultima_data_pagamento
        FROM investimentos i
        LEFT JOIN empresas e ON e.id = i.empresa_id
        LEFT JOIN investimento_pagamentos p ON p.investimento_id = i.id
        GROUP BY i.id, i.empresa_id, e.nome, i.nome_investidor, i.valor_inicial,
                 i.juros_mensais, i.data_inicio, i.captador, i.tipo_recurso,
                 i.finalidade, i.data_pgto, i.observacoes, i.valor_juros_day,
                 i.valor_divida_day, i.pgto_day, i.valor_divida_futuro,
                 i.importacao_origem, i.importacao_id
        ORDER BY COALESCE(i.data_pgto, i.data_inicio) ASC, i.id DESC
        """
    )
    dados = cur.fetchall()
    for item in dados:
        projetado = decimal_ou_zero(item.get("valor_divida_futuro"))
        importado_excel = item.get("importacao_origem") == ORIGEM_IMPORTACAO_EXCEL
        if projetado <= 0 and not importado_excel:
            projetado = decimal_ou_zero(item.get("valor_inicial")) + juros_sobre_saldo(
                item.get("valor_inicial"),
                item.get("juros_mensais"),
                item.get("data_inicio"),
                item.get("data_pgto"),
            )
        item["valor_projetado_base"] = projetado
        item["sem_projecao_futura"] = bool(importado_excel and projetado <= 0)
        item["saldo_projetado"] = projetado - decimal_ou_zero(item.get("total_pago"))
        if item["saldo_projetado"] < 0:
            item["saldo_projetado"] = Decimal("0")
    return dados


@bp_financeiro.route("/financeiro")
def pagina_financeiro():
    if "usuario_logado" not in session:
        return redirect(url_for("tela_login"))
    garantir_schema_financeiro()
    return render_template("financeiro.html")


@bp_financeiro.route("/financeiro/relacao")
def pagina_relacao_emprestimos():
    if "usuario_logado" not in session:
        return redirect(url_for("tela_login"))
    garantir_schema_financeiro()
    return render_template("financeiro_relacao.html")


@bp_financeiro.route("/financeiro/detalhe")
def pagina_detalhe_emprestimo():
    if "usuario_logado" not in session:
        return redirect(url_for("tela_login"))
    garantir_schema_financeiro()
    return render_template("financeiro_detalhe.html")


@bp_financeiro.route("/financeiro/resumo")
def pagina_resumo_financeiro():
    if "usuario_logado" not in session:
        return redirect(url_for("tela_login"))
    garantir_schema_financeiro()
    return render_template("financeiro_resumo.html")


@bp_financeiro.route("/financeiro/pagamentos")
def pagina_pagamentos_financeiro():
    if "usuario_logado" not in session:
        return redirect(url_for("tela_login"))
    garantir_schema_financeiro()
    return render_template("financeiro_pagamentos.html")


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
        return jsonify({"status": "sucesso", "dados": normalizar_lista_json(dados)})
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
                (nome, request.form.get("cnpj", "").strip(), request.form.get("ramo_atividade", "").strip()),
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
            dados = listar_investimentos_com_pagamentos(cur)
        conn.close()
        return jsonify({"status": "sucesso", "dados": normalizar_lista_json(dados)})
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
                 captador, tipo_recurso, finalidade, data_pgto, observacoes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    request.form.get("observacoes", "").strip(),
                ),
            )
        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso"})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)}), 500


@bp_financeiro.route("/api/editar-investimento/<int:id>", methods=["POST"])
def editar_investimento(id):
    if "usuario_logado" not in session:
        return jsonify({"status": "erro", "msg": "Nao autorizado"}), 401

    try:
        garantir_schema_financeiro()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE investimentos
                SET empresa_id = %s, nome_investidor = %s, valor_inicial = %s,
                    juros_mensais = %s, data_inicio = %s, captador = %s,
                    tipo_recurso = %s, finalidade = %s, data_pgto = %s,
                    observacoes = %s
                WHERE id = %s
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
                    request.form.get("observacoes", "").strip(),
                    id,
                ),
            )
        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso"})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)}), 500


@bp_financeiro.route("/api/preview-importacao-investimentos", methods=["POST"])
def preview_importacao_investimentos():
    if "usuario_logado" not in session:
        return jsonify({"status": "erro", "msg": "Nao autorizado"}), 401
    arquivo = request.files.get("arquivo")
    if not arquivo:
        return jsonify({"status": "erro", "msg": "Envie uma planilha Excel."}), 400

    try:
        registros = extrair_registros_excel(arquivo.stream)
        resumo = resumo_registros(registros)
        resumo["amostra"] = [
            {
                "id": item["importacao_id"],
                "empresa": item["empresa"],
                "credor": item["credor"],
                "captador": item["captador"],
                "tipo_recurso": item["tipo_recurso"],
                "finalidade": item["finalidade"],
                "valor": dinheiro(item["valor"]),
                "juros": str(item["juros"]),
                "data_recurso": item["data_recurso"] or "",
                "data_pgto": item["data_pgto"] or "",
            }
            for item in registros[:12]
        ]
        return jsonify({"status": "sucesso", "resumo": resumo})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)}), 500


@bp_financeiro.route("/api/importar-investimentos-excel", methods=["POST"])
def importar_investimentos_excel():
    if "usuario_logado" not in session:
        return jsonify({"status": "erro", "msg": "Nao autorizado"}), 401
    arquivo = request.files.get("arquivo")
    if not arquivo:
        return jsonify({"status": "erro", "msg": "Envie uma planilha Excel."}), 400

    try:
        garantir_schema_financeiro()
        registros = extrair_registros_excel(arquivo.stream)
        conn = get_db_connection()
        inseridos = 0
        duplicados = 0
        empresas_criadas = set()
        with conn.cursor() as cur:
            for item in registros:
                cur.execute(
                    """
                    SELECT id FROM investimentos
                    WHERE importacao_origem = %s AND importacao_id = %s
                    LIMIT 1
                    """,
                    (ORIGEM_IMPORTACAO_EXCEL, item["importacao_id"]),
                )
                if cur.fetchone():
                    duplicados += 1
                    continue

                cur.execute("SELECT id FROM empresas WHERE UPPER(nome) = UPPER(%s) LIMIT 1", (item["empresa"],))
                empresa_existente = cur.fetchone()
                empresa_id = obter_ou_criar_empresa(cur, item["empresa"])
                if not empresa_existente:
                    empresas_criadas.add(item["empresa"])

                cur.execute(
                    """
                    INSERT INTO investimentos
                    (empresa_id, nome_investidor, valor_inicial, juros_mensais, data_inicio,
                     captador, tipo_recurso, finalidade, data_pgto, observacoes,
                     valor_juros_day, valor_divida_day, pgto_day, valor_divida_futuro,
                     importacao_origem, importacao_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        empresa_id,
                        item["credor"],
                        item["valor"],
                        item["juros"],
                        item["data_recurso"],
                        item["captador"],
                        item["tipo_recurso"],
                        item["finalidade"],
                        item["data_pgto"],
                        item["observacoes"],
                        item["valor_juros_day"],
                        item["valor_divida_day"],
                        item["pgto_day"],
                        item["valor_divida_futuro"],
                        ORIGEM_IMPORTACAO_EXCEL,
                        item["importacao_id"],
                    ),
                )
                inseridos += 1
        conn.commit()
        conn.close()
        return jsonify({
            "status": "sucesso",
            "inseridos": inseridos,
            "duplicados": duplicados,
            "empresas_criadas": sorted(empresas_criadas),
            "resumo": resumo_registros(registros),
        })
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)}), 500


@bp_financeiro.route("/api/lancar-pagamento-investimento/<int:id>", methods=["POST"])
def lancar_pagamento_investimento(id):
    if "usuario_logado" not in session:
        return jsonify({"status": "erro", "msg": "Nao autorizado"}), 401

    valor = decimal_ou_zero(request.form.get("valor_pago"))
    data_pagamento = request.form.get("data_pagamento") or datetime.now().date().isoformat()
    if valor <= 0:
        return jsonify({"status": "erro", "msg": "Informe um valor de pagamento maior que zero."}), 400

    try:
        garantir_schema_financeiro()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM investimentos WHERE id = %s", (id,))
            existe = cur.fetchone()
            if existe:
                cur.execute(
                    """
                    INSERT INTO investimento_pagamentos
                    (investimento_id, data_pagamento, valor_pago, observacoes, criado_por)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (id, data_pagamento, valor, request.form.get("observacoes", "").strip(), session.get("nome_exibicao", "Sistema")),
                )
        if not existe:
            conn.close()
            return jsonify({"status": "erro", "msg": "Investimento nao encontrado."}), 404
        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso"})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)}), 500


@bp_financeiro.route("/api/pagamentos-investimentos", methods=["GET"])
def pagamentos_investimentos():
    if "usuario_logado" not in session:
        return jsonify({"status": "erro", "msg": "Nao autorizado"}), 401
    try:
        garantir_schema_financeiro()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.investimento_id, p.data_pagamento, p.valor_pago,
                       p.observacoes, p.criado_por, p.criado_em,
                       e.nome AS empresa_nome, i.nome_investidor, i.importacao_id
                FROM investimento_pagamentos p
                INNER JOIN investimentos i ON i.id = p.investimento_id
                LEFT JOIN empresas e ON e.id = i.empresa_id
                ORDER BY p.data_pagamento DESC, p.id DESC
                """
            )
            dados = cur.fetchall()
        conn.close()
        return jsonify({"status": "sucesso", "dados": dados})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)}), 500


@bp_financeiro.route("/api/excluir-pagamento-investimento/<int:id>", methods=["DELETE"])
def excluir_pagamento_investimento(id):
    if "usuario_logado" not in session:
        return jsonify({"status": "erro", "msg": "Nao autorizado"}), 401
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM investimento_pagamentos WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso"})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)}), 500


@bp_financeiro.route("/api/limpar-investimentos", methods=["DELETE"])
def limpar_investimentos():
    if "usuario_logado" not in session:
        return jsonify({"status": "erro", "msg": "Nao autorizado"}), 401

    confirmar = request.args.get("confirmar") == "SIM" and request.args.get("frase") == "LIMPAR FINANCEIRO"
    if not confirmar:
        return jsonify({"status": "erro", "msg": "Confirmacao obrigatoria."}), 400

    try:
        garantir_schema_financeiro()
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM investimento_pagamentos")
            cur.execute("DELETE FROM investimentos")
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
            cur.execute("DELETE FROM investimento_pagamentos WHERE investimento_id = %s", (id,))
            cur.execute("DELETE FROM investimentos WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso"})
    except Exception as e:
        return jsonify({"status": "erro", "msg": str(e)}), 500
