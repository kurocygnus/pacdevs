import glob
import random

import pygame

import pacman_sprite
from ghost import Ghost
from maze_generator import gerar_labirinto, CASA_FANTASMA, PAREDE
from pacman import Pacman
from recursos import caminho_recurso
from visual import (
    LARGURA_PAINEL,
    atualizar_popups,
    desenhar_tela,
    exibir_game_over,
    exibir_informacoes,
    novo_popup,
)

TILE_SIZE = 34
SCREEN_WIDTH, SCREEN_HEIGHT = TILE_SIZE * 20, TILE_SIZE * 15
FPS = 60  # Controla a velocidade da animação
VELOCIDADE_BASE_FPS = 10
VIDAS_INICIAIS = 3
PONTOS_FANTASMAS_COMIDOS = (200, 400, 800, 1600)
PONTOS_VIDA_EXTRA = 10000
FRUIT_VALUES = (100, 300, 500, 700, 1000, 2000, 3000, 5000)

# Níveis do jogo (começa no nível 1)
nivel_atual = 1

# Gera um labirinto procedural para o nível atual
MAPA = gerar_labirinto(4, 3, nivel_atual)


def contar_pontos(mapa):
    """Conta pontos e energizers restantes no mapa."""
    return sum(linha.count(2) + linha.count(4) for linha in mapa)


def cronograma_modos(nivel):
    """Tempos clássicos adaptados para FPS do projeto."""
    if nivel == 1:
        segundos = (7, 20, 7, 20, 5, 20, 5, None)
    elif nivel <= 4:
        segundos = (7, 20, 7, 20, 5, 1033, 1 / 60, None)
    else:
        segundos = (5, 20, 5, 20, 5, 1037, 1 / 60, None)
    modos = (
        Ghost.DISPERSAR,
        Ghost.PERSEGUIR,
        Ghost.DISPERSAR,
        Ghost.PERSEGUIR,
        Ghost.DISPERSAR,
        Ghost.PERSEGUIR,
        Ghost.DISPERSAR,
        Ghost.PERSEGUIR,
    )
    return list(zip(modos, segundos))


def modo_por_indice(nivel, indice):
    return cronograma_modos(nivel)[min(indice, 7)][0]


def atualizar_modo_global(nivel, indice, frames_modo, modo_atual):
    cronograma = cronograma_modos(nivel)
    _, segundos = cronograma[min(indice, len(cronograma) - 1)]
    if segundos is None or frames_modo < max(1, round(segundos * FPS)):
        return indice, modo_atual
    novo_indice = min(indice + 1, len(cronograma) - 1)
    return novo_indice, cronograma[novo_indice][0]


def duracao_frightened(nivel):
    if nivel == 1:
        segundos = 6
    elif nivel <= 4:
        segundos = 5
    elif nivel <= 8:
        segundos = 3
    elif nivel <= 18:
        segundos = 1
    else:
        segundos = 0
    return segundos * FPS


def velocidades_por_nivel(nivel):
    if nivel == 1:
        velocidades = (10, 6, 3, 8, 3)
    elif nivel <= 4:
        velocidades = (11, 5, 3, 8, 2)
    elif nivel <= 20:
        velocidades = (12, 6, 3, 8, 3)
    else:
        velocidades = (11, 6, 0, 8, 3)
    escala = VELOCIDADE_BASE_FPS / FPS
    return tuple(max(0, velocidade * escala) for velocidade in velocidades)


def aplicar_velocidades(nivel, pacman, fantasmas):
    pac_speed, ghost_speed, scared_speed, eyes_speed, tunnel_speed = velocidades_por_nivel(
        nivel
    )
    pacman.definir_velocidade(pac_speed)
    for fantasma in fantasmas:
        fantasma.definir_velocidades(
            normal=ghost_speed,
            assustado=scared_speed,
            comido=eyes_speed,
            tunel=tunnel_speed,
        )


def aplicar_modo_global(fantasmas, modo, inverter):
    for fantasma in fantasmas:
        fantasma.definir_modo_global(modo, inverter)


