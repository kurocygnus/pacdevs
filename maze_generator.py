import random
from collections import deque

# Constantes para os tipos de células
PAREDE = 1
CORREDOR = 0
PONTO = 2
CASA_FANTASMA = 3
POWER_PELLET = 4

# Mapa base inspirado no Pac-Man original
MAPA_PACMAN_ORIGINAL = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 2, 2, 1],
    [1, 2, 1, 1, 2, 1, 1, 1, 2, 1, 2, 1, 1, 1, 2, 1, 1, 2, 1],
    [1, 4, 1, 1, 2, 1, 1, 1, 2, 1, 2, 1, 1, 1, 2, 1, 1, 4, 1],
    [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
    [1, 2, 1, 1, 2, 1, 2, 1, 1, 1, 1, 1, 2, 1, 2, 1, 1, 2, 1],
    [1, 2, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 2, 1],
    [1, 1, 1, 1, 2, 1, 1, 1, 0, 1, 0, 1, 1, 1, 2, 1, 1, 1, 1],
    [0, 0, 0, 1, 2, 1, 0, 0, 0, 0, 0, 0, 0, 1, 2, 1, 0, 0, 0],
    [1, 1, 1, 1, 2, 1, 0, 1, 1, 3, 1, 1, 0, 1, 2, 1, 1, 1, 1],
    [0, 0, 0, 0, 2, 0, 0, 1, 3, 3, 3, 1, 0, 0, 2, 0, 0, 0, 0],
    [1, 1, 1, 1, 2, 1, 0, 1, 1, 1, 1, 1, 0, 1, 2, 1, 1, 1, 1],
    [0, 0, 0, 1, 2, 1, 0, 0, 0, 0, 0, 0, 0, 1, 2, 1, 0, 0, 0],
    [1, 1, 1, 1, 2, 1, 0, 1, 1, 1, 1, 1, 0, 1, 2, 1, 1, 1, 1],
    [1, 2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 2, 2, 1],
    [1, 2, 1, 1, 2, 1, 1, 1, 2, 1, 2, 1, 1, 1, 2, 1, 1, 2, 1],
    [1, 4, 2, 1, 2, 2, 2, 2, 2, 0, 2, 2, 2, 2, 2, 1, 2, 4, 1],
    [1, 1, 2, 1, 2, 1, 2, 1, 1, 1, 1, 1, 2, 1, 2, 1, 2, 1, 1],
    [1, 2, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1, 2, 2, 2, 2, 1],
    [1, 2, 1, 1, 1, 1, 1, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 2, 1],
    [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
]

def gerar_labirinto(blocos_largura=4, blocos_altura=3, nivel=1):
    """
    Gera um labirinto estilo Pac-Man proceduralmente.
    O parâmetro nível permite criar mapas diferentes para cada fase.
    
    Args:
        blocos_largura: Número de blocos na largura do mapa
        blocos_altura: Número de blocos na altura do mapa
        nivel: Nível atual do jogo (influencia a geração)
        
    Returns:
        Uma matriz 2D representando o labirinto
    """
    # Dimensões do mapa - garantir tamanhos mínimos e que a largura seja ímpar
    largura = max(19, blocos_largura * 4 + 1)
    altura = max(22, blocos_altura * 4 + 1)
    
    # Ajustar para garantir que largura seja ímpar e altura seja par
    largura = largura if largura % 2 == 1 else largura + 1
    altura = altura if altura % 2 == 0 else altura + 1
    
    # Seed determinística: o mesmo nível sempre gera o mesmo mapa.
    seed = nivel * 1009 + largura * 37 + altura * 73
    gerador = random.Random(seed)

    if largura == len(MAPA_PACMAN_ORIGINAL[0]) and altura == len(MAPA_PACMAN_ORIGINAL):
        mapa = _estrutura_do_mapa_original()
    else:
        mapa = _criar_labirinto_estruturado(largura, altura)

    criar_casa_fantasmas(mapa, largura, altura, gerador)

    gerar_portais(mapa, nivel, gerador)
    _aplicar_variacoes_controladas(mapa, nivel, gerador)
    mapa = garantir_conectividade(mapa, gerador)
    mapa_final = combinar_mapas(mapa, nivel, gerador)
    
    return mapa_final

def _estrutura_do_mapa_original():
    """Usa o desenho clássico como base estrutural sem pontos."""
    mapa = []
    for linha in MAPA_PACMAN_ORIGINAL:
        nova_linha = []
        for celula in linha:
            if celula == PAREDE:
                nova_linha.append(PAREDE)
            elif celula == CASA_FANTASMA:
                nova_linha.append(CASA_FANTASMA)
            else:
                nova_linha.append(CORREDOR)
        mapa.append(nova_linha)
    return mapa

def _criar_labirinto_estruturado(largura, altura):
    """Cria um labirinto simétrico com corredores principais garantidos."""
    mapa = [[PAREDE for _ in range(largura)] for _ in range(altura)]
    centro_x = largura // 2
    centro_y = altura // 2

    for y in range(1, altura - 1):
        for x in range(1, largura - 1):
            if y % 2 == 1 or x in (1, largura - 2, centro_x):
                mapa[y][x] = CORREDOR

    for y in (centro_y - 2, centro_y, centro_y + 2, altura - 2):
        if 0 < y < altura - 1:
            for x in range(1, largura - 1):
                mapa[y][x] = CORREDOR

    for x in range(2, centro_x, 4):
        espelho_x = largura - 1 - x
        for y in range(3, altura - 3):
            if y % 4 in (0, 1):
                mapa[y][x] = PAREDE
                mapa[y][espelho_x] = PAREDE

    return mapa

def _aplicar_variacoes_controladas(mapa, nivel, gerador):
    """Faz pequenas mudanças simétricas, mantendo o mapa conectado."""
    altura = len(mapa)
    largura = len(mapa[0])
    centro_x = largura // 2
    max_tentativas = 20 + nivel * 3
    mudancas_alvo = min(6, 1 + nivel // 2)
    mudancas = 0

    for _ in range(max_tentativas):
        if mudancas >= mudancas_alvo:
            break

        x = gerador.randrange(2, centro_x)
        y = gerador.randrange(2, altura - 2)
        espelho_x = largura - 1 - x

        if _eh_area_protegida(mapa, x, y) or _eh_area_protegida(mapa, espelho_x, y):
            continue

        valor_atual = mapa[y][x]
        if valor_atual == CASA_FANTASMA or mapa[y][espelho_x] == CASA_FANTASMA:
            continue

        novo_valor = CORREDOR if valor_atual == PAREDE else PAREDE
        antigo_esquerdo, antigo_direito = mapa[y][x], mapa[y][espelho_x]
        mapa[y][x] = novo_valor
        mapa[y][espelho_x] = novo_valor

        if not _mapa_conectado(mapa) or _cria_bloco_ruim(mapa, x, y) or _cria_bloco_ruim(mapa, espelho_x, y):
            mapa[y][x] = antigo_esquerdo
            mapa[y][espelho_x] = antigo_direito
            continue

        mudancas += 1

def _eh_area_protegida(mapa, x, y):
    altura = len(mapa)
    largura = len(mapa[0])
    centro_x = largura // 2
    centro_y = altura // 2

    if x <= 1 or x >= largura - 2 or y <= 1 or y >= altura - 2:
        return True
    if abs(x - centro_x) <= 3 and abs(y - (centro_y - 1)) <= 4:
        return True
    if y in (altura // 2, altura // 2 + 1):
        return True
    return False

def _cria_bloco_ruim(mapa, x, y):
    """Evita blocos 2x2 fechados/abertos demais, que deixam o mapa com ruído visual."""
    altura = len(mapa)
    largura = len(mapa[0])
    for by in (y - 1, y):
        for bx in (x - 1, x):
            if not (0 <= by < altura - 1 and 0 <= bx < largura - 1):
                continue
            paredes = 0
            for dy in (0, 1):
                for dx in (0, 1):
                    if mapa[by + dy][bx + dx] == PAREDE:
                        paredes += 1
            if paredes in (0, 4):
                return True
    return False

def criar_casa_fantasmas(mapa, largura, altura, gerador=None):
    """
    Cria a área central para os fantasmas, típica do Pac-Man.
    Varia de acordo com o nível, mantendo a essência do jogo original.
    """
    # Se não foi fornecido gerador, usa o módulo random padrão
    if gerador is None:
        gerador = random
        
    centro_x = largura // 2
    
    # No Pac-Man original, a casa dos fantasmas fica um pouco acima do centro
    centro_y = altura // 2 - altura // 10
    
    base_largura = min(7, largura // 3)
    base_altura = min(5, altura // 5)

    casa_largura = base_largura
    casa_altura = base_altura
    
    # Garantir que as dimensões sejam ímpares para manter a porta centralizada
    casa_largura = casa_largura if casa_largura % 2 == 1 else casa_largura + 1
    casa_altura = casa_altura if casa_altura % 2 == 1 else casa_altura + 1
    
    # Calcular os limites da casa
    inicio_x = centro_x - casa_largura // 2
    inicio_y = centro_y - casa_altura // 2
    fim_x = inicio_x + casa_largura
    fim_y = inicio_y + casa_altura
    
    # Criar a casa dos fantasmas
    for y in range(inicio_y, fim_y):
        for x in range(inicio_x, fim_x):
            # Borda da casa
            if (y == inicio_y or y == fim_y - 1 or 
                x == inicio_x or x == fim_x - 1):
                mapa[y][x] = PAREDE
            else:
                mapa[y][x] = CASA_FANTASMA
    
    # Criar porta na parte superior da casa (sempre presente)
    mapa[inicio_y][centro_x] = CORREDOR
    if inicio_y > 1:
        mapa[inicio_y - 1][centro_x] = CORREDOR
    
def adicionar_power_pellets_cantos(mapa, mapa_pontos, nivel=1, gerador=None):
    """
    Adiciona bugs críticos no mapa, com variação baseada no nível.
    Mantém a tradição dos itens especiais nos cantos, mas adiciona alguns extras
    em níveis mais avançados.
    """
    # Se não foi fornecido gerador, usa o módulo random padrão
    if gerador is None:
        gerador = random
    altura = len(mapa)
    largura = len(mapa[0])
    
    # Número base de bugs críticos (normalmente 4, como no original)
    num_power_pellets = 4
    
    # A cada 3 níveis, adiciona um bug crítico extra (até o limite de 8)
    num_extras = min(4, nivel // 3)
    num_power_pellets += num_extras
    
    # Posições tradicionais dos itens especiais (próximas aos cantos)
    posicoes_cantos = [
        (2, 2),                    # Superior esquerdo
        (2, largura - 3),          # Superior direito
        (altura - 3, 2),           # Inferior esquerdo
        (altura - 3, largura - 3)  # Inferior direito
    ]
    
    # Adicionar bugs críticos nos cantos (sempre presente)
    for y, x in posicoes_cantos:
        # Encontrar o ponto de corredor mais próximo se a posição exata não for válida
        if mapa[y][x] != CORREDOR:
            # Procurar nas proximidades
            encontrou = False
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    ny, nx = y + dy, x + dx
                    if (0 <= ny < altura and 0 <= nx < largura and 
                        mapa[ny][nx] == CORREDOR):
                        mapa_pontos[ny][nx] = POWER_PELLET
                        encontrou = True
                        break
                if encontrou:
                    break
        else:
            mapa_pontos[y][x] = POWER_PELLET
    
    # Adicionar bugs críticos extras em posições estratégicas (para níveis avançados)
    if num_extras > 0:
        # Posições potenciais para bugs críticos extras
        candidatos = []
        
        # Dividir o mapa em quadrantes para distribuição uniforme
        quadrantes = [
            (altura // 4, largura // 4),                   # Superior esquerdo
            (altura // 4, largura - largura // 4),         # Superior direito
            (altura - altura // 4, largura // 4),          # Inferior esquerdo
            (altura - altura // 4, largura - largura // 4) # Inferior direito
        ]
        
        # Para cada quadrante, encontrar posições de corredor candidatas
        for quad_y, quad_x in quadrantes:
            for dy in range(-5, 6):
                for dx in range(-5, 6):
                    y, x = quad_y + dy, quad_x + dx
                    if (0 <= y < altura and 0 <= x < largura and 
                        mapa[y][x] == CORREDOR and
                        not any((y == cy and x == cx) for cy, cx in posicoes_cantos)):
                        candidatos.append((y, x))
        
        # Adicionar bugs críticos extras em posições aleatórias
        if candidatos:
            # Embaralhar para aleatoriedade
            gerador.shuffle(candidatos)
            for i in range(min(num_extras, len(candidatos))):
                y, x = candidatos[i]
                mapa_pontos[y][x] = POWER_PELLET

# Esta função foi removida para evitar duplicação

def gerar_portais(mapa, nivel=1, gerador=None):
    """
    Cria portais nos limites do mapa para o Pac-Man poder teleportar.
    Varia a posição dos portais de acordo com o nível.
    """
    # Se não foi fornecido gerador, usa o módulo random padrão
    if gerador is None:
        gerador = random
    altura = len(mapa)
    largura = len(mapa[0])
    
    portal_y = min(altura - 3, altura // 2 + 1)
    
    # Criar portal esquerdo
    for x in range(3):
        mapa[portal_y][x] = CORREDOR
    
    # Criar portal direito
    for x in range(largura - 3, largura):
        mapa[portal_y][x] = CORREDOR
    
    for x in range(largura):
        if mapa[portal_y][x] != CASA_FANTASMA:
            mapa[portal_y][x] = CORREDOR

def combinar_mapas(mapa, nivel=1, gerador=None):
    """
    Adiciona pontos ao mapa estrutural.
    Recebe o nível e um gerador para manter consistência na randomização.
    """
    # Se não foi fornecido gerador, usa o módulo random padrão
    if gerador is None:
        gerador = random
    altura = len(mapa)
    largura = len(mapa[0])
    mapa_pontos = [[0 for _ in range(largura)] for _ in range(altura)]

    for y in range(altura):
        for x in range(largura):
            if mapa[y][x] == CORREDOR:
                mapa_pontos[y][x] = PONTO

    adicionar_power_pellets_cantos(mapa, mapa_pontos, nivel, gerador)

    mapa_final = [[0 for _ in range(largura)] for _ in range(altura)]
    
    for y in range(altura):
        for x in range(largura):
            if mapa[y][x] == PAREDE:  # Parede
                mapa_final[y][x] = PAREDE
            elif mapa[y][x] == CASA_FANTASMA:  # Casa dos fantasmas
                mapa_final[y][x] = CASA_FANTASMA
            elif mapa_pontos[y][x] == PONTO:  # Ponto comum
                mapa_final[y][x] = PONTO
            elif mapa_pontos[y][x] == POWER_PELLET:  # Bug crítico
                mapa_final[y][x] = POWER_PELLET
            else:  # Corredor vazio
                mapa_final[y][x] = CORREDOR

    return mapa_final

def _celulas_andaveis(mapa):
    altura = len(mapa)
    largura = len(mapa[0])
    for y in range(altura):
        for x in range(largura):
            if mapa[y][x] != PAREDE:
                yield x, y

def _mapa_conectado(mapa):
    celulas = list(_celulas_andaveis(mapa))
    if not celulas:
        return False

    altura = len(mapa)
    largura = len(mapa[0])
    inicio = celulas[0]
    visitados = {inicio}
    fila = deque([inicio])

    while fila:
        x, y = fila.popleft()
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < largura and 0 <= ny < altura):
                continue
            if mapa[ny][nx] == PAREDE or (nx, ny) in visitados:
                continue
            visitados.add((nx, ny))
            fila.append((nx, ny))

    return len(visitados) == len(celulas)

def garantir_conectividade(mapa, gerador=None):
    """
    Verifica e garante que todo o labirinto está conectado.
    Se houver áreas isoladas, cria conexões entre elas.
    
    Args:
        mapa: A matriz 2D representando o labirinto
        gerador: O gerador de números aleatórios
        
    Returns:
        O mapa com conectividade garantida
    """
    if gerador is None:
        gerador = random
        
    altura = len(mapa)
    largura = len(mapa[0])
    
    # Algoritmo Flood Fill para marcar áreas conectadas
    def flood_fill(mapa, matriz_visitados, x, y, area_atual):
        # Verificar limites e se a célula é válida para visita
        if (x < 0 or y < 0 or x >= largura or y >= altura or
            mapa[y][x] == PAREDE or matriz_visitados[y][x] != -1):
            return
        
        # Marcar como visitado com o ID da área atual
        matriz_visitados[y][x] = area_atual
        
        # Visitar os 4 vizinhos (cima, baixo, esquerda, direita)
        flood_fill(mapa, matriz_visitados, x, y-1, area_atual)
        flood_fill(mapa, matriz_visitados, x, y+1, area_atual)
        flood_fill(mapa, matriz_visitados, x-1, y, area_atual)
        flood_fill(mapa, matriz_visitados, x+1, y, area_atual)
    
    # Criar matriz para marcar áreas (-1 = não visitado)
    matriz_visitados = [[-1 for _ in range(largura)] for _ in range(altura)]
    
    # Identificar áreas distintas
    area_atual = 0
    for y in range(altura):
        for x in range(largura):
            if mapa[y][x] != PAREDE and matriz_visitados[y][x] == -1:
                flood_fill(mapa, matriz_visitados, x, y, area_atual)
                area_atual += 1
    
    # Se houver apenas uma área, o mapa já está todo conectado
    if area_atual <= 1:
        return mapa
    
    # Para cada área (exceto a primeira), criar uma conexão com outra área
    for area_id in range(1, area_atual):
        # Encontrar todas as células desta área
        celulas_area = []
        for y in range(altura):
            for x in range(largura):
                if matriz_visitados[y][x] == area_id:
                    celulas_area.append((x, y))
        
        # Para cada célula desta área, verificar se há uma célula adjacente
        # que pertence a outra área conectada
        conexoes_possiveis = []
        for x, y in celulas_area:
            # Verificar os 4 vizinhos
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = x + dx, y + dy
                
                if (0 <= nx < largura and 0 <= ny < altura and 
                    mapa[ny][nx] == PAREDE and  # É uma parede que podemos derrubar
                    # Verificar se o próximo após a parede é outra área (não esta mesma)
                    0 <= nx + dx < largura and 0 <= ny + dy < altura and
                    matriz_visitados[ny + dy][nx + dx] != -1 and
                    matriz_visitados[ny + dy][nx + dx] != area_id):
                    conexoes_possiveis.append((nx, ny))
        
        # Se encontrou pontos de conexão possíveis, escolher um aleatoriamente
        if conexoes_possiveis:
            x, y = gerador.choice(conexoes_possiveis)
            mapa[y][x] = CORREDOR  # Transformar a parede em corredor
        
    return mapa
