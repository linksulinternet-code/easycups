# EasyCUPS 1.1.0

Site: https://easycups-linux.rareknoll1024.chatgpt.site

Uma interface em português para gerenciar impressoras no Linux. Evolução do projeto Cups Fácil fornecido pelo autor.

**Prévia experimental:** testes automatizados do núcleo não substituem testes em impressoras reais. Não é um driver universal.

## Recursos

- Descoberta USB/rede; cadastro IPP/IPPS com IPP Everywhere ou PPD para dispositivos legados.
- Impressora padrão, pausar/retomar, página de teste e cancelamento de trabalhos.
- Controle do serviço com detecção de systemd, OpenRC, runit e SysV.
- Instalação de CUPS por apt-get, dnf, zypper, pacman, apk ou xbps-install, com autorização polkit.
- Diagnóstico JSON sem GTK: `python3 -m easycups --doctor` (código 1 indica dependências/serviço ausentes).
- Sem restauração destrutiva, sem instalação automática de drivers proprietários e sem compartilhamento por padrão.

## Instalar

Extraia o arquivo de download, abra um terminal na pasta e execute, como usuário comum:

```sh
python3 -m easycups --doctor
python3 install.py
~/.local/bin/easycups
```

O instalador copia o aplicativo para `~/.local/share/easycups`, cria o comando em `~/.local/bin` e uma entrada no menu. Respeita XDG_DATA_HOME. Não instala dependências nem altera o serviço durante a instalação do aplicativo.

## Dependências e distribuições

Python >= 3.9, PyGObject, GTK >= 4.10, libadwaita >= 1.5, comandos CUPS e pkexec com agente polkit na sessão. X11 ou Wayland. GNOME não é obrigatório.

Exemplos de dependências (confira os nomes e versões no repositório da sua distro):

| Família | Comando |
|---|---|
| Debian/Ubuntu/Mint | `sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 cups cups-client cups-filters pkexec` |
| Fedora | `sudo dnf install python3 python3-gobject gtk4 libadwaita cups cups-client cups-filters polkit` |
| Arch | `sudo pacman -S --needed python python-gobject gtk4 libadwaita cups cups-filters polkit` |
| openSUSE | Instale Python, bindings GObject, GTK4, libadwaita, CUPS e polkit pelos repositórios locais. |
| Alpine/Void | Mesmos requisitos, com OpenRC/runit; nomes dos pacotes variam. |
| NixOS/imutáveis | Use configuração declarativa/camada própria da distribuição. A instalação interna de CUPS pode não se aplicar. |

Ubuntu 22.04 e Debian 12 têm bibliotecas antigas na base e não atendem à GUI sem atualização das dependências. Nenhuma matriz de distros foi validada em VMs nesta versão. O tar.gz contém código Python independente de arquitetura, mas depende das bibliotecas do sistema. Não há Flatpak, AppImage ou RPM certificado nesta entrega.

O modo automático requer uma impressora IPP Everywhere acessível por IPP/IPPS. Para USB/socket/LPD, escolha PPD compatível ou configure uma Printer Application. PPDs e drivers legados têm suporte variável conforme a versão do CUPS.

## Remover

```sh
python3 install.py --uninstall
```

As impressoras, documentos e configurações CUPS são preservados.

## Desenvolvimento

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q easycups install.py
```

Não execute testes de impressão em máquinas de terceiros sem consentimento. Cancelar a fila inteira requer confirmação e autorização administrativa. Logs podem conter nomes de usuários/documentos: revise antes de compartilhar.

## Licença e origem

O arquivo original fornecido não continha licença. A autoria original é preservada em `NOTICE.md`; uma licença de software livre deve ser definida pelo titular antes de redistribuições por terceiros. Download público não equivale a concessão de licença.

Documentação técnica: [CUPS lpadmin](https://openprinting.github.io/cups/doc/man-lpadmin.html) e [PyGObject](https://pygobject.gnome.org/getting_started.html).
