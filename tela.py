from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import re
import time
import traceback
import customtkinter as ctk
import threading
import os
import pdfplumber
from pywinauto import Application

from pdf_requisicoes import extrair_requisicoes

CONTROLES_IGNORADOS_SIGMA = {"view_1017", "address-box"}
CAMPOS_POSICAO_SIGMA = {
    "u.consumidora": 7,
    "num.docto": 8,
    "dt.docto.dia": 9,
    "dt.docto.mes": 10,
    "dt.docto.ano": 11,
    "matricula": 12,
    "codigo_material": 14,
    "qtd.pedida": 18,
    "qtd.atendida": 19,
}
CAMPOS_SIGMA = ("data_req", "req", "cre", "sici", "desig", "qtd")
MAPEAMENTO_PDF_SIGMA = {
    "u.consumidora": "sici",
    "num.docto": "req",
}


def conectar_sigma():
    """Conecta à janela do Edge que está com o Sigma abertooo."""
    app = Application(backend="uia").connect(
        title_re=".*Microsoft.*Edge.*",
        found_index=0,
    )
    janela = app.top_window()
    janela.set_focus()
    return janela


def clicar_inclusao_sigma(janela):
    """Aciona o botao Inclusao da tela atual do Sigma."""
    botoes = [
        botao for botao in janela.descendants(control_type="Button")
        if botao.is_visible() and botao.is_enabled()
    ]

    for indice, botao in enumerate(botoes, start=1):
        nome = (botao.element_info.name or "").strip()
        if nome.casefold().startswith("inclus"):
            try:
                botao.invoke()
            except Exception:
                botao.click_input()
            print(f"Botao Inclusao acionado: [{indice}] {nome!r}")
            return

    nomes = [botao.element_info.name or "<sem texto>" for botao in botoes]
    raise RuntimeError(
        "Botao Inclusao nao encontrado entre os botoes visiveis e habilitados. "
        f"Botoes encontrados: {nomes!r}"
    )


def mapear_botoes_sigma(janela):
    """Confirma a inclusao e lista botoes e checkboxes da tela seguinte."""
    time.sleep(1)
    botoes = [
        botao for botao in janela.descendants(control_type="Button")
        if botao.is_visible()
    ]

    print(f"\n=== BOTOES ANTES DA CONFIRMACAO ({len(botoes)}) ===")
    for indice, botao in enumerate(botoes, start=1):
        print(
            f"[{indice}] texto={botao.element_info.name or ''!r} "
            f"| auto_id={botao.element_info.automation_id or ''!r} "
            f"| habilitado={botao.is_enabled()}"
        )

    confirmacao = next(
        (
            botao for botao in botoes
            if (botao.element_info.name or "").strip().casefold() == "sim"
        ),
        None,
    )
    if confirmacao is None:
        raise RuntimeError(
            "Botao de confirmacao 'sim' nao encontrado. "
            f"Botoes encontrados: "
            f"{[botao.element_info.name or '<sem texto>' for botao in botoes]!r}"
        )
    if not confirmacao.is_enabled():
        raise RuntimeError("O botao de confirmacao 'sim' esta desabilitado.")

    try:
        confirmacao.invoke()
    except Exception:
        confirmacao.click_input()
    print("Confirmacao acionada: 'sim'")

    time.sleep(1)
    botoes_seguinte = [
        botao for botao in janela.descendants(control_type="Button")
        if botao.is_visible()
    ]
    checkboxes_seguinte = [
        checkbox for checkbox in janela.descendants(control_type="CheckBox")
        if checkbox.is_visible()
    ]

    print(f"\n=== BOTOES DA TELA SEGUINTE ({len(botoes_seguinte)}) ===")
    for indice, botao in enumerate(botoes_seguinte, start=1):
        print(
            f"[{indice}] texto={botao.element_info.name or ''!r} "
            f"| auto_id={botao.element_info.automation_id or ''!r} "
            f"| habilitado={botao.is_enabled()}"
        )

    print(f"\n=== CHECKBOXES DA TELA SEGUINTE ({len(checkboxes_seguinte)}) ===")
    for indice, checkbox in enumerate(checkboxes_seguinte, start=1):
        print(
            f"[{indice}] texto={checkbox.element_info.name or ''!r} "
            f"| auto_id={checkbox.element_info.automation_id or ''!r} "
            f"| habilitado={checkbox.is_enabled()}"
        )

    checkboxes_habilitados = [
        checkbox for checkbox in checkboxes_seguinte
        if checkbox.is_enabled()
    ]
    if not checkboxes_habilitados:
        raise RuntimeError("Nenhum checkbox habilitado foi encontrado na tela seguinte.")

    checkbox_sim = checkboxes_habilitados[-1]

    try:
        selecionado = checkbox_sim.get_toggle_state() == 1
    except Exception as erro:
        raise RuntimeError(
            "Nao foi possivel verificar o estado do checkbox de fechamento."
        ) from erro

    if not selecionado:
        checkbox_sim.click_input()
        time.sleep(0.5)
        try:
            selecionado = checkbox_sim.get_toggle_state() == 1
        except Exception as erro:
            raise RuntimeError(
                "O checkbox foi clicado, mas nao foi possivel confirmar o estado."
            ) from erro

    if not selecionado:
        raise RuntimeError(
            "O checkbox de fechamento continua desmarcado; o Enter nao sera acionado."
        )

    print(
        "Checkbox selecionado: [1] "
        f"{checkbox_sim.element_info.name or '<sem texto>'!r}"
    )

    time.sleep(1)
    botoes_atuais = [
        botao for botao in janela.descendants(control_type="Button")
        if botao.is_visible() and botao.is_enabled()
    ]
    botao_enter = next(
        (
            botao for botao in botoes_atuais
            if (botao.element_info.name or "").strip().casefold() == "enter"
        ),
        None,
    )
    if botao_enter is None:
        raise RuntimeError("Botao 'Enter' nao encontrado ou esta desabilitado.")

    try:
        botao_enter.invoke()
    except Exception:
        botao_enter.click_input()
    print("Botao 'Enter' acionado.")


