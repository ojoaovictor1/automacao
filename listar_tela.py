from pywinauto import Application


# Conecta ao Edge que já está aberto com a IE Tab.
app = Application(backend="uia").connect(
    title_re=".*Microsoft.*Edge.*",
    found_index=0,
)
janela = app.top_window()
janela.set_focus()

campos = janela.descendants(control_type="Edit")

print(
    f"\n=== CONTROLES DA TELA ATUAL ===\n"
    f"Inputs encontrados: {len(campos)}\n"
)

indice_input = 0
for campo in campos:
    auto_id = campo.element_info.automation_id or ""
    nome = campo.element_info.name or ""

    # Não lista nem altera a barra de endereço ou outros controles do Edge.
    if auto_id in {"view_1017", "address-box"} or nome == "Barra de pesquisa e endereços":
        continue

    indice_input += 1
    try:
        valor = campo.get_value()
    except Exception:
        valor = "<indisponível>"

    print(
        f"[Input {indice_input}] auto_id={auto_id!r} "
        f"| name={nome!r} | valor={valor!r}"
    )

    if not campo.is_visible() or not campo.is_enabled():
        print("  -> ignorado: campo invisível ou desabilitado")
        continue

    valores_especiais = {7: "111", 8: "222"}
    valor_teste = valores_especiais.get(indice_input)
    if valor_teste is None:
        print("  -> não preenchido")
        continue

    try:
        campo.set_edit_text(valor_teste)
        print(f"  -> preenchido com {valor_teste!r}")
    except Exception as erro:
        print(f"  -> não foi possível preencher: {erro}")
