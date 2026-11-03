# JP2 Business — autoridade corporativa (estado e contrato)

## Auditoria do repositório (2026-11-03)

- Aplicação principal: Flask 3 / Python (`app.py`, `Procfile: gunicorn app:app`), HTML/Jinja em `templates/`, CSS/JS em `static/`; blueprints `financeiro`, `eventos`, `fomentos`, `carteira`, `atas`, `tarefas`, `consultoria`. `database.py` usa PyMySQL e variáveis `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`; `autocommit=True`. Dump legado em `BDADOSSQL/brobon39_ibdtec_painel.sql`; não é migration executada automaticamente. DDL adicional no próprio `app.py` no primeiro acesso. `storage.py` integra R2.
- `package.json`/`render.yaml` declaram outro serviço Next/Prisma, mas **não há** `prisma/`, `scripts/` ou árvore Next neste checkout. Não tratar o manifesto Node como backend em execução. `next.config.mjs` está presente. README descreve serviço Render separado; infraestrutura efetiva não verificável daqui. Domínio `app.ibdtec.ong.br` é citado em arquivos LEIA-ME; configuração real de produção/homologação: NOT_DISCOVERED. Docker/Railway/Vercel/Redis/GitHub Actions: NOT_IMPLEMENTED neste checkout. Segredos de produção: NOT_DISCOVERED.
- Identidade anterior: tabela `usuarios` (id, usuario, senha, nome_exibicao, perfil), `empresas` (id, nome, cnpj, ramo_atividade). Sem vínculo usuário×empresa; `empresa_id` já aparece no domínio financeiro. Login `/login` usa hash Werkzeug scrypt e aceita SHA-256 legado migrado no login. `ADMIN_USERS` pode elevar usuário. Admin usa TOTP (`pyotp`) no login. Sessão Flask assinada no **cookie**, expira após 8h (`PERMANENT_SESSION_LIFETIME`); não há armazenamento/revogação server-side. Logout `/logout` limpa cookie no navegador; não revoga outros cookies/dispositivos. Proteção CSRF global para métodos de escrita, cookie HttpOnly/SameSite Lax/Secure configurável; controle de tentativa de login em memória por processo (não distribuído). Perfil global `admin`, `socio`, `leitura` e verificações ad hoc em rotas; não é RBAC corporativo. Logs em `logs_auditoria`. MFA global para todos: NOT_IMPLEMENTED (admin usa TOTP). Password reset/rotation e revogação de sessão após troca de senha: NOT_IMPLEMENTED.
- Busca literal foi realizada no código por: user, users, usuario, usuarios, auth, authentication, authorization, login, logout, session, sessions, token, jwt, refresh, password, role, roles, permission, permissions, company, companies, empresa, empresas, tenant, tenancy, organization, oauth, oidc, openid, sso, callback, redirect. OIDC/OAuth provider, JWKS, client registry e SSO: NOT_IMPLEMENTED.

## Autoridade e limites

JP2 controla **quem é**, a associação a empresas, o contexto selecionado, o papel corporativo por empresa e a autorização de acesso a sistemas. ERP controla estoque, finanças, vendas, produção, fiscal, compras e WMS; Commerce controla catálogo, checkout, pagamentos, pedidos, canais, OMS e storefront. Nunca acessar diretamente bancos desses sistemas. Identidade corporativa futura é referenciada por `usuarios.id`, não se cria uma segunda tabela de usuários/senhas. Os outros sistemas não foram consultados nem modificados.

```
JP2 (identity/control plane)
  └── futura federação OIDC/SSO (NÃO IMPLEMENTADA)
       ├── BROBOND ERP (domínio operacional)
       ├── BROBOND COMMERCE (domínio comercial)
       └── outros sistemas
```

## Identity / Company / Membership / Corporate RBAC