def obter_campos_editaveis_sigma(janela):
    """Retorna os campos Edit visíveis e habilitados da tela do Sigma."""
    campos = []
    for campo in janela.descendants(control_type="Edit"):
        auto_id = campo.element_info.automation_id or ""
        nome = campo.element_info.name or ""

        if auto_id in CONTROLES_IGNORADOS_SIGMA or nome == "Barra de pesquisa e enderecos":
            continue
        if campo.is_visible() and campo.is_enabled():
            campos.append(campo)
    return campos


def aguardar_campos_editaveis_sigma(janela, timeout=15):
    """Aguarda a tela de lancamento disponibilizar todos os campos necessarios."""
    quantidade_necessaria = max(CAMPOS_POSICAO_SIGMA.values())
    limite = time.monotonic() + timeout
    campos = []

    while time.monotonic() < limite:
        campos = obter_campos_editaveis_sigma(janela)
        if len(campos) >= quantidade_necessaria:
            return campos
        time.sleep(0.25)

    controles_edit = [
        controle for controle in janela.descendants(control_type="Edit")
        if (controle.element_info.automation_id or "") not in CONTROLES_IGNORADOS_SIGMA
        and (controle.element_info.name or "") != "Barra de pesquisa e enderecos"
    ]
    detalhes_edits = [
        {
            "nome": controle.element_info.name or "",
            "auto_id": controle.element_info.automation_id or "",
            "visivel": controle.is_visible(),
            "habilitado": controle.is_enabled(),
        }
        for controle in controles_edit
    ]
    botoes_visiveis = [
        {
            "nome": botao.element_info.name or "",
            "auto_id": botao.element_info.automation_id or "",
            "habilitado": botao.is_enabled(),
        }
        for botao in janela.descendants(control_type="Button")
        if botao.is_visible()
    ]
    print(f"Campos Edit encontrados na tela inesperada: {detalhes_edits!r}")
    print(f"Botoes encontrados na tela inesperada: {botoes_visiveis!r}")

    raise RuntimeError(
        f"A tela nao ficou pronta: encontrados {len(campos)} campos editaveis "
        f"habilitados; eram necessarios {quantidade_necessaria}. "
        f"Consulte no terminal os nomes e IDs dos campos e botoes atuais."
    )


