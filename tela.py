import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

janela = tk.Tk()
janela.title("Automação para Lançamentos SIGMA")
janela.geometry("850x750")  # Largura x Altura em pixels
janela.resizable(False, False)  # Impede redimensionamento da janela
def selecionarArquivo():
    caminho = filedialog.askopenfilename(
        title="Selecionar arquivo",
        filetypes=(("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*"))
    )
    if caminho:
        input_resultado.delete(0, tk.END)
        input_resultado.insert(0, caminho)


def verificarArquivo():
    if input_resultado.get():
        label_resultado.configure(text="Arquivo verificado")
    else:
        label_resultado.configure(text="Selecione um arquivo primeiro")

divCima = ctk.CTkFrame(janela, fg_color="transparent")
divCima.pack(fill="x", pady=(0, 15))

lbl_sel = ctk.CTkLabel(divCima, text="Selecione o arquivo", font=ctk.CTkFont(size=13, weight="bold"), text_color="#333333")
lbl_sel.pack(side="left", padx=(0, 10))

btn_selecionar = ctk.CTkButton(
    divCima,
    text="Escolher arquivo",
    command=selecionarArquivo,
    height=35,
    font=ctk.CTkFont(size=12, weight="bold")
)
btn_selecionar.pack(side="left", padx=(0, 10))

input_resultado = ctk.CTkEntry(
    divCima,
    placeholder_text="Caminho do arquivo selecionado",
    width=320,
    height=35,
    fg_color="#ffffff",
    font=ctk.CTkFont(size=12)
)
input_resultado.pack(side="left", padx=(0, 15))

btn_verificar = ctk.CTkButton(
    divCima,
    text="Verificar arquivo",
    command=verificarArquivo,
    height=35,
    font=ctk.CTkFont(size=12, weight="bold")
)
btn_verificar.pack(side="left")

label_resultado = ctk.CTkLabel(divCima, text="")
label_resultado.pack(side="left", padx=(10, 0))

# Iniciar o loop da aplicação
janela.mainloop()