"""Desenho do labirinto, HUD e efeitos visuais do jogo."""

import functools
import math

import pygame

from maze_generator import CASA_FANTASMA, PAREDE, POWER_PELLET, PONTO

TILE_SIZE = 34
LARGURA_PAINEL = 200  # faixa à direita do labirinto onde fica o HUD

COR_FUNDO_TOPO = (9, 9, 34)
COR_FUNDO_BASE = (2, 2, 12)
COR_PAREDE = (50, 110, 255)
COR_INTERIOR_PAREDE = (7, 9, 40)
COR_CASA = (22, 8, 36)
COR_PORTA = (255, 150, 215)
COR_PONTO = (255, 222, 180)
COR_PACMAN = (255, 225, 40)
COR_TEXTO = (240, 244, 255)
COR_TEXTO_SUAVE = (150, 160, 200)


@functools.lru_cache(maxsize=None)
def fonte(tamanho):
    """SysFont é caro: cada tamanho é criado uma única vez."""
    return pygame.font.SysFont("arial,helvetica,liberationsans,dejavusans", tamanho, bold=True)


@functools.lru_cache(maxsize=128)
def brilho(cor, raio, intensidade=1.0):
    """Disco radial suave, feito para ser somado à tela (BLEND_RGB_ADD)."""
    superficie = pygame.Surface((raio * 2, raio * 2))
    for r in range(raio, 0, -1):
        fator = (1 - r / raio) ** 2 * intensidade
        pygame.draw.circle(
            superficie,
            tuple(min(255, int(canal * fator)) for canal in cor),
            (raio, raio),
            r,
        )
    return superficie


def desenhar_brilho(screen, cor, centro, raio, intensidade=1.0):
    screen.blit(
        brilho(cor, raio, intensidade),
        (int(centro[0]) - raio, int(centro[1]) - raio),
        special_flags=pygame.BLEND_RGB_ADD,
    )


def _degrade_vertical(superficie, cor_topo, cor_base):
    largura, altura = superficie.get_size()
    for y in range(altura):
        fator = y / max(1, altura - 1)
        cor = tuple(int(a + (b - a) * fator) for a, b in zip(cor_topo, cor_base))
        pygame.draw.line(superficie, cor, (0, y), (largura, y))


