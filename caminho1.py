# import re
# from pathlib import Path
# from urllib.parse import urljoin

# import requests

# URL = "http://sigma.rio.rj.gov.br/lang1/LOGONIspecViewCust.asp"

# s = requests.Session()
# s.headers["User-Agent"] = (
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#     "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 Edg/120.0"
# )

# r = s.get(URL, timeout=30)
# print("status:", r.status_code, "| encoding:", r.encoding, "| final url:", r.url)
# print("cookies:", s.cookies.get_dict())

# # ASP clássico costuma ser latin-1; garante acentos certos
# r.encoding = r.apparent_encoding or "latin-1"
# html = r.text
# Path("sigma_requests.html").write_text(html, encoding="utf-8")

# print("\n=== FORMS ===")
# for f in re.findall(r"<form.*?</form>", html, re.S | re.I):
#     print(f)
#     print("-" * 60)

# print("\n=== FRAMES / SCRIPTS EXTERNOS ===")
# for tag in re.findall(r"<(?:i?frame|script)[^>]+src=[\"']([^\"']+)", html, re.I):
#     print(urljoin(URL, tag))

# print("\n=== CHECAGENS DE NAVEGADOR ===")
# padrao = r"alert\(|userAgent|Internet Explorer|documentMode|Trident|MSIE"
# for m in re.finditer(padrao, html, re.I):
#     ini = max(0, m.start() - 200)
#     print(html[ini:m.end() + 300].replace("\n", " "))
#     print("-" * 60)

# import re
# from pathlib import Path

# import requests

# BASE = "http://sigma.rio.rj.gov.br/"
# JS = ["script.js", "funcoes.js", "funcoesae.js", "menu.js", "menuAL.js", "lang1/ASPMenuItems.js"]

# s = requests.Session()
# s.headers["User-Agent"] = (
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
#     "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 Edg/120.0"
# )
# s.get(BASE + "lang1/LOGONIspecViewCust.asp", timeout=30)

# out = Path("sigma_js")
# out.mkdir(exist_ok=True)

# # trechos que interessam: a função stub, o submit do controller e qualquer checagem de navegador
# padrao = r"function\s+stub|controller\.|CDSELECAOASP|CDENTER|Edge|Trident|MSIE|userAgent|documentMode|navigator\.|\.submit\("

# for nome in JS:
#     r = s.get(BASE + nome, timeout=30)
#     texto = r.content.decode("latin-1").replace("\r", "")
#     (out / nome.replace("/", "_")).write_text(texto, encoding="utf-8")
#     print(f"\n##### {nome} (status {r.status_code}, {len(texto)} caracteres)")
#     for m in re.finditer(padrao, texto, re.I):
#         ini = max(0, m.start() - 150)
#         print(texto[ini:m.end() + 250].replace("\n", " "))
#         print("-" * 60)

# import re
# from pathlib import Path

# arquivos = [*Path("sigma_js").glob("*.js"), Path("sigma_requests.html")]

# for f in arquivos:
#     if not f.exists():
#         continue
#     t = f.read_text(encoding="utf-8", errors="replace").replace("\r", "")
#     for padrao in (r"function\s+grabData", r"grabData\s*=", r"formNotFullyLoaded\s*=\s*false"):
#         for m in re.finditer(padrao, t, re.I):
#             print(f"##### {f.name} | {padrao}")
#             print(t[max(0, m.start() - 100): m.start() + 1500])
#             print("-" * 60)


### FUNCIONAAAA


import time
from getpass import getpass
from pywinauto import Application

matric = input("Matrícula SIGMA (Enter se usar CPF): ").strip()
cpf = "" if matric else input("CPF SIGMA (só números): ").strip()
senha = getpass("Senha SIGMA: ")

# Conecta à janela do Microsoft Edge que está aberta com a IE Tab
app = Application(backend="uia").connect(title_re=".*Microsoft.*Edge.*", found_index=0)
janela = app.top_window()
janela.set_focus()

# Busca todos os campos de texto/senha dentro da IE Tab (Internet Explorer_Server)
campos = janela.descendants(control_type="Edit")
print(f"Campos encontrados na tela de login: {len(campos)}")
for c in campos:
    print(f"  - auto_id={c.element_info.automation_id!r} | name={c.element_info.name!r}")

