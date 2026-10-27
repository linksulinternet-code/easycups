# FMEA — complemento de regressões



## Revisão 27/10/2026

Risco: resultado parcial, indisponível ou não confirmado ser apresentado como sucesso; efeito: repetição indevida, perda de dados ou decisão incorreta. Controle nesta rodada: Falhas de descoberta/fila aparecem como erro, preservando a diferença entre indisponibilidade e lista vazia. Timeout não recomenda repetir uma operação sem consultar seu resultado. Atualizador trata término por sinal como falha.

Validação e risco residual: 36 testes existentes e 2 novos testes dos callbacks reais aprovados com widgets simulados; sem comandos de impressora nesses testes. Faltam ensaio GTK e impressora real.
