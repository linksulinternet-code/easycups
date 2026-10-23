'use strict';
const selector = document.getElementById('linux');
const link = document.getElementById('download-link');
const copyButton = document.getElementById('copy-install');
const copyStatus = document.getElementById('copy-status');
let installCommand = '';
const steps = document.getElementById('method-steps');
const methods = {
  deb: {
    tag: 'INSTALAÇÃO PELO GERENCIADOR DE APLICATIVOS', title: 'Baixar, abrir e instalar.',
    description: 'O pacote .deb informa as dependências ao seu sistema. O instalador de aplicativos pode baixar o que falta e pedir sua senha.',
    requirements: 'Para Ubuntu 24.04+, Mint 22+ e Debian 13+, com ambiente gráfico.',
    file: 'easycups_1.2.0_all.deb', button: '↓ Baixar instalador .deb',
    steps: ['Abra o arquivo baixado no instalador de aplicativos.', 'Clique em Instalar e informe sua senha, se solicitada.', 'Abra EasyCUPS no menu de aplicativos.']
  },
  run: {
    tag: 'INSTALADOR ÚNICO COM ASSISTENTE', title: 'O assistente cuida da preparação.',
    description: 'Detecta sua distribuição e prepara as dependências com sua autorização. Depois, clique em Instalar EasyCUPS e Abrir EasyCUPS.',
    requirements: 'Para distros com bibliotecas atuais. Internet e senha de administrador podem ser necessárias.',
    file: 'EasyCUPS-1.2.0.run', button: '↓ Baixar instalador único .run',
    steps: ['Copie o comando abaixo, cole no Terminal e pressione Enter.', 'Confira a preparação e autorize os pacotes, se necessário.', 'No assistente, clique em Instalar EasyCUPS e depois em Abrir EasyCUPS.']
  }
};
function render() {
  const immutable = selector.value === 'immutable';
  const isDeb = selector.value === 'deb';
  document.getElementById('method').hidden = immutable;
  document.getElementById('immutable-help').hidden = !immutable;
  document.getElementById('run-instructions').hidden = isDeb || immutable;
  document.getElementById('fallback-deb').hidden = !isDeb;
  copyStatus.textContent = '';
  if (installCommand) copyButton.textContent = 'Copiar comando de instalação';
  if (immutable) return;
  const method = methods[isDeb ? 'deb' : 'run'];
  for (const key of ['tag', 'title', 'description', 'requirements']) {
    document.getElementById(`method-${key}`).textContent = method[key];
  }
  link.href = `downloads/${method.file}`;
  link.textContent = method.button;
  steps.replaceChildren(...method.steps.map(text => {
    const item = document.createElement('li'); item.textContent = text; return item;
  }));
}
selector.addEventListener('change', render);
document.getElementById('use-run').addEventListener('click', () => {
  selector.value = 'run'; render(); copyButton.focus();
});
copyButton.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(installCommand);
    copyStatus.textContent = 'Copiado! Abra o Terminal, cole o comando e pressione Enter.';
    copyButton.textContent = '✓ Comando copiado';
  } catch {
    copyStatus.textContent = 'Seu navegador não permitiu copiar. Abra “Ver o comando” e copie o texto manualmente.';
    document.getElementById('install-command').parentElement.open = true;
  }
});
fetch('release.json', {cache: 'no-cache'})
  .then(response => { if (!response.ok) throw new Error('release'); return response.json(); })
  .then(release => {
    const run = release.artifacts['.run'];
    if (!/^[a-f0-9]{64}$/.test(run.sha256) || run.file !== 'downloads/EasyCUPS-1.2.0.run') throw new Error('artifact');
    // URL pinada: o comando copiado só baixa o instalador do domínio público do projeto.
    const downloadURL = `https://easycups.vercel.app/${run.file}`;
    installCommand = `( set -eu; pasta=$(mktemp -d); trap 'rm -rf -- "$pasta"' EXIT; curl -fL '${downloadURL}' -o "$pasta/EasyCUPS.run"; printf '%s  %s\\n' '${run.sha256}' "$pasta/EasyCUPS.run" | sha256sum -c -; sh "$pasta/EasyCUPS.run" )`;
    document.getElementById('install-command').textContent = installCommand;
    copyButton.disabled = false; copyButton.textContent = 'Copiar comando de instalação';
  })
  .catch(() => {
    copyButton.textContent = 'Comando indisponível';
    document.getElementById('install-command').textContent = 'Baixe o .run e execute sh EasyCUPS-1.2.0.run na pasta do arquivo.';
    copyStatus.textContent = 'Não foi possível carregar a verificação. O download direto continua disponível.';
  });
render();
