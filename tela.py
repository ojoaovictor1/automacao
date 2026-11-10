from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import re
import customtkinter as ctk
import os
import pdfplumber

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
            self.verificar_arquivo()

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
        total_valor = 0.0

        try:
            with pdfplumber.open(caminho) as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text()
                    if not texto:
                        continue

                    for linha in texto.split('\n'):
                        linha = linha.strip()
                        match_data = re.search(r'(\d{2}[/\.-]\d{2}[/\.-]\d{4}|\d{4}[/\.-]\d{2}[/\.-]\d{2})', linha)
                        match_valor = re.search(r'([\d\.\,]+)$', linha)

                        if match_data and match_valor:
                            inicio_miolo = match_data.end()
                            fim_miolo = match_valor.start()
                            miolo = linha[inicio_miolo:fim_miolo].strip().split()

                            if len(miolo) >= 2 and miolo[0].startswith("EX-"):
                                codigo = miolo[0]
                                categoria = miolo[-1].lower()
                                descricao = " ".join(miolo[1:-1]) if len(miolo) > 2 else miolo[0]
                                valor_str = match_valor.group(1).replace(".", "").replace(",", ".")
                                valor_num = float(valor_str)

                                total_valor += valor_num

                                self.lancamentos.append({
                                    "data": match_data.group(1),
                                    "codigo": codigo,
                                    "descricao": descricao,
                                    "categoria": categoria,
                                    "valor_str": match_valor.group(1),
                                    "valor_num": valor_str
                                })

            qtd = len(self.lancamentos)
            self.lbl_info_qtd.configure(text=f"Quantidade de linhas:  {qtd} lançamentos")

            valor_fmt = f"{total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self.lbl_info_total.configure(text=f"Total do lote:  R${valor_fmt} (confere com o PDF)")

            self.btn_badge.configure(
                text="Pronto",
                fg_color='#D4EDDA',
                text_color="#155724"
            )

            for item in self.tree.get_children():
                self.tree.delete(item)

            for idx, item in enumerate(self.lancamentos, start=1):
                idx_str = f"{idx:02d}"
                self.tree.insert("", "end", iid=str(idx), values=(
                    idx_str, item["data"], item["codigo"], item["descricao"], 
                    item["categoria"], item["valor_str"], "Aguardando"
                ))

            self.lbl_progresso.configure(text=f"Progresso: 0 / {qtd}")
            self.progress_bar.set(0)
        
        except Exception as e:
            self.btn_badge.configure(text="Erro no arquivo", fg_color="#F8D7DA", text_color="#721C24")
            messagebox.showerror("Erro de Leitura", f"Falha ao ler PDF: {str(e)}")
        ###
    
    def _construir_interface(self):

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=10)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.titulo = ctk.CTkLabel(self.main_frame, text="Automação para Lançamentos SIGMA", font=("Arial", 24, "bold"), text_color="#000000")
        self.titulo.pack(anchor="w", padx=20, pady=(20, 0))

        self.descricao = ctk.CTkLabel(self.main_frame, text="Realize lançamentos de forma automática e eficiente.", font=("Arial", 14), text_color="#495057")
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

        self.btn_processar = ctk.CTkButton(frame_controles, text="Iniciar Lançamentos", fg_color="#28A745", text_color="#FFFFFF", hover_color="#0056B3", font=ctk.CTkFont(size=14, weight="bold"), height=40, width=180)
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
            text="■  Parar",
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
        tabela_titulo = ctk.CTkLabel(self.main_frame, text="Lançamentos realizados", font=ctk.CTkFont(size=14, weight="bold"), text_color="#333333")
        tabela_titulo.pack(anchor="w", pady=(0, 5), padx=15)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"), background="#E9ECEF", foreground="#495057")
        style.configure("Treeview", font=("Arial", 9), rowheight=28, background="#FFFFFF", fieldbackground="#FFFFFF")
        style.map("Treeview", background=[("selected", "#E2E6EA")], foreground=[("selected", "#000000")])

        frame_tabela = ctk.CTkFrame(self.main_frame, fg_color="#FFFFFF", border_color="#DEE2E6", border_width=1, corner_radius=8)
        frame_tabela.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        colunas = ("id", "data", "codigo", "descricao", "categoria", "valor", "status")
        self.tree = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=10)

        self.tree.heading("id", text="#")
        self.tree.heading("data", text="Data")
        self.tree.heading("codigo", text="Código")
        self.tree.heading("descricao", text="Descrição")
        self.tree.heading("categoria", text="Categoria")
        self.tree.heading("valor", text="R$")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=40, anchor="center")
        self.tree.column("data", width=90, anchor="center")
        self.tree.column("codigo", width=90, anchor="center")
        self.tree.column("descricao", width=200, anchor="w")
        self.tree.column("categoria", width=110, anchor="w")
        self.tree.column("valor", width=100, anchor="e")
        self.tree.column("status", width=110, anchor="center")

        scrollbar = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y", pady=5)

if __name__ == "__main__":
    app = AppLancamento()
    app.mainloop()