Migration manual `migrations/20261103_corporate_authority.sql`: `corporate_memberships` com UNIQUE `(user_id, empresa_id)`, FK para `usuarios` e `empresas`, papel `admin|socio|leitura` (nomenclatura existente), estado `active|revoked`; sem `organizationId`. `corporate_system_access` tem PK `(membership_id, system_id)`. Papel corporativo é contextual e **não** habilita administração global; administração de acessos requer `usuarios.perfil='admin'` relido do DB. `ADMIN_USERS` legado ainda concede privilégio em outras rotas; alinhar antes de federar. Contexto de empresa é explicitamente selecionado em `/sistemas/contexto`, guardado no cookie assinado, e **relido/validado** contra membership ativo em cada consulta corporativa. Revogar membership retira imediatamente visibilidade corporativa inclusive se o cookie antigo continuar válido. Não migra/atribui memberships automaticamente; admin deve conceder após revisão. Acesso ao JP2 legado permanece independente do catálogo durante a transição.

**Limite crítico**: módulos operacionais preexistentes não consultam `corporate_memberships`; diversos endpoints financeiros verificam apenas `usuario_logado` e recebem `empresa_id` do cliente. Logo o isolamento corporativo demonstrado nos testes aplica-se **somente às novas rotas corporativas**. Não afirmar isolamento global/tenant escape = NO em produção até revisar essas rotas.

## System Registry / URL / environment

`corporate_systems` contém slug único, nome, descrição, base_url opcional, environment, status, icon, access_policy. Seeds idempotentes: JP2 ativo; ERP, Commerce, Store inativos. `base_url` é apenas cadastral (origem HTTPS sem path, userinfo, query, fragment); não existe redirect nem token, mesmo se ativado. Admin determina URL e ambiente explicitamente; nenhum fallback entre DEVELOPMENT/STAGING/PRODUCTION. URLs reais não foram descobertas; não inventar. URLs/credenciais de integração não são incluídas no frontend/API. Catálogo completo é visível apenas para admins na página protegida. API retorna somente sistemas ativos concedidos no membership ativo e contexto atual; a tela de detalhe nunca encaminha ao sistema remoto. Para integração futura, exigir allowlist de redirect URIs por cliente e ambiente; nunca reutilizar `base_url` como allowlist de callback.

## API

`GET /api/corporate/me`: cookie Flask autenticado; identidade mínima, empresa selecionada, memberships próprios, papel selecionado, sistemas ativos autorizados. `GET /api/corporate/systems`: apenas sistemas autorizados no contexto. `Cache-Control: no-store`. **Não são endpoints bearer**, não usar como API entre aplicações. Sem CORS permissivo; clientes externos não devem consumir cookies JP2. Para API futura: validação JWT issuer/audience/expiry/scope/company, rate limit distribuído e CORS explícito antes de liberar integrações.

## OIDC / OAuth / SSO / client registration / logout

OIDC_IMPLEMENTED = NO. OIDC_ARCHITECTURE_READY = contrato documentado, **não provider operacional**. A stack Flask comporta biblioteca/provider confiável e storage persistente, mas cookie Flask stateless, ausência de sessão corporativa revogável, rate limit distribuído, chaves assimétricas/JWKS e client registry impedem publicar um authorization server seguro nesta etapa. NÃO existem `/.well-known/openid-configuration`, `/oauth/authorize`, `/oauth/token`, `/oauth/userinfo`, `/oauth/jwks`, `/oauth/revoke`, `/oauth/logout`. Não emitir tokens ou criar callbacks fictícios. Próxima implementação: escolher provider mantido e auditado; definir issuer canônico `JP2_BASE_URL`, HTTPS, registro administrativo de clientes com segredo armazenado com hash quando aplicável, redirect allowlist exata por ambiente, grants authorization code + PKCE, state/nonce, escopos mínimos `openid profile email company systems` somente quando dados existirem, consentimento/associação por empresa, assinatura assimétrica e JWKS com rotação, armazenamento transacional de códigos/sessões/revogações, introspecção ou TTL curto com revogação coordenada. Logout central deve revogar sessão persistente e informar consumidores conforme contrato acordado. Sem JWT_SECRET compartilhado, senhas copiadas, tokens em URL ou iframe.

