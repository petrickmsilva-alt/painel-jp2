# Matriz completa das rotas Flask registradas

Gerada por `python scripts/audit_routes.py` sobre `app.url_map` (inclui rotas novas para comparação).
Classificação conservadora por função registrada e chamadas diretas. Não prova segurança de helpers ou SQL dinâmico.
Identidade `cookie` significa que a função não relê usuário do DB; a proteção CSRF global para writes não substitui autorização.
Rotas operacionais permanecem fora do enforcement corporativo. `NÃO APLICÁVEL` apenas para assets públicos.

Total: 141 rotas; CONFORME: 6, NÃO APLICÁVEL: 3, NÃO CONFORME: 28, PARCIAL: 104

| Rota | Método | Domínio | Identidade | Empresa | Membership | Risco |
|---|---|---|---|---|---|---|
| / | GET | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /2fa/configurar | GET,POST | Auth legado | DB 2FA pendente | N/A | não | PARCIAL |
| /2fa/verificar | GET,POST | Auth legado | DB 2FA pendente | N/A | não | PARCIAL |
| /OneSignalSDKWorker.js | GET | Estático | público | N/A | não | NÃO APLICÁVEL |
| /adicionar-evento | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /admin/acessos | GET,POST | Corporate | DB (usuario recarregado) | alvo validado por FK/DB | admin global; grant exige ativo | CONFORME |
| /admin/alterar_perfil/<int:usuario_id> | POST | Admin legado | DB (admin revalidado) | global; não contextual | não | PARCIAL |
| /admin/alterar_senha/<int:usuario_id> | POST | Admin legado | DB (admin revalidado) | global; não contextual | não | PARCIAL |
| /admin/excluir_usuario/<int:usuario_id> | POST | Admin legado | DB (admin revalidado) | global; não contextual | não | PARCIAL |
| /admin/logs | GET | Admin legado | DB (admin revalidado) | global; não contextual | não | PARCIAL |
| /admin/logs/exportar | GET | Admin legado | DB (admin revalidado) | global; não contextual | não | PARCIAL |
| /admin/usuarios | GET,POST | Admin legado | DB (admin revalidado) | global; não contextual | não | PARCIAL |
| /agenda | GET | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /api/adicionar-empresa | POST | Financeiro | cookie (sem revalidar DB) | empresas globais | não | NÃO CONFORME |
| /api/adicionar-investimento | POST | Financeiro | cookie (sem revalidar DB) | empresa_id fornecido pelo cliente | não | NÃO CONFORME |
| /api/anexos-investimento/<int:id> | GET,POST | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/atualizar-status-investimento/<int:id> | POST | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/auditoria-investimentos | GET | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/corporate/me | GET | Corporate | DB (usuario recarregado) | membership/contexto DB | sim | CONFORME |
| /api/corporate/systems | GET | Corporate | DB (usuario recarregado) | membership/contexto DB | sim | CONFORME |
| /api/detalhe-investimento/<int:id> | GET | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/editar-investimento/<int:id> | POST | Financeiro | cookie (sem revalidar DB) | empresa_id fornecido pelo cliente | não | NÃO CONFORME |
| /api/editar-pagamento-investimento/<int:id> | POST | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/empresas | GET | Financeiro | cookie (sem revalidar DB) | empresas globais | não | NÃO CONFORME |
| /api/eventos | POST | Eventos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos | GET | Eventos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos/<int:evento_id> | POST | Eventos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos/<int:evento_id> | DELETE | Eventos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos/financeiro/<int:evento_id> | GET | Eventos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos/financeiro/<int:evento_id> | POST | Eventos | cookie (sem revalidar DB) | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos/financeiro/<int:evento_id>/custos | POST | Eventos | cookie (sem revalidar DB) | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos/financeiro/custos/<int:custo_id> | POST | Eventos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos/financeiro/custos/<int:custo_id> | DELETE | Eventos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos/fomentos | GET | Fomentos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos/fomentos | POST | Fomentos | cookie (sem revalidar DB) | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos/fomentos/<int:fomento_id> | GET | Fomentos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos/fomentos/<int:fomento_id> | DELETE | Fomentos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos/fomentos/<int:fomento_id> | POST | Fomentos | cookie (sem revalidar DB) | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos/municipios | GET | Eventos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/eventos/sincronizar-csv | POST | Eventos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/excluir-anexo-investimento/<int:id> | DELETE | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/excluir-empresa/<id> | DELETE | Financeiro | cookie (sem revalidar DB) | empresas globais | não | NÃO CONFORME |
| /api/excluir-investimento/<int:id> | DELETE | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/excluir-investimentos-lote | DELETE | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/excluir-pagamento-investimento/<int:id> | DELETE | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/financeiro-nomes | POST | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/financeiro-nomes | GET | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/home-carteira-b3 | GET | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /api/importar-investimentos-excel | POST | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/lancar-pagamento-investimento/<int:id> | POST | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/limpar-investimentos | DELETE | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/listar-eventos | GET | Eventos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /api/notificacoes | GET | Tarefas | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /api/notificacoes/ler | POST | Tarefas | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /api/pagamentos-investimentos | GET | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/performance-status | GET | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /api/preview-importacao-investimentos | POST | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/resumo-dashboard | GET | Arquivos/contatos/home | verificar função auxiliar | sem filtro membership (compartilhado) | não | PARCIAL |
| /api/resumo-investimentos | GET | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /api/tarefas/<int:tarefa_id>/checklist/<int:indice> | POST | Tarefas | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /api/tarefas/<int:tarefa_id>/status | POST | Tarefas | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /atas | GET | Atas | verificar função auxiliar | sem filtro membership (compartilhado) | não | PARCIAL |
| /atas/<int:ata_id> | GET | Atas | verificar função auxiliar | sem filtro membership (compartilhado) | não | PARCIAL |
| /atas/<int:ata_id>/editar | GET,POST | Atas | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /atas/<int:ata_id>/excluir | POST | Atas | verificar função auxiliar | sem filtro membership (compartilhado) | não | PARCIAL |
| /atas/nova | GET,POST | Atas | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /baixar_recurso/<int:arquivo_id> | GET | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /carteira-investimentos | GET | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /carteira-investimentos/ | GET | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /carteira/ | GET | Carteira | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /carteira/api/ranking-acoes | GET | Carteira | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /carteira/api/resumo | GET | Carteira | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /carteira/api/sincronizar-mercado | POST | Carteira | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /carteira/aportes | GET,POST | Carteira | cookie (sem revalidar DB) | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /carteira/aportes/excluir/<int:aporte_id> | POST | Carteira | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /carteira/ativos | GET,POST | Carteira | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /carteira/ativos/excluir/<int:ativo_id> | POST | Carteira | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /carteira/carteira | GET | Carteira | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /carteira/configuracoes | GET,POST | Carteira | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /carteira/historico | GET | Carteira | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /carteira/onde-aportar | GET,POST | Carteira | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /carteira/renda-passiva | GET | Carteira | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /carteira/reserva | GET,POST | Carteira | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /carteira/resumo | GET | Carteira | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /compromissos | GET | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /consultoria | GET | Consultoria | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /consultoria/documentos/<int:documento_id>/excluir | POST | Consultoria | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /consultoria/instituto | GET,POST | Consultoria | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /consultoria/itens/<int:item_id>/atualizar | POST | Consultoria | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /consultoria/municipios/<int:municipio_id> | GET | Consultoria | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /consultoria/municipios/<int:municipio_id>/editar | GET,POST | Consultoria | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /consultoria/municipios/novo | GET,POST | Consultoria | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /consultoria/projetos/<int:projeto_id> | GET | Consultoria | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /consultoria/projetos/<int:projeto_id>/documentos | POST | Consultoria | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /consultoria/projetos/<int:projeto_id>/editar | GET,POST | Consultoria | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /consultoria/projetos/novo | GET,POST | Consultoria | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /contatos | GET | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /contatos/adicionar | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /contatos/editar/<int:contato_id> | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /contatos/emails | GET | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /contatos/emails/adicionar | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /contatos/emails/editar/<int:email_id> | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /contatos/emails/excluir/<int:email_id> | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /contatos/excluir/<int:contato_id> | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /contatos/sites-senhas | GET | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /contatos/sites-senhas/adicionar | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /contatos/sites-senhas/editar/<int:registro_id> | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /contatos/sites-senhas/excluir/<int:registro_id> | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /criar-pasta | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /eventos | GET | Eventos | cookie (sem revalidar DB) | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /eventos/exportar | GET | Eventos | cookie (sem revalidar DB) | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /eventos/fomentos | GET | Eventos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /eventos/fomentos/<int:fomento_id>/imprimir | GET | Eventos | verificar função auxiliar | sem filtro membership (avaliar domínio) | não | PARCIAL |
| /excluir | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /excluir-evento | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /financeiro | GET | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /financeiro/auditoria | GET | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /financeiro/detalhe | GET | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /financeiro/pagamentos | GET | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /financeiro/relacao | GET | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /financeiro/resumo | GET | Financeiro | cookie (sem revalidar DB) | investimentos/empresas sem filtro membership | não | NÃO CONFORME |
| /listar | GET | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /login | GET,POST | Auth legado | DB login / cookie logout | N/A | não | PARCIAL |
| /logout | GET | Auth legado | DB login / cookie logout | N/A | não | PARCIAL |
| /manifest.json | GET | Estático | público | N/A | não | NÃO APLICÁVEL |
| /obter-pai-id | GET | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /painel-arquivos | GET | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /renomear | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /salvar-site | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /sistemas | GET | Corporate | DB (usuario recarregado) | membership/contexto DB | sim | CONFORME |
| /sistemas/<slug> | GET | Corporate | DB (usuario recarregado) | membership/contexto DB | sim | CONFORME |
| /sistemas/contexto | POST | Corporate | DB (usuario recarregado) | membership/contexto DB | sim | CONFORME |
| /static/<path:filename> | GET | Estático | público | N/A | não | NÃO APLICÁVEL |
| /tarefas | GET | Tarefas | verificar função auxiliar | sem filtro membership (compartilhado) | não | PARCIAL |
| /tarefas/<int:tarefa_id> | GET | Tarefas | verificar função auxiliar | sem filtro membership (compartilhado) | não | PARCIAL |
| /tarefas/<int:tarefa_id>/comentar | POST | Tarefas | verificar função auxiliar | sem filtro membership (compartilhado) | não | PARCIAL |
| /tarefas/<int:tarefa_id>/editar | GET,POST | Tarefas | verificar função auxiliar | sem filtro membership (compartilhado) | não | PARCIAL |
| /tarefas/<int:tarefa_id>/excluir | POST | Tarefas | verificar função auxiliar | sem filtro membership (compartilhado) | não | PARCIAL |
| /tarefas/nova | GET,POST | Tarefas | verificar função auxiliar | sem filtro membership (compartilhado) | não | PARCIAL |
| /tarefas/push-config | GET | Tarefas | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
| /upload-avancado | POST | Arquivos/contatos/home | cookie (sem revalidar DB) | sem filtro membership (compartilhado) | não | PARCIAL |