def inserir_lancamento_sigma(requisicao, campos, matricula="", codigo_material=""):
    """Preenche os campos mapeados de um lancamento do PDF."""
    data = str(requisicao.get("data_req", "")).strip()
    partes_data = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", data)
    if not partes_data:
        raise ValueError(f"Data de requisicao invalida: {data!r}")

    partes_codigo = re.fullmatch(r"(\d{4})(\d{2})(\d{3})(\d{2})", str(codigo_material).strip())
    if not partes_codigo:
        raise ValueError(
            f"Codigo do material invalido: {codigo_material!r}. "
            "Informe exatamente 11 digitos."
        )

    maior_posicao = max(CAMPOS_POSICAO_SIGMA.values())
    if len(campos) < maior_posicao:
        raise RuntimeError(
            f"A tela tem {len(campos)} inputs editaveis, "
            f"mas o campo necessario esta na posicao {maior_posicao}."
        )

    for nome_campo, valor in zip(
        ("dt.docto.dia", "dt.docto.mes", "dt.docto.ano"), partes_data.groups()
    ):
        campos[CAMPOS_POSICAO_SIGMA[nome_campo] - 1].set_edit_text(valor)

    for nome_sigma, nome_pdf in MAPEAMENTO_PDF_SIGMA.items():
        posicao = CAMPOS_POSICAO_SIGMA[nome_sigma]
        campos[posicao - 1].set_edit_text(str(requisicao.get(nome_pdf, "")))

    campos[CAMPOS_POSICAO_SIGMA["matricula"] - 1].set_edit_text(str(matricula))

    for posicao, valor in zip(range(14, 18), partes_codigo.groups()):
        campos[posicao - 1].set_edit_text(valor)

    for nome_campo in ("qtd.pedida", "qtd.atendida"):
        posicao = CAMPOS_POSICAO_SIGMA[nome_campo]
        campos[posicao - 1].set_edit_text(str(requisicao.get("qtd", "")))


def selecionar_checkbox_sigma(janela, posicoes=(8,)):
    """Seleciona o oitavo checkbox da tela do Sigma."""
    checkboxes = janela.descendants(control_type="CheckBox")

    for posicao in posicoes:
        if posicao > len(checkboxes):
            raise RuntimeError(
                f"A tela tem {len(checkboxes)} checkboxes, "
                f"mas o checkbox necessario esta na posicao {posicao}."
            )

        checkbox = checkboxes[posicao - 1]
        if not checkbox.is_visible() or not checkbox.is_enabled():
            raise RuntimeError(f"O checkbox na posicao {posicao} nao esta disponivel.")

        try:
            selecionado = checkbox.get_toggle_state() == 1
        except Exception:
            selecionado = False

        if not selecionado:
            checkbox.toggle()


def inserir_dados_sigma(requisicoes, janela, ao_inserir=None):
    """Preenche os campos mapeados para cada linha do PDF.

    A matricula nao e sobrescrita porque nao existe valor correspondente no PDF.
    """
    campos = obter_campos_editaveis_sigma(janela)

    for indice, requisicao in enumerate(requisicoes, start=1):
        inserir_lancamento_sigma(requisicao, campos)
        if ao_inserir:
            ao_inserir(indice, len(requisicoes))

    return len(requisicoes)


def inserir_pdf_no_sigma(caminho_pdf):
    """Lê o PDF e preenche os inputs da janela Sigma aberta."""
    caminho = Path(caminho_pdf)
    if not caminho.is_file():
        raise FileNotFoundError(f"PDF não encontrado: {caminho}")

    requisicoes = extrair_requisicoes(caminho)
    janela = conectar_sigma()
    return inserir_dados_sigma(requisicoes, janela)