def algum_fantasma_assustado(fantasmas):
    return any(fantasma.estado == Ghost.VULNERAVEL for fantasma in fantasmas)


def limites_saida_fantasmas(nivel, quantidade, apos_morte=False):
    if apos_morte:
        limites_base = [0, 7, 17, 32, 45, 60]
    elif nivel == 1:
        limites_base = [0, 0, 30, 60, 90, 120]
    elif nivel == 2:
        limites_base = [0, 0, 0, 50, 75, 100]
    else:
        limites_base = [0] * quantidade
    if quantidade <= len(limites_base):
        return limites_base[:quantidade]
    extras = [limites_base[-1] + 30 * i for i in range(1, quantidade - 5)]
    return limites_base + extras


def liberar_fantasmas_por_pontos(fantasmas, nivel, pontos_comidos, apos_morte=False):
    limites = limites_saida_fantasmas(nivel, len(fantasmas), apos_morte)
    for fantasma, limite in zip(fantasmas, limites):
        if pontos_comidos >= limite:
            fantasma.liberar_da_casa()


def liberar_fantasma_por_ociosidade(fantasmas, nivel, frames_sem_comer):
    limite = (3 if nivel >= 5 else 4) * FPS
    if frames_sem_comer < limite:
        return frames_sem_comer
    for fantasma in fantasmas:
        if fantasma.atraso_saida > 0:
            fantasma.liberar_da_casa()
            return 0
    return frames_sem_comer


