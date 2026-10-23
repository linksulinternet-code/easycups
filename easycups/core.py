import os, re, subprocess, shutil
HOST = ["flatpak-spawn", "--host"] if os.path.exists("/.flatpak-info") else []
URI = re.compile(r"^(ipp|ipps|http|https|socket|lpd|usb|dnssd)://[^\s'\"]+$")      # FM7
# FM10: página de teste com fallback quando o arquivo não existe na distro
TEST = 'f=/usr/share/cups/data/testprint; if [ -f "$f" ]; then lp -d "$1" "$f"; else echo "Cups Facil - pagina de teste" | lp -d "$1"; fi'

def run(cmd, admin=False, timeout=300):
    cmd = ["env", "LC_ALL=C"] + cmd                      # FM1: saída sempre em inglês p/ o parser
    if admin: cmd = ["pkexec"] + cmd
    try:
        p = subprocess.run(HOST + cmd, capture_output=True, text=True, timeout=timeout)   # FM13
    except subprocess.TimeoutExpired: return False, "Tempo esgotado. Tente novamente."
    except FileNotFoundError as e: return False, "Programa não encontrado: %s" % e.filename
    except Exception as e: return False, str(e)
    out = (p.stdout + p.stderr).strip()
    if admin and p.returncode in (126, 127):             # FM4
        return False, "Autorização cancelada, negada ou programa ausente."
    return p.returncode == 0, out

PACKAGES = {
    "apt-get": ["apt-get", "install", "-y", "cups", "cups-client", "cups-filters"],
    "dnf": ["dnf", "install", "-y", "cups", "cups-client", "cups-filters"],
    "zypper": ["zypper", "--non-interactive", "install", "cups", "cups-client", "cups-filters"],
    "pacman": ["pacman", "-S", "--needed", "cups", "cups-filters"],
    "apk": ["apk", "add", "cups", "cups-client", "cups-filters"],
    "xbps-install": ["xbps-install", "-Sy", "cups", "cups-filters"]}

def valid_uri(uri):
    return bool(URI.fullmatch(uri)) and not any(ord(c) < 32 for c in uri)

def service_command(action):
    if action not in ("start", "stop", "restart", "enable"):
        raise ValueError("Ação de serviço inválida")
    if os.path.isdir("/run/systemd/system") and shutil.which("systemctl"):
        return ["systemctl", "enable", "--now", "cups"] if action == "enable" else ["systemctl", action, "cups"]
    if shutil.which("rc-service"):
        return ["rc-update", "add", "cups", "default"] if action == "enable" else ["rc-service", "cups", action]
    if shutil.which("sv") and os.path.exists("/var/service/cups"):
        if action == "enable": raise ValueError("Ative o serviço cups conforme a documentação da sua distro.")
        return ["sv", {"start":"up", "stop":"down", "restart":"restart"}[action], "cups"]
    if action == "enable": raise ValueError("Ative a inicialização automática conforme sua distro.")
    if shutil.which("service"): return ["service", "cups", action]
    raise ValueError("Nenhum gerenciador de serviços compatível foi encontrado.")

def uniq(base, taken):
    n, i = base, 2
    while n in taken:
        n = "%s_%d" % (base, i); i += 1
    return n
