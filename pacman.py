from pacman_sprite import PacmanSprite
import pygame
from maze_generator import gerar_labirinto, PAREDE, CASA_FANTASMA

# Configurações iniciais
TILE_SIZE = 34
SCREEN_WIDTH, SCREEN_HEIGHT = TILE_SIZE * 20, TILE_SIZE * 15
FPS = 10  # Controla a velocidade da animação

ANIMACAO = {
    "up": ["closed", "half_up", "open_up"],
    "down": ["closed", "half_down", "open_down"],
    "left": ["closed", "half_left", "open_left"],
    "right": ["closed", "half_right", "open_right"],
}

DIRECOES = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}
OPOSTA = {"up": "down", "down": "up", "left": "right", "right": "left"}

# Distância (em pixels) antes/depois do centro de um cruzamento em que a curva
# ainda é aceita. Dentro dessa janela o Pac-Man "corta" a quina suavemente.
TOLERANCIA_CURVA = 8

# Quantos frames do jogo (60 FPS) cada quadro da boca fica na tela.
FRAMES_POR_QUADRO_ANIMACAO = 4

# O mapa é gerado dinamicamente pelo maze_generator
# Usamos este como fallback ou para testes
MAPA = gerar_labirinto(4, 3)

# Variável global para compartilhar a direção do Pacman com os fantasmas
direcao_pacman_global = "right"


