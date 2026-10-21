"""
Estoque de Componentes
Aplicativo local para Windows com Tkinter + SQLite.
"""
import csv
import sys
import os
import sqlite3
import subprocess
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

APP_NAME = "Estoque de Componentes"
APP_VERSION = "1.2"
AUTOR = "Jorge Alberto de Paula"


# Pasta do banco: localizada dentro da pasta do projeto,
# funcionando tanto no código Python quanto no executável.

if getattr(sys, "frozen", False):
    # Executável: ProjetoComponentes\dist\EstoqueComponentes\EstoqueComponentes.exe
    PASTA_PROJETO = Path(sys.executable).resolve().parents[2]
else:
    # Código-fonte: pasta do arquivo Python
    PASTA_PROJETO = Path(__file__).resolve().parent

PASTA_SINCRONIZADA = PASTA_PROJETO / "EstoqueComponentes"

PASTA_FALLBACK = Path.home() / "Documents" / "EstoqueComponentes"
NOME_BANCO = "estoque_componentes.db"

PASTA_FALLBACK = Path.home() / "Documents" / "EstoqueComponentes"
NOME_BANCO = "estoque_componentes.db"


# Tipos de movimentação gravados no banco (mantidos iguais aos da versão anterior).
TIPO_ENTRADA = "Entrada"
TIPO_SAIDA = "Saída"
TIPO_AJUSTE = "Ajuste de inventário"
ARG_JANELA_DATASHEET = "--datasheet-window"

# Paleta profissional — azul, branco e cinza
BG = "#F1F5F9"
PANEL = "#FFFFFF"
PANEL2 = "#E2E8F0"
BORDER = "#D5DEE9"

TEXT = "#1E293B"
MUTED = "#64748B"
ACCENT = "#2563EB"

GREEN = "#16A34A"
YELLOW = "#D97706"
RED = "#DC2626"

FIELD = "#FFFFFF"
LINHA_PAR = "#FFFFFF"
LINHA_IMPAR = "#F1F5F9"
FOOTER_BG = "#163A5F"

# (cor normal, cor hover, cor do texto)
ESTILOS_BOTAO = {
    "primario": ("#2563EB", "#1D4ED8", "#FFFFFF"),
    "datasheet": ("#DC2626", "#B91C1C", "#FFFFFF"),
    "secundario": ("#E2E8F0", "#CBD5E1", "#1E293B"),
    "cancelar": ("#64748B", "#475569", "#FFFFFF"),
    "padrao": ("#163A5F", "#244D75", "#FFFFFF"),
}

# (chave, título, largura, alinhamento)
COLS_ALERTA = [
    ("componente", "Componente", 180, "w"),
    ("codigo", "Código", 90, "center"),
    ("descricao", "Descrição", 350, "w"),
    ("quantidade", "Saldo", 70, "center"),
    ("minimo", "Mínimo", 70, "center"),
    ("gaveta", "Gaveta", 80, "center"),
    ("caixa", "Caixa", 65, "center"),
]
COLS_COMPONENTES = [
    ("id", "ID", 55, "center"),
    ("componente", "Componente", 190, "w"),
    ("codigo", "Código", 110, "center"),
    ("descricao", "Descrição", 360, "w"),
    ("quantidade", "Saldo", 85, "center"),
    ("minimo", "Mínimo", 85, "center"),
    ("gaveta", "Gaveta", 105, "center"),
    ("datasheet", "DataSheet", 180, "center"),
    ("caixa", "Caixa", 85, "center"),
]
COLS_MOVIMENTOS = [
    ("data", "Data e hora", 145, "center"),
    ("componente", "Componente", 170, "w"),
    ("codigo", "Código", 80, "center"),
    ("tipo", "Tipo", 130, "center"),
    ("quantidade", "Qtd.", 55, "center"),
    ("anterior", "Saldo anterior", 90, "center"),
    ("novo", "Saldo novo", 75, "center"),
    ("motivo", "Motivo", 220, "w"),
    ("responsavel", "Responsável", 110, "center"),
]


# --------------------------------------------------------------------------- #
# Funções auxiliares
# --------------------------------------------------------------------------- #
def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def resolver_pasta_dados():
    """Devolve a primeira pasta utilizável para guardar o banco de dados."""
    candidatas = []
    env = os.environ.get("ESTOQUE_DATA_DIR")
    if env:
        candidatas.append(Path(env))
    candidatas += [PASTA_SINCRONIZADA, PASTA_FALLBACK]
    for pasta in candidatas:
        try:
            pasta.mkdir(parents=True, exist_ok=True)
            return pasta
        except OSError:
            continue
    raise RuntimeError("Não foi possível criar uma pasta para guardar o banco de dados.")


def padrao_like(texto):
    """Prepara o texto para LIKE, tratando % e _ como caracteres comuns."""
    texto = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{texto}%"


def botao(parent, texto, comando, estilo="padrao"):
    """Cria um botão já estilizado, com efeito hover."""
    normal, hover, cor_texto = ESTILOS_BOTAO[estilo]
    b = tk.Button(
        parent, text=texto, command=comando,
        bg=normal, fg=cor_texto,
        activebackground=hover, activeforeground="#ffffff",
        disabledforeground="#8492a6",
        font=("Segoe UI", 9, "bold"),
        relief="flat", bd=0,
        highlightthickness=0,
        cursor="hand2", padx=12, pady=7,
    )
    b.bind("<Enter>", lambda e: b.configure(bg=hover) if str(b["state"]) != "disabled" else None)
    b.bind("<Leave>", lambda e: b.configure(bg=normal))
    return b


def criar_tree(parent, colunas, **opcoes):
    tree = ttk.Treeview(parent, columns=[c[0] for c in colunas], show="headings", **opcoes)
    for chave, titulo, largura, ancora in colunas:
        tree.heading(chave, text=titulo)
        tree.column(chave, width=largura, anchor=ancora)
    tree.tag_configure("par", background=LINHA_PAR)
    tree.tag_configure("impar", background=LINHA_IMPAR)
    return tree