def posicao_fruta(mapa):
    """Tile livre logo abaixo da casa dos fantasmas (onde a fruta nasce no arcade).

    A fruta precisa ficar num lugar que o Pac-Man consiga alcançar, ou seja,
    fora da casa e fora das paredes.
    """
    casas = [
        (col, row)
        for row, linha in enumerate(mapa)
        for col, celula in enumerate(linha)
        if celula == CASA_FANTASMA
    ]
    if casas:
        col = round(sum(c for c, _ in casas) / len(casas))
        row = max(r for _, r in casas) + 1
        referencia = (col, row)
    else:
        referencia = (len(mapa[0]) // 2, len(mapa) // 2)

    melhor = None
    melhor_distancia = None
    for row, linha in enumerate(mapa):
        for col, celula in enumerate(linha):
            if celula in (PAREDE, CASA_FANTASMA):
                continue
            distancia = (col - referencia[0]) ** 2 + (row - referencia[1]) ** 2
            if melhor_distancia is None or distancia < melhor_distancia:
                melhor, melhor_distancia = (col, row), distancia
    return melhor


def gatilhos_fruta(total_pontos):
    if total_pontos >= 170:
        return (70, 170)
    return (max(1, total_pontos // 3), max(2, (total_pontos * 2) // 3))


def atualizar_fruta(fruta, frutas_disparadas, pontos_comidos, total_pontos, nivel, mapa):
    if fruta is not None:
        fruta["frames"] -= 1
        return fruta if fruta["frames"] > 0 else None

    for gatilho in gatilhos_fruta(total_pontos):
        if pontos_comidos >= gatilho and gatilho not in frutas_disparadas:
            frutas_disparadas.add(gatilho)
            col, row = posicao_fruta(mapa)
            return {
                "col": col,
                "row": row,
                "valor": FRUIT_VALUES[min(nivel - 1, len(FRUIT_VALUES) - 1)],
                "frames": random.randint(9 * FPS, 10 * FPS),
            }
    return None


def main():
    global nivel_atual, MAPA
    pygame.init()
    screen = pygame.display.set_mode(
        (len(MAPA[0]) * TILE_SIZE + LARGURA_PAINEL, len(MAPA) * TILE_SIZE)
    )
    pygame.display.set_caption("PacDevs")
    clock = pygame.time.Clock()
    pacman_sprites = pacman_sprite.PacmanSprite(caminho_recurso("assets", "pacman"))

    # Posicionar o Pacman em um corredor válido
    start_pos = encontrar_posicao_inicial(MAPA)
    pacman = Pacman(x=start_pos[0], y=start_pos[1], sprites=pacman_sprites)
    pacman.reposicionar(*start_pos)

    # Pontuação do jogador
    pontuacao = 0
    recorde = 0
    vidas = VIDAS_INICIAIS
    jogo_encerrado = False
    vida_extra_concedida = False
    combo_fantasmas = 0
    popups = []

    # Cópia do mapa para controlar pontos coletados
    mapa_atual = [linha[:] for linha in MAPA]
    pontos_comidos_nivel = 0
    pontos_liberacao = 0
    usar_liberacao_pos_morte = False
    total_pontos_nivel = contar_pontos(mapa_atual)
    frutas_disparadas = set()
    fruta_ativa = None
    frames_sem_comer = 0
    indice_modo = 0
    frames_modo = 0
    modo_global = modo_por_indice(nivel_atual, indice_modo)

    # Criar fantasmas para o jogo
    fantasmas = criar_fantasmas(MAPA)
    aplicar_velocidades(nivel_atual, pacman, fantasmas)
    aplicar_modo_global(fantasmas, modo_global, inverter=False)

    rodando = True
    while rodando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif (
                jogo_encerrado
                and evento.type == pygame.KEYDOWN
                and evento.key == pygame.K_r
            ):
                nivel_atual = 1
                MAPA = gerar_labirinto(4, 3, nivel_atual)
                mapa_atual = [linha[:] for linha in MAPA]
                start_pos = encontrar_posicao_inicial(MAPA)
                pacman.reposicionar(*start_pos)
                fantasmas = criar_fantasmas(MAPA)
                pontuacao = 0
                vidas = VIDAS_INICIAIS
                vida_extra_concedida = False
                combo_fantasmas = 0
                popups = []
                pontos_comidos_nivel = 0
                pontos_liberacao = 0
                usar_liberacao_pos_morte = False
                total_pontos_nivel = contar_pontos(mapa_atual)
                frutas_disparadas = set()
                fruta_ativa = None
                frames_sem_comer = 0
                indice_modo = 0
                frames_modo = 0
                modo_global = modo_por_indice(nivel_atual, indice_modo)
                aplicar_velocidades(nivel_atual, pacman, fantasmas)
                aplicar_modo_global(fantasmas, modo_global, inverter=False)
                jogo_encerrado = False

        if jogo_encerrado:
            desenhar_tela(screen, mapa_atual, fantasmas, pacman, fruta_ativa)
            exibir_informacoes(
                screen,
                nivel_atual,
                pontuacao,
                vidas,
                recorde,
                pontos_comidos_nivel / max(1, total_pontos_nivel),
            )
            exibir_game_over(screen)
            pygame.display.flip()
            clock.tick(FPS)
            continue

        if not algum_fantasma_assustado(fantasmas):
            frames_modo += 1
            proximo_indice, proximo_modo = atualizar_modo_global(
                nivel_atual, indice_modo, frames_modo, modo_global
            )
            if proximo_indice != indice_modo:
                indice_modo = proximo_indice
                frames_modo = 0
                modo_global = proximo_modo
                aplicar_modo_global(fantasmas, modo_global, inverter=True)

        teclas = pygame.key.get_pressed()
        pacman.processar_input(teclas)
        pacman.mover(MAPA)
        pacman.atualizar_animacao()

        # Verificar coleta de pontos - usando o centro do Pac-Man
        centro_x = pacman.x + TILE_SIZE / 2
        centro_y = pacman.y + TILE_SIZE / 2
        col = int(centro_x // TILE_SIZE)
        row = int(centro_y // TILE_SIZE)

        comeu_algo = False
        if 0 <= row < len(mapa_atual) and 0 <= col < len(mapa_atual[0]):
            if mapa_atual[row][col] == 2:  # É um ponto comum
                mapa_atual[row][col] = 0  # Remove o ponto
                pontuacao += 10  # Incrementa pontuação
                pontos_comidos_nivel += 1
                pontos_liberacao += 1
                comeu_algo = True
                pacman.pausar(1)
            elif mapa_atual[row][col] == 4:  # É um bug crítico
                mapa_atual[row][col] = 0  # Remove o bug crítico
                pontuacao += 50  # Bugs críticos valem mais pontos
                pontos_comidos_nivel += 1
                pontos_liberacao += 1
                comeu_algo = True
                pacman.pausar(3)

                # Quando o Pacman corrige um bug crítico, os fantasmas ficam vulneráveis
                combo_fantasmas = 0
                duracao_susto = duracao_frightened(nivel_atual)
                for fantasma in fantasmas:
                    fantasma.tornar_vulneravel(duracao_susto, modo_global)

        if comeu_algo:
            frames_sem_comer = 0
            liberar_fantasmas_por_pontos(
                fantasmas, nivel_atual, pontos_liberacao, usar_liberacao_pos_morte
            )
        else:
            frames_sem_comer = liberar_fantasma_por_ociosidade(
                fantasmas, nivel_atual, frames_sem_comer + 1
            )

        fruta_ativa = atualizar_fruta(
            fruta_ativa,
            frutas_disparadas,
            pontos_comidos_nivel,
            total_pontos_nivel,
            nivel_atual,
            MAPA,
        )

        if fruta_ativa and col == fruta_ativa["col"] and row == fruta_ativa["row"]:
            pontuacao += fruta_ativa["valor"]
            popups.append(
                novo_popup(str(fruta_ativa["valor"]), centro_x, centro_y - TILE_SIZE, (255, 190, 90))
            )
            fruta_ativa = None

        if not vida_extra_concedida and pontuacao >= PONTOS_VIDA_EXTRA:
            vidas += 1
            vida_extra_concedida = True

        recorde = max(recorde, pontuacao)

        # Mover fantasmas e verificar colisões
        for fantasma in fantasmas:
            fantasma.mover(pacman.x, pacman.y, MAPA, pacman.direcao)
            resultado_colisao = fantasma.verificar_colisao_pacman(pacman.x, pacman.y)

            if resultado_colisao == 1:  # Colisão normal - Pacman perde vida
                vidas -= 1
                start_pos = encontrar_posicao_inicial(MAPA)
                pacman.reposicionar(*start_pos)
                fantasmas = criar_fantasmas(MAPA, apos_morte=True)
                aplicar_velocidades(nivel_atual, pacman, fantasmas)
                combo_fantasmas = 0
                popups = []
                pontos_liberacao = 0
                usar_liberacao_pos_morte = True
                fruta_ativa = None
                frames_sem_comer = 0
                indice_modo = 0
                frames_modo = 0
                modo_global = modo_por_indice(nivel_atual, indice_modo)
                aplicar_modo_global(fantasmas, modo_global, inverter=False)
                jogo_encerrado = vidas <= 0
                break

            elif resultado_colisao == 2:  # Fantasma é comido
                fantasma.foi_comido()
                pontos_fantasma = PONTOS_FANTASMAS_COMIDOS[
                    min(combo_fantasmas, len(PONTOS_FANTASMAS_COMIDOS) - 1)
                ]
                pontuacao += pontos_fantasma
                combo_fantasmas += 1
                popups.append(
                    novo_popup(str(pontos_fantasma), *fantasma._centro_atual(), (90, 205, 255))
                )

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
            pacman.reposicionar(*start_pos)

            # Criar novos fantasmas para o novo nível
            fantasmas = criar_fantasmas(MAPA)
            aplicar_velocidades(nivel_atual, pacman, fantasmas)
            combo_fantasmas = 0
            popups = []
            pontos_comidos_nivel = 0
            pontos_liberacao = 0
            usar_liberacao_pos_morte = False
            total_pontos_nivel = contar_pontos(mapa_atual)
            frutas_disparadas = set()
            fruta_ativa = None
            frames_sem_comer = 0
            indice_modo = 0
            frames_modo = 0
            modo_global = modo_por_indice(nivel_atual, indice_modo)
            aplicar_modo_global(fantasmas, modo_global, inverter=False)

        popups = atualizar_popups(popups)
        desenhar_tela(screen, mapa_atual, fantasmas, pacman, fruta_ativa, popups)

        # Exibir informações de nível e pontuação
        exibir_informacoes(
            screen,
            nivel_atual,
            pontuacao,
            vidas,
            recorde,
            pontos_comidos_nivel / max(1, total_pontos_nivel),
        )

        pygame.display.flip()
        clock.tick(FPS)


def encontrar_posicao_inicial(mapa):
    """Encontra uma posição válida (corredor) para o Pacman começar."""
    # No Pac-Man original, ele começa em uma posição específica na parte inferior central do mapa
    altura = len(mapa)
    largura = len(mapa[0])

    # Posição clássica do Pac-Man (pouco abaixo do centro do mapa, similar ao jogo original)
    posicao_y_preferida = altura * 3 // 4  # 3/4 da altura do mapa
    centro_x = largura // 2

    # Verificar a posição preferida
    if 0 <= posicao_y_preferida < altura and mapa[posicao_y_preferida][centro_x] in [
        0,
        2,
    ]:
        # Retorna posição preferida do jogo original (centralizada no tile)
        return centro_x * TILE_SIZE, posicao_y_preferida * TILE_SIZE

    # Se a posição preferida não funcionar, verificar um pouco acima e abaixo
    for offset in range(1, 5):
        if posicao_y_preferida - offset >= 0 and mapa[posicao_y_preferida - offset][
            centro_x
        ] in [0, 2]:
            return centro_x * TILE_SIZE, (posicao_y_preferida - offset) * TILE_SIZE
        if posicao_y_preferida + offset < altura and mapa[posicao_y_preferida + offset][
            centro_x
        ] in [0, 2]:
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


def encontrar_saida_fantasma(mapa):
    """Encontra a posição fora da porta da casa dos fantasmas."""
    for row in range(1, len(mapa)):
        for col in range(len(mapa[0])):
            if (
                mapa[row][col] == CASA_FANTASMA
                and mapa[row - 1][col] not in [1, CASA_FANTASMA]
            ):
                return col * TILE_SIZE, (row - 1) * TILE_SIZE
    return None


def encontrar_posicao_fantasma(mapa, indice=0):
    """Encontra uma posição válida para um fantasma dentro da casa dos fantasmas."""
    altura = len(mapa)
    largura = len(mapa[0])

    # Procurar por células marcadas como CASA_FANTASMA
    posicoes_casa = []
    for y in range(altura):
        for x in range(largura):
            if mapa[y][x] == CASA_FANTASMA:
                posicoes_casa.append((x, y))

    if posicoes_casa:
        centro_x = largura // 2
        posicoes_casa.sort(key=lambda pos: (abs(pos[0] - centro_x), pos[1], pos[0]))
        x, y = posicoes_casa[indice % len(posicoes_casa)]
        return x * TILE_SIZE, y * TILE_SIZE

    # Se não encontrou, retornar o centro do mapa
    return (largura // 2) * TILE_SIZE, (altura // 2) * TILE_SIZE


def criar_fantasmas(mapa, apos_morte=False):
    """Cria os fantasmas para o jogo usando os sprites disponíveis."""
    fantasmas = []

    # Lista de todos os arquivos de sprite de fantasmas
    sprite_paths = sorted(glob.glob(caminho_recurso("assets", "ghosts", "*.png")))

    # Lista de personalidades para os fantasmas
    personalidades = ["perseguidor", "emboscador", "vagante", "imprevisível"]
    limites_saida = limites_saida_fantasmas(
        nivel_atual, len(sprite_paths[:6]), apos_morte
    )

    # Criar um fantasma para cada sprite disponível (até 6)
    for i, sprite_path in enumerate(sprite_paths[:6]):
        if i == 0:
            posicao_saida = encontrar_saida_fantasma(mapa)
            pos_x, pos_y = (
                posicao_saida if posicao_saida else encontrar_posicao_fantasma(mapa, i)
            )
            atraso_saida = 0
        else:
            pos_x, pos_y = encontrar_posicao_fantasma(mapa, i - 1)
            atraso_saida = 0 if limites_saida[i] == 0 else 999999

        # Criar fantasma com personalidade específica
        personalidade = personalidades[i % len(personalidades)]
        fantasma = Ghost(
            pos_x, pos_y, sprite_path, TILE_SIZE, personalidade, atraso_saida
        )

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
