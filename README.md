# Estoque de Componentes

Aplicativo desktop para Windows para controle de estoque de componentes, com interface Tkinter e banco de dados SQLite local.

## Requisitos

- Windows
- Python 3
- Microsoft Edge instalado para abrir os links de datasheets dentro do aplicativo

## Executar

No PowerShell, na pasta do projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py estoque_componentes.py
```

O aplicativo cria e mantém o banco de dados local na pasta `EstoqueComponentes`. Esse banco não é versionado pelo Git.

## Estrutura

- `estoque_componentes.py`: código principal do aplicativo.
- `assets/robo_jp.png`: imagem usada pela interface.
- `EstoqueComponentes.spec`: configuração do PyInstaller para gerar o executável.
- `requirements.txt`: dependências Python.