def tabela_com_scroll(parent, colunas, horizontal=True, ao_rolar=None, **opcoes):
    """Cria uma Treeview com barras de rolagem. Devolve (quadro, tree)."""
    quadro = tk.Frame(parent, bg=BG, highlightbackground=BORDER, highlightthickness=1)
    tree = criar_tree(quadro, colunas, **opcoes)
    sy = ttk.Scrollbar(quadro, orient="vertical", command=tree.yview)

    def atualizar_scroll_vertical(*args):
        sy.set(*args)
        if ao_rolar:
            ao_rolar()

    tree.configure(yscrollcommand=atualizar_scroll_vertical)
    tree.grid(row=0, column=0, sticky="nsew")
    sy.grid(row=0, column=1, sticky="ns")
    if horizontal:
        sx = ttk.Scrollbar(quadro, orient="horizontal", command=tree.xview)

        def atualizar_scroll_horizontal(*args):
            sx.set(*args)
            if ao_rolar:
                ao_rolar()

        tree.configure(xscrollcommand=atualizar_scroll_horizontal)
        sx.grid(row=1, column=0, sticky="ew")
    quadro.rowconfigure(0, weight=1)
    quadro.columnconfigure(0, weight=1)
    return quadro, tree


def preencher_tree(tree, linhas, iids=None):
    """Substitui o conteúdo da tree, alternando a cor das linhas."""
    tree.delete(*tree.get_children())
    for i, valores in enumerate(linhas):
        opcoes = {"iid": str(iids[i])} if iids else {}
        tree.insert("", "end", values=valores, tags=("par" if i % 2 == 0 else "impar",), **opcoes)


