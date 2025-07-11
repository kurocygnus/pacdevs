import pygame
import random
import math
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
        self.velocidade = 4  # Velocidade aumentada para movimento mais fluido
        self.estado = self.NORMAL
        self.modo = self.PERSEGUIR
        self.personalidade = personalidade
        self.direcao_atual = random.choice(["up", "down", "left", "right"])
        self.tempo_vulneravel = 0
        self.tempo_modo_atual = 0
        self.tempo_total = 0
        self.posicao_inicio = (x, y)
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
            if row > 0 and mapa[row-1][col] != PAREDE:
                # Retornar a posição exata (em pixels) da saída
                return (col * self.tile_size + self.tile_size // 2, 
                        (row-1) * self.tile_size + self.tile_size // 2)
        
        return None

    def tornar_vulneravel(self, duracao=500):
        """Torna o fantasma vulnerável por um período, exceto se estiver COMIDO."""
        if self.estado != self.COMIDO:
            self.estado = self.VULNERAVEL
            self.modo = self.ASSUSTADO
            self.tempo_vulneravel = duracao
            self.velocidade = 1  # Mais lento quando vulnerável
    
    def foi_comido(self):
        """Marca o fantasma como comido e o envia de volta para a casa"""
        self.estado = self.COMIDO
        self.modo = self.PERSEGUIR
        self.comido = True
        self.velocidade = 12  # Extremamente rápido quando retornando para a casa para evitar demora
        # Quando um fantasma é comido, ele não pode ser comido novamente até voltar ao normal
        self.tempo_vulneravel = 0
        
        # Garantir que o alvo seja o centro da casa (posição inicial)
        # Recalcular a posição inicial (pode ter mudado durante o jogo)
        centro_casa_x = int(self.posicao_inicio[0] // self.tile_size) * self.tile_size + self.tile_size // 2
        centro_casa_y = int(self.posicao_inicio[1] // self.tile_size) * self.tile_size + self.tile_size // 2
        self.posicao_inicio = (centro_casa_x, centro_casa_y)
    
    def voltar_ao_normal(self):
        """Retorna o fantasma ao estado normal"""
        self.estado = self.NORMAL
        self.modo = self.PERSEGUIR
        self.velocidade = 4  # Velocidade base aumentada para movimento mais fluido
        
        # Direções preferidas quando sai da casa (priorizar UP)
        if self._esta_na_casa(None):  # None é seguro aqui, _esta_na_casa vai ser verificado no movimento
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
                esta_na_casa = (mapa[ghost_row][ghost_col] == CASA_FANTASMA)
            
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
        """Decide a próxima direção do fantasma com base em seu estado e personalidade"""
        # Posição atual do fantasma em termos de grid
        ghost_col = int((self.x + self.tile_size // 2) // self.tile_size)
        ghost_row = int((self.y + self.tile_size // 2) // self.tile_size)
        
        # Calcular posição alvo conforme a personalidade e estado
        target_x, target_y = self._calcular_alvo(pacman_x, pacman_y)
        
        # Mapeamento de direções opostas
        direcao_oposta = {
            "up": "down",
            "down": "up",
            "left": "right",
            "right": "left"
        }
        
        # Ajustar a aleatoriedade com base no estado e personalidade
        chance_aleatoria = 0
        if self.estado == self.NORMAL:
            if self.personalidade == "perseguidor":
                chance_aleatoria = 0.05  # Quase nada aleatório - persegue diretamente
            elif self.personalidade == "emboscador":
                chance_aleatoria = 0.1   # Pouco aleatório - foca em interceptar
            elif self.personalidade == "vagante":
                chance_aleatoria = 0.2  # Reduzida para ficar mais focado, mas ainda com variação
            elif self.personalidade == "imprevisível":
                chance_aleatoria = 0.4  # Menos aleatório que antes, mas ainda imprevisível
        elif self.estado == self.VULNERAVEL:
            chance_aleatoria = 0.6  # Menos aleatório quando vulnerável para fuga mais eficiente
        
        # Decidir se vai fazer um movimento aleatório
        movimento_aleatorio = random.random() < chance_aleatoria
        
        # Etapa 1: Verificar todas as direções (exceto a oposta em corredores) 
        # para encontrar caminhos válidos
        direcoes_validas = []
        
        # Tratamento especial quando na casa dos fantasmas
        if self._esta_na_casa(mapa) and self.estado != self.COMIDO:
            # Priorizar sair da casa - movimento para cima tem muito mais peso
            for direcao in ["up", "left", "right", "down"]:
                nova_x, nova_y = self.x, self.y
                
                if direcao == "up":
                    nova_y -= self.velocidade
                elif direcao == "down":
                    nova_y += self.velocidade
                elif direcao == "left":
                    nova_x -= self.velocidade
                elif direcao == "right":
                    nova_x += self.velocidade
                    
                if self.pode_mover_para(nova_x, nova_y, mapa):
                    # Pesar direções - "up" tem prioridade máxima
                    peso_direcao = 0.1 if direcao != "up" else 0.01  # Menor valor é melhor
                    nova_col = int((nova_x + self.tile_size // 2) // self.tile_size)
                    nova_row = int((nova_y + self.tile_size // 2) // self.tile_size)
                    distancia = self._calcular_distancia(nova_col, nova_row, target_x, target_y) * peso_direcao
                    direcoes_validas.append((direcao, distancia))
        else:
            # Comportamento normal fora da casa - perseguir o alvo
            em_intersecao = self._esta_em_intersecao(mapa)
            
            # Lista das direções a verificar
            direcoes_a_verificar = ["up", "down", "left", "right"]
            
            # Se não estamos em uma interseção, não voltar para trás (evitar vai-e-vem)
            if not em_intersecao and self.direcao_atual in direcao_oposta:
                # Remover a direção oposta à atual
                if direcao_oposta[self.direcao_atual] in direcoes_a_verificar:
                    direcoes_a_verificar.remove(direcao_oposta[self.direcao_atual])
            
            # Se vulnerável, inverter a lista de direções para favorecer fuga
            if self.estado == self.VULNERAVEL:
                direcoes_a_verificar.reverse()
                
            for direcao in direcoes_a_verificar:
                # Calcular nova posição
                nova_x, nova_y = self.x, self.y
                
                if direcao == "up":
                    nova_y -= self.velocidade
                elif direcao == "down":
                    nova_y += self.velocidade
                elif direcao == "left":
                    nova_x -= self.velocidade
                elif direcao == "right":
                    nova_x += self.velocidade
                
                # Verificar se movimento é válido
                if self.pode_mover_para(nova_x, nova_y, mapa):
                    # Converter para coordenadas da grade
                    nova_col = int((nova_x + self.tile_size // 2) // self.tile_size)
                    nova_row = int((nova_y + self.tile_size // 2) // self.tile_size)
                    
                    # Calcular distância até o alvo
                    distancia = self._calcular_distancia(nova_col, nova_row, target_x, target_y)
                    
                    # Ajustar distância com base no estado
                    if self.estado == self.VULNERAVEL:
                        # Quando vulnerável, preferir direções LONGE do alvo (Pacman)
                        distancia = -distancia  # Inverte para preferir distâncias maiores
                    elif movimento_aleatorio and self.estado == self.NORMAL:
                        # Adicionar ruído para comportamento mais imprevisível
                        fator_aleatorio = 0.7 + random.random() * 0.6  # Entre 0.7 e 1.3
                        distancia = distancia * fator_aleatorio
                    
                    # Dar preferência à direção atual em corredores para movimento mais fluido
                    if direcao == self.direcao_atual and not em_intersecao:
                        distancia *= 0.8  # Diminui a distância para priorizar a direção atual
                        
                    direcoes_validas.append((direcao, distancia))
        
        # Se não há direções válidas (sem considerar a oposta), incluir a direção oposta
        if not direcoes_validas:
            direcao_reversa = direcao_oposta.get(self.direcao_atual)
            nova_x, nova_y = self.x, self.y
            
            if direcao_reversa == "up":
                nova_y -= self.velocidade
            elif direcao_reversa == "down":
                nova_y += self.velocidade
            elif direcao_reversa == "left":
                nova_x -= self.velocidade
            elif direcao_reversa == "right":
                nova_x += self.velocidade
                
            if self.pode_mover_para(nova_x, nova_y, mapa):
                # Calcular nova posição em termos de grid
                nova_col = int((nova_x + self.tile_size // 2) // self.tile_size)
                nova_row = int((nova_y + self.tile_size // 2) // self.tile_size)
                
                # Adicionar direção oposta como válida
                distancia = self._calcular_distancia(nova_col, nova_row, target_x, target_y)
                direcoes_validas.append((direcao_reversa, distancia))
        
        # Se não encontrou direções válidas (improvável, mas possível)
        if not direcoes_validas:
            print("AVISO: Fantasma sem saída. Usando direção aleatória.")
            # Tentar qualquer direção, mesmo que pareça inválida
            return random.choice(["up", "down", "left", "right"])
        
        # Comportamento baseado no estado e personalidade
        if self.estado == self.VULNERAVEL:
            # Quando vulnerável, foge do Pacman (distâncias maiores são melhores)
            # As distâncias já foram invertidas na etapa anterior
            direcoes_validas.sort(key=lambda x: x[1])  # Menor valor primeiro (que na verdade é a maior distância)
            
            # Adicionar aleatoriedade para evitar padrões previsíveis
            if len(direcoes_validas) > 1 and random.random() < 0.4:
                # Escolher aleatoriamente entre as duas melhores opções de fuga
                return random.choice(direcoes_validas[:2])[0]
            return direcoes_validas[0][0]  # Melhor opção para fugir
            
        elif self.estado == self.COMIDO:
            # Quando comido, vai direto para a casa (menor distância até a casa)
            direcoes_validas.sort(key=lambda x: x[1])  # Ordenar crescente (menor distância primeiro)
            return direcoes_validas[0][0]  # Escolher o caminho mais curto para a casa
            
        else:  # NORMAL - Comportamento de perseguição baseado na personalidade
            # Ordenar por distância (menor valor = melhor caminho para o alvo)
            direcoes_validas.sort(key=lambda x: x[1])
            
            # Ajustar comportamento baseado na personalidade
            if self.personalidade == "perseguidor":
                # Perseguidor (Blinky): sempre vai direto para o pacman
                return direcoes_validas[0][0]  # Caminho mais curto
                
            elif self.personalidade == "emboscador":
                # Emboscador (Pinky): tenta interceptar o pacman, mas é bastante direto
                if len(direcoes_validas) > 1 and random.random() < 0.15:
                    # Ocasionalmente escolhe a segunda melhor opção para ser menos previsível
                    return direcoes_validas[1][0]
                return direcoes_validas[0][0]  # Normalmente a melhor opção
                
            elif self.personalidade == "vagante":
                # Vagante (Inky): comportamento mais indireto e errático
                if len(direcoes_validas) > 1:
                    # 50% de chance de escolher entre as duas melhores opções
                    if random.random() < 0.5:
                        return random.choice(direcoes_validas[:2])[0]
                return direcoes_validas[0][0]
                
            else:  # "imprevisível" (Clyde)
                # Completamente imprevisível, mas ainda com tendência a se aproximar
                # 70% de chance de escolher aleatoriamente entre as direções válidas
                if len(direcoes_validas) > 1 and random.random() < 0.7:
                    return random.choice(direcoes_validas)[0]  # Completamente aleatório
                return direcoes_validas[0][0]  # 30% de chance de escolher o melhor caminho
        
        # Fallback: continuar na direção atual ou escolher aleatoriamente
        return direcoes_validas[0][0] if direcoes_validas else self.direcao_atual
    
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
            return (int(self.posicao_inicio[0] // self.tile_size), 
                    int(self.posicao_inicio[1] // self.tile_size))
        
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
            # Mira 4 casas à frente do Pacman na direção que ele está olhando (Pinky)
            # Tenta prever onde o Pacman estará e interceptá-lo
            offset_x, offset_y = 0, 0
            if direcao_pacman == "right":
                offset_x = 4
            elif direcao_pacman == "left":
                offset_x = -4
            elif direcao_pacman == "up":
                offset_y = -4
                # Reproduzir o famoso bug do Pac-Man original para Pinky
                offset_x = -4  # Na direção UP, também vai 4 tiles para a esquerda
            else:  # down
                offset_y = 4
                
            # Limitar as coordenadas para não ultrapassar os limites do mapa
            target_x = max(0, min(pacman_col + offset_x, 30))  # Assumindo largura máxima de 30
            target_y = max(0, min(pacman_row + offset_y, 30))  # Assumindo altura máxima de 30
            return (target_x, target_y)
                
        elif self.personalidade == "vagante":
            # Inky: comportamento mais complexo - baseado em posição do Blinky e do Pacman
            # Simplificação: mira em um ponto a 2 tiles à frente do Pacman e "reflete" esse vetor
            offset_x, offset_y = 0, 0
            if direcao_pacman == "right":
                offset_x = 2
            elif direcao_pacman == "left":
                offset_x = -2
            elif direcao_pacman == "up":
                offset_y = -2
            else:  # down
                offset_y = 2
                
            # Posição 2 tiles à frente do Pacman
            pos_frente_x = pacman_col + offset_x
            pos_frente_y = pacman_row + offset_y
            
            # Usar a própria posição como referência (no original seria a posição do Blinky)
            ghost_col = int(self.x // self.tile_size)
            ghost_row = int(self.y // self.tile_size)
            
            # Calcular vetor entre a posição à frente e o fantasma
            vetor_x = pos_frente_x - ghost_col
            vetor_y = pos_frente_y - ghost_row
            
            # Dobrar o vetor para criar um efeito de "reflexão" (objetivo do Inky)
            alvo_x = pos_frente_x + vetor_x
            alvo_y = pos_frente_y + vetor_y
            
            # Limitar para dentro dos limites do mapa
            alvo_x = max(0, min(alvo_x, 30))
            alvo_y = max(0, min(alvo_y, 30))
            
            return (alvo_x, alvo_y)
            
        else:  # "imprevisível" (Clyde)
            # Comportamento do Clyde: persegue até chegar perto, depois foge
            distancia_ao_pacman = self._calcular_distancia(
                int(self.x // self.tile_size), int(self.y // self.tile_size),
                pacman_col, pacman_row
            )
            
            if distancia_ao_pacman > 8:  # Se estiver longe, persegue diretamente
                return (pacman_col, pacman_row)
            else:  # Se estiver a menos de 8 tiles, vai para o canto inferior esquerdo
                # Adicionar alternância periódica para evitar ficar preso em um padrão
                # A cada 200 frames, mudar o canto de destino
                if (self.tempo_total // 200) % 2 == 0:
                    return (1, 24)  # Canto inferior esquerdo
                else:
                    return (24, 24)  # Canto inferior direito
    
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
        """Move o fantasma de acordo com seu comportamento atual"""
        # Atualizar contadores
        self.tempo_total += 1
        
        # Processar estado vulnerável
        if self.estado == self.VULNERAVEL:
            self.tempo_vulneravel -= 1
            if self.tempo_vulneravel <= 0:
                self.voltar_ao_normal()

        # ---- CASO ESPECIAL: Fantasma COMIDO ----
        if self.estado == self.COMIDO:
            # Centralizar na casa dos fantasmas é o objetivo quando comido
            if self._esta_na_casa(mapa):
                # Calcular o centro da casa
                posicao_central_x = (int(self.posicao_inicio[0] // self.tile_size) * self.tile_size) + self.tile_size // 2
                posicao_central_y = (int(self.posicao_inicio[1] // self.tile_size) * self.tile_size) + self.tile_size // 2
                
                # Verificar se chegou ao centro da casa
                if abs((self.x + self.tile_size // 2) - posicao_central_x) < 4 and abs((self.y + self.tile_size // 2) - posicao_central_y) < 4:
                    # Centralizar exatamente e voltar ao normal
                    self.x = self.posicao_inicio[0]
                    self.y = self.posicao_inicio[1]
                    self.voltar_ao_normal()
                    self.comido = False
                else:
                    # Caso contrário, mover para o centro da casa
                    if self.x + self.tile_size // 2 < posicao_central_x:
                        self.x += min(self.velocidade, posicao_central_x - (self.x + self.tile_size // 2))
                    elif self.x + self.tile_size // 2 > posicao_central_x:
                        self.x -= min(self.velocidade, (self.x + self.tile_size // 2) - posicao_central_x)
                        
                    if self.y + self.tile_size // 2 < posicao_central_y:
                        self.y += min(self.velocidade, posicao_central_y - (self.y + self.tile_size // 2))
                    elif self.y + self.tile_size // 2 > posicao_central_y:
                        self.y -= min(self.velocidade, (self.y + self.tile_size // 2) - posicao_central_y)
            else:
                # Se não está na casa, encontrar caminho para a casa
                target_x, target_y = self._calcular_alvo(pacman_x, pacman_y)
                # Converter para pixels
                target_x_px = target_x * self.tile_size + self.tile_size // 2
                target_y_px = target_y * self.tile_size + self.tile_size // 2
                
                # Mover diretamente para o alvo (casa)
                if self.x + self.tile_size // 2 < target_x_px:
                    nova_x = self.x + self.velocidade
                    if self.pode_mover_para(nova_x, self.y, mapa):
                        self.x = nova_x
                        self.direcao_atual = "right"
                elif self.x + self.tile_size // 2 > target_x_px:
                    nova_x = self.x - self.velocidade
                    if self.pode_mover_para(nova_x, self.y, mapa):
                        self.x = nova_x
                        self.direcao_atual = "left"
                        
                if self.y + self.tile_size // 2 < target_y_px:
                    nova_y = self.y + self.velocidade
                    if self.pode_mover_para(self.x, nova_y, mapa):
                        self.y = nova_y
                        self.direcao_atual = "down"
                elif self.y + self.tile_size // 2 > target_y_px:
                    nova_y = self.y - self.velocidade
                    if self.pode_mover_para(self.x, nova_y, mapa):
                        self.y = nova_y
                        self.direcao_atual = "up"
            
            # Retorna imediatamente para evitar outro processamento
            return
            
        # ---- CASO ESPECIAL: DENTRO DA CASA DOS FANTASMAS ----
        if self._esta_na_casa(mapa) and self.estado != self.COMIDO:
            # Encontrar a saída da casa (geralmente logo acima da casa)
            saida = self._encontrar_saida_casa(mapa)
            
            if saida:
                saida_x, saida_y = saida
                
                # Centralizar horizontalmente primeiro
                if abs((self.x + self.tile_size // 2) - saida_x) > 4:
                    if (self.x + self.tile_size // 2) < saida_x:
                        self.x += min(self.velocidade, saida_x - (self.x + self.tile_size // 2))
                        self.direcao_atual = "right"
                    else:
                        self.x -= min(self.velocidade, (self.x + self.tile_size // 2) - saida_x)
                        self.direcao_atual = "left"
                # Depois mover para cima para sair da casa
                else:
                    nova_y = self.y - self.velocidade
                    if self.pode_mover_para(self.x, nova_y, mapa):
                        self.y = nova_y
                        self.direcao_atual = "up"
                    else:
                        # Se não pode mover para cima, tentar outras direções
                        direcoes = ["left", "right", "down"]
                        random.shuffle(direcoes)
                        
                        for dir in direcoes:
                            nova_x, nova_y = self.x, self.y
                            
                            if dir == "left":
                                nova_x -= self.velocidade
                            elif dir == "right":
                                nova_x += self.velocidade
                            elif dir == "down":
                                nova_y += self.velocidade
                                
                            if self.pode_mover_para(nova_x, nova_y, mapa):
                                self.x, self.y = nova_x, nova_y
                                self.direcao_atual = dir
                                break
            else:
                # Se não encontrou saída, mover para cima como fallback
                nova_y = self.y - self.velocidade
                if self.pode_mover_para(self.x, nova_y, mapa):
                    self.y = nova_y
                    self.direcao_atual = "up"
                    
            # Retorna após lidar com o movimento na casa
            return
        # ---- CASO NORMAL: Movimento baseado em personalidade e estado ----
        
        # Pegar a posição central atual para cálculos de centralização
        ghost_col = int((self.x + self.tile_size // 2) // self.tile_size)
        ghost_row = int((self.y + self.tile_size // 2) // self.tile_size)
        centro_celula_x = ghost_col * self.tile_size + self.tile_size // 2
        centro_celula_y = ghost_row * self.tile_size + self.tile_size // 2
        
        # Verificar se está centralizado na célula
        eh_centralizado = abs(self.x + self.tile_size // 2 - centro_celula_x) < 4 and \
                         abs(self.y + self.tile_size // 2 - centro_celula_y) < 4
        
        # Verificar se está em uma interseção
        em_intersecao = self._esta_em_intersecao(mapa)
        
        # Decisão de nova direção
        mudar_direcao = False
        
        # Checar se podemos continuar na direção atual
        nova_x, nova_y = self.x, self.y
        if self.direcao_atual == "up":
            nova_y -= self.velocidade
        elif self.direcao_atual == "down":
            nova_y += self.velocidade
        elif self.direcao_atual == "left":
            nova_x -= self.velocidade
        elif self.direcao_atual == "right":
            nova_x += self.velocidade
        
        # Decidir se precisamos de uma nova direção
        if not self.pode_mover_para(nova_x, nova_y, mapa):
            # Bateu em uma parede
            mudar_direcao = True
        elif em_intersecao and eh_centralizado:
            # Estamos em um cruzamento e centralizados - decidir direção baseado no alvo
            mudar_direcao = True
        elif eh_centralizado and self.tempo_total % 20 == 0:
            # Periodicamente mudar direção mesmo em corredores (evitar ficar preso em loops)
            mudar_direcao = True
            
        # Se precisamos mudar de direção
        if mudar_direcao:
            self.direcao_atual = self.decidir_direcao(pacman_x, pacman_y, mapa)
            
            # Recalcular nova posição com a nova direção
            nova_x, nova_y = self.x, self.y
            if self.direcao_atual == "up":
                nova_y -= self.velocidade
            elif self.direcao_atual == "down":
                nova_y += self.velocidade
            elif self.direcao_atual == "left":
                nova_x -= self.velocidade
            elif self.direcao_atual == "right":
                nova_x += self.velocidade
                
        # Aplicar movimento final (com centralização para evitar ficar preso)
        if self.pode_mover_para(nova_x, nova_y, mapa):
            # Movimento principal na direção escolhida
            self.x, self.y = nova_x, nova_y
            
            # Centralização suave para corredores
            if self.direcao_atual in ["left", "right"] and not em_intersecao:
                # Se movendo horizontalmente, centralizar verticalmente
                diferenca_y = (self.y + self.tile_size // 2) - centro_celula_y
                if abs(diferenca_y) > 2:
                    if diferenca_y > 0:
                        self.y -= min(1, diferenca_y)
                    else:
                        self.y += min(1, -diferenca_y)
                        
            elif self.direcao_atual in ["up", "down"] and not em_intersecao:
                # Se movendo verticalmente, centralizar horizontalmente
                diferenca_x = (self.x + self.tile_size // 2) - centro_celula_x
                if abs(diferenca_x) > 2:
                    if diferenca_x > 0:
                        self.x -= min(1, diferenca_x)
                    else:
                        self.x += min(1, -diferenca_x)
        else:
            # Se não pode mover, escolher uma direção aleatória como último recurso
            direcoes = ["up", "down", "left", "right"]
            direcoes.remove(self.direcao_atual)  # Remover a direção atual
            random.shuffle(direcoes)
            
            for dir in direcoes:
                nova_x, nova_y = self.x, self.y
                if dir == "up":
                    nova_y -= self.velocidade
                elif dir == "down":
                    nova_y += self.velocidade
                elif dir == "left":
                    nova_x -= self.velocidade
                elif dir == "right":
                    nova_x += self.velocidade
                    
                if self.pode_mover_para(nova_x, nova_y, mapa):
                    self.x, self.y = nova_x, nova_y
                    self.direcao_atual = dir
                    break        # Verificar portais (tuneis nas laterais do mapa)
        largura_tela = len(mapa[0]) * self.tile_size
        altura_tela = len(mapa) * self.tile_size
        
        if self.x < -self.tile_size:
            self.x = largura_tela - self.velocidade
        elif self.x >= largura_tela:
            self.x = 0
            
        if self.y < -self.tile_size:
            self.y = altura_tela - self.velocidade
        elif self.y >= altura_tela:
            self.y = 0
            
        # Centralização suave para evitar ficar preso em paredes ou corredores estreitos
        self._ajustar_posicao_no_corredor(mapa)
    
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
            ghost_center_x, ghost_center_y,
            pacman_center_x, pacman_center_y
        )
        
        if distancia < dist_colisao:
            # Verificar estado do fantasma
            if self.estado == self.VULNERAVEL:
                return 2  # Fantasma é comido
            elif self.estado == self.NORMAL:
                return 1  # Pacman perde vida
        
        return 0  # Sem colisão
    
    def verificar_colisao_com_fantasma(self, outro_fantasma):
        """
        Verifica se este fantasma colidiu com outro fantasma.
        Retorna True se colidir, False caso contrário.
        """
        # Ignorar colisões para fantasmas comidos (estão voltando para casa)
        if self.estado == self.COMIDO or outro_fantasma.estado == self.COMIDO:
            return False

        # Ignorar colisões dentro da casa dos fantasmas
        if self._esta_na_casa(None) or outro_fantasma._esta_na_casa(None):
            return False
            
        # Distância para considerar colisão (um pouco menor que com o Pacman)
        dist_colisao = self.tile_size * 0.6
        
        # Calcular distância entre os centros dos fantasmas
        self_center_x = self.x + self.tile_size // 2
        self_center_y = self.y + self.tile_size // 2
        outro_center_x = outro_fantasma.x + outro_fantasma.tile_size // 2
        outro_center_y = outro_fantasma.y + outro_fantasma.tile_size // 2
        
        distancia = self._calcular_distancia(
            self_center_x, self_center_y,
            outro_center_x, outro_center_y
        )
        
        return distancia < dist_colisao
    
    def reagir_a_colisao(self, mapa):
        """
        Reage a uma colisão com outro fantasma mudando de direção.
        """
        # Mapeamento de direções opostas
        direcao_oposta = {
            "up": "down",
            "down": "up",
            "left": "right",
            "right": "left"
        }
        
        # Posição atual em termos de grid
        ghost_col = int((self.x + self.tile_size // 2) // self.tile_size)
        ghost_row = int((self.y + self.tile_size // 2) // self.tile_size)
        
        # Calcular o centro da célula atual
        centro_x = ghost_col * self.tile_size + self.tile_size // 2
        centro_y = ghost_row * self.tile_size + self.tile_size // 2
        
        # Centralizar fantasma na célula para evitar problemas com detecção de colisão
        # Isso é crucial para evitar travamentos após colisões
        self.x = centro_x - self.tile_size // 2
        self.y = centro_y - self.tile_size // 2
        
        # Lista de direções possíveis excluindo a direção atual e sua oposta
        todas_direcoes = ["up", "down", "left", "right"]
        direcoes_possiveis = [dir for dir in todas_direcoes 
                            if dir != self.direcao_atual and dir != direcao_oposta[self.direcao_atual]]
        
        # Decidir direção com base nas opções viáveis
        direcoes_viaveis = []
        for direcao in direcoes_possiveis:
            nova_x, nova_y = self._calcular_nova_posicao(direcao)
            if self.pode_mover_para(nova_x, nova_y, mapa):
                direcoes_viaveis.append(direcao)
        
        # Se temos direções viáveis, escolher uma aleatoriamente
        if direcoes_viaveis:
            nova_direcao = random.choice(direcoes_viaveis)
            self.direcao_atual = nova_direcao
            nova_x, nova_y = self._calcular_nova_posicao(nova_direcao)
            
            # Aplicar um deslocamento maior na nova direção para evitar nova colisão imediata
            self.x, self.y = nova_x, nova_y
            # Aplicar um segundo deslocamento para separar ainda mais os fantasmas
            nova_x, nova_y = self._calcular_nova_posicao(nova_direcao)
            if self.pode_mover_para(nova_x, nova_y, mapa):
                self.x, self.y = nova_x, nova_y
            return
                
        # Se não foi possível mudar para uma direção lateral, tentar a oposta como último recurso
        dir_oposta = direcao_oposta[self.direcao_atual]
        nova_x, nova_y = self._calcular_nova_posicao(dir_oposta)
        if self.pode_mover_para(nova_x, nova_y, mapa):
            self.direcao_atual = dir_oposta
            # Mover mais longe na direção oposta para evitar nova colisão
            self.x, self.y = nova_x, nova_y
            nova_x, nova_y = self._calcular_nova_posicao(dir_oposta)
            if self.pode_mover_para(nova_x, nova_y, mapa):
                self.x, self.y = nova_x, nova_y
    
    def desenhar(self, screen):
        """Desenha o fantasma na tela"""
        # Desenhar sprite base
        screen.blit(self.sprite.image, (self.x, self.y))
        
        # Mostrar estado visualmente com overlays
        overlay = pygame.Surface((self.tile_size, self.tile_size), pygame.SRCALPHA)
        
        if self.estado == self.VULNERAVEL:
            # Piscar quando o tempo de vulnerabilidade estiver acabando
            if self.tempo_vulneravel < 100 and self.tempo_vulneravel % 20 < 10:
                overlay.fill((255, 255, 255, 100))  # Branco piscando (vulnerabilidade acabando)
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
            pygame.draw.circle(screen, (255, 255, 255), (olho_esq_x + olho_raio, olho_y + olho_raio), olho_raio)
            
            # Olho direito
            olho_dir_x = self.x + 2 * self.tile_size // 3 - olho_raio // 2
            pygame.draw.circle(screen, (255, 255, 255), (olho_dir_x + olho_raio, olho_y + olho_raio), olho_raio)
            
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
                pontos = [(centro_x, centro_y), 
                         (centro_x + seta_tamanho, centro_y - seta_tamanho // 2),
                         (centro_x + seta_tamanho, centro_y + seta_tamanho // 2)]
            elif self.direcao_atual == "left":
                pontos = [(centro_x, centro_y), 
                         (centro_x - seta_tamanho, centro_y - seta_tamanho // 2),
                         (centro_x - seta_tamanho, centro_y + seta_tamanho // 2)]
            elif self.direcao_atual == "up":
                pontos = [(centro_x, centro_y), 
                         (centro_x - seta_tamanho // 2, centro_y - seta_tamanho),
                         (centro_x + seta_tamanho // 2, centro_y - seta_tamanho)]
            else:  # "down"
                pontos = [(centro_x, centro_y), 
                         (centro_x - seta_tamanho // 2, centro_y + seta_tamanho),
                         (centro_x + seta_tamanho // 2, centro_y + seta_tamanho)]
                
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
                    self.y -= min(self.velocidade / 3, centro_fantasma_y - centro_celula_y)
                else:
                    self.y += min(self.velocidade / 3, centro_celula_y - centro_fantasma_y)
        
        elif self.direcao_atual in ["up", "down"]:
            # Se movendo verticalmente, centralizar horizontalmente
            if abs(centro_fantasma_x - centro_celula_x) > tolerancia:
                if centro_fantasma_x > centro_celula_x:
                    self.x -= min(self.velocidade / 3, centro_fantasma_x - centro_celula_x)
                else:
                    self.x += min(self.velocidade / 3, centro_celula_x - centro_fantasma_x)
    
    def _esta_em_intersecao(self, mapa):
        """Verifica se o fantasma está em uma interseção (mais de uma direção possível)"""
        # Obter posição atual na grade
        ghost_col = int((self.x + self.tile_size // 2) // self.tile_size)
        ghost_row = int((self.y + self.tile_size // 2) // self.tile_size)
        
        # Verificar se está centralizado o suficiente na célula
        centro_x = ghost_col * self.tile_size + self.tile_size // 2
        centro_y = ghost_row * self.tile_size + self.tile_size // 2
        
        # Se não estiver próximo ao centro da célula, não está em uma interseção
        # Reduzir tolerância para garantir decisões mais precisas nas intersecções
        tolerancia = 3  # pixels de tolerância para centralização (reduzido)
        if abs(self.x + self.tile_size // 2 - centro_x) > tolerancia or \
           abs(self.y + self.tile_size // 2 - centro_y) > tolerancia:
            return False
            
        # Contar direções válidas e guardar quais são
        direcoes_possiveis = 0
        direcoes_validas = []
        
        for direcao in ["up", "down", "left", "right"]:
            nova_row, nova_col = ghost_row, ghost_col
            
            if direcao == "up":
                nova_row -= 1
            elif direcao == "down":
                nova_row += 1
            elif direcao == "left":
                nova_col -= 1
            elif direcao == "right":
                nova_col += 1
                
            # Verificar limites (portais)
            if nova_row < 0 or nova_row >= len(mapa) or nova_col < 0 or nova_col >= len(mapa[0]):
                direcoes_possiveis += 1
                direcoes_validas.append(direcao)
                continue
                
            # Se não é parede, é direção válida
            if mapa[nova_row][nova_col] != PAREDE:
                direcoes_possiveis += 1
                direcoes_validas.append(direcao)
        
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