class Pacman:
    """Pac-Man que anda pelo centro dos corredores.

    O movimento é baseado em tiles: a posição sempre fica alinhada ao centro da
    "faixa" do corredor no eixo perpendicular ao movimento. As curvas só
    acontecem perto do centro de um tile (com uma pequena tolerância) e a
    parada diante de uma parede é exata. Assim ele nunca fica entalado numa
    quina, mesmo que a tecla seja apertada antes ou depois do cruzamento.
    """

    def __init__(self, x, y, sprites: PacmanSprite):
        self.x = x
        self.y = y
        self.sprites = sprites
        self.direcao = "right"
        self.anim_index = 0
        self.velocidade = 12
        self.pausa_movimento = 0
        self.tempo_animacao = 0
        self.direcao_desejada = "right"
        self.pontos = 0
        self.moveu = False
        self._teclas_anteriores = set()

    # ------------------------------------------------------------------ estado
    def reposicionar(self, x, y):
        """Volta ao ponto inicial (nova vida, novo nível ou reinício)."""
        global direcao_pacman_global
        self.x = x
        self.y = y
        self.direcao = "right"
        self.direcao_desejada = "right"
        self.pausa_movimento = 0
        self.anim_index = 0
        self.tempo_animacao = 0
        self.moveu = False
        direcao_pacman_global = self.direcao

    # ------------------------------------------------------------------- input
    def processar_input(self, teclas):
        """Lê as setas. A tecla recém-pressionada sempre tem prioridade.

        A direção desejada permanece guardada (buffer) até a curva ficar
        possível, como no jogo original.
        """
        mapeamento = (
            (pygame.K_UP, "up"),
            (pygame.K_DOWN, "down"),
            (pygame.K_LEFT, "left"),
            (pygame.K_RIGHT, "right"),
        )
        pressionadas = [direcao for tecla, direcao in mapeamento if teclas[tecla]]
        novas = [d for d in pressionadas if d not in self._teclas_anteriores]
        if novas:
            self.direcao_desejada = novas[-1]
        self._teclas_anteriores = set(pressionadas)

    # --------------------------------------------------------------- geometria
    def _centro(self):
        return self.x + TILE_SIZE / 2, self.y + TILE_SIZE / 2

    def _tile_atual(self):
        centro_x, centro_y = self._centro()
        return int(centro_x // TILE_SIZE), int(centro_y // TILE_SIZE)

    @staticmethod
    def _centro_do_tile(col, row):
        return col * TILE_SIZE + TILE_SIZE / 2, row * TILE_SIZE + TILE_SIZE / 2

    @staticmethod
    def _linha_de_portal(mapa, row):
        return mapa[row][0] != PAREDE and mapa[row][len(mapa[0]) - 1] != PAREDE

    def _tile_livre(self, col, row, mapa):
        """O Pac-Man pode ocupar o tile? (colunas -1 e largura são o túnel)."""
        altura = len(mapa)
        largura = len(mapa[0])
        if not 0 <= row < altura:
            return False
        if col < 0 or col >= largura:
            return -1 <= col <= largura and self._linha_de_portal(mapa, row)
        return mapa[row][col] not in (PAREDE, CASA_FANTASMA)

    def _pode_ir(self, col, row, direcao, mapa):
        """Dá para sair do tile (col, row) na direção indicada?"""
        dx, dy = DIRECOES[direcao]
        largura = len(mapa[0])
        if dy and not 0 <= col < largura:
            return False  # dentro do túnel só se anda na horizontal
        return self._tile_livre(col + dx, row + dy, mapa)

    def pode_mover_para(self, direcao, mapa=None):
        """Indica se o Pac-Man consegue andar na direção a partir da posição atual."""
        if mapa is None:
            mapa = MAPA
        col, row = self._tile_atual()
        dx, dy = DIRECOES[direcao]
        centro_x, centro_y = self._centro()
        tile_x, tile_y = self._centro_do_tile(col, row)
        if (tile_x - centro_x) * dx + (tile_y - centro_y) * dy > 0:
            return True  # ainda há espaço até o centro do tile
        return self._pode_ir(col, row, direcao, mapa)

    # --------------------------------------------------------------- movimento
    def mover(self, mapa=None):
        global direcao_pacman_global

        if mapa is None:
            mapa = MAPA

        self.moveu = False
        if self.pausa_movimento > 0:
            self.pausa_movimento -= 1
            return

        self._aplicar_portal(mapa)
        self._tentar_virar(mapa)
        self._avancar(self.velocidade, mapa)
        self._aplicar_portal(mapa)

        # Os fantasmas usam esta direção para prever o caminho do Pac-Man
        direcao_pacman_global = self.direcao

    def _tentar_virar(self, mapa):
        desejada = self.direcao_desejada
        if desejada == self.direcao:
            return

        col, row = self._tile_atual()
        centro_x, centro_y = self._centro()
        tile_x, tile_y = self._centro_do_tile(col, row)

        if desejada == OPOSTA[self.direcao]:
            # Inverter é sempre permitido quando há por onde andar
            if self.pode_mover_para(desejada, mapa):
                self.direcao = desejada
            return

        # Curva de 90°: precisa estar perto do centro do tile e ter saída livre
        dx, dy = DIRECOES[self.direcao]
        falta_ate_centro = (tile_x - centro_x) * dx + (tile_y - centro_y) * dy
        if abs(falta_ate_centro) <= TOLERANCIA_CURVA and self._pode_ir(
            col, row, desejada, mapa
        ):
            self.direcao = desejada

    def _avancar(self, passo, mapa):
        dx, dy = DIRECOES[self.direcao]
        col, row = self._tile_atual()
        centro_x, centro_y = self._centro()
        tile_x, tile_y = self._centro_do_tile(col, row)

        if self._pode_ir(col, row, self.direcao, mapa):
            avanco = passo
        else:
            # Parede à frente: anda no máximo até o centro do tile (parada exata)
            falta_ate_centro = (tile_x - centro_x) * dx + (tile_y - centro_y) * dy
            avanco = max(0.0, min(passo, falta_ate_centro))

        self.x += dx * avanco
        self.y += dy * avanco

        # Puxa suavemente para o centro da faixa do corredor (eixo perpendicular)
        if dx:
            erro = tile_y - centro_y
            self.y += max(-passo, min(passo, erro))
        else:
            erro = tile_x - centro_x
            self.x += max(-passo, min(passo, erro))

        self.moveu = avanco > 0

    def _aplicar_portal(self, mapa):
        """Teletransporte do túnel lateral, sem perder subpixels."""
        largura_px = len(mapa[0]) * TILE_SIZE
        periodo = largura_px + TILE_SIZE  # túnel + uma coluna invisível
        if self.direcao == "left" and self.x <= -TILE_SIZE:
            self.x += periodo
        elif self.direcao == "right" and self.x >= largura_px:
            self.x -= periodo

        altura_px = len(mapa) * TILE_SIZE
        self.y = max(0, min(self.y, altura_px - TILE_SIZE))

    # ---------------------------------------------------------------- desenho
    def atualizar_animacao(self):
        """Avança a boca apenas enquanto o Pac-Man realmente se move."""
        if not self.moveu:
            return
        self.tempo_animacao += 1
        if self.tempo_animacao >= FRAMES_POR_QUADRO_ANIMACAO:
            self.tempo_animacao = 0
            self.anim_index = (self.anim_index + 1) % len(ANIMACAO[self.direcao])

    def definir_velocidade(self, velocidade):
        self.velocidade = velocidade

    def pausar(self, frames):
        self.pausa_movimento = max(self.pausa_movimento, frames)

    def desenhar(self, screen):
        frame_name = ANIMACAO[self.direcao][self.anim_index]
        frame = self.sprites.get_frame(frame_name)
        screen.blit(frame, (self.x, self.y))
