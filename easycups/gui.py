#!/usr/bin/env python3
import gi, os, re, sys, subprocess, threading
gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

# FM16: libadwaita antigo derruba o app na abertura -> falha com mensagem clara
if (Adw.get_major_version(), Adw.get_minor_version()) < (1, 5):
    sys.exit("EasyCUPS precisa de libadwaita >= 1.5 (Ubuntu 24.04+, Debian 13+, Fedora 40+).")

from .core import run, TEST, valid_uri, service_command, PACKAGES, uniq
C = Gtk.Align.CENTER
ALIVE = [True]

def bg(fn, cb):
    def w():
        r = fn()
        GLib.idle_add(lambda: (cb(r) if ALIVE[0] else None, False)[1])   # FM14
    threading.Thread(target=w, daemon=True).start()

def svc(action):
    try: return service_command(action)
    except ValueError as e: return ["python3", "-c", "import sys; sys.exit(sys.argv[1])", str(e)]

def check():  # FM5/FM4: (cups_rodando, aviso)
    nop = not run(["sh", "-c", "command -v pkexec"])[0]
    up = "scheduler is running" in run(["lpstat", "-r"])[1]
    return up, ("pkexec (polkit) não encontrado: ações de administrador não vão funcionar." if nop
                else "" if up else "O serviço CUPS não está rodando. Abra a aba Serviço.")

def uniq(base, taken):  # FM6
    n, i = base, 2
    while n in taken: n = "%s_%d" % (base, i); i += 1
    return n

