# Regressões — 27/10/2026

Estado: desenvolvimento em validação. Nenhuma implantação, ativação de canal, homologação física ou merge é representado por este documento.

## Mudança

Falhas de descoberta/fila aparecem como erro, preservando a diferença entre indisponibilidade e lista vazia. Timeout não recomenda repetir uma operação sem consultar seu resultado. Atualizador trata término por sinal como falha.

## Evidência e limites

36 testes existentes e 2 novos testes dos callbacks reais aprovados com widgets simulados; sem comandos de impressora nesses testes. Faltam ensaio GTK e impressora real.

## Padrão LinkSul

Secure, stable, simple, scalable; preservar dados, permissões, identidade visual e regras existentes. Referência: proposta v0.1.1 da metodologia, commit e5bd602599b0340dae5a7672ae6224a2905b72f9, PR linksul-metodologia-software#4 (ainda em revisão). Teste local, CI, instalação e produção são estados distintos.

## Aceite e recuperação

Reproduzir o gatilho da regressão com dados fictícios; confirmar saída e estado preservado; ensaiar caminho de erro/cancelamento. Antes de distribuir, relacionar commit, versão do artefato e ambiente de execução. Guardar backups de dados e configuração; eventual reversão de código não desfaz transações, mensagens ou dados já gravados. Não repetir operações com resultado desconhecido.
