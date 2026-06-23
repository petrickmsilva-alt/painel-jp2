from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
import json
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
CARTEIRA_TEMPLATE_FALLBACKS = {"layout_carteira.html":"\u003c!DOCTYPE html\u003e\u003chtml lang=\"pt-br\"\u003e\u003chead\u003e\u003cmeta charset=\"utf-8\"\u003e\u003cmeta name=\"viewport\" content=\"width=device-width, initial-scale=1\"\u003e\u003ctitle\u003eCarteira de Investimentos | JP2\u003c/title\u003e\u003clink href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\"\u003e\u003clink rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css\"\u003e\u003cstyle\u003e\nbody{background:#f4f7fb;display:flex;margin:0;min-height:100vh;color:#101828}.sidebar-toggle-btn{align-items:center;background:#fff;border:1px solid #d7e2ef;border-radius:0 8px 8px 0;box-shadow:0 12px 30px rgba(15,23,42,.16);color:#1e293b;display:inline-flex;height:38px;justify-content:center;left:260px;position:fixed;top:18px;transition:.22s;width:38px;z-index:130}.sidebar-toggle-btn:hover{background:#155eef;border-color:#155eef;color:#fff}body.sidebar-collapsed #sidebar{margin-left:-260px}body.sidebar-collapsed .sidebar-toggle-btn{left:0}#sidebar{background:#101a2b;border-right:1px solid rgba(255,255,255,.08);color:white;flex-shrink:0;padding:24px 18px;width:260px;transition:.22s}.sidebar-kicker{color:#93a4bd;font-size:11px;font-weight:850;letter-spacing:.1em;text-transform:uppercase}.sidebar-title{font-size:22px;font-weight:850;line-height:1.1;margin:6px 0 18px}.sidebar-divider{background:rgba(255,255,255,.12);height:1px;margin:18px 0}.sidebar-section{color:#93a4bd;display:block;font-size:11px;font-weight:850;letter-spacing:.1em;margin:20px 8px 8px;text-transform:uppercase}#sidebar a{align-items:center;border:1px solid transparent;border-radius:8px;color:#d6e0ef;display:flex;font-weight:750;gap:10px;margin-bottom:7px;padding:11px 10px;text-decoration:none}#sidebar a:hover,#sidebar a.active{background:#172b49;border-color:rgba(21,94,239,.45);color:#fff}#sidebar i{color:#7fb4ff;font-size:16px}.content{flex-grow:1;min-width:0;overflow-x:hidden;padding:30px}.cart-shell{max-width:1220px;margin:0 auto;padding-bottom:44px}.head{align-items:flex-start;display:flex;justify-content:space-between;gap:18px;margin-bottom:20px}.kicker{color:#667085;font-size:12px;font-weight:850;letter-spacing:.08em;text-transform:uppercase}.title{color:#101828;font-size:30px;font-weight:850;margin:3px 0 4px}.subtitle{color:#667085;font-size:14px;max-width:760px}.panel{background:#fff;border:1px solid #d9e2ef;border-radius:10px;box-shadow:0 14px 36px rgba(15,23,42,.06)}.metric-grid{display:grid;gap:12px;grid-template-columns:repeat(4,minmax(0,1fr));margin-bottom:16px}.metric{background:#fff;border:1px solid #d9e2ef;border-radius:10px;padding:18px;box-shadow:0 14px 36px rgba(15,23,42,.05)}.metric span{color:#667085;display:block;font-size:11px;font-weight:850;letter-spacing:.05em;text-transform:uppercase}.metric strong{display:block;font-size:24px;font-weight:900;margin-top:7px}.form-label{color:#344054;font-size:12px;font-weight:850;letter-spacing:.03em;text-transform:uppercase}.form-control,.form-select{border-color:#d5deeb;border-radius:8px;min-height:42px}.btn{border-radius:8px;font-weight:800}.table thead th{background:#f8fafc;color:#667085;font-size:11px;font-weight:850;letter-spacing:.05em;text-transform:uppercase}.pill{border-radius:999px;display:inline-flex;font-size:11px;font-weight:850;padding:5px 9px}.pill-ok{background:#e7f8ef;color:#067647}.pill-watch{background:#eef4ff;color:#155eef}.pill-stop{background:#fff1f0;color:#b42318}.money{font-weight:900}.muted{color:#667085;font-size:12px}.score{font-size:20px;font-weight:900}@media(max-width:920px){body{display:block}.content{padding:18px 12px}#sidebar{width:100%}.metric-grid{grid-template-columns:1fr 1fr}.head{flex-direction:column}}@media(max-width:560px){.metric-grid{grid-template-columns:1fr}}\u003c/style\u003e\u003c/head\u003e\u003cbody\u003e\u003cbutton class=\"sidebar-toggle-btn\" type=\"button\" onclick=\"alternarMenuLateral()\" title=\"Ocultar ou mostrar menu\"\u003e\u003ci class=\"bi bi-layout-sidebar-inset\"\u003e\u003c/i\u003e\u003c/button\u003e\u003caside id=\"sidebar\"\u003e\u003cdiv class=\"sidebar-kicker\"\u003ePainel de investimentos\u003c/div\u003e\u003cdiv class=\"sidebar-title\"\u003eCarteira executiva\u003c/div\u003e\u003cdiv class=\"sidebar-divider\"\u003e\u003c/div\u003e\u003ca href=\"/\"\u003e\u003ci class=\"bi bi-arrow-left\"\u003e\u003c/i\u003e Voltar ao Painel\u003c/a\u003e\u003cspan class=\"sidebar-section\"\u003eDecisão\u003c/span\u003e\u003ca href=\"/carteira\" class=\"{% if request.path == \u0027/carteira/\u0027 or request.path == \u0027/carteira\u0027 %}active{% endif %}\"\u003e\u003ci class=\"bi bi-command\"\u003e\u003c/i\u003e Comando\u003c/a\u003e\u003ca href=\"/carteira/onde-aportar\" class=\"{% if \u0027/onde-aportar\u0027 in request.path %}active{% endif %}\"\u003e\u003ci class=\"bi bi-bullseye\"\u003e\u003c/i\u003e Onde aportar\u003c/a\u003e\u003ca href=\"/carteira/resumo\" class=\"{% if \u0027/resumo\u0027 in request.path %}active{% endif %}\"\u003e\u003ci class=\"bi bi-pie-chart\"\u003e\u003c/i\u003e Resumo\u003c/a\u003e\u003cspan class=\"sidebar-section\"\u003eGestão\u003c/span\u003e\u003ca href=\"/carteira/ativos\" class=\"{% if \u0027/ativos\u0027 in request.path %}active{% endif %}\"\u003e\u003ci class=\"bi bi-wallet2\"\u003e\u003c/i\u003e Ativos\u003c/a\u003e\u003ca href=\"/carteira/aportes\" class=\"{% if \u0027/aportes\u0027 in request.path %}active{% endif %}\"\u003e\u003ci class=\"bi bi-cash-coin\"\u003e\u003c/i\u003e Aportes\u003c/a\u003e\u003ca href=\"/carteira/configuracoes\" class=\"{% if \u0027/configuracoes\u0027 in request.path %}active{% endif %}\"\u003e\u003ci class=\"bi bi-sliders\"\u003e\u003c/i\u003e Política da carteira\u003c/a\u003e\u003c/aside\u003e\u003cmain class=\"content\"\u003e{% with messages=get_flashed_messages() %}{% if messages %}\u003cdiv class=\"cart-shell\"\u003e\u003cdiv class=\"alert alert-success\"\u003e{{ messages[-1] }}\u003c/div\u003e\u003c/div\u003e{% endif %}{% endwith %}{% block content %}{% endblock %}\u003c/main\u003e\u003cscript src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js\"\u003e\u003c/script\u003e\u003cscript\u003efunction alternarMenuLateral(){const r=document.body.classList.toggle(\u0027sidebar-collapsed\u0027);localStorage.setItem(\u0027jp2CarteiraSidebarCollapsed\u0027,r?\u00271\u0027:\u00270\u0027)}document.addEventListener(\u0027DOMContentLoaded\u0027,()=\u003e{if(localStorage.getItem(\u0027jp2CarteiraSidebarCollapsed\u0027)===\u00271\u0027)document.body.classList.add(\u0027sidebar-collapsed\u0027)});function preencherAtivo(btn){const d=btn.dataset;for(const k in d){const el=document.querySelector(`[name=\"${k}\"]`);if(el)el.value=d[k];}scrollTo({top:0,behavior:\u0027smooth\u0027});}\u003c/script\u003e\u003c/body\u003e\u003c/html\u003e\r\n","carteira_dashboard.html":"{% extends \u0027layout_carteira.html\u0027 %}{% block content %}\u003cdiv class=\"cart-shell\"\u003e\u003cheader class=\"head\"\u003e\u003cdiv\u003e\u003cdiv class=\"kicker\"\u003ePainel inicial\u003c/div\u003e\u003ch1 class=\"title\"\u003eCarteira de Investimentos JP2Business\u003c/h1\u003e\u003cdiv class=\"subtitle\"\u003eComando central para patrimônio, classes, score, risco e direção de aporte.\u003c/div\u003e\u003c/div\u003e\u003ca class=\"btn btn-primary\" href=\"/carteira/onde-aportar\"\u003e\u003ci class=\"bi bi-bullseye\"\u003e\u003c/i\u003e Simular aporte\u003c/a\u003e\u003c/header\u003e\u003cdiv class=\"metric-grid\"\u003e\u003cdiv class=\"metric\"\u003e\u003cspan\u003ePatrimônio cadastrado\u003c/span\u003e\u003cstrong\u003e{{ br_money(total) }}\u003c/strong\u003e\u003c/div\u003e\u003cdiv class=\"metric\"\u003e\u003cspan\u003eAtivos\u003c/span\u003e\u003cstrong\u003e{{ ativos|length }}\u003c/strong\u003e\u003c/div\u003e\u003cdiv class=\"metric\"\u003e\u003cspan\u003eScore médio\u003c/span\u003e\u003cstrong\u003e{{ score_medio or \u0027-\u0027 }}\u003c/strong\u003e\u003c/div\u003e\u003cdiv class=\"metric\"\u003e\u003cspan\u003eMelhor direção\u003c/span\u003e\u003cstrong\u003e{{ candidatos[0].ticker if candidatos else \u0027-\u0027 }}\u003c/strong\u003e\u003c/div\u003e\u003c/div\u003e\u003cdiv class=\"row g-3\"\u003e\u003cdiv class=\"col-lg-7\"\u003e\u003csection class=\"panel p-3\"\u003e\u003ch5 class=\"fw-bold mb-3\"\u003eClasses abaixo da meta\u003c/h5\u003e\u003ctable class=\"table align-middle\"\u003e\u003cthead\u003e\u003ctr\u003e\u003cth\u003eClasse\u003c/th\u003e\u003cth\u003eAtual\u003c/th\u003e\u003cth\u003eMeta\u003c/th\u003e\u003cth\u003eGap\u003c/th\u003e\u003cth\u003eValor\u003c/th\u003e\u003c/tr\u003e\u003c/thead\u003e\u003ctbody\u003e{% for g in grupos[:8] %}\u003ctr\u003e\u003ctd\u003e\u003cstrong\u003e{{ g.classe }}\u003c/strong\u003e\u003cdiv class=\"muted\"\u003e{{ g.descricao }}\u003c/div\u003e\u003c/td\u003e\u003ctd\u003e{{ \u0027%.1f\u0027|format(g.atual) }}%\u003c/td\u003e\u003ctd\u003e{{ \u0027%.1f\u0027|format(g.alvo) }}%\u003c/td\u003e\u003ctd\u003e\u003cspan class=\"pill {{ \u0027pill-ok\u0027 if g.gap \u003e 0 else \u0027pill-watch\u0027 }}\"\u003e{{ \u0027%.1f\u0027|format(g.gap) }}%\u003c/span\u003e\u003c/td\u003e\u003ctd class=\"money\"\u003e{{ br_money(g.valor) }}\u003c/td\u003e\u003c/tr\u003e{% endfor %}\u003c/tbody\u003e\u003c/table\u003e\u003c/section\u003e\u003c/div\u003e\u003cdiv class=\"col-lg-5\"\u003e\u003csection class=\"panel p-3\"\u003e\u003ch5 class=\"fw-bold mb-3\"\u003eAtivos com melhor sinal\u003c/h5\u003e{% for a in candidatos[:6] %}\u003cdiv class=\"d-flex justify-content-between border-bottom py-2\"\u003e\u003cdiv\u003e\u003cstrong\u003e{{ a.ticker }}\u003c/strong\u003e\u003cdiv class=\"muted\"\u003e{{ a.nome }} - {{ a.classe }}\u003c/div\u003e\u003c/div\u003e\u003cdiv class=\"text-end\"\u003e\u003cdiv class=\"score\"\u003e{{ a.score }}\u003c/div\u003e\u003cspan class=\"pill pill-ok\"\u003e{{ a.decisao }}\u003c/span\u003e\u003c/div\u003e\u003c/div\u003e{% else %}\u003cdiv class=\"text-secondary\"\u003eCadastre ativos com indicadores para o sistema indicar aportes.\u003c/div\u003e{% endfor %}\u003c/section\u003e\u003c/div\u003e\u003c/div\u003e\u003c/div\u003e{% endblock %}\r\n","carteira_ativos.html":"{% extends \u0027layout_carteira.html\u0027 %}{% block content %}\u003cdiv class=\"cart-shell\"\u003e\u003cheader class=\"head\"\u003e\u003cdiv\u003e\u003cdiv class=\"kicker\"\u003eGestão de ativos\u003c/div\u003e\u003ch1 class=\"title\"\u003eCadastro e score dos ativos\u003c/h1\u003e\u003cdiv class=\"subtitle\"\u003eRegistre ações, FIIs, renda fixa, ETFs, stocks e REITs com indicadores para o motor de decisão.\u003c/div\u003e\u003c/div\u003e\u003c/header\u003e\u003csection class=\"panel p-3 mb-3\"\u003e\u003cform method=\"post\" class=\"row g-3\"\u003e\u003cinput type=\"hidden\" name=\"id\"\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eTicker\u003c/label\u003e\u003cinput class=\"form-control\" name=\"ticker\" required\u003e\u003c/div\u003e\u003cdiv class=\"col-md-4\"\u003e\u003clabel class=\"form-label\"\u003eNome\u003c/label\u003e\u003cinput class=\"form-control\" name=\"nome\" required\u003e\u003c/div\u003e\u003cdiv class=\"col-md-3\"\u003e\u003clabel class=\"form-label\"\u003eClasse\u003c/label\u003e\u003cselect class=\"form-select\" name=\"classe\"\u003e{% for c in classes %}\u003coption\u003e{{ c }}\u003c/option\u003e{% endfor %}\u003c/select\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003ePaís\u003c/label\u003e\u003cinput class=\"form-control\" name=\"pais\" value=\"Brasil\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-1\"\u003e\u003clabel class=\"form-label\"\u003eMoeda\u003c/label\u003e\u003cinput class=\"form-control\" name=\"moeda\" value=\"BRL\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-3\"\u003e\u003clabel class=\"form-label\"\u003eSetor\u003c/label\u003e\u003cinput class=\"form-control\" name=\"setor\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-3\"\u003e\u003clabel class=\"form-label\"\u003eValor atual\u003c/label\u003e\u003cinput class=\"form-control\" name=\"valor_atual\" placeholder=\"R$ 0,00\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eQuantidade\u003c/label\u003e\u003cinput class=\"form-control\" name=\"quantidade\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003ePreço médio\u003c/label\u003e\u003cinput class=\"form-control\" name=\"preco_medio\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eStatus\u003c/label\u003e\u003cselect class=\"form-select\" name=\"status\"\u003e\u003coption value=\"aportar\"\u003eAportar\u003c/option\u003e\u003coption value=\"observar\" selected\u003eObservar\u003c/option\u003e\u003coption value=\"pausar\"\u003ePausar\u003c/option\u003e\u003c/select\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eDY %\u003c/label\u003e\u003cinput class=\"form-control\" name=\"dividend_yield\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eROIC %\u003c/label\u003e\u003cinput class=\"form-control\" name=\"roic\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eMargem líquida %\u003c/label\u003e\u003cinput class=\"form-control\" name=\"margem_liquida\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eDívida/EBITDA\u003c/label\u003e\u003cinput class=\"form-control\" name=\"divida_ebitda\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eLiquidez diária\u003c/label\u003e\u003cinput class=\"form-control\" name=\"liquidez_diaria\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eGovernança\u003c/label\u003e\u003cinput class=\"form-control\" name=\"governanca\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eP/L\u003c/label\u003e\u003cinput class=\"form-control\" name=\"pl\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eP/VP\u003c/label\u003e\u003cinput class=\"form-control\" name=\"pvp\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eROE %\u003c/label\u003e\u003cinput class=\"form-control\" name=\"roe\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eLucro CAGR %\u003c/label\u003e\u003cinput class=\"form-control\" name=\"lucro_cagr\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003ePreço teto\u003c/label\u003e\u003cinput class=\"form-control\" name=\"preco_teto\"\u003e\u003c/div\u003e\u003cdiv class=\"col-12\"\u003e\u003clabel class=\"form-label\"\u003eObservações\u003c/label\u003e\u003ctextarea class=\"form-control\" name=\"observacoes\" rows=\"2\"\u003e\u003c/textarea\u003e\u003c/div\u003e\u003cdiv class=\"col-12 text-end\"\u003e\u003cbutton class=\"btn btn-outline-secondary\" type=\"reset\"\u003eLimpar\u003c/button\u003e \u003cbutton class=\"btn btn-primary\"\u003e\u003ci class=\"bi bi-save\"\u003e\u003c/i\u003e Salvar ativo\u003c/button\u003e\u003c/div\u003e\u003c/form\u003e\u003c/section\u003e\u003csection class=\"panel p-3\"\u003e\u003ctable class=\"table align-middle\"\u003e\u003cthead\u003e\u003ctr\u003e\u003cth\u003eTicker\u003c/th\u003e\u003cth\u003eClasse\u003c/th\u003e\u003cth\u003eValor\u003c/th\u003e\u003cth\u003eIndicadores\u003c/th\u003e\u003cth\u003eScore\u003c/th\u003e\u003cth\u003eDecisão\u003c/th\u003e\u003cth\u003eAções\u003c/th\u003e\u003c/tr\u003e\u003c/thead\u003e\u003ctbody\u003e{% for a in ativos %}\u003ctr\u003e\u003ctd\u003e\u003cstrong\u003e{{ a.ticker }}\u003c/strong\u003e\u003cdiv class=\"muted\"\u003e{{ a.nome }}\u003c/div\u003e\u003c/td\u003e\u003ctd\u003e{{ a.classe }}\u003cdiv class=\"muted\"\u003e{{ a.pais }} - {{ a.moeda }}\u003c/div\u003e\u003c/td\u003e\u003ctd class=\"money\"\u003e{{ br_money(a.valor_atual) }}\u003c/td\u003e\u003ctd\u003e\u003cdiv class=\"muted\"\u003eROIC {{ a.roic or 0 }}% | Margem {{ a.margem_liquida or 0 }}%\u003c/div\u003e\u003cdiv class=\"muted\"\u003eDívida {{ a.divida_ebitda or 0 }} | Liquidez {{ br_money(a.liquidez_diaria) }}\u003c/div\u003e\u003cdiv class=\"muted\"\u003eP/L {{ a.pl or 0 }} | P/VP {{ a.pvp or 0 }} | ROE {{ a.roe or 0 }}%\u003c/div\u003e\u003c/td\u003e\u003ctd\u003e\u003cspan class=\"score\"\u003e{{ a.score }}\u003c/span\u003e\u003c/td\u003e\u003ctd\u003e\u003cspan class=\"pill {{ \u0027pill-ok\u0027 if a.decisao == \u0027Aportar\u0027 else \u0027pill-stop\u0027 if a.decisao == \u0027Não aportar\u0027 else \u0027pill-watch\u0027 }}\"\u003e{{ a.decisao }}\u003c/span\u003e\u003c/td\u003e\u003ctd\u003e\u003cform method=\"post\" action=\"/carteira/ativos/excluir/{{ a.id }}\" onsubmit=\"return confirm(\u0027Excluir este ativo?\u0027)\"\u003e\u003cbutton class=\"btn btn-sm btn-outline-danger\"\u003e\u003ci class=\"bi bi-trash\"\u003e\u003c/i\u003e\u003c/button\u003e\u003c/form\u003e\u003c/td\u003e\u003c/tr\u003e{% else %}\u003ctr\u003e\u003ctd colspan=\"7\" class=\"text-center text-secondary py-4\"\u003eNenhum ativo cadastrado.\u003c/td\u003e\u003c/tr\u003e{% endfor %}\u003c/tbody\u003e\u003c/table\u003e\u003c/section\u003e\u003c/div\u003e{% endblock %}\r\n","carteira_onde_aportar.html":"{% extends \u0027layout_carteira.html\u0027 %}{% block content %}\u003cdiv class=\"cart-shell\"\u003e\u003cheader class=\"head\"\u003e\u003cdiv\u003e\u003cdiv class=\"kicker\"\u003eMotor de decisão\u003c/div\u003e\u003ch1 class=\"title\"\u003eOnde aportar agora\u003c/h1\u003e\u003cdiv class=\"subtitle\"\u003eInforme o valor disponível e o sistema distribui por classe abaixo da meta e ativos com melhor score.\u003c/div\u003e\u003c/div\u003e\u003c/header\u003e\u003csection class=\"panel p-3 mb-3\"\u003e\u003cform method=\"post\" class=\"row g-2 align-items-end\"\u003e\u003cdiv class=\"col-md-8\"\u003e\u003clabel class=\"form-label\"\u003eValor disponível\u003c/label\u003e\u003cinput class=\"form-control form-control-lg\" name=\"valor_aporte\" value=\"{{ br_money(valor) }}\"\u003e\u003c/div\u003e\u003cdiv class=\"col-md-4\"\u003e\u003cbutton class=\"btn btn-primary btn-lg w-100\"\u003e\u003ci class=\"bi bi-magic\"\u003e\u003c/i\u003e Gerar direção\u003c/button\u003e\u003c/div\u003e\u003c/form\u003e\u003c/section\u003e\u003cdiv class=\"metric-grid\"\u003e\u003cdiv class=\"metric\"\u003e\u003cspan\u003eCarteira atual\u003c/span\u003e\u003cstrong\u003e{{ br_money(total) }}\u003c/strong\u003e\u003c/div\u003e\u003cdiv class=\"metric\"\u003e\u003cspan\u003eAporte simulado\u003c/span\u003e\u003cstrong\u003e{{ br_money(valor) }}\u003c/strong\u003e\u003c/div\u003e\u003cdiv class=\"metric\"\u003e\u003cspan\u003eAtivos elegíveis\u003c/span\u003e\u003cstrong\u003e{{ candidatos|length }}\u003c/strong\u003e\u003c/div\u003e\u003cdiv class=\"metric\"\u003e\u003cspan\u003ePrioridade\u003c/span\u003e\u003cstrong\u003e{{ grupos[0].classe if grupos else \u0027-\u0027 }}\u003c/strong\u003e\u003c/div\u003e\u003c/div\u003e\u003csection class=\"panel p-3\"\u003e\u003ch5 class=\"fw-bold mb-3\"\u003eDistribuição recomendada\u003c/h5\u003e\u003ctable class=\"table align-middle\"\u003e\u003cthead\u003e\u003ctr\u003e\u003cth\u003eClasse\u003c/th\u003e\u003cth\u003eAtivo\u003c/th\u003e\u003cth\u003eValor sugerido\u003c/th\u003e\u003cth\u003eMotivo\u003c/th\u003e\u003c/tr\u003e\u003c/thead\u003e\u003ctbody\u003e{% for r in alocacoes %}\u003ctr\u003e\u003ctd\u003e\u003cstrong\u003e{{ r.classe }}\u003c/strong\u003e\u003c/td\u003e\u003ctd\u003e{% if r.ativo %}\u003cstrong\u003e{{ r.ativo.ticker }}\u003c/strong\u003e\u003cdiv class=\"muted\"\u003e{{ r.ativo.nome }} | score {{ r.ativo.score }}\u003c/div\u003e{% else %}\u003cspan class=\"text-secondary\"\u003eCadastrar ativo elegível\u003c/span\u003e{% endif %}\u003c/td\u003e\u003ctd class=\"money\"\u003e{{ br_money(r.valor) }}\u003c/td\u003e\u003ctd\u003e{{ r.motivo }}\u003c/td\u003e\u003c/tr\u003e{% endfor %}\u003c/tbody\u003e\u003c/table\u003e\u003c/section\u003e\u003c/div\u003e{% endblock %}\r\n","carteira_resumo.html":"{% extends \u0027layout_carteira.html\u0027 %}{% block content %}\u003cdiv class=\"cart-shell\"\u003e\u003cheader class=\"head\"\u003e\u003cdiv\u003e\u003cdiv class=\"kicker\"\u003eResumo geral\u003c/div\u003e\u003ch1 class=\"title\"\u003eCarteira atual x carteira ideal\u003c/h1\u003e\u003cdiv class=\"subtitle\"\u003eVisão por classe, concentração e qualidade dos ativos cadastrados.\u003c/div\u003e\u003c/div\u003e\u003cbutton class=\"btn btn-outline-secondary\" onclick=\"window.print()\"\u003e\u003ci class=\"bi bi-printer\"\u003e\u003c/i\u003e Imprimir\u003c/button\u003e\u003c/header\u003e\u003cdiv class=\"metric-grid\"\u003e\u003cdiv class=\"metric\"\u003e\u003cspan\u003eTotal\u003c/span\u003e\u003cstrong\u003e{{ br_money(total) }}\u003c/strong\u003e\u003c/div\u003e\u003cdiv class=\"metric\"\u003e\u003cspan\u003eClasses\u003c/span\u003e\u003cstrong\u003e{{ grupos|length }}\u003c/strong\u003e\u003c/div\u003e\u003cdiv class=\"metric\"\u003e\u003cspan\u003eAtivos\u003c/span\u003e\u003cstrong\u003e{{ ativos|length }}\u003c/strong\u003e\u003c/div\u003e\u003cdiv class=\"metric\"\u003e\u003cspan\u003eMaior gap\u003c/span\u003e\u003cstrong\u003e{{ grupos[0].classe if grupos else \u0027-\u0027 }}\u003c/strong\u003e\u003c/div\u003e\u003c/div\u003e\u003csection class=\"panel p-3 mb-3\"\u003e\u003ch5 class=\"fw-bold mb-3\"\u003eResumo por classe\u003c/h5\u003e\u003ctable class=\"table align-middle\"\u003e\u003cthead\u003e\u003ctr\u003e\u003cth\u003eClasse\u003c/th\u003e\u003cth\u003eValor\u003c/th\u003e\u003cth\u003eAtual\u003c/th\u003e\u003cth\u003eMeta\u003c/th\u003e\u003cth\u003eGap\u003c/th\u003e\u003cth\u003eAtivos\u003c/th\u003e\u003c/tr\u003e\u003c/thead\u003e\u003ctbody\u003e{% for g in grupos %}\u003ctr\u003e\u003ctd\u003e\u003cstrong\u003e{{ g.classe }}\u003c/strong\u003e\u003cdiv class=\"muted\"\u003e{{ g.descricao }}\u003c/div\u003e\u003c/td\u003e\u003ctd class=\"money\"\u003e{{ br_money(g.valor) }}\u003c/td\u003e\u003ctd\u003e{{ \u0027%.1f\u0027|format(g.atual) }}%\u003c/td\u003e\u003ctd\u003e{{ \u0027%.1f\u0027|format(g.alvo) }}%\u003c/td\u003e\u003ctd\u003e\u003cspan class=\"pill {{ \u0027pill-ok\u0027 if g.gap \u003e 0 else \u0027pill-watch\u0027 }}\"\u003e{{ \u0027%.1f\u0027|format(g.gap) }}%\u003c/span\u003e\u003c/td\u003e\u003ctd\u003e{{ g.ativos }}\u003c/td\u003e\u003c/tr\u003e{% endfor %}\u003c/tbody\u003e\u003c/table\u003e\u003c/section\u003e\u003csection class=\"panel p-3\"\u003e\u003ch5 class=\"fw-bold mb-3\"\u003eRanking dos ativos\u003c/h5\u003e\u003ctable class=\"table align-middle\"\u003e\u003cthead\u003e\u003ctr\u003e\u003cth\u003eAtivo\u003c/th\u003e\u003cth\u003eClasse\u003c/th\u003e\u003cth\u003eValor\u003c/th\u003e\u003cth\u003eScore\u003c/th\u003e\u003cth\u003eDecisão\u003c/th\u003e\u003cth\u003eAlertas\u003c/th\u003e\u003c/tr\u003e\u003c/thead\u003e\u003ctbody\u003e{% for a in ativos|sort(attribute=\u0027score\u0027, reverse=true) %}\u003ctr\u003e\u003ctd\u003e\u003cstrong\u003e{{ a.ticker }}\u003c/strong\u003e\u003cdiv class=\"muted\"\u003e{{ a.nome }}\u003c/div\u003e\u003c/td\u003e\u003ctd\u003e{{ a.classe }}\u003c/td\u003e\u003ctd class=\"money\"\u003e{{ br_money(a.valor_atual) }}\u003c/td\u003e\u003ctd class=\"score\"\u003e{{ a.score }}\u003c/td\u003e\u003ctd\u003e\u003cspan class=\"pill {{ \u0027pill-ok\u0027 if a.decisao == \u0027Aportar\u0027 else \u0027pill-stop\u0027 if a.decisao == \u0027Não aportar\u0027 else \u0027pill-watch\u0027 }}\"\u003e{{ a.decisao }}\u003c/span\u003e\u003c/td\u003e\u003ctd\u003e{{ \u0027, \u0027.join(a.bloqueios) if a.bloqueios else \u0027, \u0027.join(a.motivos) }}\u003c/td\u003e\u003c/tr\u003e{% endfor %}\u003c/tbody\u003e\u003c/table\u003e\u003c/section\u003e\u003c/div\u003e{% endblock %}\r\n","carteira_aportes.html":"{% extends \u0027layout_carteira.html\u0027 %}{% block content %}\u003cdiv class=\"cart-shell\"\u003e\u003cheader class=\"head\"\u003e\u003cdiv\u003e\u003cdiv class=\"kicker\"\u003eAportes\u003c/div\u003e\u003ch1 class=\"title\"\u003eHistórico de movimentações\u003c/h1\u003e\u003cdiv class=\"subtitle\"\u003eRegistre compras, vendas, dividendos e aportes planejados da carteira.\u003c/div\u003e\u003c/div\u003e\u003c/header\u003e\u003csection class=\"panel p-3 mb-3\"\u003e\u003cform method=\"post\" class=\"row g-3\"\u003e\u003cdiv class=\"col-md-4\"\u003e\u003clabel class=\"form-label\"\u003eAtivo\u003c/label\u003e\u003cselect class=\"form-select\" name=\"ativo_id\"\u003e\u003coption value=\"\"\u003eSem ativo específico\u003c/option\u003e{% for a in ativos %}\u003coption value=\"{{ a.id }}\"\u003e{{ a.ticker }} - {{ a.nome }}\u003c/option\u003e{% endfor %}\u003c/select\u003e\u003c/div\u003e\u003cdiv class=\"col-md-3\"\u003e\u003clabel class=\"form-label\"\u003eClasse\u003c/label\u003e\u003cselect class=\"form-select\" name=\"classe\"\u003e{% for c in classes %}\u003coption\u003e{{ c }}\u003c/option\u003e{% endfor %}\u003c/select\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eTipo\u003c/label\u003e\u003cselect class=\"form-select\" name=\"tipo\"\u003e\u003coption\u003ecompra\u003c/option\u003e\u003coption\u003evenda\u003c/option\u003e\u003coption\u003edividendo\u003c/option\u003e\u003coption\u003eaporte planejado\u003c/option\u003e\u003c/select\u003e\u003c/div\u003e\u003cdiv class=\"col-md-2\"\u003e\u003clabel class=\"form-label\"\u003eValor\u003c/label\u003e\u003cinput class=\"form-control\" name=\"valor\" required\u003e\u003c/div\u003e\u003cdiv class=\"col-md-1\"\u003e\u003clabel class=\"form-label\"\u003eData\u003c/label\u003e\u003cinput type=\"date\" class=\"form-control\" name=\"data_aporte\" value=\"{{ hoje }}\"\u003e\u003c/div\u003e\u003cdiv class=\"col-12\"\u003e\u003clabel class=\"form-label\"\u003eObservações\u003c/label\u003e\u003ctextarea class=\"form-control\" name=\"observacoes\" rows=\"2\"\u003e\u003c/textarea\u003e\u003c/div\u003e\u003cdiv class=\"col-12 text-end\"\u003e\u003cbutton class=\"btn btn-primary\"\u003e\u003ci class=\"bi bi-plus-circle\"\u003e\u003c/i\u003e Registrar\u003c/button\u003e\u003c/div\u003e\u003c/form\u003e\u003c/section\u003e\u003csection class=\"panel p-3\"\u003e\u003ctable class=\"table align-middle\"\u003e\u003cthead\u003e\u003ctr\u003e\u003cth\u003eData\u003c/th\u003e\u003cth\u003eAtivo\u003c/th\u003e\u003cth\u003eClasse\u003c/th\u003e\u003cth\u003eTipo\u003c/th\u003e\u003cth\u003eValor\u003c/th\u003e\u003cth\u003eCriado por\u003c/th\u003e\u003cth\u003e\u003c/th\u003e\u003c/tr\u003e\u003c/thead\u003e\u003ctbody\u003e{% for p in aportes %}\u003ctr\u003e\u003ctd\u003e{{ p.data_aporte }}\u003c/td\u003e\u003ctd\u003e\u003cstrong\u003e{{ p.ticker or \u0027-\u0027 }}\u003c/strong\u003e\u003cdiv class=\"muted\"\u003e{{ p.nome or p.observacoes or \u0027\u0027 }}\u003c/div\u003e\u003c/td\u003e\u003ctd\u003e{{ p.classe }}\u003c/td\u003e\u003ctd\u003e\u003cspan class=\"pill pill-watch\"\u003e{{ p.tipo }}\u003c/span\u003e\u003c/td\u003e\u003ctd class=\"money\"\u003e{{ br_money(p.valor) }}\u003c/td\u003e\u003ctd\u003e{{ p.criado_por or \u0027-\u0027 }}\u003c/td\u003e\u003ctd\u003e\u003cform method=\"post\" action=\"/carteira/aportes/excluir/{{ p.id }}\" onsubmit=\"return confirm(\u0027Excluir este lançamento?\u0027)\"\u003e\u003cbutton class=\"btn btn-sm btn-outline-danger\"\u003e\u003ci class=\"bi bi-trash\"\u003e\u003c/i\u003e\u003c/button\u003e\u003c/form\u003e\u003c/td\u003e\u003c/tr\u003e{% else %}\u003ctr\u003e\u003ctd colspan=\"7\" class=\"text-center text-secondary py-4\"\u003eNenhum aporte registrado.\u003c/td\u003e\u003c/tr\u003e{% endfor %}\u003c/tbody\u003e\u003c/table\u003e\u003c/section\u003e\u003c/div\u003e{% endblock %}\r\n","carteira_configuracoes.html":"{% extends \u0027layout_carteira.html\u0027 %}{% block content %}\u003cdiv class=\"cart-shell\"\u003e\u003cheader class=\"head\"\u003e\u003cdiv\u003e\u003cdiv class=\"kicker\"\u003ePolítica da carteira\u003c/div\u003e\u003ch1 class=\"title\"\u003eMetas e limites\u003c/h1\u003e\u003cdiv class=\"subtitle\"\u003eDefina a carteira ideal. O motor usa estes percentuais para dizer onde aportar.\u003c/div\u003e\u003c/div\u003e\u003c/header\u003e\u003cform method=\"post\"\u003e\u003csection class=\"panel p-3\"\u003e\u003ctable class=\"table align-middle\"\u003e\u003cthead\u003e\u003ctr\u003e\u003cth\u003eClasse\u003c/th\u003e\u003cth\u003eMeta %\u003c/th\u003e\u003cth\u003eLimite por ativo %\u003c/th\u003e\u003cth\u003eDescrição\u003c/th\u003e\u003c/tr\u003e\u003c/thead\u003e\u003ctbody\u003e{% for p in politica %}\u003ctr\u003e\u003ctd\u003e\u003cstrong\u003e{{ p.classe }}\u003c/strong\u003e\u003cinput type=\"hidden\" name=\"classe\" value=\"{{ p.classe }}\"\u003e\u003c/td\u003e\u003ctd style=\"width:130px\"\u003e\u003cinput class=\"form-control\" name=\"alvo_{{ p.classe }}\" value=\"{{ p.percentual_alvo }}\"\u003e\u003c/td\u003e\u003ctd style=\"width:160px\"\u003e\u003cinput class=\"form-control\" name=\"limite_{{ p.classe }}\" value=\"{{ p.limite_por_ativo }}\"\u003e\u003c/td\u003e\u003ctd\u003e\u003cinput class=\"form-control\" name=\"descricao_{{ p.classe }}\" value=\"{{ p.descricao or \u0027\u0027 }}\"\u003e\u003c/td\u003e\u003c/tr\u003e{% endfor %}\u003c/tbody\u003e\u003c/table\u003e\u003cdiv class=\"text-end\"\u003e\u003cbutton class=\"btn btn-primary\"\u003e\u003ci class=\"bi bi-save\"\u003e\u003c/i\u003e Salvar política\u003c/button\u003e\u003c/div\u003e\u003c/section\u003e\u003c/form\u003e\u003c/div\u003e{% endblock %}\r\n"}

