"""Localiza arquivos do jogo (assets) rodando do código-fonte ou empacotado."""

import os
import sys


def caminho_recurso(*partes):
    """Caminho absoluto de um recurso, independente do diretório de execução.

    Empacotado com PyInstaller (AppImage) os arquivos ficam em `sys._MEIPASS`;
    rodando com `python main.py` ficam ao lado deste arquivo.
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *partes)