class AppLancamento(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Automação para Lançamentos SIGMA")
        self.geometry("960x750")
        self.configure(fg_color="#F4F6F9")
        self.resizable(False, False)

        self.caminho_pdf = ""
        self.lancamentos = []
        self.em_execucao = False
        self.parar_execucao = False

        self._construir_interface()

    def selecionar_arquivo(self):
        caminho = filedialog.askopenfilename(filetypes=[("Arquivos PDF", "*.pdf")])
        if caminho:
            self.caminho_pdf = caminho
            self.input_resultado.delete(0, "end")
            self.input_resultado.insert(0, Path(caminho).name)

    def verificar_arquivo(self):
        caminho = self.caminho_pdf or self.input_resultado.get()

        if not caminho or not os.path.exists(caminho):
            if os.path.exists(Path(caminho).name):
                caminho = str(Path(caminho).name)
            else:
                messagebox.showerror("Erro", "Arquivo PDF não encontrado")
                return

        self.caminho_pdf = caminho
        nome_arq = Path(caminho).name
        self.lbl_info_arq.configure(text=f"Arquivo:  {nome_arq}")

        self.lancamentos = []
        total_qtd = 0

        try:
            with pdfplumber.open(caminho) as pdf:
                for pagina in pdf.pages:
                    for tabela in pagina.extract_tables():
                        if not tabela:
                            continue

                        cabecalho = [self._normalizar_celula(celula).upper() for celula in tabela[0]]
                        esperado = ["DATA REQ", "REQ", "CRE", "SICI", "DESIG", "UNIDADE ESCOLAR", "QTD"]
                        if cabecalho[:len(esperado)] != esperado:
                            continue

                        for linha in tabela[1:]:
                            if len(linha) < len(esperado):
                                continue

                            valores = [self._normalizar_celula(celula) for celula in linha[:len(esperado)]]
                            if not valores[0] or not re.fullmatch(r"\d{2}/\d{2}/\d{4}", valores[0]):
                                continue

                            try:
                                qtd = int(valores[6])
                            except ValueError:
                                continue

                            registro = {
                                "data_req": valores[0],
                                "req": valores[1],
                                "cre": valores[2],
                                "sici": valores[3],
                                "desig": valores[4],
                                "unidade_escolar": valores[5],
                                "qtd": qtd,
                            }
                            self.lancamentos.append(registro)
                            total_qtd += qtd

            if not self.lancamentos:
                raise ValueError("Os dados da tabela não foram encontrados no PDF.")

            qtd = len(self.lancamentos)
            self.lbl_info_qtd.configure(text=f"Quantidade de linhas:  {qtd} requisições")
            self.lbl_info_total.configure(text=f"Quantidade total solicitada:  {total_qtd}")

            self.btn_badge.configure(
                text="Verificado com sucesso",
                fg_color='#D4EDDA',
                text_color="#155724"
            )

            for item in self.tree.get_children():
                self.tree.delete(item)

            for idx, item in enumerate(self.lancamentos, start=1):
                idx_str = f"{idx:02d}"
                self.tree.insert("", "end", iid=str(idx), values=(
                    idx_str, item["data_req"], item["req"], item["cre"], item["sici"],
                    item["desig"], item["unidade_escolar"], item["qtd"], "Aguardando"
                ))

            self.lbl_progresso.configure(text=f"Progresso: 0 / {qtd}")
            self.progress_bar.set(0)
        
        except Exception as e:
            self.btn_badge.configure(text="Erro no arquivo", fg_color="#F8D7DA", text_color="#721C24")
            messagebox.showerror("Erro de Leitura", f"Falha ao ler PDF: {str(e)}")

    @staticmethod
    def _normalizar_celula(valor):
        return re.sub(r"\s+", " ", str(valor or "")).strip()

    @staticmethod
    def formatar_para_iso(data_str):
        data_limpa = data_str.replace('.', '/').replace('-', '/').strip()
        partes = data_limpa.split('/')
        if len(partes) == 3:
            if len(partes[0]) == 4:
                return f"{partes[0]}-{partes[1]}-{partes[2]}"
            elif len(partes[2]) == 4:
                return f"{partes[2]}-{partes[1]}-{partes[0]}"
        return data_str

    def executar_sigma(self):
        """Preenche os campos do Sigma com os dados de cada linha do PDF."""
        etapa = "validar lançamentos"
        indice = 0
        try:
            if not self.lancamentos:
                raise ValueError("Selecione e verifique um PDF valido primeiro.")

            etapa = "conectar ao Sigma"
            janela = conectar_sigma()
            matricula = self.input_matricula.get().strip()
            codigo_material = self.input_codigo.get().strip()

            total = len(self.lancamentos)
            for indice, requisicao in enumerate(self.lancamentos, start=1):
                if self.parar_execucao:
                    break

                etapa = "aguardar campos editáveis"
                campos = aguardar_campos_editaveis_sigma(janela)
                etapa = "preencher dados"
                self.after(0, self._atualizar_linha_tabela, str(indice), "Lançando...")
                inserir_lancamento_sigma(requisicao, campos, matricula, codigo_material)
                etapa = "selecionar checkbox do lançamento"
                selecionar_checkbox_sigma(janela)
                etapa = "clicar em Inclusão"
                clicar_inclusao_sigma(janela)
                etapa = "confirmar e concluir lançamento"
                mapear_botoes_sigma(janela)
                self.after(0, self._atualizar_linha_tabela, str(indice), "OK")
                self.after(0, self._atualizar_progresso, indice, total, indice / total)

        except Exception as erro:
            detalhe = repr(erro)
            print(
                f"Erro no lançamento {indice or '-'} durante a etapa '{etapa}': {detalhe}"
            )
            traceback.print_exc()
            mensagem = (
                f"Lançamento: {indice or '-'}\n"
                f"Etapa: {etapa}\n"
                f"Erro: {detalhe}"
            )
            self.after(0, messagebox.showerror, "Erro ao lançar", mensagem)
        finally:
            self.em_execucao = False
            self.after(0, self.btn_processar.configure, {"state": "normal"})

    def _iniciar_lancamentos_thread(self):
        self.em_execucao = True
        self.parar_execucao = False

        threading.Thread(target=self.executar_sigma, daemon=True).start()

    def _atualizar_linha_tabela(self, item_id, novo_status):
        valores = list(self.tree.item(item_id, "values"))
        valores[8] = novo_status
        self.tree.item(item_id, values=valores)

    def _atualizar_progresso(self, atual, total, percentual):
        self.lbl_progresso.configure(text=f"Progresso: {atual} / {total}")
        self.progress_bar.set(percentual)
    
    def _construir_interface(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=10)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.titulo = ctk.CTkLabel(self.main_frame, text="Automação para Lançamentos SIGMA", font=("Arial", 24, "bold"), text_color="#000000")
        self.titulo.pack(anchor="w", padx=20, pady=(20, 0))

        self.descricao = ctk.CTkLabel(self.main_frame, text="Lançamentos de forma automática e eficiente.", font=("Arial", 14), text_color="#495057")
        self.descricao.pack(anchor="w", padx=20)

        # div arquivo
        self.frame_arquivo = ctk.CTkFrame(self.main_frame, fg_color="transparent", corner_radius=10)
        self.frame_arquivo.pack(fill="x", padx=20, pady=(20, 10))

        self.label_arquivo = ctk.CTkLabel(self.frame_arquivo, text="Selecione o arquivo:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#495057")
        self.label_arquivo.pack(side="left", padx=(15, 10), pady=10)

        self.botao_selecionar = ctk.CTkButton(self.frame_arquivo, text="Selecionar Arquivo", command=self.selecionar_arquivo)
        self.botao_selecionar.pack(side="left", padx=(0, 10), pady=10)

        self.input_resultado = ctk.CTkEntry(self.frame_arquivo, width=200, fg_color="#FFFFFF", text_color="#495059")
        self.input_resultado.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=10)

        self.botao_verificar = ctk.CTkButton(self.frame_arquivo, text="Verificar Arquivo", command=self.verificar_arquivo)
        self.botao_verificar.pack(side="left", padx=(0, 15), pady=10)

        self.frame_codigo = ctk.CTkFrame(self.main_frame, fg_color="transparent", corner_radius=10)
        self.frame_codigo.pack(fill="x", padx=20, pady=(0, 10))

        self.label_codigo = ctk.CTkLabel(self.frame_codigo, text="Código do produto:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#495057")
        self.label_codigo.pack(side="left", padx=(15, 10), pady=10)

        self.input_codigo = ctk.CTkEntry(self.frame_codigo, width=200, fg_color="#FFFFFF", text_color="#495059")
        self.input_codigo.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=10)

        self.label_matricula = ctk.CTkLabel(self.frame_codigo, text="Matrícula:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#495057")
        self.label_matricula.pack(side="left", padx=(15, 10), pady=10)

        self.input_matricula = ctk.CTkEntry(self.frame_codigo, width=200, fg_color="#FFFFFF", text_color="#495059")
        self.input_matricula.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=10)

        # Relatório do arquivo
        lbl_rel_title = ctk.CTkLabel(self.main_frame, text="Relatório do arquivo", font=ctk.CTkFont(size=14, weight="bold"), text_color="#000")
        lbl_rel_title.pack(anchor="w", pady=(0, 5), padx=20)

        self.frame_relatorio = ctk.CTkFrame(self.main_frame, fg_color="#FFFFFF", border_color="#DEE2E6", border_width=1, corner_radius=8)
        self.frame_relatorio.pack(fill="x", pady=(0, 15), padx=20)

        frame_card_info = ctk.CTkFrame(self.frame_relatorio , fg_color="transparent", border_color="#DEE2E6", border_width=1, corner_radius=8)
        frame_card_info.pack(side="left", padx=15, anchor="w")

        self.lbl_info_arq = ctk.CTkLabel(frame_card_info, text="Arquivo:   Nenhum arquivo selecionado", font=ctk.CTkFont(size=13), text_color="#333333")
        self.lbl_info_arq.pack(anchor="w", pady=2)

        self.lbl_info_qtd = ctk.CTkLabel(frame_card_info, text="Quantidade de linhas:   --", font=ctk.CTkFont(size=13), text_color="#333333")
        self.lbl_info_qtd.pack(anchor="w", pady=2)

        self.lbl_info_total = ctk.CTkLabel(frame_card_info, text="Total do lote:   --", font=ctk.CTkFont(size=13), text_color="#333333")
        self.lbl_info_total.pack(anchor="w", pady=2)

        frame_card_status = ctk.CTkFrame(self.frame_relatorio, fg_color="transparent")
        frame_card_status.pack(side="right", padx=15, anchor="e")

        self.btn_badge = ctk.CTkButton(
            frame_card_status,
            text="Aguardando arquivo",
            fg_color="#E2E3E5",
            text_color="#383D41",
            hover=False,
            height=32,
            corner_radius=16,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_badge.pack(anchor="e")

        # Controles
        frame_controles = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        frame_controles.pack(fill="x", pady=(0, 15))

        self.btn_processar = ctk.CTkButton(frame_controles, text="Iniciar Lançamentos", fg_color="#28A745", text_color="#FFFFFF", hover_color="#0056B3", font=ctk.CTkFont(size=14, weight="bold"), height=40, width=180, command=self._iniciar_lancamentos_thread)
        self.btn_processar.pack(side="left", padx=(15, 15), pady=10)

        frame_progresso = ctk.CTkFrame(frame_controles, fg_color="transparent")
        frame_progresso.pack(side="left", fill="x", expand=True, padx=(0, 15))

        self.lbl_progresso = ctk.CTkLabel(frame_progresso, text="Progresso: 0 / 0", font=ctk.CTkFont(size=13, weight="bold"), text_color="#333333")
        self.lbl_progresso.pack(anchor="w")

        self.progress_bar = ctk.CTkProgressBar(frame_progresso, height=12, progress_color="#007BFF")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(4, 0))

        self.btn_parar = ctk.CTkButton(
            frame_controles,
            text="Parar",
            fg_color="#FFFFFF",
            text_color="#DC3545",
            border_color="#DC3545",
            border_width=1,
            hover_color="#F8D7DA",
            height=40,
            width=100,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.btn_parar.pack(side="right", padx=(0, 15), pady=10)

        # Tabela
        tabela_titulo = ctk.CTkLabel(self.main_frame, text="Status dos Lançamentos", font=ctk.CTkFont(size=14, weight="bold"), text_color="#333333")
        tabela_titulo.pack(anchor="w", pady=(0, 5), padx=15)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"), background="#E9ECEF", foreground="#495057")
        style.configure("Treeview", font=("Arial", 9), rowheight=28, background="#FFFFFF", fieldbackground="#FFFFFF")
        style.map("Treeview", background=[("selected", "#E2E6EA")], foreground=[("selected", "#000000")])

        frame_tabela = ctk.CTkFrame(self.main_frame, fg_color="#FFFFFF", border_color="#DEE2E6", border_width=1, corner_radius=8)
        frame_tabela.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        colunas = ("id", "data_req", "req", "cre", "sici", "desig", "unidade_escolar", "qtd", "status")
        self.tree = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=10)

        self.tree.heading("id", text="#")
        self.tree.heading("data_req", text="Data Req")
        self.tree.heading("req", text="Req")
        self.tree.heading("cre", text="CRE")
        self.tree.heading("sici", text="SICI")
        self.tree.heading("desig", text="DESIG")
        self.tree.heading("unidade_escolar", text="Unidade Escolar")
        self.tree.heading("qtd", text="QTD")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=40, anchor="center")
        self.tree.column("data_req", width=90, anchor="center")
        self.tree.column("req", width=55, anchor="center")
        self.tree.column("cre", width=50, anchor="center")
        self.tree.column("sici", width=70, anchor="center")
        self.tree.column("desig", width=75, anchor="center")
        self.tree.column("unidade_escolar", width=260, anchor="w")
        self.tree.column("qtd", width=50, anchor="center")
        self.tree.column("status", width=110, anchor="center")

        scrollbar = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y", pady=5)

if __name__ == "__main__":
    app = AppLancamento()
    app.mainloop()