# --------------------------------------------------------------------------- #
# Aplicativo
# --------------------------------------------------------------------------- #
class EstoqueApp:
    def __init__(self, root, db_path):
        self.root = root
        self.db_path = Path(db_path)
        self.cont_ids = {}  # rótulo do combobox da contagem -> id do componente

        self.root.title(f"{APP_NAME} | v{APP_VERSION}")
        self.root.configure(bg=BG)
        self.root.minsize(1000, 650)
        self.centralizar(1180, 760)

        self.db = sqlite3.connect(self.db_path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.criar_banco()

        self.estilizar()
        self.montar_interface()
        self.atualizar_tudo()

    # ------------------------------------------------------------------ janela
    def centralizar(self, largura, altura):
        """Centraliza a janela principal na tela."""
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        largura = min(largura, sw - 40)
        altura = min(altura, sh - 80)
        x = max(0, (sw - largura) // 2)
        y = max(0, (sh - altura) // 2)
        self.root.geometry(f"{largura}x{altura}+{x}+{y}")

    def janela_modal(self, titulo, largura, altura, redimensionavel=(False, False)):
        """Cria uma janela modal centralizada sobre a janela principal."""
        win = tk.Toplevel(self.root)
        win.title(titulo)
        win.configure(bg=BG)
        win.transient(self.root)
        win.resizable(*redimensionavel)
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - largura) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - altura) // 2
        win.geometry(f"{largura}x{altura}+{max(0, x)}+{max(0, y)}")
        win.wait_visibility()
        win.grab_set()
        win.focus_set()
        win.bind("<Escape>", lambda e: win.destroy())
        return win

    # ------------------------------------------------------------------- banco
    def criar_banco(self):
        """Cria as tabelas necessárias no SQLite."""
        with self.db:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS componentes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    componente TEXT NOT NULL,
                    codigo TEXT DEFAULT '',
                    descricao TEXT DEFAULT '',
                    gaveta TEXT DEFAULT '',
                    datasheet TEXT DEFAULT '',
                    caixa TEXT DEFAULT '',
                    quantidade INTEGER NOT NULL DEFAULT 0,
                    estoque_minimo INTEGER NOT NULL DEFAULT 0,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    UNIQUE(componente, codigo, descricao, gaveta, caixa)
                )
            """)
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS movimentacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    componente_id INTEGER NOT NULL,
                    data_hora TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    quantidade INTEGER NOT NULL,
                    saldo_anterior INTEGER NOT NULL,
                    saldo_novo INTEGER NOT NULL,
                    motivo TEXT DEFAULT '',
                    responsavel TEXT DEFAULT '',
                    FOREIGN KEY(componente_id) REFERENCES componentes(id)
                )
            """)
            self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_mov_componente ON movimentacoes(componente_id)"
            )

    def contar_componentes(self):
        return self.db.execute("SELECT COUNT(*) FROM componentes").fetchone()[0]

    def registrar_movimento(self, ident, tipo, quantidade, saldo_anterior, saldo_novo, motivo, responsavel):
        """Atualiza o saldo e grava o histórico na mesma transação."""
        with self.db:
            self.db.execute(
                "UPDATE componentes SET quantidade=?, atualizado_em=? WHERE id=?",
                (saldo_novo, agora(), ident),
            )
            self.db.execute(
                """INSERT INTO movimentacoes
                   (componente_id, data_hora, tipo, quantidade, saldo_anterior, saldo_novo, motivo, responsavel)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (ident, agora(), tipo, quantidade, saldo_anterior, saldo_novo, motivo, responsavel),
            )


    # ------------------------------------------------------------------ estilo
    def estilizar(self):
        st = ttk.Style()
        st.theme_use("clam")

        # Fonte padrão
        st.configure(".", font=("Segoe UI", 10))

        # Fundos e textos
        st.configure("TSeparator", background=BORDER)
        st.configure("TFrame", background=BG)
        st.configure("Panel.TFrame", background=PANEL)

        st.configure(
            "TLabel",
            background=BG,
            foreground=TEXT
        )
        st.configure(
            "Muted.TLabel",
            background=BG,
            foreground=MUTED
        )
        st.configure(
            "Title.TLabel",
            font=("Segoe UI", 20, "bold"),
            foreground=TEXT,
            background=BG
        )
        st.configure(
            "Sub.TLabel",
            font=("Segoe UI", 10),
            foreground=MUTED,
            background=BG
        )

        # Tabelas
        st.configure(
            "Treeview",
            background=LINHA_PAR,
            fieldbackground=FIELD,
            foreground=TEXT,
            rowheight=35,
            borderwidth=0,
            font=("Segoe UI", 10)
        )
        st.configure(
            "Treeview.Heading",
            background="#163A5F",
            foreground="#FFFFFF",
            padding=(12, 11),
            font=("Segoe UI", 10, "bold")
        )
        st.map(
            "Treeview",
            background=[("selected", "#2563EB")],
            foreground=[("selected", "#FFFFFF")]
        )

        # Barras de rolagem
        for orient in ("Vertical", "Horizontal"):
            st.configure(
                f"{orient}.TScrollbar",
                background=PANEL2,
                troughcolor=BG,
                bordercolor=BG,
                arrowcolor=TEXT
            )

        # Barra de navegação
        st.configure(
            "App.TNotebook",
            background=BG,
            borderwidth=0,
            padding=0,
        )
        st.layout("App.TNotebook.Tab", [])

        # Campos de preenchimento
        st.configure(
            "TEntry",
            fieldbackground=FIELD,
            foreground=TEXT,
            insertcolor=TEXT,
            padding=7
        )
        st.configure(
            "TCombobox",
            fieldbackground=FIELD,
            foreground=TEXT,
            padding=6
        )
        st.configure(
            "TSpinbox",
            fieldbackground=FIELD,
            foreground=TEXT,
            padding=6
        )

        st.map(
            "TCombobox",
            fieldbackground=[("readonly", FIELD)],
            foreground=[("readonly", TEXT)],
            selectbackground=[("readonly", "#DBEAFE")],
            selectforeground=[("readonly", TEXT)]
        )

        # Lista suspensa dos campos
        self.root.option_add(
            "*TCombobox*Listbox.background", FIELD
        )
        self.root.option_add(
            "*TCombobox*Listbox.foreground", TEXT
        )
        self.root.option_add(
            "*TCombobox*Listbox.selectBackground", "#2563EB"
        )
        self.root.option_add(
            "*TCombobox*Listbox.selectForeground", "#FFFFFF"
        )


    # --------------------------------------------------------------- interface
    def montar_interface(self):
    
        top = tk.Frame(self.root, bg=BG, padx=22, pady=12)
        top.pack(fill="x")

        # Robô JP do projeto
        self.robo_img_tk = None
        caminho_robo = Path(__file__).resolve().parent / "assets" / "robo_jp.png"

        if Image is not None and caminho_robo.is_file():
            try:
                imagem = Image.open(caminho_robo).convert("RGBA")
                imagem.thumbnail((64, 64), Image.Resampling.LANCZOS)
                self.robo_img_tk = ImageTk.PhotoImage(imagem)

                tk.Label(
                    top,
                    image=self.robo_img_tk,
                    bg=BG
                ).pack(side="left", padx=(0, 14))
            except Exception as erro:
                print(f"Não foi possível carregar o robô JP: {erro}")

        titulo = tk.Frame(top, bg=BG)
        titulo.pack(side="left", fill="y", pady=5)

        tk.Label(
            titulo,
            text="ESTOQUE DE COMPONENTES",
            bg=BG,
            fg=ACCENT,
            font=("Segoe UI", 21, "bold", "underline")
        ).pack(anchor="w")

        tk.Label(
            titulo,
            text="Controle inteligente de componentes",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(3, 0))

        tk.Label(
            top,
            text="CONTROLE LOCAL",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9, "bold")
        ).pack(side="right", pady=8)


        # Rodapé criado ANTES do notebook para não ser empurrado para fora da janela
        footer = tk.Frame(self.root, bg=FOOTER_BG, padx=16, height=48)
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)
        ttk.Separator(self.root, orient="horizontal").pack(side="bottom", fill="x")

        tk.Label(
            footer,
            text=f"✦ Desenvolvido por {AUTOR}  •  {APP_NAME.upper()}  •  VERSÃO {APP_VERSION}",
            bg=FOOTER_BG, fg="#eaeaf7", font=("Georgia", 8), anchor="w", padx=4,
        ).pack(side="left", fill="y")
        botao(footer, "Backup", self.backup).pack(side="right", pady=6, padx=(6, 0))
        botao(footer, "Exportar CSV", self.exportar_csv).pack(side="right", pady=6, padx=6)

        # Navegação principal
        self.nb = ttk.Notebook(self.root, style="App.TNotebook")
        self.tab_painel = ttk.Frame(self.nb, padding=16)
        self.tab_componentes = ttk.Frame(self.nb, padding=12)
        self.tab_mov = ttk.Frame(self.nb, padding=12)
        self.tab_contagem = ttk.Frame(self.nb, padding=16)
        abas = [
            ("Painel", self.tab_painel),
            ("Componentes", self.tab_componentes),
            ("Movimentações", self.tab_mov),
            ("Contagem de estoque", self.tab_contagem),
        ]
        for nome, pagina in abas:
            self.nb.add(pagina, text=nome)

        navegacao = tk.Frame(self.root, bg=BG, padx=18)
        navegacao.pack(fill="x")
        self.nav_abas = []
        for indice, (nome, _) in enumerate(abas):
            item = tk.Frame(navegacao, bg=BG)
            item.pack(side="left", fill="x", expand=True)
            botao_aba = tk.Button(
                item,
                text=nome,
                command=lambda i=indice: self.selecionar_aba(i),
                bg=PANEL,
                fg=ACCENT,
                activebackground=PANEL,
                activeforeground=ACCENT,
                font=("Segoe UI", 10, "bold"),
                relief="flat",
                bd=0,
                highlightthickness=0,
                cursor="hand2",
                padx=18,
                pady=12,
            )
            botao_aba.pack(fill="x")
            indicador = tk.Frame(item, bg=ACCENT, height=3)
            indicador.pack(fill="x")
            self.nav_abas.append((botao_aba, indicador))

        tk.Frame(navegacao, bg=BORDER, height=1).pack(fill="x")
        self.nb.bind("<<NotebookTabChanged>>", self.atualizar_abas)
        self.nb.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.atualizar_abas()

        self.montar_painel()
        self.montar_componentes()
        self.montar_movimentacoes()
        self.montar_contagem()


    def selecionar_aba(self, indice):
        self.nb.select(indice)
        self.atualizar_abas()

    def atualizar_abas(self, _event=None):
        selecionada = self.nb.index(self.nb.select())
        for indice, (botao_aba, indicador) in enumerate(self.nav_abas):
            ativa = indice == selecionada
            botao_aba.configure(
                bg=PANEL if ativa else BG,
                fg=ACCENT if ativa else MUTED,
                activebackground=PANEL if ativa else BG,
                activeforeground=ACCENT if ativa else TEXT,
            )
            indicador.configure(bg=ACCENT if ativa else BG)

    
    def card(self, parent, titulo, valor, cor=ACCENT):
        f = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=8,
            pady=3
        )

        tk.Label(
            f,
            text=titulo.upper(),
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 7, "bold")
        ).pack(anchor="w")

        lab = tk.Label(
            f,
            text=str(valor),
            bg=PANEL,
            fg=cor,
            font=("Segoe UI", 14, "bold")
        )
        lab.pack(anchor="w", pady=(0, 0))

        return f, lab


    def montar_painel(self):
        ttk.Label(self.tab_painel, text="Visão geral", style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.tab_painel, text="Resumo do inventário e alertas de reposição.",
                  style="Sub.TLabel").pack(anchor="w", pady=(3, 16))

        cards = tk.Frame(self.tab_painel, bg=BG)
        cards.pack(fill="x")
        self.card_widgets = []
        
        for titulo, cor in [
            ("Componentes cadastrados", ACCENT),
            ("Unidades em estoque", GREEN),
            ("Sem estoque", RED)
        ]:
            w, lab = self.card(cards, titulo, "0", cor)
            w.pack(side="left", fill="both", expand=True, padx=(0, 10))
            self.card_widgets.append(lab)

        section = tk.Frame(self.tab_painel, bg=BG)
        section.pack(fill="both", expand=True, pady=(6, 0))
        tk.Label(section, text="Itens que precisam de atenção", bg=BG, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 10))
        quadro, self.alert_tree = tabela_com_scroll(section, COLS_ALERTA, horizontal=False, height=11)
        quadro.pack(fill="both", expand=True)
        self.alert_tree.bind("<Double-1>", self.duplo_clique_alerta)

    def montar_componentes(self):
        toolbar = tk.Frame(self.tab_componentes, bg=BG)
        toolbar.pack(fill="x", pady=(0, 10))
        tk.Label(toolbar, text="Cadastro de componentes", bg=BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        botao(toolbar, "+ Novo componente", self.novo_componente, "primario").pack(side="right")

        searchrow = tk.Frame(self.tab_componentes, bg=BG)
        searchrow.pack(fill="x", pady=(0, 10))
        tk.Label(searchrow, text="Pesquisar:", bg=BG, fg=MUTED).pack(side="left")
        self.busca = tk.StringVar()
        ent = ttk.Entry(searchrow, textvariable=self.busca, width=42)
        ent.pack(side="left", padx=8)
        ent.bind("<KeyRelease>", lambda e: self.carregar_componentes())
        botao(searchrow, "Editar selecionado", self.abrir_componente_selecionado).pack(side="right", padx=(8, 0))
        botao(searchrow, "Entrada / saída", self.movimentar_selecionado, "primario").pack(side="right")

        self.datasheet_botoes = {}
        self._atualizacao_botoes_datasheet = None
        quadro, self.comp_tree = tabela_com_scroll(
            self.tab_componentes,
            COLS_COMPONENTES,
            ao_rolar=self.agendar_botoes_datasheet,
        )
        quadro.pack(fill="both", expand=True)
        self.comp_tree.bind("<Configure>", lambda _e: self.agendar_botoes_datasheet())

        bottom = tk.Frame(self.tab_componentes, bg=BG)
        bottom.pack(fill="x", pady=(8, 0))
        tk.Label(bottom, text="Clique em DataSheet para abrir o link; use Editar selecionado para alterar o componente.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        self.lbl_resultados = tk.Label(bottom, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.lbl_resultados.pack(side="right")

    def montar_movimentacoes(self):
        row = tk.Frame(self.tab_mov, bg=BG)
        row.pack(fill="x", pady=(0, 12))
        tk.Label(row, text="Histórico de movimentações", bg=BG, fg=TEXT,
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        botao(row, "Registrar movimentação", self.nova_movimentacao, "primario").pack(side="right")
        quadro, self.mov_tree = tabela_com_scroll(self.tab_mov, COLS_MOVIMENTOS)
        quadro.pack(fill="both", expand=True)

    def montar_contagem(self):
        ttk.Label(self.tab_contagem, text="Contagem física do estoque", style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.tab_contagem,
                  text="Informe a quantidade que você contou. O sistema registra o ajuste no histórico.",
                  style="Sub.TLabel").pack(anchor="w", pady=(4, 18))

        form = tk.Frame(self.tab_contagem, bg=PANEL, padx=20, pady=20,
                        highlightbackground=BORDER, highlightthickness=1)
        form.pack(fill="x", anchor="n")
        self.cont_busca = tk.StringVar()
        self.cont_qtd = tk.StringVar(value="0")
        self.cont_motivo = tk.StringVar(value="Contagem física inicial")
        self.cont_resp = tk.StringVar()
        self.cont_saldo = tk.StringVar(value="—")

        tk.Label(form, text="Componente", bg=PANEL, fg=TEXT).grid(row=0, column=0, sticky="w", pady=7)
        self.cont_combo = ttk.Combobox(form, textvariable=self.cont_busca, state="readonly", width=65)
        self.cont_combo.grid(row=0, column=1, sticky="ew", padx=12, pady=7)
        self.cont_combo.bind("<<ComboboxSelected>>", self.atualizar_saldo_contagem)

        tk.Label(form, text="Saldo atual no sistema", bg=PANEL, fg=TEXT).grid(row=1, column=0, sticky="w", pady=7)
        tk.Label(form, textvariable=self.cont_saldo, bg=PANEL, fg=YELLOW,
                 font=("Segoe UI", 11, "bold")).grid(row=1, column=1, sticky="w", padx=12, pady=7)

        tk.Label(form, text="Quantidade contada", bg=PANEL, fg=TEXT).grid(row=2, column=0, sticky="w", pady=7)
        ttk.Spinbox(form, from_=0, to=999999999, textvariable=self.cont_qtd,
                    width=18).grid(row=2, column=1, sticky="w", padx=12, pady=7)

        tk.Label(form, text="Motivo", bg=PANEL, fg=TEXT).grid(row=3, column=0, sticky="w", pady=7)
        ttk.Entry(form, textvariable=self.cont_motivo, width=68).grid(row=3, column=1, sticky="ew", padx=12, pady=7)

        tk.Label(form, text="Responsável (opcional)", bg=PANEL, fg=TEXT).grid(row=4, column=0, sticky="w", pady=7)
        ttk.Entry(form, textvariable=self.cont_resp, width=40).grid(row=4, column=1, sticky="w", padx=12, pady=7)

        botao(form, "Salvar contagem e ajustar saldo", self.salvar_contagem, "primario").grid(
            row=5, column=1, sticky="w", padx=12, pady=(15, 5))
        form.columnconfigure(1, weight=1)

        tk.Label(self.tab_contagem, text="Importante: cada ajuste fica registrado no histórico de movimentações.",
                 bg=BG, fg=YELLOW, font=("Segoe UI", 10)).pack(anchor="w", pady=16)

    # -------------------------------------------------------- carga de dados
    def atualizar_tudo(self):
        self.carregar_componentes()
        self.carregar_movimentacoes()
        self.atualizar_painel()
        self.carregar_combo_contagem()

    def carregar_componentes(self):
        selecionado = self.id_selecionado()
        q = padrao_like(self.busca.get().strip())
        rows = self.db.execute(
            """SELECT * FROM componentes
               WHERE componente LIKE ? ESCAPE '\\' OR codigo LIKE ? ESCAPE '\\'
                  OR descricao LIKE ? ESCAPE '\\' OR gaveta LIKE ? ESCAPE '\\'
                  OR caixa LIKE ? ESCAPE '\\'
               ORDER BY componente, codigo, descricao""",
            (q, q, q, q, q),
        ).fetchall()
        linhas = []
        for r in rows:
            ds = r["datasheet"] or ""
            ds_exibicao = "DataSheet" if ds.lower().startswith(("http://", "https://")) else ""
            linhas.append((r["id"], r["componente"], r["codigo"], r["descricao"], r["quantidade"],
                           r["estoque_minimo"], r["gaveta"], ds_exibicao, r["caixa"]))
        preencher_tree(self.comp_tree, linhas, iids=[r["id"] for r in rows])
        self.agendar_botoes_datasheet()
        self.lbl_resultados.config(text=f"{len(rows)} componente(s)")
        # Mantém a seleção após recarregar
        if selecionado is not None and self.comp_tree.exists(str(selecionado)):
            self.comp_tree.selection_set(str(selecionado))
            self.comp_tree.see(str(selecionado))

    def agendar_botoes_datasheet(self):
        if self._atualizacao_botoes_datasheet is None:
            self._atualizacao_botoes_datasheet = self.root.after_idle(
                self.atualizar_botoes_datasheet
            )

    def atualizar_botoes_datasheet(self):
        self._atualizacao_botoes_datasheet = None
        indice_datasheet = [c[0] for c in COLS_COMPONENTES].index("datasheet")
        botoes_visiveis = set()

        for item in self.comp_tree.get_children():
            valores = self.comp_tree.item(item, "values")
            if len(valores) <= indice_datasheet or valores[indice_datasheet] != "DataSheet":
                continue
            caixa = self.comp_tree.bbox(item, "datasheet")
            if not caixa:
                continue

            x, y, largura, altura = caixa
            if x + largura <= 0 or x >= self.comp_tree.winfo_width():
                continue
            botoes_visiveis.add(item)
            botao_datasheet = self.datasheet_botoes.get(item)
            if botao_datasheet is None:
                botao_datasheet = botao(
                    self.comp_tree,
                    "DataSheet",
                    lambda ident=item: self.abrir_datasheet_item(ident),
                    "datasheet",
                )
                botao_datasheet.configure(font=("Segoe UI", 8, "bold"), padx=9, pady=1)
                self.datasheet_botoes[item] = botao_datasheet

            largura_botao = botao_datasheet.winfo_reqwidth()
            altura_botao = min(botao_datasheet.winfo_reqheight(), altura)
            botao_datasheet.place(
                x=x + (largura - largura_botao) // 2,
                y=y + (altura - altura_botao) // 2,
                width=largura_botao,
                height=altura_botao,
            )
            botao_datasheet.lift()

        for item in list(self.datasheet_botoes):
            if item not in botoes_visiveis:
                self.datasheet_botoes.pop(item).destroy()

    def carregar_movimentacoes(self):
        rows = self.db.execute(
            """SELECT m.*, c.componente, c.codigo FROM movimentacoes m
               JOIN componentes c ON c.id = m.componente_id
               ORDER BY m.id DESC LIMIT 1500"""
        ).fetchall()
        linhas = [(r["data_hora"], r["componente"], r["codigo"], r["tipo"], r["quantidade"],
                   r["saldo_anterior"], r["saldo_novo"], r["motivo"], r["responsavel"]) for r in rows]
        preencher_tree(self.mov_tree, linhas)

    def atualizar_painel(self):
        total, unidades, zero = self.db.execute(
            """SELECT COUNT(*),
                      COALESCE(SUM(quantidade), 0),
                      COALESCE(SUM(CASE WHEN quantidade = 0 THEN 1 ELSE 0 END), 0)
               FROM componentes"""
        ).fetchone()
        for w, v in zip(self.card_widgets, (total, unidades, zero)):
            w.config(text=f"{v:,}".replace(",", "."))

        rows = self.db.execute(
            """SELECT * FROM componentes
               WHERE quantidade = 0 OR (estoque_minimo > 0 AND quantidade <= estoque_minimo)
               ORDER BY CASE WHEN quantidade = 0 THEN 0 ELSE 1 END, componente LIMIT 300"""
        ).fetchall()
        linhas = [(r["componente"], r["codigo"], r["descricao"], r["quantidade"],
                   r["estoque_minimo"], r["gaveta"], r["caixa"]) for r in rows]
        preencher_tree(self.alert_tree, linhas, iids=[r["id"] for r in rows])

    def carregar_combo_contagem(self):
        ident_atual = self.cont_ids.get(self.cont_busca.get())
        rows = self.db.execute(
            "SELECT id, componente, codigo, descricao FROM componentes ORDER BY componente, codigo"
        ).fetchall()
        self.cont_ids = {
            f'{r["id"]} | {r["componente"]} | {r["codigo"]} | {r["descricao"]}': r["id"] for r in rows
        }
        self.cont_combo["values"] = list(self.cont_ids)
        rotulo_por_id = {v: k for k, v in self.cont_ids.items()}
        if ident_atual in rotulo_por_id:
            self.cont_busca.set(rotulo_por_id[ident_atual])
        elif self.cont_ids:
            self.cont_combo.current(0)
        else:
            self.cont_busca.set("")
        self.atualizar_saldo_contagem()

    def atualizar_saldo_contagem(self, _event=None):
        ident = self.cont_ids.get(self.cont_busca.get())
        r = None
        if ident is not None:
            r = self.db.execute("SELECT quantidade FROM componentes WHERE id=?", (ident,)).fetchone()
        self.cont_saldo.set(str(r["quantidade"]) if r else "—")

    # ----------------------------------------------------------------- seleção
    def id_selecionado(self, tree=None):
        tree = self.comp_tree if tree is None else tree
        sel = tree.selection()
        return int(sel[0]) if sel else None

    def duplo_clique_alerta(self, event):
        item = self.alert_tree.identify_row(event.y)
        if not item:
            return
        r = self.db.execute("SELECT * FROM componentes WHERE id=?", (int(item),)).fetchone()
        if r:
            self.form_componente(r)

    def movimentar_selecionado(self):
        ident = self.id_selecionado()
        if ident is None:
            messagebox.showinfo("Seleção", "Selecione um componente primeiro.")
            return
        self.nova_movimentacao(ident)

    def abrir_componente_selecionado(self):
        ident = self.id_selecionado()
        if ident is None:
            messagebox.showinfo("Seleção", "Selecione um componente na tabela.")
            return
        r = self.db.execute("SELECT * FROM componentes WHERE id=?", (ident,)).fetchone()
        if r:
            self.form_componente(r)

    def abrir_datasheet_item(self, ident):
        self.comp_tree.selection_set(str(ident))
        self.abrir_datasheet_selecionado()

    def abrir_datasheet_selecionado(self):
        ident = self.id_selecionado()
        if ident is None:
            messagebox.showinfo("Datasheet", "Selecione um componente na tabela.")
            return
        r = self.db.execute(
            "SELECT componente, codigo, descricao, datasheet FROM componentes WHERE id=?", (ident,)
        ).fetchone()
        url = (r["datasheet"] or "").strip()
        if url.lower().startswith(("https://", "http://")):
            comando = [sys.executable]
            if not getattr(sys, "frozen", False):
                comando.append(str(Path(__file__).resolve()))
            comando.extend((ARG_JANELA_DATASHEET, url, r["componente"]))

            try:
                subprocess.Popen(comando)
            except OSError as erro:
                messagebox.showerror(
                    "Datasheet",
                    f"Não foi possível abrir o datasheet.\n\nDetalhes: {erro}",
                )
            return
        messagebox.showinfo(
            "Datasheet não cadastrado",
            "Este componente não possui um link de datasheet cadastrado.\n"
            "Edite o componente para adicionar a URL.",
        )

    # ------------------------------------------------------------ formulários
    def novo_componente(self):
        self.form_componente()

    def form_componente(self, registro=None):
        win = self.janela_modal("Editar componente" if registro else "Novo componente",
                                690, 560, redimensionavel=(True, False))
        campos = [("componente", "Componente *"), ("codigo", "Código"), ("descricao", "Descrição"),
                  ("gaveta", "Gaveta / localização"), ("caixa", "Caixa"),
                  ("datasheet", "URL do datasheet"), ("estoque_minimo", "Estoque mínimo")]
        vars_ = {chave: tk.StringVar(value=str(registro[chave]) if registro else "")
                 for chave, _ in campos}
        if not registro:
            vars_["estoque_minimo"].set("0")

        tk.Label(win, text="Dados do componente", bg=BG, fg=TEXT,
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=22, pady=(20, 12))
        frm = tk.Frame(win, bg=PANEL, padx=20, pady=16)
        frm.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        primeiro = None
        for i, (chave, rotulo) in enumerate(campos):
            tk.Label(frm, text=rotulo, bg=PANEL, fg=TEXT).grid(row=i, column=0, sticky="w", pady=6)
            entrada = ttk.Entry(frm, textvariable=vars_[chave], width=60)
            entrada.grid(row=i, column=1, sticky="ew", padx=(12, 0), pady=6)
            primeiro = primeiro or entrada
        frm.columnconfigure(1, weight=1)
        primeiro.focus_set()

        if registro:
            tk.Label(frm,
                     text=f"Saldo atual: {registro['quantidade']} unidade(s). "
                          "Para corrigir o saldo use Contagem de estoque.",
                     bg=PANEL, fg=YELLOW, wraplength=490, justify="left").grid(
                row=len(campos), column=0, columnspan=2, sticky="w", pady=(10, 0))

        def salvar(_event=None):
            comp = vars_["componente"].get().strip()
            if not comp:
                messagebox.showwarning("Campo obrigatório", "Informe o nome do componente.", parent=win)
                return
            try:
                minimo = int(vars_["estoque_minimo"].get().strip() or 0)
            except ValueError:
                messagebox.showwarning("Valor inválido", "O estoque mínimo deve ser um número inteiro.", parent=win)
                return
            if minimo < 0:
                messagebox.showwarning("Valor inválido", "O estoque mínimo não pode ser negativo.", parent=win)
                return
            dados = (comp,
                     vars_["codigo"].get().strip(), vars_["descricao"].get().strip(),
                     vars_["gaveta"].get().strip(), vars_["datasheet"].get().strip(),
                     vars_["caixa"].get().strip(), minimo)
            try:
                with self.db:
                    if registro:
                        self.db.execute(
                            """UPDATE componentes SET componente=?, codigo=?, descricao=?, gaveta=?,
                               datasheet=?, caixa=?, estoque_minimo=?, atualizado_em=? WHERE id=?""",
                            (*dados, agora(), registro["id"]))
                    else:
                        self.db.execute(
                            """INSERT INTO componentes
                               (componente, codigo, descricao, gaveta, datasheet, caixa,
                                estoque_minimo, criado_em, atualizado_em)
                               VALUES (?,?,?,?,?,?,?,?,?)""",
                            (*dados, agora(), agora()))
            except sqlite3.IntegrityError:
                messagebox.showerror("Cadastro duplicado",
                                     "Já existe um componente com os mesmos dados principais "
                                     "(componente, código, descrição, gaveta e caixa).", parent=win)
                return
            win.destroy()
            self.atualizar_tudo()

        buttons = tk.Frame(frm, bg=PANEL)
        buttons.grid(row=len(campos) + 1, column=0, columnspan=2, sticky="e", pady=(18, 0))
        botao(buttons, "Cancelar", win.destroy, "cancelar").pack(side="right", padx=(8, 0))
        botao(buttons, "Salvar componente", salvar, "primario").pack(side="right")
        win.bind("<Return>", salvar)

    def nova_movimentacao(self, ident_inicial=None):
        rows = self.db.execute(
            "SELECT id, componente, codigo, quantidade FROM componentes ORDER BY componente, codigo"
        ).fetchall()
        if not rows:
            messagebox.showinfo("Estoque vazio", "Cadastre os componentes primeiro.")
            return

        win = self.janela_modal("Registrar movimentação", 620, 430)
        tk.Label(win, text="Entrada ou saída de estoque", bg=BG, fg=TEXT,
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=22, pady=(20, 12))
        frm = tk.Frame(win, bg=PANEL, padx=20, pady=16)
        frm.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        selecionado = tk.StringVar()
        tipo = tk.StringVar(value=TIPO_ENTRADA)
        qtd = tk.StringVar(value="1")
        motivo = tk.StringVar()
        resp = tk.StringVar()

        ids = {f'{r["id"]} | {r["componente"]} | {r["codigo"]} | saldo: {r["quantidade"]}': r["id"]
               for r in rows}
        rotulos = list(ids)
        tk.Label(frm, text="Componente", bg=PANEL, fg=TEXT).grid(row=0, column=0, sticky="w")
        combo = ttk.Combobox(frm, textvariable=selecionado, values=rotulos, state="readonly", width=67)
        combo.grid(row=0, column=1, sticky="ew", pady=8)
        indice = next((i for i, r in enumerate(rows) if r["id"] == ident_inicial), 0)
        combo.current(indice)

        tk.Label(frm, text="Tipo", bg=PANEL, fg=TEXT).grid(row=1, column=0, sticky="w", pady=8)
        ttk.Combobox(frm, textvariable=tipo, values=[TIPO_ENTRADA, TIPO_SAIDA], state="readonly",
                     width=18).grid(row=1, column=1, sticky="w", pady=8)
        tk.Label(frm, text="Quantidade", bg=PANEL, fg=TEXT).grid(row=2, column=0, sticky="w", pady=8)
        ttk.Spinbox(frm, from_=1, to=999999999, textvariable=qtd,
                    width=18).grid(row=2, column=1, sticky="w", pady=8)
        tk.Label(frm, text="Motivo / referência", bg=PANEL, fg=TEXT).grid(row=3, column=0, sticky="w", pady=8)
        ttk.Entry(frm, textvariable=motivo, width=55).grid(row=3, column=1, sticky="ew", pady=8)
        tk.Label(frm, text="Responsável", bg=PANEL, fg=TEXT).grid(row=4, column=0, sticky="w", pady=8)
        ttk.Entry(frm, textvariable=resp, width=35).grid(row=4, column=1, sticky="w", pady=8)
        frm.columnconfigure(1, weight=1)

        def salvar():
            ident = ids.get(selecionado.get())
            if ident is None:
                messagebox.showwarning("Seleção", "Selecione um componente.", parent=win)
                return
            try:
                q = int(qtd.get())
            except ValueError:
                messagebox.showwarning("Quantidade inválida", "Informe uma quantidade inteira positiva.", parent=win)
                return
            if q <= 0:
                messagebox.showwarning("Quantidade inválida", "A quantidade deve ser maior que zero.", parent=win)
                return
            saldo = self.db.execute("SELECT quantidade FROM componentes WHERE id=?", (ident,)).fetchone()["quantidade"]
            novo = saldo + q if tipo.get() == TIPO_ENTRADA else saldo - q
            if novo < 0:
                messagebox.showerror("Estoque insuficiente",
                                     f"Saldo atual: {saldo}. Não é possível retirar {q}.", parent=win)
                return
            self.registrar_movimento(ident, tipo.get(), q, saldo, novo,
                                     motivo.get().strip(), resp.get().strip())
            win.destroy()
            self.atualizar_tudo()

        bar = tk.Frame(frm, bg=PANEL)
        bar.grid(row=5, column=0, columnspan=2, sticky="e", pady=(20, 0))
        botao(bar, "Cancelar", win.destroy, "cancelar").pack(side="right", padx=(8, 0))
        botao(bar, "Salvar movimentação", salvar, "primario").pack(side="right")

    def salvar_contagem(self):
        ident = self.cont_ids.get(self.cont_busca.get())
        if ident is None:
            messagebox.showwarning("Seleção", "Selecione um componente.")
            return
        try:
            nova = int(self.cont_qtd.get())
        except ValueError:
            messagebox.showwarning("Quantidade inválida", "A quantidade deve ser um número inteiro.")
            return
        if nova < 0:
            messagebox.showwarning("Quantidade inválida", "A quantidade não pode ser negativa.")
            return
        anterior = self.db.execute("SELECT quantidade FROM componentes WHERE id=?", (ident,)).fetchone()["quantidade"]
        if nova == anterior:
            messagebox.showinfo("Sem alteração", f"A quantidade contada é igual ao saldo atual ({anterior}).")
            return
        if not messagebox.askyesno("Confirmar contagem",
                                   f"Saldo atual: {anterior}\nQuantidade contada: {nova}\n\nConfirmar ajuste?"):
            return
        motivo = self.cont_motivo.get().strip() or "Contagem física"
        self.registrar_movimento(ident, TIPO_AJUSTE, nova - anterior, anterior, nova,
                                 motivo, self.cont_resp.get().strip())
        self.atualizar_tudo()
        messagebox.showinfo("Contagem salva", "O saldo foi atualizado e o ajuste foi registrado no histórico.")

    # ------------------------------------------------------------- exportar
    def exportar_csv(self):
        caminho = filedialog.asksaveasfilename(
            title="Exportar inventário", defaultextension=".csv",
            initialfile="inventario_componentes.csv", filetypes=[("CSV", "*.csv")])
        if not caminho:
            return
        rows = self.db.execute(
            """SELECT componente, codigo, descricao, gaveta, datasheet, caixa,
                      quantidade, estoque_minimo, atualizado_em
               FROM componentes ORDER BY componente, codigo""").fetchall()
        try:
            with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Componente", "Código", "Descrição", "Gaveta", "Datasheet",
                                 "Caixa", "Quantidade", "Estoque mínimo", "Atualizado em"])
                writer.writerows(tuple(r) for r in rows)
        except OSError as e:
            messagebox.showerror("Erro ao exportar",
                                 f"Não foi possível salvar o arquivo.\n\nDetalhes: {e}")
            return
        messagebox.showinfo("Exportação concluída", f"Arquivo salvo em:\n{caminho}")

    def backup(self):
        caminho = filedialog.asksaveasfilename(
            title="Salvar cópia de segurança", defaultextension=".db",
            initialfile=f"backup_estoque_{datetime.now():%Y%m%d_%H%M}.db",
            filetypes=[("Banco SQLite", "*.db")])
        if not caminho:
            return
        if Path(caminho).resolve() == self.db_path.resolve():
            messagebox.showerror("Backup", "Escolha um arquivo diferente do banco de dados em uso.")
            return
        destino = None
        try:
            destino = sqlite3.connect(caminho)
            self.db.backup(destino)  # cópia consistente, mesmo com o banco aberto
        except (sqlite3.Error, OSError) as e:
            messagebox.showerror("Erro no backup", f"Não foi possível criar o backup.\n\nDetalhes: {e}")
            return
        finally:
            if destino is not None:
                destino.close()
        messagebox.showinfo("Backup concluído", f"Cópia de segurança salva em:\n{caminho}")

    def fechar(self):
        try:
            self.db.close()
        finally:
            self.root.destroy()


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == ARG_JANELA_DATASHEET:
        url, componente = sys.argv[2:4]
        try:
            import webview

            webview.create_window(
                f"Datasheet — {componente}",
                url=url,
                width=1080,
                height=720,
                min_size=(640, 420),
                on_top=True,
            )
            webview.start(gui="edgechromium")
        except Exception as erro:
            messagebox.showerror(
                APP_NAME,
                f"Não foi possível abrir a janela do datasheet.\n\nDetalhes: {erro}",
            )
        return

    root = tk.Tk()
    try:
        pasta = resolver_pasta_dados()
    except RuntimeError as e:
        messagebox.showerror(APP_NAME, str(e))
        root.destroy()
        return
    app = EstoqueApp(root, pasta / NOME_BANCO)
    root.protocol("WM_DELETE_WINDOW", app.fechar)
    root.mainloop()


if __name__ == "__main__":
    main()
