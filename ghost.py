import pygame
import random
import math
from collections import deque
from maze_generator import CASA_FANTASMA, PAREDE


class GhostSprite:
    """Gerencia os sprites dos fantasmas"""

    def __init__(self, image_path):
        self.image = pygame.image.load(image_path).convert_alpha()
        # Redimensionar para o tamanho apropriado se necessário
        # Assumindo que queremos fantasmas de tamanho 30x30 pixels
        target_size = (30, 30)
        self.image = pygame.transform.scale(self.image, target_size)


class Ghost:
    """Classe que representa um fantasma no jogo"""

    # Estados do fantasma
    NORMAL = 0
    VULNERAVEL = 1
    COMIDO = 2

    # Modos de movimento
    PERSEGUIR = 0  # Perseguir o pacman
    DISPERSAR = 1  # Ir para cantos específicos
    ASSUSTADO = 2  # Movimento aleatório quando vulnerável

    def __init__(self, x, y, sprite_path, tile_size, personalidade="perseguidor"):
        """
        Inicializa um novo fantasma.

        Args:
            x, y: Posição inicial
            sprite_path: Caminho para a imagem do fantasma
            tile_size: Tamanho de cada bloco do labirinto
            personalidade: Define o comportamento do fantasma ('perseguidor', 'emboscador',
                          'vagante' ou 'imprevisível')
        """
        self.x = x
        self.y = y
        self.tile_size = tile_size
        self.sprite = GhostSprite(sprite_path)
        self.velocidade = 4
        self.estado = self.NORMAL
        self.modo = self.PERSEGUIR
        self.personalidade = personalidade
        self.direcao_atual = random.choice(["up", "down", "left", "right"])
        self.tempo_vulneravel = 0
        self.tempo_modo_atual = 0
        self.tempo_total = 0
        self.posicao_inicio = self._alinhar_top_left_ao_tile(x, y)
        self.comido = False

        # Cada fantasma tem uma posição alvo diferente no modo dispersar
        self.posicao_dispersar = self._definir_posicao_dispersar()

        # Cor para desenhar em modo de debug
        self.cor = (255, 0, 0)  # Vermelho por padrão

    def _definir_posicao_dispersar(self):
        """Define para onde o fantasma vai quando está no modo dispersar"""
        if self.personalidade == "perseguidor":
            return (0, 0)  # Canto superior esquerdo
        elif self.personalidade == "emboscador":
            return (800, 0)  # Canto superior direito
        elif self.personalidade == "vagante":
            return (0, 600)  # Canto inferior esquerdo
        else:  # "imprevisível"
            return (800, 600)  # Canto inferior direito

    def _esta_na_casa(self, mapa):
        """Retorna True se o fantasma está dentro da casa dos fantasmas."""
        # Se mapa não for fornecido (chamada de voltar_ao_normal), não verifica
        if mapa is None:
            return False

        # Pegar posição central do fantasma
        col = int((self.x + self.tile_size // 2) // self.tile_size)
        row = int((self.y + self.tile_size // 2) // self.tile_size)

        # Verificar diretamente se está na casa
        if 0 <= row < len(mapa) and 0 <= col < len(mapa[0]):
            return mapa[row][col] == CASA_FANTASMA

        return False

    def _encontrar_saida_casa(self, mapa):
        """Encontra a saída da casa dos fantasmas"""
        altura = len(mapa)
        largura = len(mapa[0])

        # Procurar por células CASA_FANTASMA na matriz do mapa
        casas = []
        for row in range(altura):
            for col in range(largura):
                if mapa[row][col] == CASA_FANTASMA:
                    casas.append((col, row))

        if not casas:
            return None

        # Verificar acima de cada casa para encontrar uma saída
        for col, row in casas:
            # Verificar se a célula acima existe e não é parede
            if row > 0 and mapa[row - 1][col] != PAREDE:
                # Retornar a posição exata (em pixels) da saída
                return (
                    col * self.tile_size + self.tile_size // 2,
                    (row - 1) * self.tile_size + self.tile_size // 2,
                )

        return None

    def tornar_vulneravel(self, duracao=500):
        """Torna o fantasma vulnerável por um período, exceto se estiver COMIDO."""
        if self.estado != self.COMIDO:
            self.estado = self.VULNERAVEL
            self.modo = self.ASSUSTADO
            self.tempo_vulneravel = duracao
            self.velocidade = 3

    def foi_comido(self):
        """Marca o fantasma como comido e o envia de volta para a casa"""
        self.estado = self.COMIDO
        self.modo = self.PERSEGUIR
        self.comido = True
        self.velocidade = 8
        # Quando um fantasma é comido, ele não pode ser comido novamente até voltar ao normal
        self.tempo_vulneravel = 0

        # Garantir que o alvo seja o centro da casa (posição inicial)
        # Recalcular a posição inicial (pode ter mudado durante o jogo)
        self.posicao_inicio = self._alinhar_top_left_ao_tile(*self.posicao_inicio)

    def voltar_ao_normal(self):
        """Retorna o fantasma ao estado normal"""
        self.estado = self.NORMAL
        self.modo = self.PERSEGUIR
        self.velocidade = 4

        # Direções preferidas quando sai da casa (priorizar UP)
        if self._esta_na_casa(
            None
        ):  # None é seguro aqui, _esta_na_casa vai ser verificado no movimento
            self.direcao_atual = "up"  # Quando volta ao normal na casa, vai para cima
        else:
            # Escolher direção inicial aleatória quando volta ao normal para evitar padrões repetitivos
            self.direcao_atual = random.choice(["up", "down", "left", "right"])

        # Pequeno atraso antes de começar a perseguir novamente (alternância de modos)
        self.tempo_modo_atual = 0

    def pode_mover_para(self, nova_x, nova_y, mapa):
        """Verificação de movimento do fantasma com tratamento especial para a casa"""
        # Usar o centro do sprite para verificação
        centro_x = nova_x + self.tile_size // 2
        centro_y = nova_y + self.tile_size // 2

        # Converter para posição na grade
        col = int(centro_x // self.tile_size)
        row = int(centro_y // self.tile_size)

        # Verificar limites do mapa (portais)
        if row < 0 or row >= len(mapa) or col < 0 or col >= len(mapa[0]):
            return True  # Portais são sempre permitidos

        # Verificar se é parede (nunca pode atravessar)
        if mapa[row][col] == PAREDE:
            return False

        # Regras especiais para a casa dos fantasmas
        if mapa[row][col] == CASA_FANTASMA:
            # Posição atual do fantasma
            ghost_col = int((self.x + self.tile_size // 2) // self.tile_size)
            ghost_row = int((self.y + self.tile_size // 2) // self.tile_size)

            # Verificar se está atualmente na casa
            esta_na_casa = False
            if 0 <= ghost_row < len(mapa) and 0 <= ghost_col < len(mapa[0]):
                esta_na_casa = mapa[ghost_row][ghost_col] == CASA_FANTASMA

            if esta_na_casa:
                # Se já está na casa, pode se mover livremente dentro dela
                return True
            elif self.estado == self.COMIDO:
                # Se está comido, pode entrar na casa
                return True
            else:
                # Se está fora da casa e não está comido, não pode entrar
                return False

        # Qualquer outra célula é válida
        return True

    def decidir_direcao(self, pacman_x, pacman_y, mapa):
        """Escolhe a próxima direção apenas a partir do centro de um tile."""
        ghost_col, ghost_row = self._tile_atual()
        target_x, target_y = self._calcular_alvo(pacman_x, pacman_y)
        direcoes_validas = self._direcoes_validas(mapa)
        if not direcoes_validas:
            return self.direcao_atual

        if self._esta_na_casa(mapa) and self.estado != self.COMIDO:
            saida = self._encontrar_saida_casa(mapa)
            if saida:
                target_x = int(saida[0] // self.tile_size)
                target_y = int(saida[1] // self.tile_size)
                proximo_passo = self._proxima_direcao_por_caminho(
                    target_x, target_y, mapa, direcoes_validas
                )
                if proximo_passo:
                    return proximo_passo
            ordem_saida = {"up": 0, "left": 1, "right": 1, "down": 3}
            return min(
                direcoes_validas,
                key=lambda direcao: (
                    self._distancia_do_proximo_tile(direcao, target_x, target_y),
                    ordem_saida.get(direcao, 2),
                ),
            )

        if self.estado == self.VULNERAVEL:
            direcao_fuga = self._melhor_direcao_de_fuga(
                pacman_x, pacman_y, mapa, direcoes_validas
            )
            if direcao_fuga:
                return direcao_fuga

        proximo_passo = self._proxima_direcao_por_caminho(
            target_x, target_y, mapa, direcoes_validas
        )
        if proximo_passo:
            return proximo_passo

        ordenadas = sorted(
            direcoes_validas,
            key=lambda direcao: self._distancia_do_proximo_tile(
                direcao, target_x, target_y
            ),
        )

        if self.estado == self.COMIDO or self.personalidade == "perseguidor":
            return ordenadas[0]
        if self.personalidade == "emboscador":
            return (
                ordenadas[1]
                if len(ordenadas) > 1 and random.random() < 0.1
                else ordenadas[0]
            )
        if self.personalidade == "vagante":
            return (
                random.choice(ordenadas[:2])
                if len(ordenadas) > 1 and random.random() < 0.25
                else ordenadas[0]
            )
        return (
            random.choice(ordenadas[:2])
            if len(ordenadas) > 1 and random.random() < 0.35
            else ordenadas[0]
        )

    def _calcular_alvo(self, pacman_x, pacman_y):
        """Calcula a posição alvo do fantasma com base no seu estado e personalidade"""
        pacman_col = int(pacman_x // self.tile_size)
        pacman_row = int(pacman_y // self.tile_size)

        # Calcular a direção atual do Pacman com base nas coordenadas
        try:
            # Tentar acessar a direção do módulo pacman (variável global)
            from pacman import direcao_pacman_global

            direcao_pacman = direcao_pacman_global
        except:
            # Se não conseguir, estimar com base na posição atual e anterior
            # Usando um valor padrão como fallback
            direcao_pacman = "right"  # valor padrão

        # Se estiver voltando para a casa após ser comido
        if self.estado == self.COMIDO:
            # Usar a posição inicial exata em tiles
            return (
                int(self.posicao_inicio[0] // self.tile_size),
                int(self.posicao_inicio[1] // self.tile_size),
            )

        # Se estiver no modo dispersar
        if self.modo == self.DISPERSAR:
            # Usar valores fixos de dispersão baseados em uma estimativa do tamanho do mapa
            mapa_altura = 15  # Estimativa baseada em SCREEN_HEIGHT / TILE_SIZE
            mapa_largura = 20  # Estimativa baseada em SCREEN_WIDTH / TILE_SIZE

            if self.personalidade == "perseguidor":
                return (1, 1)  # Canto superior esquerdo
            elif self.personalidade == "emboscador":
                return (mapa_largura - 2, 1)  # Canto superior direito
            elif self.personalidade == "vagante":
                return (1, mapa_altura - 2)  # Canto inferior esquerdo
            else:  # "imprevisível"
                return (mapa_largura - 2, mapa_altura - 2)  # Canto inferior direito

        # No modo de perseguição, o comportamento depende da personalidade
        if self.personalidade == "perseguidor":
            # Mira diretamente no Pacman (Blinky) - comportamento agressivo
            return (pacman_col, pacman_row)

        elif self.personalidade == "emboscador":
            # Mira algumas casas à frente do Pacman na direção que ele está olhando.
            # Tenta prever onde o Pacman estará e interceptá-lo
            offset_x, offset_y = 0, 0
            if direcao_pacman == "right":
                offset_x = 2
            elif direcao_pacman == "left":
                offset_x = -2
            elif direcao_pacman == "up":
                offset_y = -2
            else:  # down
                offset_y = 2

            # Limitar as coordenadas para não ultrapassar os limites do mapa
            target_x = max(
                0, min(pacman_col + offset_x, 30)
            )  # Assumindo largura máxima de 30
            target_y = max(
                0, min(pacman_row + offset_y, 30)
            )  # Assumindo altura máxima de 30
            return (target_x, target_y)

        elif self.personalidade == "vagante":
            # Persegue um ponto levemente à frente do Pacman, sem abrir distância demais.
            offset_x, offset_y = 0, 0
            if direcao_pacman == "right":
                offset_x = 1
            elif direcao_pacman == "left":
                offset_x = -1
            elif direcao_pacman == "up":
                offset_y = -1
            else:  # down
                offset_y = 1
            return (
                max(0, min(pacman_col + offset_x, 30)),
                max(0, min(pacman_row + offset_y, 30)),
            )

        else:  # "imprevisível" (Clyde)
            return (pacman_col, pacman_row)

    def _alinhar_top_left_ao_tile(self, x, y):
        """Converte qualquer ponto dentro do tile para o top-left daquele tile."""
        return (
            int(x // self.tile_size) * self.tile_size,
            int(y // self.tile_size) * self.tile_size,
        )

    def _centro_atual(self):
        return self.x + self.tile_size // 2, self.y + self.tile_size // 2

    def _tile_atual(self):
        centro_x, centro_y = self._centro_atual()
        return int(centro_x // self.tile_size), int(centro_y // self.tile_size)

    def _centro_do_tile(self, col, row):
        return (
            col * self.tile_size + self.tile_size // 2,
            row * self.tile_size + self.tile_size // 2,
        )

    def _delta_direcao(self, direcao):
        deltas = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0),
        }
        return deltas.get(direcao, (0, 0))

    def _direcao_oposta(self):
        return {
            "up": "down",
            "down": "up",
            "left": "right",
            "right": "left",
        }

    def _esta_centralizado(self, tolerancia=2):
        col, row = self._tile_atual()
        centro_x, centro_y = self._centro_do_tile(col, row)
        atual_x, atual_y = self._centro_atual()
        return (
            abs(atual_x - centro_x) <= tolerancia
            and abs(atual_y - centro_y) <= tolerancia
        )

    def _snap_para_centro_do_tile(self):
        col, row = self._tile_atual()
        centro_x, centro_y = self._centro_do_tile(col, row)
        self.x = centro_x - self.tile_size // 2
        self.y = centro_y - self.tile_size // 2

    def _tile_permitido(self, col, row, mapa):
        if row < 0 or row >= len(mapa) or col < 0 or col >= len(mapa[0]):
            return True
        if mapa[row][col] == PAREDE:
            return False
        if mapa[row][col] == CASA_FANTASMA:
            atual_col, atual_row = self._tile_atual()
            esta_na_casa = (
                0 <= atual_row < len(mapa)
                and 0 <= atual_col < len(mapa[0])
                and mapa[atual_row][atual_col] == CASA_FANTASMA
            )
            return esta_na_casa or self.estado == self.COMIDO
        return True

    def _direcoes_validas(self, mapa):
        col, row = self._tile_atual()
        direcoes = []
        for direcao in ["up", "down", "left", "right"]:
            dx, dy = self._delta_direcao(direcao)
            if self._tile_permitido(col + dx, row + dy, mapa):
                direcoes.append(direcao)
        return direcoes

    def _pode_ir_direcao(self, direcao, mapa):
        col, row = self._tile_atual()
        dx, dy = self._delta_direcao(direcao)
        return self._tile_permitido(col + dx, row + dy, mapa)

    def _distancia_do_proximo_tile(self, direcao, target_x, target_y):
        col, row = self._tile_atual()
        dx, dy = self._delta_direcao(direcao)
        return self._calcular_distancia(col + dx, row + dy, target_x, target_y)

    def _melhor_direcao_de_fuga(self, pacman_x, pacman_y, mapa, direcoes_validas):
        """Escolhe o vizinho que fica mais longe do Pac-Man pelo caminho real."""
        pacman_col = max(0, min(int(pacman_x // self.tile_size), len(mapa[0]) - 1))
        pacman_row = max(0, min(int(pacman_y // self.tile_size), len(mapa) - 1))
        distancias = self._mapa_de_distancias((pacman_col, pacman_row), mapa)
        col, row = self._tile_atual()

        candidatos = []
        for direcao in direcoes_validas:
            dx, dy = self._delta_direcao(direcao)
            proximo = (col + dx, row + dy)
            distancia = distancias.get(proximo)
            if distancia is None:
                distancia = self._calcular_distancia(
                    proximo[0], proximo[1], pacman_col, pacman_row
                )
            candidatos.append((direcao, distancia))

        if not candidatos:
            return None

        candidatos.sort(key=lambda item: item[1], reverse=True)
        melhores = [item for item in candidatos if item[1] == candidatos[0][1]]
        return random.choice(melhores)[0]

    def _mapa_de_distancias(self, inicio, mapa):
        if not self._tile_permitido_para_busca(inicio[0], inicio[1], mapa):
            inicio = self._tile_andavel_mais_proximo(inicio[0], inicio[1], mapa)
            if inicio is None:
                return {}

        distancias = {inicio: 0}
        fila = deque([inicio])
        while fila:
            col, row = fila.popleft()
            for direcao in ("up", "down", "left", "right"):
                dx, dy = self._delta_direcao(direcao)
                proximo = (col + dx, row + dy)
                if proximo in distancias:
                    continue
                if not self._tile_permitido_para_busca(proximo[0], proximo[1], mapa):
                    continue
                distancias[proximo] = distancias[(col, row)] + 1
                fila.append(proximo)
        return distancias

    def _proxima_direcao_por_caminho(self, target_x, target_y, mapa, direcoes_validas):
        """Retorna o primeiro passo de um caminho real pela grade até o alvo."""
        inicio = self._tile_atual()
        altura = len(mapa)
        largura = len(mapa[0])
        alvo = (
            max(0, min(int(target_x), largura - 1)),
            max(0, min(int(target_y), altura - 1)),
        )

        if mapa[alvo[1]][alvo[0]] == PAREDE:
            alvo = self._tile_andavel_mais_proximo(alvo[0], alvo[1], mapa)
            if alvo is None:
                return None

        visitados = {inicio}
        fila = deque()
        for direcao in direcoes_validas:
            dx, dy = self._delta_direcao(direcao)
            proximo = (inicio[0] + dx, inicio[1] + dy)
            if proximo in visitados:
                continue
            fila.append((proximo[0], proximo[1], direcao))
            visitados.add(proximo)

        while fila:
            col, row, primeira_direcao = fila.popleft()
            if (col, row) == alvo:
                return primeira_direcao

            for direcao in ("up", "down", "left", "right"):
                dx, dy = self._delta_direcao(direcao)
                nx, ny = col + dx, row + dy
                if (nx, ny) in visitados:
                    continue
                if not self._tile_permitido_para_busca(nx, ny, mapa):
                    continue
                visitados.add((nx, ny))
                fila.append((nx, ny, primeira_direcao))

        return None

    def _tile_andavel_mais_proximo(self, target_x, target_y, mapa):
        altura = len(mapa)
        largura = len(mapa[0])
        melhor = None
        melhor_distancia = float("inf")
        for row in range(altura):
            for col in range(largura):
                if mapa[row][col] == PAREDE:
                    continue
                distancia = self._calcular_distancia(col, row, target_x, target_y)
                if distancia < melhor_distancia:
                    melhor = (col, row)
                    melhor_distancia = distancia
        return melhor

    def _tile_permitido_para_busca(self, col, row, mapa):
        if row < 0 or row >= len(mapa) or col < 0 or col >= len(mapa[0]):
            return False
        if mapa[row][col] == PAREDE:
            return False
        if (
            mapa[row][col] == CASA_FANTASMA
            and self.estado != self.COMIDO
            and not self._esta_na_casa(mapa)
        ):
            return False
        return True

    def _mover_um_passo(self, direcao, mapa):
        if not self._pode_ir_direcao(direcao, mapa):
            return False

        col, row = self._tile_atual()
        dx, dy = self._delta_direcao(direcao)
        target_x, target_y = self._centro_do_tile(col + dx, row + dy)
        atual_x, atual_y = self._centro_atual()

        if dx:
            passo = min(self.velocidade, abs(target_x - atual_x))
            self.x += dx * passo
        elif dy:
            passo = min(self.velocidade, abs(target_y - atual_y))
            self.y += dy * passo
        return True

    def _continuar_ate_centro_da_direcao(self):
        col, row = self._tile_atual()
        centro_x, centro_y = self._centro_do_tile(col, row)
        atual_x, atual_y = self._centro_atual()
        dx, dy = self._delta_direcao(self.direcao_atual)

        if dx:
            target_col = (
                col
                if (dx > 0 and atual_x <= centro_x) or (dx < 0 and atual_x >= centro_x)
                else col + dx
            )
            target_x, _ = self._centro_do_tile(target_col, row)
            passo = min(self.velocidade, abs(target_x - atual_x))
            self.x += (1 if target_x > atual_x else -1) * passo
        elif dy:
            target_row = (
                row
                if (dy > 0 and atual_y <= centro_y) or (dy < 0 and atual_y >= centro_y)
                else row + dy
            )
            _, target_y = self._centro_do_tile(col, target_row)
            passo = min(self.velocidade, abs(target_y - atual_y))
            self.y += (1 if target_y > atual_y else -1) * passo
        else:
            self._snap_para_centro_do_tile()

    def _aplicar_portais(self, mapa):
        largura_tela = len(mapa[0]) * self.tile_size
        altura_tela = len(mapa) * self.tile_size

        if self.x < -self.tile_size:
            self.x = largura_tela - self.tile_size
        elif self.x >= largura_tela:
            self.x = 0

        if self.y < -self.tile_size:
            self.y = altura_tela - self.tile_size
        elif self.y >= altura_tela:
            self.y = 0

    def _calcular_nova_posicao(self, direcao):
        """Calcula a nova posição baseada na direção"""
        nova_x, nova_y = self.x, self.y

        if direcao == "up":
            nova_y -= self.velocidade
        elif direcao == "down":
            nova_y += self.velocidade
        elif direcao == "left":
            nova_x -= self.velocidade
        elif direcao == "right":
            nova_x += self.velocidade

        return nova_x, nova_y

    def _calcular_distancia(self, x1, y1, x2, y2):
        """Calcula a distância euclidiana entre dois pontos"""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def mover(self, pacman_x, pacman_y, mapa):
        """Move o fantasma pela grade, evitando curvas fora do centro dos tiles."""
        self.tempo_total += 1

        if self.estado == self.VULNERAVEL:
            self.tempo_vulneravel -= 1
            if self.tempo_vulneravel <= 0:
                self.voltar_ao_normal()

        if not self._esta_centralizado():
            self._continuar_ate_centro_da_direcao()
            self._aplicar_portais(mapa)
            return

        self._snap_para_centro_do_tile()

        if self.estado == self.COMIDO and self._esta_na_casa(mapa):
            inicio_col = int(self.posicao_inicio[0] // self.tile_size)
            inicio_row = int(self.posicao_inicio[1] // self.tile_size)
            if self._tile_atual() == (inicio_col, inicio_row):
                self.x, self.y = self.posicao_inicio
                self.voltar_ao_normal()
                self.comido = False
                return

        deve_decidir = (
            not self._pode_ir_direcao(self.direcao_atual, mapa)
            or self._esta_em_intersecao(mapa)
            or self.estado == self.VULNERAVEL
            or self.estado == self.COMIDO
            or self._esta_na_casa(mapa)
        )

        if deve_decidir:
            self.direcao_atual = self.decidir_direcao(pacman_x, pacman_y, mapa)

        if not self._mover_um_passo(self.direcao_atual, mapa):
            direcoes_validas = self._direcoes_validas(mapa)
            if direcoes_validas:
                self.direcao_atual = random.choice(direcoes_validas)
                self._mover_um_passo(self.direcao_atual, mapa)

        self._aplicar_portais(mapa)

    def verificar_colisao_pacman(self, pacman_x, pacman_y):
        """
        Verifica se o fantasma colidiu com o Pacman.
        Retorna:
            0 - Sem colisão
            1 - Colisão normal (Pacman perde vida)
            2 - Fantasma vulnerável (Fantasma é comido)
        """
        # Distância para considerar colisão
        dist_colisao = self.tile_size * 0.7

        # Calcular distância entre centro do fantasma e do pacman
        ghost_center_x = self.x + self.tile_size // 2
        ghost_center_y = self.y + self.tile_size // 2
        pacman_center_x = pacman_x + self.tile_size // 2
        pacman_center_y = pacman_y + self.tile_size // 2

        distancia = self._calcular_distancia(
            ghost_center_x, ghost_center_y, pacman_center_x, pacman_center_y
        )

        if distancia < dist_colisao:
            # Verificar estado do fantasma
            if self.estado == self.VULNERAVEL:
                return 2  # Fantasma é comido
            elif self.estado == self.NORMAL:
                return 1  # Pacman perde vida

        return 0  # Sem colisão

    def verificar_colisao_com_fantasma(self, outro_fantasma, mapa=None):
        """
        Verifica se este fantasma colidiu com outro fantasma.
        Retorna True se colidir, False caso contrário.
        """
        # Ignorar colisões para fantasmas comidos (estão voltando para casa)
        if self.estado == self.COMIDO or outro_fantasma.estado == self.COMIDO:
            return False

        # Ignorar colisões dentro da casa dos fantasmas
        if mapa is not None and (
            self._esta_na_casa(mapa) or outro_fantasma._esta_na_casa(mapa)
        ):
            return False

        # Distância para considerar colisão (um pouco menor que com o Pacman)
        dist_colisao = self.tile_size * 0.6

        # Calcular distância entre os centros dos fantasmas
        self_center_x = self.x + self.tile_size // 2
        self_center_y = self.y + self.tile_size // 2
        outro_center_x = outro_fantasma.x + outro_fantasma.tile_size // 2
        outro_center_y = outro_fantasma.y + outro_fantasma.tile_size // 2

        distancia = self._calcular_distancia(
            self_center_x, self_center_y, outro_center_x, outro_center_y
        )

        return distancia < dist_colisao

    def reagir_a_colisao(self, mapa):
        """
        Reage a uma colisão com outro fantasma mudando de direção.
        """
        self._snap_para_centro_do_tile()
        oposta = self._direcao_oposta().get(self.direcao_atual)
        direcoes = [
            direcao
            for direcao in self._direcoes_validas(mapa)
            if direcao not in (self.direcao_atual, oposta)
        ]
        if not direcoes:
            direcoes = [
                direcao
                for direcao in self._direcoes_validas(mapa)
                if direcao != self.direcao_atual
            ]
        if direcoes:
            self.direcao_atual = random.choice(direcoes)

    def desenhar(self, screen):
        """Desenha o fantasma na tela"""
        # Desenhar sprite base
        screen.blit(self.sprite.image, (self.x, self.y))

        # Mostrar estado visualmente com overlays
        overlay = pygame.Surface((self.tile_size, self.tile_size), pygame.SRCALPHA)

        if self.estado == self.VULNERAVEL:
            # Piscar quando o tempo de vulnerabilidade estiver acabando
            if self.tempo_vulneravel < 100 and self.tempo_vulneravel % 20 < 10:
                overlay.fill(
                    (255, 255, 255, 100)
                )  # Branco piscando (vulnerabilidade acabando)
            else:
                overlay.fill((0, 0, 255, 150))  # Azul semi-transparente (vulnerável)
            screen.blit(overlay, (self.x, self.y))

        elif self.estado == self.COMIDO:
            # Fantasma comido (apenas olhos)
            overlay.fill((0, 0, 0, 200))  # Preto semi-transparente
            screen.blit(overlay, (self.x, self.y))

            # Desenhar olhos brancos
            olho_raio = self.tile_size // 6
            olho_y = self.y + self.tile_size // 3

            # Olho esquerdo
            olho_esq_x = self.x + self.tile_size // 3 - olho_raio // 2
            pygame.draw.circle(
                screen,
                (255, 255, 255),
                (olho_esq_x + olho_raio, olho_y + olho_raio),
                olho_raio,
            )

            # Olho direito
            olho_dir_x = self.x + 2 * self.tile_size // 3 - olho_raio // 2
            pygame.draw.circle(
                screen,
                (255, 255, 255),
                (olho_dir_x + olho_raio, olho_y + olho_raio),
                olho_raio,
            )

        else:  # NORMAL
            # Adicionar efeito de brilho sutil de acordo com a personalidade
            if self.personalidade == "perseguidor":
                overlay.fill((255, 0, 0, 50))  # Vermelho sutil
            elif self.personalidade == "emboscador":
                overlay.fill((255, 192, 203, 50))  # Rosa sutil
            elif self.personalidade == "vagante":
                overlay.fill((0, 255, 255, 50))  # Ciano sutil
            else:  # "imprevisível"
                overlay.fill((255, 165, 0, 50))  # Laranja sutil

            screen.blit(overlay, (self.x, self.y))

        # Indicador de direção (pequena seta na direção atual)
        if self.estado != self.COMIDO:
            seta_tamanho = self.tile_size // 6
            seta_cor = (255, 255, 255)
            centro_x = self.x + self.tile_size // 2
            centro_y = self.y + self.tile_size // 2

            if self.direcao_atual == "right":
                pontos = [
                    (centro_x, centro_y),
                    (centro_x + seta_tamanho, centro_y - seta_tamanho // 2),
                    (centro_x + seta_tamanho, centro_y + seta_tamanho // 2),
                ]
            elif self.direcao_atual == "left":
                pontos = [
                    (centro_x, centro_y),
                    (centro_x - seta_tamanho, centro_y - seta_tamanho // 2),
                    (centro_x - seta_tamanho, centro_y + seta_tamanho // 2),
                ]
            elif self.direcao_atual == "up":
                pontos = [
                    (centro_x, centro_y),
                    (centro_x - seta_tamanho // 2, centro_y - seta_tamanho),
                    (centro_x + seta_tamanho // 2, centro_y - seta_tamanho),
                ]
            else:  # "down"
                pontos = [
                    (centro_x, centro_y),
                    (centro_x - seta_tamanho // 2, centro_y + seta_tamanho),
                    (centro_x + seta_tamanho // 2, centro_y + seta_tamanho),
                ]

            pygame.draw.polygon(screen, seta_cor, pontos)

    def _centralizar_na_grade(self):
        """Centraliza o fantasma na grade para melhor navegação nos corredores"""
        # Obter posição atual em termos de células do grid
        grid_x = int(self.x // self.tile_size)
        grid_y = int(self.y // self.tile_size)

        # Calcular centro da célula atual
        centro_celula_x = grid_x * self.tile_size + self.tile_size // 2
        centro_celula_y = grid_y * self.tile_size + self.tile_size // 2

        # Centralizar fantasma na célula atual quando estiver movendo-se
        centro_fantasma_x = self.x + self.tile_size // 2
        centro_fantasma_y = self.y + self.tile_size // 2

        # Tolerância maior para centralização (evita que fantasmas fiquem presos)
        tolerancia = self.velocidade * 1.5

        # Centralizar somente se estiver significativamente desalinhado
        # Isso permite movimento mais fluido sem ficar preso em corredores
        if self.direcao_atual in ["left", "right"]:
            # Se movendo horizontalmente, centralizar verticalmente
            if abs(centro_fantasma_y - centro_celula_y) > tolerancia:
                if centro_fantasma_y > centro_celula_y:
                    self.y -= min(
                        self.velocidade / 3, centro_fantasma_y - centro_celula_y
                    )
                else:
                    self.y += min(
                        self.velocidade / 3, centro_celula_y - centro_fantasma_y
                    )

        elif self.direcao_atual in ["up", "down"]:
            # Se movendo verticalmente, centralizar horizontalmente
            if abs(centro_fantasma_x - centro_celula_x) > tolerancia:
                if centro_fantasma_x > centro_celula_x:
                    self.x -= min(
                        self.velocidade / 3, centro_fantasma_x - centro_celula_x
                    )
                else:
                    self.x += min(
                        self.velocidade / 3, centro_celula_x - centro_fantasma_x
                    )

    def _esta_em_intersecao(self, mapa):
        """Verifica se o fantasma está em uma interseção (mais de uma direção possível)"""
        if not self._esta_centralizado(3):
            return False

        direcoes_validas = self._direcoes_validas(mapa)
        direcoes_possiveis = len(direcoes_validas)

        # Considerar uma interseção "real" se tivermos mais de 2 direções
        # ou se temos exatamente 2 direções que não são opostas (curva em L)
        if direcoes_possiveis > 2:
            return True
        elif direcoes_possiveis == 2:
            # Verificar se as duas direções são opostas (corredor) ou formam uma curva (interseção)
            pares_opostos = [{"up", "down"}, {"left", "right"}]
            eh_corredor = False

            for par in pares_opostos:
                if set(direcoes_validas).issubset(par):
                    eh_corredor = True
                    break

            return not eh_corredor  # É interseção se NÃO for um corredor reto

        return False  # Sem saídas ou beco sem saída

    def _ajustar_posicao_no_corredor(self, mapa):
        """Faz pequenos ajustes na posição para evitar ficar preso em cantos ou paredes"""
        # Obter posição atual na grade
        ghost_col = int((self.x + self.tile_size // 2) // self.tile_size)
        ghost_row = int((self.y + self.tile_size // 2) // self.tile_size)

        # Centro da célula atual
        centro_x = ghost_col * self.tile_size + self.tile_size // 2
        centro_y = ghost_row * self.tile_size + self.tile_size // 2

        # Centralização suave quando estiver movendo em corredores
        if self.direcao_atual in ["left", "right"]:
            # Se movendo horizontalmente, centralizar verticalmente
            diferenca_y = (self.y + self.tile_size // 2) - centro_y
            if abs(diferenca_y) > 2:  # Apenas se estiver desalinhado
                ajuste = min(self.velocidade // 2, abs(diferenca_y))
                if diferenca_y > 0:
                    self.y -= ajuste
                else:
                    self.y += ajuste

        elif self.direcao_atual in ["up", "down"]:
            # Se movendo verticalmente, centralizar horizontalmente
            diferenca_x = (self.x + self.tile_size // 2) - centro_x
            if abs(diferenca_x) > 2:  # Apenas se estiver desalinhado
                ajuste = min(self.velocidade // 2, abs(diferenca_x))
                if diferenca_x > 0:
                    self.x -= ajuste
                else:
                    self.x += ajuste
