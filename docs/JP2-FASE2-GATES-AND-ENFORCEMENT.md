# Fase 2 — gates, enforcement e fundação de sessão revogável

**Data:** 2026-11-03 · **PR:** separado, a partir de `arena/007b5907-painel-jp2`.
O PR #125 (Fase 1, `arena/8f6d73bb-painel-jp2`) foi preservado: nenhum push,
merge, close ou alteração naquela branch. Esta branch contém os commits da
Fase 1 por fast-forward e, acima deles, apenas os commits desta fase.

## Estado declarado (não conclusões de produção)

| Marcador | Valor |
|---|---|
| `OIDC_IMPLEMENTED` | **NO** |
| `ENFORCEMENT_PADRAO` | **DESLIGADO** (opt-in por `JP2_ENFORCE_CORPORATE_CONTEXT`) |
| `SESSOES_REVOGAVEIS_PADRAO` | **DESLIGADO** (opt-in por `JP2_REVOCABLE_SESSIONS`) |
| `ISOLAMENTO_GLOBAL_DE_DADOS` | **NAO COMPROVADO** |
| `ENFORCEMENT_EM_PRODUCAO` | **NAO ATIVADO** |
| `MYSQL_DE_HOMOLOGACAO` | **NAO EXECUTADO** |
| `DEPLOY` | **NAO EXECUTADO** |
| `ACESSO_A_ERP_OU_COMMERCE` | **NAO REALIZADO** (nenhum banco, URL, credencial ou repositório) |

Marcadores verificados pelo gate de contrato (não remova nem altere):

```
OIDC_IMPLEMENTED = NO
ENFORCEMENT_PADRAO = DESLIGADO
ISOLAMENTO_GLOBAL_DE_DADOS = NAO COMPROVADO
MYSQL_DE_HOMOLOGACAO = NAO EXECUTADO
```

Não declaramos os gates nem o enforcement como concluídos em produção. Gates de
CI são verificações locais/isoladas; enforcement é uma política **desligada por
padrão** que depende de migration manual, grants revisados e homologação.

## O que foi implementado

### 1. Gates de contrato (CI)

Novo workflow `.github/workflows/jp2-fase2-gates.yml` (MySQL 8 descartável,
sem secrets de produção) e `scripts/check_contract.py`, que falha o build se:

- qualquer rota `/oauth`, `/jwks`, `/userinfo`, `/.well-known` ou
  `openid-configuration` aparecer, ou existir módulo `oidc*.py`/`oauth*.py`;
- o inventário gerado `scripts/audit_routes.py` divergir de
  `docs/JP2-LEGACY-ROUTE-MATRIX.md` (141 rotas — nenhuma rota nova nesta fase);
- as duas flags deixarem de estar **desligadas por padrão**;
- os módulos novos contiverem artefatos de federação, URL externa/cliente HTTP,
  DDL em tempo de request ou leitura de migration;
- os seeds de ERP/Commerce no catálogo deixarem de estar `inactive`;
- este documento deixar de declarar os marcadores de estado acima.

O workflow também roda `compileall`, Ruff e `unittest discover -s tests -v` com
`JP2_REQUIRE_MYSQL=1`, de modo que a suíte de integração MySQL da Fase 1 e a
nova suíte de sessões não sejam ignoradas por skip silencioso.

### 2. Enforcement opt-in em rotas legadas

`corporate_enforcement.py` registra um `before_request` que, **somente com
`JP2_ENFORCE_CORPORATE_CONTEXT=1`**:

1. relê a identidade do banco (`usuarios`), não aceitando cookie como prova;
2. exige membership **ativa** e contexto de empresa explicitamente selecionado,
   revalidado contra `corporate_memberships`;
3. recusa `empresa_id` enviado pelo cliente (query/form/JSON) quando divergente
   do contexto, inclusive valor inválido;
4. bloqueia rotas de efeito global sem filtro por membership
   (`/api/empresas`, `/api/adicionar-empresa`, `/api/excluir-empresa`,
   importação de planilhas e exclusões em lote);
5. registra cada negativa em `corporate_audit` com `result='denied'`;
6. **falha fechada**: erro de banco ou exceção inesperada gera `403`, sem
   expor SQL, ids ou stack trace ao cliente.

Estão isentos: `/login`, `/logout`, `/2fa*`, assets estáticos e as rotas do
próprio blueprint corporativo (que já revalidam identidade/membership).