# ------------------------------------------------------------------ labirinto
def construir_labirinto(mapa, tile=TILE_SIZE):
    """Pré-renderiza fundo, paredes neon e casa dos fantasmas (uma vez por mapa)."""
    linhas = len(mapa)
    colunas = len(mapa[0])
    largura, altura = colunas * tile, linhas * tile
    meio = tile // 2

    fundo = pygame.Surface((largura, altura))
    _degrade_vertical(fundo, COR_FUNDO_TOPO, COR_FUNDO_BASE)

    paredes = {
        (col, row)
        for row in range(linhas)
        for col in range(colunas)
        if mapa[row][col] == PAREDE
    }

    # Interior da casa dos fantasmas
    for row in range(linhas):
        for col in range(colunas):
            if mapa[row][col] == CASA_FANTASMA:
                pygame.draw.rect(fundo, COR_CASA, (col * tile, row * tile, tile, tile))

    def tracar(alvo, cor, raio, preencher_blocos):
        """Desenha as paredes como tubos de raio `raio` ligando centros de tiles."""
        for col, row in paredes:
            cx, cy = col * tile + meio, row * tile + meio
            pygame.draw.circle(alvo, cor, (cx, cy), raio)
            tem_direita = (col + 1, row) in paredes
            tem_baixo = (col, row + 1) in paredes
            if tem_direita:
                pygame.draw.rect(alvo, cor, (cx, cy - raio, tile, raio * 2))
            if tem_baixo:
                pygame.draw.rect(alvo, cor, (cx - raio, cy, raio * 2, tile))
            if preencher_blocos and tem_direita and tem_baixo and (col + 1, row + 1) in paredes:
                pygame.draw.rect(alvo, cor, (cx, cy, tile, tile))

    # Brilho: o contorno desfocado é somado ao fundo
    luz = pygame.Surface((largura, altura))
    tracar(luz, COR_PAREDE, 8, False)
    reduzida = pygame.transform.smoothscale(luz, (max(1, largura // 6), max(1, altura // 6)))
    luz = pygame.transform.smoothscale(reduzida, (largura, altura))
    fundo.blit(luz, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    fundo.blit(luz, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    # Tubo azul por fora e miolo escuro por dentro = contorno fino e nítido
    tracar(fundo, COR_PAREDE, 7, False)
    tracar(fundo, COR_INTERIOR_PAREDE, 4, True)

    # Porta da casa: barra rosa no topo da célula da casa que dá para o corredor
    for row in range(1, linhas):
        for col in range(colunas):
            if mapa[row][col] == CASA_FANTASMA and mapa[row - 1][col] not in (PAREDE, CASA_FANTASMA):
                porta = pygame.Rect(col * tile + 3, row * tile - 2, tile - 6, 4)
                pygame.draw.rect(fundo, COR_PORTA, porta, border_radius=2)
                desenhar_brilho(fundo, COR_PORTA, porta.center, 22, 0.6)
    return fundo


_cache_labirinto = {"chave": None, "superficie": None}


def _labirinto(mapa_atual):
    chave = tuple(
        tuple(celula in (PAREDE, CASA_FANTASMA) for celula in linha) for linha in mapa_atual
    )
    if _cache_labirinto["chave"] != chave:
        _cache_labirinto["chave"] = chave
        _cache_labirinto["superficie"] = construir_labirinto(mapa_atual)
    return _cache_labirinto["superficie"]


# ---------------------------------------------------------------------- itens
def desenhar_ponto(screen, centro):
    pygame.draw.circle(screen, COR_PONTO, centro, 3)


def desenhar_bug_critico(screen, tile_x, tile_y):
    """Desenha o item que deixa os fantasmas vulneráveis (um bug pulsante)."""
    centro_x = tile_x + TILE_SIZE // 2
    centro_y = tile_y + TILE_SIZE // 2
    pulso = abs(pygame.time.get_ticks() % 800 - 400) / 400
    raio = int(TILE_SIZE * (0.2 + pulso * 0.04))
    cor_corpo = (235, 55, 70)
    cor_linha = (40, 8, 22)

    desenhar_brilho(screen, (255, 90, 90), (centro_x, centro_y), 22, 0.35 + pulso * 0.35)

    for offset_y in (-raio // 2, 0, raio // 2):
        for lado in (-1, 1):
            pygame.draw.line(
                screen,
                (255, 190, 90),
                (centro_x + lado * (raio - 2), centro_y + offset_y),
                (centro_x + lado * (raio + 5), centro_y + offset_y - 3),
                2,
            )
    pygame.draw.circle(screen, cor_corpo, (centro_x, centro_y), raio)
    pygame.draw.circle(screen, (255, 140, 130), (centro_x - raio // 3, centro_y - raio // 3), max(2, raio // 4))
    pygame.draw.line(
        screen, cor_linha, (centro_x, centro_y - raio + 2), (centro_x, centro_y + raio - 2), 2
    )
    pygame.draw.circle(screen, cor_linha, (centro_x - raio // 3, centro_y - raio // 3), 2)
    pygame.draw.circle(screen, cor_linha, (centro_x + raio // 3, centro_y - raio // 3), 2)


def desenhar_fruta(screen, fruta):
    """Desenha a fruta bônus (cerejas) logo abaixo da casa dos fantasmas."""
    centro_x = fruta["col"] * TILE_SIZE + TILE_SIZE // 2
    centro_y = fruta["row"] * TILE_SIZE + TILE_SIZE // 2
    cor = (255, 60, 90) if fruta["valor"] < 1000 else (255, 180, 40)

    desenhar_brilho(screen, cor, (centro_x, centro_y), 24, 0.55)
    pygame.draw.line(screen, (80, 200, 90), (centro_x - 5, centro_y + 3), (centro_x + 2, centro_y - 9), 2)
    pygame.draw.line(screen, (80, 200, 90), (centro_x + 7, centro_y + 2), (centro_x + 2, centro_y - 9), 2)
    pygame.draw.ellipse(screen, (90, 220, 100), (centro_x + 1, centro_y - 13, 11, 6))
    for deslocamento_x, deslocamento_y in ((-6, 4), (7, 3)):
        posicao = (centro_x + deslocamento_x, centro_y + deslocamento_y)
        pygame.draw.circle(screen, cor, posicao, 6)
        pygame.draw.circle(screen, (255, 235, 235), (posicao[0] - 2, posicao[1] - 2), 2)


# --------------------------------------------------------------------- popups
def novo_popup(texto, x, y, cor=(255, 255, 255), frames=60):
    return {"texto": texto, "x": x, "y": y, "cor": cor, "frames": frames, "total": frames}


def atualizar_popups(popups):
    for popup in popups:
        popup["frames"] -= 1
    return [popup for popup in popups if popup["frames"] > 0]


def desenhar_popups(screen, popups):
    for popup in popups:
        progresso = 1 - popup["frames"] / popup["total"]
        texto = fonte(18).render(popup["texto"], True, popup["cor"])
        texto.set_alpha(int(255 * min(1.0, popup["frames"] / (popup["total"] * 0.4))))
        posicao = texto.get_rect(center=(popup["x"], popup["y"] - 22 * progresso))
        screen.blit(texto, posicao)


# ----------------------------------------------------------------------- tela
def desenhar_tela(screen, mapa_atual, fantasmas, pacman, fruta_ativa=None, popups=()):
    """Desenha labirinto, itens, fantasmas e Pac-Man."""
    screen.fill((0, 0, 0))
    screen.blit(_labirinto(mapa_atual), (0, 0))

    for row, linha in enumerate(mapa_atual):
        for col, celula in enumerate(linha):
            if celula == PONTO:
                desenhar_ponto(
                    screen, (col * TILE_SIZE + TILE_SIZE // 2, row * TILE_SIZE + TILE_SIZE // 2)
                )
            elif celula == POWER_PELLET:
                desenhar_bug_critico(screen, col * TILE_SIZE, row * TILE_SIZE)

    if fruta_ativa:
        desenhar_fruta(screen, fruta_ativa)

    for fantasma in fantasmas:
        fantasma.desenhar(screen)

    # O Pac-Man vai por último para ficar por cima dos fantasmas quando os come
    desenhar_brilho(
        screen,
        COR_PACMAN,
        (pacman.x + TILE_SIZE // 2, pacman.y + TILE_SIZE // 2),
        30,
        0.4,
    )
    pacman.desenhar(screen)

    desenhar_popups(screen, popups)


# ------------------------------------------------------------------------ HUD
def _icone_pacman(tamanho):
    superficie = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
    centro = tamanho // 2
    pygame.draw.circle(superficie, COR_PACMAN, (centro, centro), centro)
    boca = [
        (centro, centro),
        (tamanho + 2, centro - int(tamanho * 0.42)),
        (tamanho + 2, centro + int(tamanho * 0.42)),
    ]
    pygame.draw.polygon(superficie, (0, 0, 0, 0), boca)
    return superficie


def _cartao(screen, retangulo, borda=(70, 90, 190, 120)):
    superficie = pygame.Surface(retangulo.size, pygame.SRCALPHA)
    pygame.draw.rect(superficie, (255, 255, 255, 14), superficie.get_rect(), border_radius=10)
    pygame.draw.rect(superficie, borda, superficie.get_rect(), width=1, border_radius=10)
    screen.blit(superficie, retangulo.topleft)


def exibir_informacoes(screen, nivel, pontuacao, vidas, recorde, progresso=0.0):
    """Painel à direita do labirinto: título, nível, pontos, recorde, vidas e progresso."""
    x0 = screen.get_width() - LARGURA_PAINEL
    altura = screen.get_height()

    painel = pygame.Surface((LARGURA_PAINEL, altura))
    _degrade_vertical(painel, (16, 16, 48), (5, 5, 20))
    screen.blit(painel, (x0, 0))
    pygame.draw.line(screen, COR_PAREDE, (x0, 0), (x0, altura), 2)

    # Título
    pac = fonte(34).render("PAC", True, COR_PACMAN)
    devs = fonte(34).render("DEVS", True, (90, 205, 255))
    total = pac.get_width() + 6 + devs.get_width()
    inicio = x0 + (LARGURA_PAINEL - total) // 2
    screen.blit(pac, (inicio, 22))
    screen.blit(devs, (inicio + pac.get_width() + 6, 22))

    margem = 16
    largura_cartao = LARGURA_PAINEL - 2 * margem
    y = 86
    for rotulo, valor in (("NÍVEL", str(nivel)), ("PONTUAÇÃO", str(pontuacao)), ("RECORDE", str(recorde))):
        cartao = pygame.Rect(x0 + margem, y, largura_cartao, 62)
        _cartao(screen, cartao)
        screen.blit(fonte(13).render(rotulo, True, COR_TEXTO_SUAVE), (cartao.x + 12, cartao.y + 8))
        screen.blit(fonte(28).render(valor, True, COR_TEXTO), (cartao.x + 12, cartao.y + 26))
        y += 74

    # Vidas
    cartao = pygame.Rect(x0 + margem, y, largura_cartao, 62)
    _cartao(screen, cartao)
    screen.blit(fonte(13).render("VIDAS", True, COR_TEXTO_SUAVE), (cartao.x + 12, cartao.y + 8))
    icone = _icone_pacman(22)
    for indice in range(min(vidas, 5)):
        screen.blit(icone, (cartao.x + 12 + indice * 28, cartao.y + 30))
    if vidas > 5:
        screen.blit(fonte(16).render(f"+{vidas - 5}", True, COR_TEXTO), (cartao.x + 12 + 5 * 28, cartao.y + 32))
    y += 74

    # Progresso da fase (bugs corrigidos)
    screen.blit(fonte(13).render("PROGRESSO", True, COR_TEXTO_SUAVE), (x0 + margem + 2, y + 4))
    barra = pygame.Rect(x0 + margem, y + 26, largura_cartao, 12)
    pygame.draw.rect(screen, (28, 30, 70), barra, border_radius=6)
    preenchido = barra.copy()
    preenchido.width = max(0, int(barra.width * max(0.0, min(1.0, progresso))))
    if preenchido.width > 0:
        pygame.draw.rect(screen, (90, 205, 255), preenchido, border_radius=6)

    # Dica de controles
    dica = fonte(13).render("Setas: mover", True, COR_TEXTO_SUAVE)
    screen.blit(dica, dica.get_rect(center=(x0 + LARGURA_PAINEL // 2, altura - 28)))


def exibir_game_over(screen):
    """Escurece o labirinto e mostra a tela de fim de jogo."""
    largura = screen.get_width() - LARGURA_PAINEL
    altura = screen.get_height()
    sombra = pygame.Surface((largura, altura), pygame.SRCALPHA)
    sombra.fill((0, 0, 8, 185))
    screen.blit(sombra, (0, 0))

    centro = (largura // 2, altura // 2)
    desenhar_brilho(screen, (255, 40, 60), (centro[0], centro[1] - 30), 150, 0.45)
    titulo = fonte(64).render("GAME OVER", True, (255, 80, 90))
    contorno = fonte(64).render("GAME OVER", True, (90, 0, 10))
    ret = titulo.get_rect(center=(centro[0], centro[1] - 30))
    screen.blit(contorno, ret.move(3, 3))
    screen.blit(titulo, ret)

    pulso = 0.55 + 0.45 * math.sin(pygame.time.get_ticks() / 280)
    instrucao = fonte(22).render("Pressione R para reiniciar", True, COR_TEXTO)
    instrucao.set_alpha(int(255 * pulso))
    screen.blit(instrucao, instrucao.get_rect(center=(centro[0], centro[1] + 42)))
