# EasyCUPS 1.2.1

**Site e instaladores:** https://easycups.vercel.app

Gerenciador de impressoras CUPS em português. A versão 1.2 simplifica a instalação: pacote `.deb`, instalador único `.run`, assistente gráfico e botão **Procurar minha impressora** no aplicativo.

## Para o cliente

### Ubuntu 24.04+, Mint 22+ e Debian 13+

1. No site, escolha Ubuntu / Mint / Debian e baixe o `.deb`.
2. Abra o arquivo no instalador de aplicativos da distribuição e clique em Instalar. A senha e o download das dependências podem ser solicitados.
3. Abra EasyCUPS pelo menu e clique em **Procurar minha impressora**.

Algumas lojas não abrem pacotes locais. Nesse caso, o site oferece a alternativa `.run`, que prepara as dependências. Não use `dpkg -i` isoladamente: ele não resolve dependências automaticamente.

### Outras distribuições

Baixe `EasyCUPS-1.2.1.run` e, na pasta de download, execute `sh EasyCUPS-1.2.1.run`. O site também fornece uma linha pronta para copiar, baixar, verificar e iniciar.

O instalador detecta apt-get, dnf, zypper, pacman, apk ou xbps-install. Mostra o comando e pede confirmação antes de preparar dependências pelos repositórios da distro. Eleva somente o comando de pacotes por sudo, pkexec ou doas; nunca executa a interface como root. Em seguida abre o assistente **Instalar EasyCUPS → Abrir EasyCUPS**. Não adiciona repositórios de terceiros.

O `.run` contém o aplicativo: não exige baixar e extrair o código manualmente. Verifica SHA-256 do conteúdo antes de extrair. Internet é necessária para dependências ausentes. O shell e as ferramentas básicas `tar`, `base64`, `sha256sum`, `awk` e `mktemp` devem existir.

**Limites:** GTK >= 4.10, libadwaita >= 1.5, Python >= 3.9, PyGObject e CUPS. Não há compatibilidade garantida com qualquer distro ou impressora. Sistemas antigos podem não oferecer as bibliotecas; NixOS e sistemas ostree/imutáveis exigem procedimento específico. Comandos de pacotes preparados para seis famílias, ainda sem validação em todas elas.

## Usar

Ligue a impressora por USB ou conecte-a à mesma rede Wi-Fi. Abra EasyCUPS, clique em Procurar minha impressora e selecione o dispositivo. Para IPP Everywhere, escolha Automático. Modelos USB/legados podem exigir PPD ou Printer Application do fabricante. Se o CUPS estiver parado, abra Serviço e clique em Iniciar; o Linux poderá pedir senha.

A aplicação permite definir padrão, pausar/retomar, enviar página de teste, gerenciar trabalhos e consultar logs. Não apaga todas as impressoras para resolver falhas. Instalação do app preserva configurações existentes; os pacotes do sistema seguem os procedimentos normais do gerenciador da distro.

## Remover

- `.deb`: remova EasyCUPS pela loja/gerenciador de aplicativos.
- `.run`: `python3 ~/.local/share/easycups/uninstall.py --uninstall` (ajuste o caminho se usar XDG_DATA_HOME).
- Código: `python3 install.py --uninstall`.

A desinstalação do aplicativo não remove CUPS, impressoras ou dependências compartilhadas. Evite misturar `.deb` e instalação por usuário; remova a anterior antes de trocar o método.

## Desenvolvimento e verificação

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q easycups install.py packaging tests
python3 packaging/build.py
sh site/dist/downloads/EasyCUPS-1.2.1.run --check
python3 -m easycups --doctor
```

`--doctor` não exige GTK e não altera o sistema. O `.run --check` também não instala pacotes nem inicia serviços. Testes de instalação usam diretórios temporários, incluindo caminhos com espaços, atualização, desinstalação, falha de cópia e rollback. O pacote Debian é inspecionado e extraído para validar sua estrutura; não significa instalação real certificada em toda a matriz.

O instalador e a GUI são testados no ambiente de desenvolvimento. Impressão física e testes em VMs de cada distribuição ainda estão pendentes.

## Origem e licença

Evolução do Cups Fácil fornecido pelo usuário. O arquivo original não incluía licença; consulte NOTICE.md. A licença de redistribuição deve ser definida pelo titular. Projeto independente, sem afiliação oficial com CUPS/OpenPrinting ou distribuições.

Referências de requisitos e dependências: [PyGObject](https://pygobject.gnome.org/getting_started.html), [GTK em Ubuntu 24.04](https://packages.ubuntu.com/noble/gir1.2-gtk-4.0), [libadwaita em Ubuntu 24.04](https://packages.ubuntu.com/noble/gir1.2-adw-1), [CUPS lpadmin](https://openprinting.github.io/cups/doc/man-lpadmin.html).


## Atualizações automáticas — 26/10/2026

[Funcionamento, ativação, testes, riscos e recuperação](docs/ATUALIZACOES.md). Política em updates/policy.json e Dependabot diário para dependências aplicáveis. Implementação em validação; a configuração só atua após integração na branch padrão e os canais de aplicativos exigem ativação descrita no guia. Não faz merge automático nem aprova dados operacionais.


## Revisão de regressões — 27/10/2026

Falhas de descoberta/fila aparecem como erro, preservando a diferença entre indisponibilidade e lista vazia. Timeout não recomenda repetir uma operação sem consultar seu resultado. Atualizador trata término por sinal como falha.

36 testes existentes e 2 novos testes dos callbacks reais aprovados com widgets simulados; sem comandos de impressora nesses testes. Faltam ensaio GTK e impressora real.

Critérios de aceite, limites e recuperação: [docs/REGRESSOES.md](docs/REGRESSOES.md). Referência de padrão: proposta v0.1.1 em linksul-metodologia-software#4, ainda em revisão.
