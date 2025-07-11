import os
import pygame
import sys
import glob
import random
from pacman import Pacman
import pacman_sprite
from ghost import Ghost
from maze_generator import gerar_labirinto, CASA_FANTASMA
TILE_SIZE = 34
SCREEN_WIDTH, SCREEN_HEIGHT = TILE_SIZE * 20, TILE_SIZE * 15
FPS = 10  # Controla a velocidade da animação

# Níveis do jogo (começa no nível 1)
nivel_atual = 1

# Gera um labirinto procedural para o nível atual
MAPA = gerar_labirinto(4, 3, nivel_atual)

def main():
    global nivel_atual, MAPA
    pygame.init()
    screen = pygame.display.set_mode((768, 768))
    pygame.display.set_caption("PacDevs")
    clock = pygame.time.Clock()
    pacman_sprites = pacman_sprite.PacmanSprite("assets/pacman")

    # Posicionar o Pacman em um corredor válido
    start_pos = encontrar_posicao_inicial(MAPA)
    pacman = Pacman(x=start_pos[0], y=start_pos[1], sprites=pacman_sprites)
    
    # Pontuação do jogador
    pontuacao = 0
    
    # Cópia do mapa para controlar pontos coletados
    mapa_atual = [linha[:] for linha in MAPA]

    # Criar fantasmas para o jogo
    fantasmas = criar_fantasmas(MAPA)

    rodando = True
    while rodando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False

        teclas = pygame.key.get_pressed()
        pacman.processar_input(teclas)
        pacman.mover(MAPA)
        pacman.atualizar_animacao()
        
        # Verificar coleta de pontos - usando o centro do Pac-Man
        centro_x = pacman.x + TILE_SIZE // 2
        centro_y = pacman.y + TILE_SIZE // 2
        col = centro_x // TILE_SIZE
        row = centro_y // TILE_SIZE
        
        if 0 <= row < len(mapa_atual) and 0 <= col < len(mapa_atual[0]):
            if mapa_atual[row][col] == 2:  # É um ponto comum
                mapa_atual[row][col] = 0   # Remove o ponto
                pontuacao += 10            # Incrementa pontuação
            elif mapa_atual[row][col] == 4:  # É um power pellet
                mapa_atual[row][col] = 0   # Remove o power pellet
                pontuacao += 50            # Power pellets valem mais pontos
                
                # Quando o Pacman come um power pellet, os fantasmas ficam vulneráveis
                for fantasma in fantasmas:
                    fantasma.tornar_vulneravel(500)  # Vulnerável por 500 frames
                
        # Mover fantasmas e verificar colisões
        vidas_perdidas = False
        for fantasma in fantasmas:
            fantasma.mover(pacman.x, pacman.y, MAPA)
            resultado_colisao = fantasma.verificar_colisao_pacman(pacman.x, pacman.y)
            
            if resultado_colisao == 1:  # Colisão normal - Pacman perde vida
                vidas_perdidas = True
                # Resetar posição do Pacman
                start_pos = encontrar_posicao_inicial(MAPA)
                pacman.x, pacman.y = start_pos
                
                # Manter os fantasmas onde estão, apenas devolvê-los ao estado normal
                # Isso é mais realista e evita problemas com fantasmas presos
                for f in fantasmas:
                    f.voltar_ao_normal()
                break
                
            elif resultado_colisao == 2:  # Fantasma é comido
                fantasma.foi_comido()
                pontuacao += 200  # Pontuação por comer um fantasma
        
        # Verificar colisões entre fantasmas
        fantasmas_colidiram = set()  # Conjunto para rastrear quais fantasmas já colidiram
        
        # Otimização: só verificar colisões se tivermos mais de um fantasma
        if len(fantasmas) > 1:
            for i, fantasma1 in enumerate(fantasmas):
                for j, fantasma2 in enumerate(fantasmas[i+1:], i+1):  # Evitar verificar o mesmo par duas vezes
                    # Ignorar se algum deles já colidiu neste frame ou está em estado COMIDO
                    if (i in fantasmas_colidiram or j in fantasmas_colidiram or 
                        fantasma1.estado == Ghost.COMIDO or fantasma2.estado == Ghost.COMIDO):
                        continue
                    
                    # Otimização: pré-verificação de distância para evitar cálculos desnecessários
                    # Se os fantasmas estão longe um do outro, não precisamos verificar colisão
                    dist_aprox = abs(fantasma1.x - fantasma2.x) + abs(fantasma1.y - fantasma2.y)
                    if dist_aprox > TILE_SIZE * 1.5:  # Distância de Manhattan como filtro rápido
                        continue
                    
                    # Verificar colisão precisa
                    if fantasma1.verificar_colisao_com_fantasma(fantasma2):
                        # Ambos os fantasmas mudam de direção
                        fantasma1.reagir_a_colisao(MAPA)
                        fantasma2.reagir_a_colisao(MAPA)
                        
                        # Adicionar ao conjunto de fantasmas que já colidiram
                        fantasmas_colidiram.add(i)
                        fantasmas_colidiram.add(j)
                
        # Verificar se todos os pontos foram coletados
        pontos_restantes = 0
        for linha in mapa_atual:
            pontos_restantes += linha.count(2) + linha.count(4)
            
        if pontos_restantes == 0:
            # Avançar para o próximo nível
            nivel_atual += 1
            
            # Gerar novo mapa procedural baseado no novo nível
            MAPA = gerar_labirinto(4, 3, nivel_atual)
            mapa_atual = [linha[:] for linha in MAPA]
            
            # Posicionar o Pacman em um novo ponto inicial
            start_pos = encontrar_posicao_inicial(MAPA)
            pacman.x, pacman.y = start_pos
            
            # Criar novos fantasmas para o novo nível
            fantasmas = criar_fantasmas(MAPA)

        screen.fill((0, 0, 0))

        # Desenhar o mapa com paredes e pontos estilo Pac-Man clássico
        for row in range(len(mapa_atual)):
            for col in range(len(mapa_atual[0])):
                tile_x = col * TILE_SIZE
                tile_y = row * TILE_SIZE
                
                if mapa_atual[row][col] == 1:  # Parede
                    # Desenhar paredes mais finas, estilo Pac-Man
                    margem = TILE_SIZE // 6  # Margem para paredes mais finas
                    
                    # Verificar paredes adjacentes para conectar visualmente
                    tem_parede_acima = row > 0 and mapa_atual[row-1][col] == 1
                    tem_parede_abaixo = row < len(mapa_atual)-1 and mapa_atual[row+1][col] == 1
                    tem_parede_esquerda = col > 0 and mapa_atual[row][col-1] == 1
                    tem_parede_direita = col < len(mapa_atual[0])-1 and mapa_atual[row][col+1] == 1
                    
                    # Cor de parede azul escuro (como no Pac-Man original)
                    cor_parede = (0, 0, 200)
                    
                    # Desenhar o bloco central
                    pygame.draw.rect(screen, cor_parede, 
                                   (tile_x + margem, tile_y + margem, 
                                    TILE_SIZE - 2*margem, TILE_SIZE - 2*margem))
                    
                    # Conectar com paredes adjacentes
                    if tem_parede_acima:
                        pygame.draw.rect(screen, cor_parede, 
                                       (tile_x + margem, tile_y, 
                                        TILE_SIZE - 2*margem, margem))
                    if tem_parede_abaixo:
                        pygame.draw.rect(screen, cor_parede, 
                                       (tile_x + margem, tile_y + TILE_SIZE - margem, 
                                        TILE_SIZE - 2*margem, margem))
                    if tem_parede_esquerda:
                        pygame.draw.rect(screen, cor_parede, 
                                       (tile_x, tile_y + margem, 
                                        margem, TILE_SIZE - 2*margem))
                    if tem_parede_direita:
                        pygame.draw.rect(screen, cor_parede, 
                                       (tile_x + TILE_SIZE - margem, tile_y + margem, 
                                        margem, TILE_SIZE - 2*margem))
                        
                elif mapa_atual[row][col] == 2:  # Ponto comum
                    # Pontos menores e mais brilhantes
                    pygame.draw.circle(screen, (255, 255, 0), 
                                     (tile_x + TILE_SIZE//2, tile_y + TILE_SIZE//2), 
                                     TILE_SIZE//10)
                    
                elif mapa_atual[row][col] == 3:  # Casa dos fantasmas
                    # Porta da casa dos fantasmas em vermelho escuro
                    pygame.draw.rect(screen, (150, 0, 0), 
                                   (tile_x, tile_y, TILE_SIZE, TILE_SIZE))
                    
                elif mapa_atual[row][col] == 4:  # Power pellet
                    # Power pellets pulsantes (animação simples)
                    tamanho = TILE_SIZE // 3.5 + (TILE_SIZE // 20) * abs(pygame.time.get_ticks() % 1000 - 500) / 500
                    pygame.draw.circle(screen, (255, 255, 255), 
                                     (tile_x + TILE_SIZE//2, tile_y + TILE_SIZE//2), 
                                     tamanho)

        # Desenhar fantasmas
        for fantasma in fantasmas:
            fantasma.desenhar(screen)
            
        # Desenhar o Pacman por último para que fique por cima dos fantasmas quando os come
        pacman.desenhar(screen)
        
        # Exibir informações de nível e pontuação
        exibir_informacoes(screen, nivel_atual, pontuacao)

        pygame.display.flip()
        clock.tick(FPS)

def exibir_informacoes(screen, nivel, pontuacao):
    """Exibe informações de nível e pontuação na tela."""
    # Configurar fonte
    fonte = pygame.font.SysFont('Arial', 24, bold=True)
    
    # Informação de nível
    texto_nivel = fonte.render(f'Nível: {nivel}', True, (255, 255, 255))
    screen.blit(texto_nivel, (20, 20))
    
    # Informação de pontuação
    texto_pontuacao = fonte.render(f'Pontuação: {pontuacao}', True, (255, 255, 255))
    screen.blit(texto_pontuacao, (20, 50))

def encontrar_posicao_inicial(mapa):
    """Encontra uma posição válida (corredor) para o Pacman começar."""
    # No Pac-Man original, ele começa em uma posição específica na parte inferior central do mapa
    altura = len(mapa)
    largura = len(mapa[0])
    
    # Posição clássica do Pac-Man (pouco abaixo do centro do mapa, similar ao jogo original)
    posicao_y_preferida = altura * 3 // 4  # 3/4 da altura do mapa
    centro_x = largura // 2
    
    # Verificar a posição preferida
    if 0 <= posicao_y_preferida < altura and mapa[posicao_y_preferida][centro_x] in [0, 2]:
        # Retorna posição preferida do jogo original (centralizada no tile)
        return centro_x * TILE_SIZE, posicao_y_preferida * TILE_SIZE
    
    # Se a posição preferida não funcionar, verificar um pouco acima e abaixo
    for offset in range(1, 5):
        if posicao_y_preferida - offset >= 0 and mapa[posicao_y_preferida - offset][centro_x] in [0, 2]:
            return centro_x * TILE_SIZE, (posicao_y_preferida - offset) * TILE_SIZE
        if posicao_y_preferida + offset < altura and mapa[posicao_y_preferida + offset][centro_x] in [0, 2]:
            return centro_x * TILE_SIZE, (posicao_y_preferida + offset) * TILE_SIZE
            
    # Opção de backup: verificar o portal lateral
    meio_y = altura // 2
    
    # Verificar lado esquerdo primeiro (portal)
    for x in range(3):
        if mapa[meio_y][x] in [0, 2]:  # Corredor ou ponto
            return x * TILE_SIZE, meio_y * TILE_SIZE
    
    # Verificar lado direito (portal)
    for x in range(largura - 3, largura):
        if mapa[meio_y][x] in [0, 2]:
            return x * TILE_SIZE, meio_y * TILE_SIZE
    
    # Se ainda não encontrou, procura por qualquer corredor
    for row in range(altura):
        for col in range(largura):
            if mapa[row][col] in [0, 2]:  # Corredor ou ponto
                return col * TILE_SIZE, row * TILE_SIZE
    
    # Se não encontrar, retorna posição padrão
    return TILE_SIZE, TILE_SIZE

def encontrar_posicao_fantasma(mapa):
    """Encontra uma posição válida para um fantasma dentro da casa dos fantasmas."""
    altura = len(mapa)
    largura = len(mapa[0])
    
    # Procurar por células marcadas como CASA_FANTASMA
    posicoes_casa = []
    for y in range(altura):
        for x in range(largura):
            if mapa[y][x] == CASA_FANTASMA:
                posicoes_casa.append((x, y))
    
    # Se encontrou posições da casa, escolher uma aleatoriamente
    if posicoes_casa:
        x, y = random.choice(posicoes_casa)
        return x * TILE_SIZE, y * TILE_SIZE
    
    # Se não encontrou, retornar o centro do mapa
    return (largura // 2) * TILE_SIZE, (altura // 2) * TILE_SIZE

def criar_fantasmas(mapa):
    """Cria os fantasmas para o jogo usando os sprites disponíveis."""
    fantasmas = []
    
    # Lista de todos os arquivos de sprite de fantasmas
    sprite_paths = glob.glob("assets/ghosts/*.png")
    
    # Lista de personalidades para os fantasmas
    personalidades = ["perseguidor", "emboscador", "vagante", "imprevisível"]

    # Criar um fantasma para cada sprite disponível (até 5)
    for i, sprite_path in enumerate(sprite_paths[:5]):
        # Encontrar uma posição inicial para o fantasma na casa dos fantasmas
        pos_x, pos_y = encontrar_posicao_fantasma(mapa)
        
        # Pequeno deslocamento para evitar sobreposição exata
        pos_x += random.randint(-5, 5)
        pos_y += random.randint(-5, 5)
        
        # Criar fantasma com personalidade específica
        personalidade = personalidades[i % len(personalidades)]
        fantasma = Ghost(pos_x, pos_y, sprite_path, TILE_SIZE, personalidade)
        
        # Adicionar à lista
        fantasmas.append(fantasma)
    
    return fantasmas

def encerrar():
    pygame.quit()

if __name__ == "__main__":
    try:
        main()
    finally:
        encerrar()