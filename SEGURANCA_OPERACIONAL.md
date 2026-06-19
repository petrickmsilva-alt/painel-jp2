# Checklist de seguranca operacional

## Rotacao de senhas e chaves

1. Trocar a senha do usuario MySQL no HostGator.
2. Atualizar `DB_PASSWORD` no Render.
3. Criar uma nova chave do Cloudflare R2 com acesso apenas ao bucket do painel.
4. Atualizar no Render:
   - `R2_ACCESS_KEY_ID`
   - `R2_SECRET_ACCESS_KEY`
   - `R2_ACCOUNT_ID`
   - `R2_BUCKET_NAME`
5. Gerar um novo `FLASK_SECRET_KEY` forte e atualizar no Render.
6. Revogar as chaves antigas no Cloudflare depois que o deploy novo estiver funcionando.

## Permissoes minimas no MySQL

O usuario do painel deve ter permissao apenas no banco do painel:

```sql
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX
ON brobon39_ibdtec_painel.*
TO 'brobon39_ibdtec_petrick'@'%';
FLUSH PRIVILEGES;
```

Evitar permissao global, `DROP`, `SUPER`, `FILE` ou acesso a outros bancos.

## Cloudflare WAF

No dominio `app.ibdtec.ong.br`:

1. Ativar modo proxy laranja no DNS.
2. Em Security/WAF, criar regras para bloquear paises que nao precisam acessar o painel.
3. Ativar regras gerenciadas contra SQL Injection e XSS.
4. Criar rate limit para `/login`, por exemplo 10 tentativas por minuto por IP.
5. Criar rate limit para rotas de upload.

## Backup testado

1. Criar backup manual no HostGator antes de cada grande importacao.
2. Baixar o arquivo `.sql`.
3. Restaurar esse backup em um banco de teste pelo menos uma vez por mes.
4. Guardar uma copia em local externo seguro.
5. Registrar data, responsavel e resultado do teste de restauracao.

## Politica de acesso

1. Cada socio deve ter usuario proprio.
2. Administradores devem ativar 2FA no primeiro login apos esta rodada.
3. Remover usuarios que nao fazem mais parte da operacao.
4. Revisar logs de auditoria semanalmente.