# Preenche usando o id exato do HTML do SIGMA (DIVCDMATRIC / DIVNRCPF / DIVCDSENHA1)
if matric:
    campo_mat = janela.child_window(auto_id="DIVCDMATRIC", control_type="Edit")
    campo_mat.set_edit_text(matric)
else:
    campo_cpf = janela.child_window(auto_id="DIVNRCPF", control_type="Edit")
    campo_cpf.set_edit_text(cpf)

campo_senha = janela.child_window(auto_id="DIVCDSENHA1", control_type="Edit")
campo_senha.set_focus()
campo_senha.type_keys(senha, with_spaces=True)

# Pressiona Enter para submeter o formulário (equivale ao CDENTER = "@")
campo_senha.type_keys("{ENTER}")

print("\nAguardando carregamento da tela pós-login...")
time.sleep(3)

# Mapeia todos os inputs da tela seguinte dentro da IE Tab
campos_pos = janela.descendants(control_type="Edit")
botoes_pos = janela.descendants(control_type="Button")
combos_pos = janela.descendants(control_type="ComboBox")

print(f"\n=== PÓS-LOGIN ({len(campos_pos)} inputs, {len(combos_pos)} selects, {len(botoes_pos)} botões) ===")
for c in campos_pos:
    print(f"  [Edit] auto_id={c.element_info.automation_id!r} | name={c.element_info.name!r} | valor={c.get_value()!r}")

for cb in combos_pos:
    print(f"  [Combo] auto_id={cb.element_info.automation_id!r} | name={cb.element_info.name!r}")

#FUNCIONAAAA

# import re
# from getpass import getpass
# from pathlib import Path
# from urllib.parse import urlencode, urljoin

# import requests

# BASE = "http://sigma.rio.rj.gov.br/"
# PAGINA_LOGIN = BASE + "lang1/LOGONIspecViewCust.asp"
# XMIT = BASE + "xmit.asp"
# UA = "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko"


# def login(matricula="", cpf="", senha=""):
#     """Faz login e devolve (sessão, URL da tela inicial)."""
#     s = requests.Session()
#     s.headers["User-Agent"] = UA

#     # 1) abre a página de login (gera os cookies de sessão)
#     s.get(PAGINA_LOGIN, timeout=30)

#     # 2) POST igual ao do formulário "controller"
#     corpo = urlencode(
#         {
#             "CDSELECAOASP": "",
#             "CDMATRIC": matricula,
#             "NRCPF": cpf,
#             "CDSENHA1": senha,
#             "CDENTER": "@",
#         },
#         encoding="latin-1",  # o site usa ISO-8859-1
#     )
#     r = s.post(
#         XMIT,
#         data=corpo,
#         timeout=30,
#         allow_redirects=False,
#         headers={
#             "Content-Type": "application/x-www-form-urlencoded",
#             "Referer": PAGINA_LOGIN,
#         },
#     )

#     destino = r.headers.get("Location", "")
#     if r.status_code != 302 or "LOGON" in destino.upper():
#         html = r.content.decode("latin-1", errors="replace")
#         m = re.search(r'var\s+texto\s*=\s*"([^"]*)"', html)
#         msg = m.group(1).strip() if m else "sem mensagem do sistema"
#         raise RuntimeError(f"Login recusado: {msg}")

#     return s, urljoin(XMIT, destino)


# if __name__ == "__main__":
#     s, destino = login(
#         getpass("Matrícula SIGMA: "),
#         getpass("CPF SIGMA (só números): "),
#         getpass("Senha SIGMA: "),
#     )
#     print("Login aceito. Tela inicial:", destino)

#     r = s.get(destino, timeout=30)
#     html = r.content.decode("latin-1").replace("\r", "")
#     Path("sigma_home.html").write_text(html, encoding="utf-8")
#     print("status:", r.status_code, "| tamanho:", len(html))

#     m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
#     print("título:", m.group(1).strip() if m else "(sem título)")

#     print("\n=== FORMS (só nomes) ===")
#     for nome, corpo_form in re.findall(
#         r"<form\s+name\s*=\s*\"?(\w+)\"?[^>]*>(.*?)</form>", html, re.S | re.I
#     ):
#         print(nome, "->", re.findall(r"name\s*=\s*\"?(\w+)", corpo_form, re.I))

#     print("\n=== CHAMADAS DE TELA ===")
#     for chamada in sorted(set(re.findall(r"IrPara\w*\([^)]*\)", html))):
#         print(chamada)