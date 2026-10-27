# Atualizações — 26/10/2026

## Comportamento

O aplicativo consulta seu canal HTTPS assinado em segundo plano ao abrir sem argumentos, prepara uma cópia privada e usa a versão validada na próxima abertura. Funciona em instalação no usuário e em .deb sem modificar /usr: o pacote do sistema continua sendo o lançador/retorno. Assinatura Ed25519 por chave pública fixada, SHA-256, tamanho, aplicativo, canal e versão são conferidos. Links, travessia de diretórios, arquivos excessivos e código Python inválido são recusados. Nenhum documento, impressora, configuração de rede ou relatório é enviado. Falha de rede/assinatura mantém o aplicativo instalado. CLI com argumentos não consulta a rede. Se a versão atualizada encerra com erro, retorna ao pacote instalado e bloqueia aquele hash até haver correção. Releases deste canal devem manter formato de dados compatível; rollback de código não reverte migrações. Requer OpenSSL com Ed25519 e Python 3.10 para receber atualizações.

Instalações antigas precisam receber este atualizador uma vez manualmente. Para desativar: definir enabled=false em update-channel.json antes de empacotar. Remover/renomear somente a pasta updates do aplicativo no XDG_DATA_HOME volta ao pacote instalado; preserve sessions/relatorios. A cópia de atualização é revalidada antes de executar, sem elevar a interface a root. Não há instalação automática de dependências novas durante uma atualização: versões com novos requisitos precisam de instalador apropriado e não devem entrar neste canal de código.

Ativação do canal: configurar a chave privada correspondente à chave pública do aplicativo como secret LINKSUL_UPDATE_SIGNING_KEY no ambiente GitHub updates-production; manter a chave fora do repositório. O workflow signed-update.yml prepara e publica o canal ao publicar release final, ou por execução manual, após verificar CI do mesmo commit, domínio e projeto estático correto. O ambiente updates-production precisa de revisão/proteção efetiva, secret VERCEL_TOKEN de escopo restrito e variables VERCEL_ORG_ID/VERCEL_PROJECT_ID do projeto de downloads. O publicador só envia site/dist e os três arquivos assinados; não envia o restante do repositório. Sem essas configurações ele recusa a publicação. Não atribuir a essa rotina credenciais de portais com dados nem usá-la para contornar gates de outros projetos. EasyScan e EasyCUPS têm origem de canal definida, ainda sem feed assinado publicado nesta alteração; EasyNetTest precisa de uma origem aprovada antes de ativar. Nunca tornar repositório privado público ou embutir token no aplicativo para contornar essa configuração. Configurar a publicação do canal é pendência de ativação, não funcionalidade comprovada em produção.

## Dependências

.github/dependabot.yml consulta GitHub Actions e os ecossistemas presentes diariamente às 07:00 (America/Sao_Paulo). Cria PRs; não faz merge ou deploy automático. Atualizações major permanecem separadas dos grupos compatíveis. Credenciais, versões de pacotes do sistema Linux e dados operacionais não são administrados pelo Dependabot. Após merge da configuração na branch padrão o serviço do GitHub poderá iniciar as consultas. PRs devem cumprir README, testes e revisão do projeto; configuração em branch de validação não equivale a ativação.

## FMEA e recuperação

| Falha | Prevenção / recuperação |
|---|---|
| Origem/assinatura/pacote inválido | Recusar; conservar instalação/publicação anterior |
| Rede indisponível ou sessão vencida | Não bloquear o uso atual; tentar em nova verificação |
| Nova versão incompatível | Validar pacote/requisitos e CI antes de publicar; voltar ao artefato/pacote anterior |
| Perda de trabalho em atualização web | Aviso e recarga deliberada; não repetir envios nem apagar filas |
| Dependência quebra comportamento | PR, lockfile, testes e revisão; sem automerge |
| Código confundido com aprovação de dados | Nenhuma alteração/aprovação de dados é automática |

## Evidência e estado

Implementado em branch/PR de validação. tools/check_updates.py verifica política e executa os testes pertinentes sem rede nem segredos. CI existente continua sendo responsável pelos fluxos completos do projeto. Não declarar ativação, publicação ou atualização de todas as instalações antes de merge/release, configuração do canal e teste de uma instalação que receba a versão. Rollback de código não restaura dados externos.
