import math
import random
from collections import deque

import pygame

from maze_generator import CASA_FANTASMA, PAREDE
from visual import desenhar_brilho

# A ordem das direções é a preferência de desempate do Pac-Man original.
DIRECOES = {
    "up": (0, -1),
    "left": (-1, 0),
    "down": (0, 1),
    "right": (1, 0),
}
OPOSTA = {"up": "down", "down": "up", "left": "right", "right": "left"}
ORDEM_PREFERENCIA = {"up": 0, "left": 1, "down": 2, "right": 3}

COR_PERSONALIDADE = {
    "perseguidor": (255, 70, 70),
    "emboscador": (255, 150, 220),
    "vagante": (0, 230, 235),
    "imprevisível": (255, 170, 40),
}
COR_VULNERAVEL = (70, 100, 255)
COR_PISCANDO = (255, 255, 255)

EPSILON = 1e-6
# Teto de segmentos (tile -> tile) percorridos em um único frame.
MAX_SEGMENTOS_POR_FRAME = 4


class GhostSprite:
    """Rosto completo do fantasma, com contorno colorido na silhueta.

    O recorte original é mantido inteiro (sem máscara circular): só a margem
    transparente é aparada e a imagem é reduzida preservando a proporção.
    """

    LIMIAR_ALPHA = 10
    ESPESSURA_CONTORNO = 2

    def __init__(self, image_path, tamanho=46):
        self.tamanho = tamanho
        original = pygame.image.load(image_path)
        if pygame.display.get_surface() is not None:
            original = original.convert_alpha()
        else:
            original = original.convert_alpha() if original.get_bitsize() == 32 else original
        self.rosto = self._preparar_rosto(original, tamanho - 2 * self.ESPESSURA_CONTORNO)
        self.silhueta = pygame.mask.from_surface(self.rosto, self.LIMIAR_ALPHA)
        self._cache = {}

    def _preparar_rosto(self, imagem, lado_maximo):
        """Apara a margem transparente e reduz para caber em `lado_maximo`."""
        mascara = pygame.mask.from_surface(imagem, self.LIMIAR_ALPHA)
        principal = mascara.connected_component()  # ignora pixels soltos
        retangulos = principal.get_bounding_rects()
        if retangulos:
            area = retangulos[0].unionall(retangulos[1:])
            limpa = imagem.copy()
            filtro = principal.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
            limpa.blit(filtro, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            imagem = limpa.subsurface(area).copy()

        largura, altura = imagem.get_size()
        escala = min(lado_maximo / largura, lado_maximo / altura)
        novo_tamanho = (max(1, round(largura * escala)), max(1, round(altura * escala)))
        try:
            return pygame.transform.smoothscale(imagem, novo_tamanho)
        except ValueError:  # formatos sem suporte a smoothscale
            return pygame.transform.scale(imagem, novo_tamanho)

    def avatar(self, cor_contorno, tinta=None):
        """Rosto inteiro com contorno de cor; `tinta` é um RGBA aplicado só no rosto."""
        chave = (cor_contorno, tinta)
        if chave not in self._cache:
            borda = self.ESPESSURA_CONTORNO
            largura, altura = self.rosto.get_size()
            superficie = pygame.Surface((largura + 2 * borda, altura + 2 * borda), pygame.SRCALPHA)

            contorno = self.silhueta.to_surface(
                setcolor=(*cor_contorno, 255), unsetcolor=(0, 0, 0, 0)
            )
            for dx in range(-borda, borda + 1):
                for dy in range(-borda, borda + 1):
                    if dx * dx + dy * dy <= borda * borda + 1:
                        superficie.blit(contorno, (borda + dx, borda + dy))

            rosto = self.rosto.copy()
            if tinta is not None:
                camada = self.silhueta.to_surface(setcolor=tinta, unsetcolor=(0, 0, 0, 0))
                rosto.blit(camada, (0, 0))
            superficie.blit(rosto, (borda, borda))
            self._cache[chave] = superficie
        return self._cache[chave]


class Ghost:
    """Fantasma que anda tile a tile e escolhe o caminho pelo labirinto real.

    Toda decisão acontece exatamente no centro de um tile. Entre dois centros o
    fantasma só avança em linha reta até o tile de destino, então ele nunca fica
    "entre" tiles sem saber para onde ir. O alvo (Pac-Man, canto, saída da
    casa...) é alcançado pelo menor caminho de verdade (busca em largura) e não
    pela distância em linha reta, que prendia os fantasmas em voltas ao redor
    de blocos de parede.
    """

    # Estados do fantasma
    NORMAL = 0
    VULNERAVEL = 1
    COMIDO = 2

    # Modos de movimento
    PERSEGUIR = 0  # Perseguir o pacman
    DISPERSAR = 1  # Ir para cantos específicos
    ASSUSTADO = 2  # Movimento aleatório quando vulnerável
    SAINDO_CASA = 3  # Sair da casa dos fantasmas

    def __init__(
        self,
        x,
        y,
        sprite_path,
        tile_size,
        personalidade="perseguidor",
        atraso_saida=0,
    ):
        """
        Inicializa um novo fantasma.

        Args:
            x, y: Posição inicial (é alinhada ao tile que contém o ponto)
            sprite_path: Caminho para a imagem do fantasma
            tile_size: Tamanho de cada bloco do labirinto
            personalidade: Define o comportamento do fantasma ('perseguidor', 'emboscador',
                          'vagante' ou 'imprevisível')
            atraso_saida: 0 sai logo; maior que 0 espera na casa até ser liberado
        """
        self.tile_size = tile_size
        self.sprite = GhostSprite(sprite_path)
        self.posicao_inicio = self._alinhar_top_left_ao_tile(x, y)
        self.x, self.y = self.posicao_inicio
        self.velocidade_normal = 4
        self.velocidade_assustado = 2
        self.velocidade_comido = 8
        self.velocidade_tunel = 2
        self.velocidade = self.velocidade_normal
        self.estado = self.NORMAL
        self.modo = self.SAINDO_CASA if atraso_saida == 0 else self.DISPERSAR
        self.modo_retorno = self.DISPERSAR
        self.personalidade = personalidade
        self.direcao_atual = "left" if atraso_saida == 0 else "up"
        self.reversao_pendente = False
        self.tempo_vulneravel = 0
        self.tempo_total = 0
        self.atraso_saida = atraso_saida
        self.comido = False

        # Segmento em andamento: o fantasma sai do centro de `origem` e vai até
        # o centro de `destino` (None quando está parado exatamente num centro).
        self.origem = None
        self.destino = None

        # Cache dos pontos especiais da casa (por mapa)
        self._mapa_da_casa = None
        self._tile_saida = None
        self._tile_renascer = None

    # ------------------------------------------------------------------ casa
    def _esta_na_casa(self, mapa):
        """Retorna True se o fantasma está dentro da casa dos fantasmas."""
        if mapa is None:
            return False
        col, row = self._tile_atual()
        if 0 <= row < len(mapa) and 0 <= col < len(mapa[0]):
            return mapa[row][col] == CASA_FANTASMA
        return False

    def _carregar_casa(self, mapa):
        """Descobre (uma vez por mapa) o tile da porta e o tile de renascimento."""
        if self._mapa_da_casa is mapa:
            return
        self._mapa_da_casa = mapa
        self._tile_saida = None
        self._tile_renascer = None

        altura = len(mapa)
        largura = len(mapa[0])
        casas = [
            (col, row)
            for row in range(altura)
            for col in range(largura)
            if mapa[row][col] == CASA_FANTASMA
        ]
        if not casas:
            return

        # A saída é o tile livre logo acima de uma célula da casa; entre várias,
        # prefere a mais próxima do centro horizontal do mapa.
        centro_col = largura // 2
        portas = [
            (col, row)
            for col, row in casas
            if row > 0 and mapa[row - 1][col] not in (PAREDE, CASA_FANTASMA)
        ]
        if portas:
            col, row = min(portas, key=lambda c: (abs(c[0] - centro_col), c[1]))
            self._tile_renascer = (col, row)
            self._tile_saida = (col, row - 1)
        else:
            self._tile_renascer = min(
                casas, key=lambda c: (abs(c[0] - centro_col), c[1])
            )

    # ----------------------------------------------------- controle de estado
    def definir_velocidades(
        self, normal=None, assustado=None, comido=None, tunel=None
    ):
        """Atualiza velocidades por fase sem trocar o estado atual."""
        if normal is not None:
            self.velocidade_normal = normal
        if assustado is not None:
            self.velocidade_assustado = assustado
        if comido is not None:
            self.velocidade_comido = comido
        if tunel is not None:
            self.velocidade_tunel = tunel
        self._atualizar_velocidade(None)

    def definir_modo_global(self, modo, inverter=False):
        """Aplica o modo scatter/chase vindo do temporizador global."""
        if self.estado != self.NORMAL or self.modo == self.SAINDO_CASA:
            self.modo_retorno = modo
            return
        if self.modo != modo:
            self.modo = modo
            self.modo_retorno = modo
            if inverter:
                self.reversao_pendente = True

    def liberar_da_casa(self):
        """Libera um fantasma retido por contador de pontos."""
        if self.atraso_saida > 0:
            self.atraso_saida = 0
            if self.estado == self.NORMAL:
                self.modo = self.SAINDO_CASA

    def tornar_vulneravel(self, duracao=500, modo_retorno=None):
        """Torna o fantasma vulnerável por um período, exceto se estiver COMIDO."""
        if self.estado != self.COMIDO:
            if duracao <= 0:
                self.reversao_pendente = True
                return
            if modo_retorno is not None:
                self.modo_retorno = modo_retorno
            elif self.modo not in (self.ASSUSTADO, self.SAINDO_CASA):
                self.modo_retorno = self.modo
            self.estado = self.VULNERAVEL
            self.modo = self.ASSUSTADO
            self.tempo_vulneravel = duracao
            self.reversao_pendente = True
            self._atualizar_velocidade(None)

    def foi_comido(self):
        """Marca o fantasma como comido e o envia de volta para a casa"""
        self.estado = self.COMIDO
        self.modo = self.PERSEGUIR
        self.comido = True
        self.velocidade = self.velocidade_comido
        self.tempo_vulneravel = 0
        self.reversao_pendente = False
        # Depois de renascer ele deve sair da casa na hora (não esperar contador)
        self.atraso_saida = 0

    def voltar_ao_normal(self):
        """Retorna o fantasma ao estado normal (a direção em curso é mantida)."""
        self.estado = self.NORMAL
        self.modo = self.modo_retorno
        self.velocidade = self.velocidade_normal

    # ------------------------------------------------------------- geometria
    def _alinhar_top_left_ao_tile(self, x, y):
        """Converte qualquer ponto dentro do tile para o top-left daquele tile."""
        return (
            int(x // self.tile_size) * self.tile_size,
            int(y // self.tile_size) * self.tile_size,
        )

    def _centro_atual(self):
        return self.x + self.tile_size / 2, self.y + self.tile_size / 2

    def _tile_atual(self):
        centro_x, centro_y = self._centro_atual()
        return int(centro_x // self.tile_size), int(centro_y // self.tile_size)

    def _centro_do_tile(self, col, row):
        return (
            col * self.tile_size + self.tile_size / 2,
            row * self.tile_size + self.tile_size / 2,
        )

    @staticmethod
    def _calcular_distancia(x1, y1, x2, y2):
        """Calcula a distância euclidiana entre dois pontos"""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    # ----------------------------------------------------------------- mapa
    @staticmethod
    def _eh_portal(mapa, row):
        return mapa[row][0] != PAREDE and mapa[row][len(mapa[0]) - 1] != PAREDE

    def _casa_permitida(self, mapa):
        """Só entra na casa quem já está dentro dela ou quem foi comido."""
        return self.estado == self.COMIDO or self._esta_na_casa(mapa)

    @staticmethod
    def _tile_permitido(col, row, mapa, casa_ok):
        if not (0 <= row < len(mapa) and 0 <= col < len(mapa[0])):
            return False
        celula = mapa[row][col]
        if celula == PAREDE:
            return False
        if celula == CASA_FANTASMA:
            return casa_ok
        return True

    def _vizinho_fisico(self, col, row, direcao, mapa):
        """Tile para onde o fantasma andaria saindo de (col, row), ou None.

        Pode devolver as colunas virtuais -1 e `largura` (o túnel lateral, fora
        da tela), que o fantasma atravessa e teleporta para o lado oposto.
        """
        dx, dy = DIRECOES[direcao]
        altura = len(mapa)
        largura = len(mapa[0])
        novo_col, novo_row = col + dx, row + dy

        if not 0 <= novo_row < altura:
            return None
        if col < 0 or col >= largura:  # já dentro do túnel: só volta para o mapa
            if dy or not 0 <= novo_col < largura:
                return None
            return (novo_col, novo_row)
        if novo_col < 0 or novo_col >= largura:  # entrando no túnel
            return (novo_col, novo_row) if self._eh_portal(mapa, novo_row) else None
        if self._tile_permitido(novo_col, novo_row, mapa, self._casa_permitida(mapa)):
            return (novo_col, novo_row)
        return None

    def _tile_andavel_mais_proximo(self, alvo_col, alvo_row, mapa, casa_ok):
        melhor = None
        melhor_distancia = float("inf")
        for row in range(len(mapa)):
            for col in range(len(mapa[0])):
                if not self._tile_permitido(col, row, mapa, casa_ok):
                    continue
                distancia = self._calcular_distancia(col, row, alvo_col, alvo_row)
                if distancia < melhor_distancia:
                    melhor = (col, row)
                    melhor_distancia = distancia
        return melhor

    def _mapa_de_distancias(self, alvo, mapa, casa_ok):
        """Distância (em tiles, pelo labirinto) de cada tile até o alvo."""
        altura = len(mapa)
        largura = len(mapa[0])
        distancias = {alvo: 0}
        fila = deque([alvo])
        while fila:
            col, row = fila.popleft()
            for dx, dy in DIRECOES.values():
                novo_col, novo_row = col + dx, row + dy
                if not 0 <= novo_row < altura:
                    continue
                if novo_col < 0 or novo_col >= largura:
                    if not self._eh_portal(mapa, novo_row):
                        continue
                    novo_col %= largura  # o túnel liga as duas bordas
                proximo = (novo_col, novo_row)
                if proximo in distancias:
                    continue
                if not self._tile_permitido(novo_col, novo_row, mapa, casa_ok):
                    continue
                distancias[proximo] = distancias[(col, row)] + 1
                fila.append(proximo)
        return distancias

    # --------------------------------------------------------------- decisão
    def _calcular_alvo(self, pacman_x, pacman_y, direcao_pacman, mapa):
        """Calcula o tile alvo do fantasma (modo dispersar ou perseguir)."""
        largura = len(mapa[0])
        altura = len(mapa)

        # O Pac-Man é localizado pelo centro (e não pelo canto do sprite)
        pacman_col = int((pacman_x + self.tile_size / 2) // self.tile_size)
        pacman_row = int((pacman_y + self.tile_size / 2) // self.tile_size)
        pacman_col = max(0, min(pacman_col, largura - 1))
        pacman_row = max(0, min(pacman_row, altura - 1))

        if direcao_pacman is None:
            try:
                from pacman import direcao_pacman_global

                direcao_pacman = direcao_pacman_global
            except ImportError:
                direcao_pacman = "right"

        cantos = {
            "perseguidor": (1, 1),
            "emboscador": (largura - 2, 1),
            "vagante": (1, altura - 2),
        }
        canto = cantos.get(self.personalidade, (largura - 2, altura - 2))

        if self.modo == self.DISPERSAR:
            return canto

        if self.personalidade == "perseguidor":
            # Mira diretamente no Pacman (Blinky) - comportamento agressivo
            return (pacman_col, pacman_row)

        if self.personalidade == "emboscador":
            # Mira duas casas à frente do Pacman para interceptá-lo
            dx, dy = DIRECOES.get(direcao_pacman, (1, 0))
            return (
                max(0, min(pacman_col + 2 * dx, largura - 1)),
                max(0, min(pacman_row + 2 * dy, altura - 1)),
            )

        if self.personalidade == "vagante":
            # Aproximação do Inky: projeta um ponto à frente do Pacman a partir de si
            dx, dy = DIRECOES.get(direcao_pacman, (1, 0))
            frente_x = pacman_col + 2 * dx
            frente_y = pacman_row + 2 * dy
            if direcao_pacman == "up":  # bug clássico do arcade: também 2 à esquerda
                frente_x -= 2
            ghost_col, ghost_row = self._tile_atual()
            return (
                max(0, min(frente_x + (frente_x - ghost_col), largura - 1)),
                max(0, min(frente_y + (frente_y - ghost_row), altura - 1)),
            )

        # "imprevisível" (Clyde): persegue de longe e foge para o canto quando perto
        ghost_col, ghost_row = self._tile_atual()
        if (
            self._calcular_distancia(ghost_col, ghost_row, pacman_col, pacman_row)
            >= 8
        ):
            return (pacman_col, pacman_row)
        return canto

    def _melhor_por_caminho(self, candidatas, alvo, mapa):
        """Entre as direções candidatas, a que deixa o fantasma mais perto do alvo."""
        casa_ok = self._casa_permitida(mapa)
        largura = len(mapa[0])
        alvo_col = max(0, min(int(alvo[0]), largura - 1))
        alvo_row = max(0, min(int(alvo[1]), len(mapa) - 1))
        if not self._tile_permitido(alvo_col, alvo_row, mapa, casa_ok):
            proximo = self._tile_andavel_mais_proximo(alvo_col, alvo_row, mapa, casa_ok)
            if proximo is None:
                return random.choice(candidatas)
            alvo_col, alvo_row = proximo

        distancias = self._mapa_de_distancias((alvo_col, alvo_row), mapa, casa_ok)

        def custo(opcao):
            direcao, (col, row) = opcao
            distancia = distancias.get((col % largura, row))
            if distancia is None:  # sem caminho: cai para a distância em linha reta
                distancia = 1000 + self._calcular_distancia(
                    col, row, alvo_col, alvo_row
                )
            return (distancia, ORDEM_PREFERENCIA[direcao])

        return min(candidatas, key=custo)

    def _decidir_direcao(self, pacman_x, pacman_y, direcao_pacman, mapa):
        """Escolhe (direcao, tile_destino) a partir do centro do tile atual."""
        col, row = self._tile_atual()
        opcoes = []
        for direcao in DIRECOES:
            vizinho = self._vizinho_fisico(col, row, direcao, mapa)
            if vizinho is not None:
                opcoes.append((direcao, vizinho))
        if not opcoes:
            return None

        oposta = OPOSTA[self.direcao_atual]
        sem_re = [opcao for opcao in opcoes if opcao[0] != oposta]

        if self.reversao_pendente:
            self.reversao_pendente = False
            if self.estado != self.COMIDO and self.modo != self.SAINDO_CASA:
                for opcao in opcoes:
                    if opcao[0] == oposta:
                        return opcao

        if len(opcoes) == 1:
            return opcoes[0]

        self._carregar_casa(mapa)
        if self.estado == self.COMIDO and self._tile_renascer is not None:
            return self._melhor_por_caminho(opcoes, self._tile_renascer, mapa)
        if self.modo == self.SAINDO_CASA and self._tile_saida is not None:
            return self._melhor_por_caminho(opcoes, self._tile_saida, mapa)
        if self.estado == self.VULNERAVEL:
            return random.choice(sem_re or opcoes)

        alvo = self._calcular_alvo(pacman_x, pacman_y, direcao_pacman, mapa)
        return self._melhor_por_caminho(sem_re or opcoes, alvo, mapa)

    def _atualizar_modo_no_tile(self, mapa):
        """Ajusta o modo conforme o fantasma entra/sai da casa."""
        if self.estado != self.COMIDO and self._esta_na_casa(mapa):
            self.modo = self.SAINDO_CASA
        elif self.modo == self.SAINDO_CASA:
            self.modo = (
                self.ASSUSTADO if self.estado == self.VULNERAVEL else self.modo_retorno
            )

    def _renascer_se_chegou(self, mapa):
        """Olhos que chegam ao ponto de renascimento voltam a ser um fantasma."""
        if self.estado != self.COMIDO:
            return
        self._carregar_casa(mapa)
        if self._tile_renascer is None or self._tile_atual() == self._tile_renascer:
            self.voltar_ao_normal()
            self.comido = False

    def _escolher_destino(self, pacman_x, pacman_y, direcao_pacman, mapa):
        """Decide o próximo segmento. Devolve False se não há para onde ir."""
        self._renascer_se_chegou(mapa)
        self._atualizar_modo_no_tile(mapa)
        escolha = self._decidir_direcao(pacman_x, pacman_y, direcao_pacman, mapa)
        if escolha is None:
            return False
        self.direcao_atual, self.destino = escolha
        self.origem = self._tile_atual()
        return True

    # ------------------------------------------------------------- movimento
    def _aguardando_na_casa(self, mapa):
        """Fantasma retido na casa fica parado até ser liberado."""
        if self.estado == self.COMIDO or self.atraso_saida <= 0:
            return False
        if not self._esta_na_casa(mapa):
            return False
        if self.estado == self.NORMAL:
            self.atraso_saida -= 1
            if self.atraso_saida <= 0:
                self.modo = self.SAINDO_CASA
                return False
        return True

    def _reverter_no_meio_do_caminho(self, mapa):
        """Inversão imediata (energizer / troca de modo) sem esperar o próximo tile."""
        if not self.reversao_pendente:
            return
        if (
            self.estado == self.COMIDO
            or self.modo == self.SAINDO_CASA
            or self._esta_na_casa(mapa)
        ):
            self.reversao_pendente = False
            return
        if self.destino is not None:
            self.origem, self.destino = self.destino, self.origem
            self.direcao_atual = OPOSTA[self.direcao_atual]
            self.reversao_pendente = False
        # Parado num centro: _decidir_direcao consome a reversão pendente.

    def _percorrer(self, restante, mapa):
        """Anda até `restante` pixels rumo ao destino; devolve o que sobrou."""
        alvo_x, alvo_y = self._centro_do_tile(*self.destino)
        centro_x, centro_y = self._centro_atual()
        falta = abs(alvo_x - centro_x) + abs(alvo_y - centro_y)
        passo = min(restante, falta)
        dx, dy = DIRECOES[self.direcao_atual]
        self.x += dx * passo
        self.y += dy * passo

        if falta - passo <= EPSILON:
            self._chegar_ao_destino(mapa)
        return restante - passo

    def _chegar_ao_destino(self, mapa):
        """Encaixa exatamente no centro do tile (sem acumular erro de float)."""
        col, row = self.destino
        largura = len(mapa[0])
        if col < 0:
            col = largura  # saiu pela esquerda: reaparece fora da borda direita
        elif col >= largura:
            col = -1
        self.x = col * self.tile_size
        self.y = row * self.tile_size
        self.origem = None
        self.destino = None

    def _esta_no_tunel_lateral(self, mapa):
        col, row = self._tile_atual()
        if not 0 <= row < len(mapa):
            return False
        largura = len(mapa[0])
        return self._eh_portal(mapa, row) and (col <= 2 or col >= largura - 3)

    def _atualizar_velocidade(self, mapa):
        if self.estado == self.COMIDO:
            self.velocidade = self.velocidade_comido
        elif self.estado == self.VULNERAVEL:
            self.velocidade = self.velocidade_assustado
        elif mapa is not None and self._esta_no_tunel_lateral(mapa):
            self.velocidade = self.velocidade_tunel
        else:
            self.velocidade = self.velocidade_normal

    def mover(self, pacman_x, pacman_y, mapa, direcao_pacman=None):
        """Avança o fantasma um frame, decidindo apenas nos centros dos tiles."""
        self.tempo_total += 1
        self._atualizar_velocidade(mapa)

        if self.estado == self.VULNERAVEL:
            self.tempo_vulneravel -= 1
            if self.tempo_vulneravel <= 0:
                self.voltar_ao_normal()
                self._atualizar_velocidade(mapa)

        if self._aguardando_na_casa(mapa):
            return

        self._reverter_no_meio_do_caminho(mapa)

        restante = self.velocidade
        for _ in range(MAX_SEGMENTOS_POR_FRAME):
            if restante <= EPSILON:
                break
            if self.destino is None and not self._escolher_destino(
                pacman_x, pacman_y, direcao_pacman, mapa
            ):
                break
            restante = self._percorrer(restante, mapa)

    # -------------------------------------------------------------- colisão
    def verificar_colisao_pacman(self, pacman_x, pacman_y):
        """
        Verifica se o fantasma colidiu com o Pacman.
        Retorna:
            0 - Sem colisão
            1 - Colisão normal (Pacman perde vida)
            2 - Fantasma vulnerável (Fantasma é comido)
        """
        dist_colisao = self.tile_size * 0.7

        ghost_center_x, ghost_center_y = self._centro_atual()
        pacman_center_x = pacman_x + self.tile_size / 2
        pacman_center_y = pacman_y + self.tile_size / 2

        distancia = self._calcular_distancia(
            ghost_center_x, ghost_center_y, pacman_center_x, pacman_center_y
        )

        if distancia < dist_colisao:
            if self.estado == self.VULNERAVEL:
                return 2  # Fantasma é comido
            if self.estado == self.NORMAL:
                return 1  # Pacman perde vida

        return 0  # Sem colisão

    # ---------------------------------------------------------------- desenho
    def _desenhar_olhos(self, screen, centro_x, centro_y):
        """Fantasma comido: só os olhos, que olham para onde ele está indo."""
        dx, dy = DIRECOES[self.direcao_atual]
        for lado in (-1, 1):
            olho = (centro_x + lado * 6, centro_y - 2)
            pygame.draw.ellipse(screen, (255, 255, 255), (olho[0] - 5, olho[1] - 7, 10, 14))
            pygame.draw.circle(screen, (40, 70, 255), (olho[0] + dx * 2, olho[1] + dy * 3), 3)

    def desenhar(self, screen):
        """Desenha o fantasma na tela"""
        centro_x, centro_y = self._centro_atual()
        centro_x = int(centro_x)
        centro_y = int(centro_y + math.sin(self.tempo_total * 0.12) * 1.2)

        if self.estado == self.COMIDO:
            self._desenhar_olhos(screen, centro_x, centro_y)
            return

        tinta = None
        if self.estado == self.VULNERAVEL:
            piscando = self.tempo_vulneravel < 120 and (self.tempo_vulneravel // 10) % 2 == 0
            cor = COR_PISCANDO if piscando else COR_VULNERAVEL
            tinta = (255, 255, 255, 90) if piscando else (30, 60, 255, 130)
        else:
            cor = COR_PERSONALIDADE.get(self.personalidade, COR_PERSONALIDADE["imprevisível"])

        desenhar_brilho(screen, cor, (centro_x, centro_y), 26, 0.5)
        imagem = self.sprite.avatar(cor, tinta)
        screen.blit(imagem, imagem.get_rect(center=(centro_x, centro_y)))