## Events / audit / segurança

`corporate_audit` registra acesso/negação, mudanças de contexto, membership e grant/revoke com ator, empresa, sistema quando aplicável, timestamp, IP do request, user-agent truncado, correlation_id gerado e resultado. Não armazena senha ou tokens. Logs legados de login/logout permanecem em `logs_auditoria`, sem correlação com auditoria corporativa. Os eventos de integração `USER_CREATED`, `USER_UPDATED`, `USER_DISABLED`, `MEMBERSHIP_CREATED`, `MEMBERSHIP_REVOKED`, `ROLE_CHANGED`, `COMPANY_CREATED`, `COMPANY_UPDATED`, `SYSTEM_ACCESS_GRANTED`, `SYSTEM_ACCESS_REVOKED` são **contrato futuro**, não publicações atuais. Quando houver outbox, envelopes: `event_id`, `event_type`, `aggregate_id`, `timestamp`, `correlation_id`, `payload`, `version`; consumidores idempotentes por event_id e operações de grant/membership protegidas por chave única. Sem event bus até haver infraestrutura operacional.

Proteções existentes: CSRF para writes, cookies Secure/HttpOnly/SameSite, templates com autoescape, queries parametrizadas; novas páginas não fazem redirect remoto. **Pendências**: rate limit distribuído (incluindo APIs corporativas e MFA), revogação server-side de sessão, proteção completa contra replay TOTP, revisão de legacy SHA-256, política de senha e reset, revisão tenant de TODOS os módulos, tratamento de falhas de DB e hardening de logs. O `X-Forwarded-For` legado não é confiável sem proxy configurado. Não declarar security PASS global.

## Contratos futuros

**JP2 → BROBOND ERP:** JP2 provê identidade, autenticação, acesso corporativo, contexto empresa, papel e SSO federado; ERP valida tokens emitidos pelo JP2 (issuer/audience/company/expiry/scope) e gerencia autorização operacional e dados ERP. Sem senha corporativa separada no ERP; sem banco compartilhado.

**JP2 → BROBOND COMMERCE:** mesmas garantias de identidade/autenticação/acesso corporativo, claims mínimos e escopos por tenant; Commerce gerencia catálogo, checkout, pagamentos, pedidos, canais, OMS e storefront. Sem banco compartilhado nem senha corporativa separada. Sistemas futuros seguem o mesmo modelo e só entram via registro e aprovação explícita.

## Roadmap e operação

1. Fase 1: modelo corporativo, catálogo e acesso contextual (este PR, requer migration manual e grants administrados).
2. Fase 2: OIDC Provider, sessão revogável e chaves/clientes/redirects.
3. Fase 3: ERP como OIDC client **no repositório próprio**.
4. Fase 4: Commerce como OIDC client no repositório próprio.
5. Fase 5: Corporate API bearer com scopes/tenant e rate limit distribuído.
6. Fase 6: integração de eventos/outbox/idempotência.
7. Fase 7: dashboard corporativo expandido.
8. Fase 8: auditoria/observabilidade centralizadas.

Antes de habilitar produção: backup testado, aplicar SQL ao MySQL JP2 com permissões DDL controladas, validar FKs e nomes/tipos no banco real, revisar memberships e grants individualmente, conferir `FLASK_SECRET_KEY`, HTTPS/cookies e WAF, executar testes MySQL reais em homologação. Não rodar migration automaticamente em requisição ou deploy. Configuração relevante: `FLASK_SECRET_KEY`, `FLASK_COOKIE_SECURE`, `ADMIN_USERS`, `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`. `JP2_BASE_URL` e URLs BROBOND: propostas futuras, **não exigidas/implementadas**. `render.yaml` aponta Node sem fontes suficientes; conciliar manifestos antes de promover deploy.
