from pacman_sprite import PacmanSprite
import pygame
import os
from maze_generator import gerar_labirinto

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

# O mapa é gerado dinamicamente pelo maze_generator
# Usamos este como fallback ou para testes
MAPA = gerar_labirinto(4, 3)

# Variável global para compartilhar a direção do Pacman com os fantasmas
direcao_pacman_global = "right"

class Pacman:
    def __init__(self, x, y, sprites: PacmanSprite):
        self.x = x
        self.y = y
        self.sprites = sprites
        self.direcao = "right"
        self.anim_index = 0
        self.velocidade = 12
        self.tempo_animacao = 0
        self.direcao_desejada = "right"
        self.pontos = 0

    def processar_input(self, teclas):
        global direcao_pacman_global
        
        if teclas[pygame.K_UP]:
            self.direcao_desejada = "up"
        elif teclas[pygame.K_DOWN]:
            self.direcao_desejada = "down"
        elif teclas[pygame.K_LEFT]:
            self.direcao_desejada = "left"
        elif teclas[pygame.K_RIGHT]:
            self.direcao_desejada = "right"
            
        # Atualizar a variável global quando a direção mudar
        if self.direcao_desejada == self.direcao:
            direcao_pacman_global = self.direcao

    def pode_mover_para(self, direcao, mapa=None):
        # Use o mapa fornecido ou o mapa padrão
        if mapa is None:
            mapa = MAPA
            
        # Inicializar valores padrão
        nova_x = self.x
        nova_y = self.y
        
        # Hitbox menor para o Pac-Man (para que ele possa passar por corredores mais estreitos)
        margem = TILE_SIZE // 4  # Margem para tornar a hitbox do Pac-Man menor
        hitbox_tamanho = TILE_SIZE - 2 * margem
        
        # Centro do Pac-Man
        centro_x = self.x + TILE_SIZE // 2
        centro_y = self.y + TILE_SIZE // 2
        
        # Calcular nova posição conforme a direção
        if direcao == "up":
            nova_y = self.y - self.velocidade
        elif direcao == "down":
            nova_y = self.y + self.velocidade
        elif direcao == "left":
            nova_x = self.x - self.velocidade
        elif direcao == "right":
            nova_x = self.x + self.velocidade
        
        # Pontos de colisão (usando uma hitbox menor para passar em corredores mais estreitos)
        pontos_colisao = [
            (nova_x + margem, nova_y + margem),  # Superior esquerdo da hitbox
            (nova_x + margem + hitbox_tamanho, nova_y + margem),  # Superior direito da hitbox
            (nova_x + margem, nova_y + margem + hitbox_tamanho),  # Inferior esquerdo da hitbox
            (nova_x + margem + hitbox_tamanho, nova_y + margem + hitbox_tamanho)  # Inferior direito da hitbox
        ]
        
        # Verificar colisão nos quatro cantos da hitbox
        for ponto_x, ponto_y in pontos_colisao:
            col = ponto_x // TILE_SIZE
            row = ponto_y // TILE_SIZE
            
            # Verificar limites do mapa
            if not (0 <= row < len(mapa) and 0 <= col < len(mapa[0])):
                continue  # Pular para o próximo ponto se estiver fora dos limites
                
            # Verificar colisões
            if mapa[row][col] == 1:  # Parede
                return False  # Não pode mover
            if mapa[row][col] == 3:  # Casa dos fantasmas
                # Só permite passar pela porta designada
                return False
                
        # Se chegou aqui, não colidiu com nenhuma parede
        return True

    def mover(self, mapa=None):
        # Use o mapa fornecido ou o mapa padrão
        if mapa is None:
            mapa = MAPA
        
        # Centralizar o pacman nos corredores
        self.centralizar_nos_corredores()
            
        # Tenta mudar de direção se possível
        if self.pode_mover_para(self.direcao_desejada, mapa):
            self.direcao = self.direcao_desejada
            
            # Atualiza a variável global quando a direção realmente mudar
            global direcao_pacman_global
            direcao_pacman_global = self.direcao

        if self.pode_mover_para(self.direcao, mapa):
            if self.direcao == "up":
                self.y -= self.velocidade
            elif self.direcao == "down":
                self.y += self.velocidade
            elif self.direcao == "left":
                self.x -= self.velocidade
            elif self.direcao == "right":
                self.x += self.velocidade
                
        # Verificar se passou pelos limites da tela (portal tipo Pac-Man)
        largura_tela = len(mapa[0]) * TILE_SIZE
        altura_tela = len(mapa) * TILE_SIZE
        
        # Portais horizontais (esquerda/direita)
        if self.x < -TILE_SIZE:
            self.x = largura_tela - self.velocidade
        elif self.x >= largura_tela:
            self.x = 0
            
        # Portais verticais (cima/baixo)
        if self.y < -TILE_SIZE:
            self.y = altura_tela - self.velocidade
        elif self.y >= altura_tela:
            self.y = 0
    
    def centralizar_nos_corredores(self):
        """Ajuda a centralizar o Pac-Man nos corredores para evitar colisões com paredes."""
        # Se estamos se movendo horizontalmente, ajuste a posição vertical
        if self.direcao in ["left", "right"]:
            # Calcular o centro do tile em que estamos
            tile_y = (self.y // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
            # Distância do centro do Pac-Man ao centro do tile
            dist_y = abs(self.y + TILE_SIZE // 2 - tile_y)
            
            # Ser mais sensível ao centralizar (para corredores mais estreitos)
            if dist_y < self.velocidade * 2:
                # Centralizar gradualmente para um movimento mais suave
                ajuste = min(self.velocidade // 2, abs(self.y + TILE_SIZE // 2 - tile_y))
                if self.y + TILE_SIZE // 2 > tile_y:
                    self.y -= ajuste
                elif self.y + TILE_SIZE // 2 < tile_y:
                    self.y += ajuste
        
        # Se estamos se movendo verticalmente, ajuste a posição horizontal
        elif self.direcao in ["up", "down"]:
            # Calcular o centro do tile em que estamos
            tile_x = (self.x // TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
            # Distância do centro do Pac-Man ao centro do tile
            dist_x = abs(self.x + TILE_SIZE // 2 - tile_x)
            
            # Ser mais sensível ao centralizar
            if dist_x < self.velocidade * 2:
                # Centralizar gradualmente para um movimento mais suave
                ajuste = min(self.velocidade // 2, abs(self.x + TILE_SIZE // 2 - tile_x))
                if self.x + TILE_SIZE // 2 > tile_x:
                    self.x -= ajuste
                elif self.x + TILE_SIZE // 2 < tile_x:
                    self.x += ajuste

    def atualizar_animacao(self):
        self.anim_index = (self.anim_index + 1) % len(ANIMACAO[self.direcao])

    def desenhar(self, screen):
        frame_name = ANIMACAO[self.direcao][self.anim_index]
        frame = self.sprites.get_frame(frame_name)
        screen.blit(frame, (self.x, self.y))