@bp_carteira.record_once
def registrar_templates_fallback(state):
    fallback_loader = DictLoader(CARTEIRA_TEMPLATE_FALLBACKS)
    if state.app.jinja_loader:
        state.app.jinja_loader = ChoiceLoader([state.app.jinja_loader, fallback_loader])
    else:
        state.app.jinja_loader = fallback_loader

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
CRITERIOS_PADRAO = [
    ("Ações Brasil", "roic_min", 10, 15, 18, "ROIC mínimo para empresa produtiva"),
    ("Ações Brasil", "margem_liquida_min", 8, 12, 16, "Margem líquida mínima"),
    ("Ações Brasil", "divida_ebitda_max", 3.5, 2.5, 18, "Bloqueio de dívida elevada"),
    ("Ações Brasil", "liquidez_diaria_min", 6000000, 10000000, 10, "Liquidez média diária"),
    ("Stocks", "roic_min", 10, 15, 18, "ROIC mínimo para empresas globais"),
    ("Stocks", "margem_liquida_min", 8, 12, 16, "Margem líquida mínima"),
    ("Stocks", "divida_ebitda_max", 3.5, 2.5, 18, "Dívida controlada"),
    ("FIIs", "dividend_yield_min", 6, 8, 10, "Renda passiva mínima"),
    ("REITs", "dividend_yield_min", 4, 6, 8, "Renda em dólar"),
    ("ETFs", "liquidez_diaria_min", 1000000, 5000000, 8, "Liquidez do ETF"),
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
        garantir_coluna(cur, "carteira_ativos", "pl", "DECIMAL(18,4) DEFAULT 0")
        garantir_coluna(cur, "carteira_ativos", "pvp", "DECIMAL(18,4) DEFAULT 0")
        garantir_coluna(cur, "carteira_ativos", "roe", "DECIMAL(10,4) DEFAULT 0")
        garantir_coluna(cur, "carteira_ativos", "lucro_cagr", "DECIMAL(10,4) DEFAULT 0")
        garantir_coluna(cur, "carteira_ativos", "preco_teto", "DECIMAL(18,4) DEFAULT 0")
        cur.execute("SELECT COUNT(*) AS total FROM carteira_politica")
        if int(cur.fetchone()["total"] or 0) == 0:
            cur.executemany("INSERT INTO carteira_politica (classe, percentual_alvo, limite_por_ativo, prioridade, descricao) VALUES (%s,%s,%s,%s,%s)", POLITICA_PADRAO)
        cur.execute("SELECT COUNT(*) AS total FROM carteira_inteligencia_criterios")
        if int(cur.fetchone()["total"] or 0) == 0:
            cur.executemany("INSERT INTO carteira_inteligencia_criterios (classe, criterio, minimo, ideal, peso, descricao) VALUES (%s,%s,%s,%s,%s,%s)", CRITERIOS_PADRAO)
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

    if classe in ("Ações Brasil", "Stocks"):
        if roic >= roic_ideal: score += 18; motivos.append("ROIC forte")
        elif roic >= roic_min: score += 12; motivos.append("ROIC adequado")
        else: score -= 14; bloqueios.append("ROIC abaixo do filtro")
        if margem >= margem_ideal: score += 16; motivos.append("margem confortável")
        elif margem >= margem_min: score += 9; motivos.append("margem mínima atendida")
        else: score -= 16; bloqueios.append("margem abaixo de 8%")
        if roe >= 12: score += 6; motivos.append("ROE saudável")
        if lucro_cagr >= 8: score += 6; motivos.append("crescimento de lucro")
        if pl and pl <= 18: score += 5; motivos.append("valuation aceitável")
        elif pl > 28: score -= 8; bloqueios.append("valuation caro")
    if classe in ("FIIs", "REITs"):
        if dy >= dy_min: score += 12; motivos.append("renda passiva atrativa")
        else: score -= 8; bloqueios.append("renda passiva baixa")
        if pvp and pvp <= 1.05: score += 6; motivos.append("P/VP controlado")
        elif pvp > 1.20: score -= 6; bloqueios.append("P/VP esticado")
    if classe in ("ETFs",):
        if liquidez >= max(1000000, liquidez_min): score += 8; motivos.append("ETF com liquidez")
    if divida and divida <= divida_ideal: score += 10; motivos.append("dívida controlada")
    elif divida > divida_max: score -= 18; bloqueios.append("dívida elevada")
    if liquidez >= liquidez_min: score += 10; motivos.append("liquidez adequada")
    elif classe in ("Ações Brasil", "FIIs", "Stocks", "REITs") and liquidez > 0: score -= 8; bloqueios.append("liquidez fraca")
    if any(x in gov for x in ("novo", "nível", "nivel", "adr", "etf", "reit")): score += 8; motivos.append("governança favorável")
    if preco_teto and preco and preco <= preco_teto: score += 8; motivos.append("preço dentro do teto")
    elif preco_teto and preco > preco_teto: score -= 10; bloqueios.append("preço acima do teto")
    if status == "aportar": score += 8
    if status == "pausar": score = min(score, 35); bloqueios.append("marcado para pausar")
    score = max(0, min(100, int(round(score))))
    decisao = "Aportar" if score >= 75 and not bloqueios else "Observar" if score >= 55 else "Não aportar"
    if status == "pausar": decisao = "Não aportar"
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


def ticker_yahoo(ticker, classe, pais):
    t=(ticker or "").upper().strip()
    if pais == "Brasil" and classe in ("Ações Brasil", "FIIs") and not t.endswith(".SA"):
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
        d=request.form; ativo_id=d.get("id"); payload=((d.get("ticker") or "").upper().strip(), d.get("nome") or "", d.get("classe") or "Ações Brasil", d.get("pais") or "Brasil", d.get("setor") or "", d.get("moeda") or "BRL", num(d.get("quantidade")), num(d.get("preco_medio")), num(d.get("valor_atual")), num(d.get("dividend_yield")), num(d.get("roic")), num(d.get("margem_liquida")), num(d.get("divida_ebitda")), num(d.get("liquidez_diaria")), d.get("governanca") or "", d.get("status") or "observar", d.get("observacoes") or "", num(d.get("pl")), num(d.get("pvp")), num(d.get("roe")), num(d.get("lucro_cagr")), num(d.get("preco_teto")))
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
    conn=get_db_connection()
    with conn.cursor() as cur: cur.execute("SELECT a.*, c.ticker, c.nome FROM carteira_aportes a LEFT JOIN carteira_ativos c ON c.id=a.ativo_id ORDER BY a.data_aporte DESC,a.id DESC LIMIT 500"); lista=cur.fetchall()
    conn.close(); return render_template("carteira_aportes.html", ativos=listar_ativos(), aportes=lista, classes=CLASSES, hoje=date.today().isoformat(), br_money=br_money)


@bp_carteira.route("/aportes/excluir/<int:aporte_id>", methods=["POST"])
@login_required
def excluir_aporte(aporte_id):
    conn=get_db_connection()
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
        conn=get_db_connection()
        with conn.cursor() as cur:
            for classe in request.form.getlist("classe"):
                cur.execute("UPDATE carteira_politica SET percentual_alvo=%s, limite_por_ativo=%s, descricao=%s WHERE classe=%s", (num(request.form.get(f"alvo_{classe}")), num(request.form.get(f"limite_{classe}"),10), request.form.get(f"descricao_{classe}") or "", classe))
        conn.close(); flash("Política atualizada."); return redirect(url_for("carteira.configuracoes"))
    return render_template("carteira_configuracoes.html", politica=listar_politica())


@bp_carteira.route("/api/resumo")
@login_required
def api_resumo():
    ativos=listar_ativos(); grupos,total=resumo_classes(ativos); return jsonify({"total":total,"classes":grupos,"ativos":ativos})


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
