# Carteira de Investimentos JP2BUSINESS

Sistema premium de carteira de investimentos para ativos financeiros, objetivos, ranking, alertas, aporte do mes, reserva, renda passiva e motor de decisao JP2BUSINESS.

Este projeto deve ficar separado do modulo financeiro de eventos do painel principal. No painel JP2, o modulo antigo pode ser tratado como **Investimentos em Eventos**; este projeto fica como **Carteira de Investimentos**.

## Stack

- Next.js
- TypeScript
- MySQL
- Prisma
- Render
- Cloudflare
- GitHub

## Rodar localmente

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
npm start
```

## Variaveis de ambiente

Crie um arquivo `.env`:

```bash
DATABASE_URL="mysql://usuario:senha@host:3306/banco"
```

No Render, cadastre a `DATABASE_URL` manualmente em **Environment**. O `render.yaml` nao cria banco automaticamente porque o projeto esta configurado para MySQL.

## Deploy no Render

O arquivo `render.yaml` ja define:

- Web Service Node
- Build command
- Start command
- Variavel `DATABASE_URL` para preencher no Render

Depois de subir para o GitHub, no Render escolha o repositorio e use o Blueprint ou crie o Web Service manualmente.

Depois que o Render gerar a URL publica do modulo, cadastre esta URL no painel principal usando a variavel:

```bash
CARTEIRA_INVESTIMENTOS_URL="https://sua-carteira.onrender.com"
```

## Autoridade corporativa (Flask)

O painel Flask contém o catálogo de sistemas e o controle de acesso por empresa em
`/sistemas` e `/admin/acessos`. Antes de usar, aplicar manualmente
`migrations/20261103_corporate_authority.sql` no **banco MySQL do próprio JP2**
(após backup e validação em homologação). Não há grants automáticos: o administrador
deve criar memberships e autorizações explícitas. ERP/Commerce ainda não possuem
SSO e nenhum token federado é emitido. Consulte
`docs/JP2-CORPORATE-AUTHORITY-ARCHITECTURE.md` para limites, segurança e roadmap.

Teste isolado do Flask: `python -m unittest discover -s tests -v` após instalar
`requirements.txt` em ambiente virtual. O manifesto Node legado não corresponde à
árvore de fontes deste checkout e deve ser reconciliado antes de qualquer deploy.
