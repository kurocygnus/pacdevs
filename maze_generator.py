import random
import copy
from templates import templates

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
    
    # Usamos o nível como seed para ter geração consistente mas diferente por fase
    seed = nivel * 1000 + random.randint(0, 999)
    gerador = random.Random(seed)
    
    # Inicializa o mapa com corredores
    mapa = [[CORREDOR for _ in range(largura)] for _ in range(altura)]
    
    # Adiciona paredes nas bordas
    for x in range(largura):
        mapa[0][x] = PAREDE
        mapa[altura-1][x] = PAREDE
    for y in range(altura):
        mapa[y][0] = PAREDE
        mapa[y][largura-1] = PAREDE
    
    # Vamos criar um mapa com simetria, como o Pac-Man original
    # Primeiro definimos a metade esquerda, depois espelhamos para a direita
    metade_largura = largura // 2
    
    # Criar padrão de grade interno (estilo Pac-Man) - apenas metade esquerda
    for y in range(2, altura-2, 2):
        for x in range(2, metade_largura, 2):
            # Probabilidade de criar um bloco varia com a distância do centro (para deixar o centro mais aberto)
            distancia_centro = abs(y - altura // 2)
            prob_bloco = 0.7 + (distancia_centro / altura) * 0.2  # Maior probabilidade longe do centro
            
            if gerador.random() < prob_bloco:
                # Criar um bloco de parede
                mapa[y][x] = PAREDE
                
                # Criar extensões em diferentes direções, baseado no nível
                # Níveis maiores têm padrões mais complexos
                num_extensoes = 1 + (nivel // 5)  # A cada 5 níveis aumenta a complexidade
                
                for _ in range(num_extensoes):
                    # Escolher direções aleatórias para extensões
                    direcao = gerador.choice(['cima', 'baixo', 'esquerda', 'direita'])
                    comprimento = gerador.randint(1, 2)  # Extensões de 1-2 blocos
                    
                    for i in range(1, comprimento + 1):
                        if direcao == 'cima' and y - i > 2:
                            mapa[y-i][x] = PAREDE
                        elif direcao == 'baixo' and y + i < altura-3:
                            mapa[y+i][x] = PAREDE
                        elif direcao == 'esquerda' and x - i > 2:
                            mapa[y][x-i] = PAREDE
                        elif direcao == 'direita' and x + i < metade_largura-1:
                            mapa[y][x+i] = PAREDE
    
    # Espelhar o mapa horizontalmente para criar simetria
    for y in range(altura):
        for x in range(metade_largura):
            if x > 0 and x < metade_largura - 1:  # Evitar sobrescrever as bordas
                espelho_x = largura - 1 - x
                mapa[y][espelho_x] = mapa[y][x]
                
    # Adicionar passagens randomizadas no centro
    centro_x = largura // 2
    for y in range(2, altura-2, 4):
        # 70% de chance de criar uma passagem no centro
        if gerador.random() < 0.7:
            mapa[y][centro_x] = CORREDOR
            # Adicionar alguns blocos de abertura ao redor
            if y > 2 and y < altura - 3:
                mapa[y-1][centro_x] = CORREDOR
                mapa[y+1][centro_x] = CORREDOR
    
    # Criar área central para os fantasmas
    criar_casa_fantasmas(mapa, largura, altura, gerador)
    
    # Inicializa o mapa de pontos
    mapa_pontos = [[0 for _ in range(largura)] for _ in range(altura)]
    
    # Adicionar pontos nos corredores
    for y in range(altura):
        for x in range(largura):
            if mapa[y][x] == CORREDOR:
                mapa_pontos[y][x] = PONTO
    
    # Adicionar power pellets nos cantos e posições estratégicas
    adicionar_power_pellets_cantos(mapa, mapa_pontos, nivel, gerador)
    
    # Garantir que o labirinto está completamente conectado
    mapa = garantir_conectividade(mapa, gerador)
    
    # Combinar os mapas de paredes e pontos
    mapa_final = combinar_mapas(mapa, mapa_pontos, nivel, gerador)
    
    return mapa_final

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
    
    # Tamanho da casa dos fantasmas - varia ligeiramente por nível
    # mas mantém-se dentro dos padrões do jogo original
    base_largura = min(7, largura // 3)
    base_altura = min(5, altura // 5)
    
    # Pequena variação no tamanho - para mapas diferentes entre fases
    variacao_largura = gerador.randint(-1, 1) * 2
    variacao_altura = gerador.randint(-1, 1)
    
    casa_largura = base_largura + variacao_largura
    casa_altura = base_altura + variacao_altura
    
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
    
    # Ocasionalmente criar pilares dentro da casa (em níveis avançados)
    if gerador.random() < 0.3:
        pilar_x = centro_x + gerador.choice([-1, 1])
        pilar_y = centro_y + gerador.choice([-1, 0, 1])
        
        # Verificar se a posição é válida
        if (inicio_x < pilar_x < fim_x - 1) and (inicio_y < pilar_y < fim_y - 1):
            mapa[pilar_y][pilar_x] = PAREDE

def adicionar_power_pellets_cantos(mapa, mapa_pontos, nivel=1, gerador=None):
    """
    Adiciona power pellets no mapa, com variação baseada no nível.
    Mantém a tradição de power pellets nos cantos, mas adiciona alguns extras
    em níveis mais avançados.
    """
    # Se não foi fornecido gerador, usa o módulo random padrão
    if gerador is None:
        gerador = random
    altura = len(mapa)
    largura = len(mapa[0])
    
    # Número base de power pellets (normalmente 4, como no original)
    num_power_pellets = 4
    
    # A cada 3 níveis, adiciona um power pellet extra (até o limite de 8)
    num_extras = min(4, nivel // 3)
    num_power_pellets += num_extras
    
    # Posições tradicionais dos power pellets (próximas aos cantos)
    posicoes_cantos = [
        (2, 2),                    # Superior esquerdo
        (2, largura - 3),          # Superior direito
        (altura - 3, 2),           # Inferior esquerdo
        (altura - 3, largura - 3)  # Inferior direito
    ]
    
    # Adicionar power pellets nos cantos (sempre presente)
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
    
    # Adicionar power pellets extras em posições estratégicas (para níveis avançados)
    if num_extras > 0:
        # Posições potenciais para power pellets extras
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
        
        # Adicionar power pellets extras em posições aleatórias
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
    
    # No Pac-Man original, os portais normalmente estão no meio horizontal
    # Para adicionar variedade, podemos deslocar ligeiramente baseado no nível
    
    # Calcular posição y do portal com base no nível
    # Em níveis baixos: perto do meio
    # Em níveis altos: pode estar mais para cima ou para baixo
    variacao = altura // 6  # Máximo de variação
    deslocamento = (gerador.randint(-variacao, variacao) * nivel // 10) % variacao
    
    # Portal y position - normalmente próximo ao meio, mas com variação
    portal_y = (altura // 2 + deslocamento) % (altura - 4) + 2  # Garantir que fique dentro dos limites
    
    # Criar portal esquerdo
    for x in range(3):
        mapa[portal_y][x] = CORREDOR
    
    # Criar portal direito
    for x in range(largura - 3, largura):
        mapa[portal_y][x] = CORREDOR
    
    # Em níveis avançados, pode adicionar um segundo par de portais
    if nivel > 5 and gerador.random() < 0.4:
        # Portal secundário em uma posição diferente
        portal2_y = (portal_y + altura // 2) % (altura - 4) + 2
        
        # Verificar se está suficientemente distante do primeiro portal
        if abs(portal2_y - portal_y) > altura // 4:
            # Criar segundo par de portais
            for x in range(3):
                mapa[portal2_y][x] = CORREDOR
            
            for x in range(largura - 3, largura):
                mapa[portal2_y][x] = CORREDOR

def combinar_mapas(mapa, mapa_pontos, nivel=1, gerador=None):
    """
    Combina o mapa de paredes com o mapa de pontos.
    Recebe o nível e um gerador para manter consistência na randomização.
    """
    # Se não foi fornecido gerador, usa o módulo random padrão
    if gerador is None:
        gerador = random
    altura = len(mapa)
    largura = len(mapa[0])
    mapa_final = [[0 for _ in range(largura)] for _ in range(altura)]
    
    for y in range(altura):
        for x in range(largura):
            if mapa[y][x] == PAREDE:  # Parede
                mapa_final[y][x] = PAREDE
            elif mapa[y][x] == CASA_FANTASMA:  # Casa dos fantasmas
                mapa_final[y][x] = CASA_FANTASMA
            elif mapa_pontos[y][x] == PONTO:  # Ponto comum
                mapa_final[y][x] = PONTO
            elif mapa_pontos[y][x] == POWER_PELLET:  # Power pellet
                mapa_final[y][x] = POWER_PELLET
            else:  # Corredor vazio
                mapa_final[y][x] = CORREDOR
    
    # Garantir que os portais estão desobstruídos
    gerar_portais(mapa_final, nivel, gerador)
    
    return mapa_final

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