**Limite crítico (inalterado):** este é um gate de **acesso**, não isolamento de
dados. `financeiro.py` e os demais módulos legados continuam com SQL sem filtro
por membership; consultas por `id` (`/api/detalhe-investimento/<id>` etc.) e
dados compartilhados de outros domínios **não** passam a ser isolados. A matriz
da Fase 1 permanece 6 CONFORME / 28 NÃO CONFORME / 104 PARCIAL / 3 N/A.
Não afirmar "tenant escape = NO" em produção.

### 3. Fundação de sessão revogável (opt-in)

`revocable_sessions.py` + `migrations/20261104_revocable_sessions.sql`:

- handle opaco aleatório no cookie assinado do Flask; no banco fica apenas seu
  digest SHA-256, na tabela `jp2_sessions` (FK para `usuarios`, `expires_at`,
  `revoked_at`, `revoke_reason`), criada por migration **manual e idempotente**;
- com `JP2_REVOCABLE_SESSIONS=1`, o login emite a linha e cada request
  autenticada revalida: ausência do handle, revogação, expiração ou falha de
  banco encerram a sessão (fail-closed). Cookies antigos precisam de novo login;
- `revoke()` no logout e `revoke_user()` para revogação administrativa de todos
  os dispositivos de um usuário (fundação para troca de senha e revogação de
  membership);
- **não é** provedor OIDC, não emite credencial assinada, não é aceito por
  ERP/Commerce e não cria allowlist de redirect, client registry, PKCE, JWKS,
  escopos ou logout federado. Nenhum endpoint OIDC incompleto foi publicado.

A tabela usa prefixo `jp2_` (não `corporate_`) para não alterar o inventário de
tabelas/FKs verificado pela suíte MySQL da Fase 1. Sessão Flask assinada e
stateless continua sendo o mecanismo de cookie; a revogação vem da checagem da
linha no banco, não de uma segunda implementação de cookies.

## Como ativar (procedimento, não executado aqui)

1. Backup testado e aplicação **manual** de
   `migrations/20261103_corporate_authority.sql` e
   `migrations/20261104_revocable_sessions.sql` em homologação, com DDL
   controlado; validar FKs, tipos e charset no banco real.
2. Revisar e conceder memberships/grants individualmente. Sem isso, ligar o
   gate bloqueia usuários legítimos.
3. Subir as flags apenas em homologação e observar `corporate_audit` com
   `action='LEGACY_CONTEXT_DENIED'`, taxa de `403` e logs de falha de banco.
4. Antes de produção: revisar o SQL de **todos** os módulos legados, rate limit
   distribuído, lifecycle/status de usuário, replay de TOTP e o manifesto Node
   incompleto. Nenhum desses itens foi resolvido nesta fase.

## Evidências

| Verificação | Resultado |
|---|---|
| `compileall`, `ruff` (legado + novos), `git diff --check` (local) | ✅ passaram |
| `scripts/check_contract.py` (local) | ✅ `CONTRACT PASS`: 141 rotas, nenhuma rota de federação, flags desligadas, nenhum acesso externo/DDL em request |
| Inventário reproduzível (`audit_routes.py` + `git diff --exit-code`) | ✅ matriz inalterada: 141 rotas (6/28/104/3) |
| `unittest discover -s tests -v` (local, sem MySQL) | ✅ 38 testes passaram; **2 classes MySQL integração puladas** — não há servidor MySQL isolado neste sandbox |
| Suíte MySQL 8 descartável (CI, `JP2_REQUIRE_MYSQL=1`) | **aguardando o run deste PR** |
| Banco real de homologação/produção | **não executado** |
| Deploy, migration em banco real, SSO/tokens | **não executados** |

Local significa apenas este sandbox: sem MySQL, sem homologação e sem produção.
Um `CONTRACT PASS` local não é gate de CI verde e muito menos autorização de deploy.

## Roadmap (inalterado quanto ao OIDC)

1. Fase 1 — modelo corporativo, catálogo e acesso contextual (PR #125).
2. Fase 2 (parcial, este PR) — gates de contrato, enforcement opt-in e fundação
   de sessão revogável. OIDC Provider, chaves/clientes/redirects **seguem NÃO
   IMPLEMENTADOS**; devem usar provider mantido e auditado, sessão persistente,
   Authorization Code + PKCE, state/nonce, assinatura assimétrica com JWKS e
   rotação, escopos mínimos e logout central.
3. Fases 3–4 — ERP e Commerce como clientes OIDC **em seus próprios
   repositórios**, nunca com banco compartilhado.
4. Fases 5–8 — API bearer com scopes/tenant, eventos/outbox, dashboard e
   observabilidade.