class Win(Adw.ApplicationWindow):
    def __init__(s, **k):
        super().__init__(default_width=920, default_height=680, title="EasyCUPS", **k)
        s.init = False; s.busy = False; s.prow = []; s.qrow = []; s.drow = []; s.sw = {}
        s.connect("close-request", lambda *_: (ALIVE.__setitem__(0, False), False)[1])
        s.toasts = Adw.ToastOverlay(); s.stack = Adw.ViewStack()
        s.banner = Adw.Banner(button_label="Ir para Serviço")
        s.banner.connect("button-clicked", lambda _: s.stack.set_visible_child_name("srv"))
        for n, t, i, p in (("imp", "Impressoras", "printer-symbolic", s.p_printers()),
                           ("add", "Adicionar", "list-add-symbolic", s.p_add()),
                           ("fila", "Fila", "view-list-symbolic", s.p_queue()),
                           ("srv", "Serviço", "system-run-symbolic", s.p_service()),
                           ("adv", "Avançado", "preferences-system-symbolic", s.p_adv())):
            s.stack.add_titled_with_icon(p, n, t, i)
        hb = Adw.HeaderBar(title_widget=Adw.ViewSwitcher(stack=s.stack, policy=Adw.ViewSwitcherPolicy.WIDE))
        tv = Adw.ToolbarView(content=s.stack); tv.add_top_bar(hb); tv.add_top_bar(s.banner)
        s.toasts.set_child(tv); s.set_content(s.toasts); s.status()

    # ---------- helpers ----------
    def toast(s, t): s.toasts.add_toast(Adw.Toast(title=t))

    def fail(s, msg):
        msg = (msg or "Erro desconhecido")[-600:]
        if re.search(r"Connection refused|Bad file descriptor|cupsd|scheduler", msg):
            msg += "\n\nO CUPS parece parado. Vá em Serviço › Iniciar."
        d = Adw.AlertDialog(heading="Não deu certo", body=msg); d.add_response("ok", "Entendi"); d.present(s)

    def do(s, cmd, ok, after=None, admin=True, timeout=300):
        if s.busy: return s.toast("Aguarde a ação anterior terminar…")      # FM3
        s.busy = True; s.toast("Executando…")
        def cb(r):
            s.busy = False
            s.toast(ok) if r[0] else s.fail(r[1])
            if after: after()
        bg(lambda: run(cmd, admin, timeout), cb)

    def row(s, g, title, sub, label, fn, danger=False):
        r = Adw.ActionRow(title=title, subtitle=sub)
        b = Gtk.Button(label=label, valign=C)
        b.add_css_class("destructive-action" if danger else "suggested-action")
        b.connect("clicked", lambda _: fn()); r.add_suffix(b)
        (getattr(g, "add_row", None) or g.add)(r); return r

    def refresh_btn(s, g, fn):
        b = Gtk.Button(icon_name="view-refresh-symbolic", valign=C); b.add_css_class("flat")
        b.connect("clicked", lambda _: fn()); g.set_header_suffix(b)

    def confirm(s, title, body, label, fn):
        d = Adw.AlertDialog(heading=title, body=body)
        d.add_response("x", "Cancelar"); d.add_response("ok", label); d.set_close_response("x")
        d.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        d.connect("response", lambda _, k: fn() if k == "ok" else None); d.present(s)

    def ask(s, title, default, fn):
        e = Gtk.Entry(text=default, activates_default=True)
        d = Adw.AlertDialog(heading=title); d.set_extra_child(e)
        d.add_response("x", "Cancelar"); d.add_response("ok", "OK"); d.set_default_response("ok")
        d.connect("response", lambda _, k: fn(e.get_text().strip()) if k == "ok" and e.get_text().strip() else None)
        d.present(s)

    def ppd(s, cb):  # FM8: valida extensão e estrutura antes de aplicar
        def picked(p):
            if not p.lower().endswith((".ppd", ".ppd.gz")): return s.toast("Escolha um arquivo .ppd")
            def chk():
                return run(["cupstestppd", "-q", p]) if run(["sh", "-c", "command -v cupstestppd"])[0] else (True, "")
            bg(chk, lambda r: cb(p) if r[0] else s.fail("PPD inválido:\n" + r[1]))
        fd = Gtk.FileDialog(title="Escolha o arquivo .ppd")
        def done(d, res):
            try: picked(d.open_finish(res).get_path())
            except GLib.Error: pass
        fd.open(s, None, done)

    # ---------- impressoras ----------
    def p_printers(s):
        pg = Adw.PreferencesPage()
        welcome = Adw.PreferencesGroup(title="Comece por aqui", description="Conecte por USB ou use a mesma rede Wi-Fi da impressora.")
        s.row(welcome, "Instalar minha impressora", "Vamos procurar dispositivos conectados ao computador e à rede.", "Procurar minha impressora", lambda: (s.stack.set_visible_child_name("add"), s.scan()))
        pg.add(welcome)
        s.pgrp = Adw.PreferencesGroup(title="Suas impressoras", description="Clique numa impressora para ver as opções")
        s.refresh_btn(s.pgrp, s.refresh); pg.add(s.pgrp); s.refresh(); return pg

    def refresh(s):
        bg(lambda: (run(["lpstat", "-p"])[1], run(["lpstat", "-d"])[1]), s.fill)

    def fill(s, r):
        o, d = r
        dflt = d.split(":", 1)[1].strip() if d.startswith("system default destination:") else ""   # FM9
        for x in s.prow: s.pgrp.remove(x)
        s.prow = []; R = s.refresh
        for ln in o.splitlines():
            p = ln.split()
            if len(p) < 2 or p[0] != "printer": continue
            n = p[1]; off = p[2:3] == ["disabled"]
            e = Adw.ExpanderRow(title=n, subtitle=("Pausada" if off else "Pronta") + (" · Padrão" if n == dflt else ""))
            e.add_prefix(Gtk.Image.new_from_icon_name("printer-symbolic"))
            s.row(e, "Definir como padrão", "", "Definir", lambda n=n: s.do(["lpadmin", "-d", n], "Padrão definido", R))
            s.row(e, "Página de teste", "Confirma se está tudo funcionando", "Imprimir",
                  lambda n=n: s.do(["sh", "-c", TEST, "sh", n], "Enviada para a fila", admin=False))
            s.row(e, "Pausar / Retomar", "", "Retomar" if off else "Pausar",
                  lambda n=n, off=off: s.do(["cupsenable" if off else "cupsdisable", n], "Pronto", R))
            s.row(e, "Trocar driver (PPD)", "Use um arquivo .ppd específico", "Escolher…",
                  lambda n=n: s.ppd(lambda p: s.do(["lpadmin", "-p", n, "-P", p], "Driver trocado", R)))
            s.row(e, "Remover", "", "Remover", lambda n=n: s.confirm(f"Remover {n}?", "Isso não apaga seus documentos.",
                  "Remover", lambda: s.do(["lpadmin", "-x", n], "Removida", R)), True)
            s.pgrp.add(e); s.prow.append(e)
        if not s.prow:
            none = "No destinations" in o or not o
            r0 = Adw.ActionRow(title="Nenhuma impressora ainda" if none else "Não consegui ler as impressoras",
                               subtitle="Ligue sua impressora e clique em Procurar minha impressora acima." if none else "Abra Serviço para verificar a impressão.")
            s.pgrp.add(r0); s.prow.append(r0)

    # ---------- adicionar ----------
    def p_add(s):
        pg = Adw.PreferencesPage()
        s.dg = Adw.PreferencesGroup(title="Adicionar impressora", description="Ligue a impressora. Se ela usa Wi-Fi, conecte este computador à mesma rede.")
        s.row(s.dg, "Procurar impressoras", "USB e rede (pode levar alguns segundos)", "Procurar", s.scan)
        s.row(s.dg, "Adicionar por endereço", "Ex.: ipp://192.168.0.10/ipp/print ou socket://IP:9100", "Digitar…",
              lambda: s.ask("Endereço da impressora", "ipp://", s.add))
        pg.add(s.dg); return pg

    def scan(s):
        s.toast("Procurando…"); bg(lambda: run(["lpinfo", "-v"], timeout=60), s.found)

    def found(s, result):
        ok, o = result
        if not ok:
            s.fail("Não foi possível procurar impressoras.\n" + o)
            return
        for x in s.drow: s.dg.remove(x)
        s.drow = []; seen = set()
        for ln in o.splitlines():
            m = re.match(r"(\w+) (\S+://\S+)", ln)
            if m and m[2] not in seen:                                           # dedupe
                seen.add(m[2]); s.drow.append(s.row(s.dg, m[2], "Conexão: " + m[1], "Adicionar", lambda u=m[2]: s.add(u)))
        if not s.drow: s.toast("Nenhuma impressora encontrada. Tente por endereço.")

    def add(s, uri):
        if not valid_uri(uri): return s.toast("Endereço inválido. Ex.: ipp://192.168.0.10/ipp/print")   # FM7
        bg(lambda: {l.split()[0] for l in run(["lpstat", "-a"])[1].splitlines() if l.split()},
           lambda taken: s.add2(uri, taken))

    def add2(s, uri, taken):
        name = uniq(re.sub(r"[^A-Za-z0-9_]", "_", uri.split("://", 1)[-1].split("?")[0])[:30].strip("_") or "Impressora", taken)
        d = Adw.AlertDialog(heading="Como instalar o driver?",
                            body="Para impressoras modernas com IPP, escolha Automático. Modelos antigos ou USB podem precisar de um driver do fabricante (arquivo PPD).")
        for k, t in (("x", "Cancelar"), ("auto", "Automático"), ("ppd", "Escolher PPD…")): d.add_response(k, t)
        if not uri.startswith(("ipp://", "ipps://")):
            d.set_response_enabled("auto", False)
        d.set_response_appearance("auto", Adw.ResponseAppearance.SUGGESTED); d.set_close_response("x")
        base = ["lpadmin", "-p", name, "-E", "-v", uri, "-o", "printer-is-shared=false"]   # FM15: não compartilha por padrão
        def r(_, k):
            if k == "auto" and not uri.startswith(("ipp://", "ipps://")):
                return s.fail("O modo automático requer IPP/IPPS. Para USB, socket ou LPD, escolha um PPD do fabricante ou configure uma Printer Application.")
            if k == "auto": s.do(base + ["-m", "everywhere"], "Impressora adicionada: " + name, s.refresh)
            elif k == "ppd": s.ppd(lambda p: s.do(base + ["-P", p], "Impressora adicionada: " + name, s.refresh))
        d.connect("response", r); d.present(s)

    # ---------- fila ----------
    def p_queue(s):
        pg = Adw.PreferencesPage(); s.qg = Adw.PreferencesGroup(title="Trabalhos na fila")
        s.refresh_btn(s.qg, s.queue); pg.add(s.qg); g = Adw.PreferencesGroup()
        s.row(g, "Cancelar todos os trabalhos", "Útil quando a fila trava", "Cancelar tudo",
              lambda: s.confirm("Cancelar todos os trabalhos?", "Os trabalhos pendentes de todas as impressoras serão cancelados.", "Cancelar trabalhos", lambda: s.do(["cancel", "-a"], "Fila limpa", s.queue)), True)
        pg.add(g); s.queue(); return pg

    def queue(s): bg(lambda: run(["lpstat", "-o"]), s.qfill)

    def qfill(s, result):
        ok, o = result
        for x in s.qrow: s.qg.remove(x)
        s.qrow = []
        if not ok:
            row = Adw.ActionRow(title="Não foi possível consultar a fila", subtitle=o[-300:])
            s.qg.add(row); s.qrow.append(row)
            return
        for ln in o.splitlines():
            p = ln.split()
            if not p or not re.match(r".+-\d+$", p[0]): continue
            s.qrow.append(s.row(s.qg, p[0], " ".join(p[1:4]), "Cancelar",
                                lambda j=p[0]: s.do(["cancel", j], "Cancelado", s.queue, admin=False), True))
        if not s.qrow:
            r0 = Adw.ActionRow(title="Fila vazia"); s.qg.add(r0); s.qrow.append(r0)

    # ---------- serviço ----------
    def p_service(s):
        pg = Adw.PreferencesPage(); g = Adw.PreferencesGroup(title="Serviço de impressão (CUPS)")
        s.st = Adw.ActionRow(title="Estado", subtitle="verificando…"); g.add(s.st)
        S = lambda a, m: (lambda: s.do(svc(a), m, s.status))
        s.row(g, "Instalar CUPS", "Instala e ativa tudo o que é necessário", "Instalar", s.install)
        s.row(g, "Reiniciar", "Reinicia o serviço sem remover suas impressoras", "Reiniciar", S("restart", "Reiniciado"))
        s.row(g, "Iniciar", "", "Iniciar", S("start", "Iniciado"))
        s.row(g, "Parar", "", "Parar", S("stop", "Parado"))
        s.row(g, "Iniciar com o computador", "", "Ativar",
              lambda: s.do(svc("enable"), "Ativado", s.status))
        pg.add(g); return pg

    def status(s):
        def cb(r):
            s.st.set_subtitle("● Rodando" if r[0] else "○ Parado ou não instalado")
            s.banner.set_title(r[1]); s.banner.set_revealed(bool(r[1]))
        bg(check, cb)

    def install(s):
        for manager, command in PACKAGES.items():
            if run(["sh", "-c", "command -v " + manager])[0]:
                return s.confirm("Instalar CUPS?", "O gerenciador de pacotes da distro instalará CUPS e filtros. Depois, use Iniciar para ativar o serviço.", "Instalar", lambda: s.do(command, "Pacotes CUPS instalados; use Iniciar", lambda: (s.status(), s.refresh()), timeout=900))
        s.fail("Gerenciador não reconhecido. Instale CUPS usando as ferramentas da sua distribuição; sistemas imutáveis exigem o procedimento próprio da distro.")

    # ---------- avançado ----------
    def p_adv(s):
        pg = Adw.PreferencesPage(); g = Adw.PreferencesGroup(title="Avançado")
        for f, t, sub in (("share-printers", "Compartilhar impressoras na rede", "Outros computadores podem usar"),
                          ("remote-admin", "Administração remota", "Painel web acessível pela rede"),
                          ("debug-logging", "Log detalhado", "Para diagnosticar problemas")):
            w = Adw.SwitchRow(title=t, subtitle=sub); s.sw["_" + f.replace("-", "_")] = w
            w.connect("notify::active", lambda w, _, f=f: s.flag(w, f)); g.add(w)
        s.row(g, "Painel web do CUPS", "http://localhost:631", "Abrir",
              lambda: Gtk.UriLauncher(uri="http://localhost:631").launch(s, None, None))
        s.row(g, "Log de erros", "Últimas linhas", "Ver", s.log)
        pg.add(g); bg(lambda: run(["cupsctl"])[1], s.sync); return pg

    def flag(s, w, f):  # FM15: confirma o perigoso e reverte o botão se falhar/cancelar
        if s.init: return
        on = w.get_active()
        def revert(): s.init = True; w.set_active(not on); s.init = False
        def apply():
            if s.busy: return revert()
            s.busy = True
            def cb(r):
                s.busy = False
                if r[0]: s.toast("Salvo")
                else: revert(); s.fail(r[1])
            bg(lambda: run(["cupsctl", ("--" if on else "--no-") + f], True), cb)
        if on and f == "remote-admin":
            d = Adw.AlertDialog(heading="Ativar administração remota?",
                                body="Qualquer pessoa na sua rede poderá tentar acessar a administração. Use só em redes confiáveis.")
            d.add_response("x", "Cancelar"); d.add_response("ok", "Ativar"); d.set_close_response("x")
            d.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
            d.connect("response", lambda _, k: apply() if k == "ok" else revert()); d.present(s)
        else: apply()

    def sync(s, o):
        s.init = True
        for ln in o.splitlines():
            k, _, v = ln.partition("=")
            if k in s.sw: s.sw[k].set_active(v == "1")
        s.init = False

    def log(s):  # FM17: cai para o journal quando não há error_log
        def show(r):
            tv = Gtk.TextView(editable=False, monospace=True); tv.get_buffer().set_text(r[1][-6000:] or "Sem registros")
            d = Adw.AlertDialog(heading="Log do CUPS")
            d.set_extra_child(Gtk.ScrolledWindow(min_content_height=320, min_content_width=520, child=tv))
            d.add_response("ok", "Fechar"); d.present(s)
        bg(lambda: run(["sh", "-c", "tail -n 60 /var/log/cups/error_log 2>/dev/null || journalctl -u cups -n 60 --no-pager"], True), show)

class A(Adw.Application):
    def __init__(s):
        super().__init__(application_id="io.github.easycups.EasyCUPS")
        s.connect("activate", lambda a: Win(application=a).present())

if __name__ == "__main__":
    A().run()
