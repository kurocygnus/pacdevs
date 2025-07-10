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
    
    def tornar_vulneravel(self, duracao=500):
        """Torna o fantasma vulnerável por um período"""
        self.estado = self.VULNERAVEL
        self.modo = self.ASSUSTADO
        self.tempo_vulneravel = duracao
        self.velocidade = 1  # Mais lento quando vulnerável
    
    def foi_comido(self):
        """Marca o fantasma como comido e o envia de volta para a casa"""
        self.estado = self.COMIDO
        self.modo = self.PERSEGUIR
        self.comido = True
        self.velocidade = 5  # Rápido quando retornando para a casa
    
    def voltar_ao_normal(self):
        """Retorna o fantasma ao estado normal"""
        self.estado = self.NORMAL
        self.modo = self.PERSEGUIR
        self.velocidade = 4  # Velocidade aumentada para movimento mais fluido
    
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
            return True
        
        # Verificar apenas se o tile não é parede
        if mapa[row][col] == PAREDE:
            return False
        
        # Verificar casa dos fantasmas - EXCEÇÃO PARA O SPAWN POINT
        # Permitir que fantasmas saiam da casa, mas não permitir entrada sem ser comido
        if mapa[row][col] == CASA_FANTASMA:
            # Verificar se está saindo da casa
            ghost_col = int((self.x + self.tile_size // 2) // self.tile_size)
            ghost_row = int((self.y + self.tile_size // 2) // self.tile_size)
            
            # Posição atual é casa dos fantasmas?
            atual_eh_casa = False
            if 0 <= ghost_row < len(mapa) and 0 <= ghost_col < len(mapa[0]):
                atual_eh_casa = (mapa[ghost_row][ghost_col] == CASA_FANTASMA)
            
            # Se está DENTRO da casa, permitir movimento para qualquer direção
            # Se está FORA da casa e não está comido, não permitir entrar
            if atual_eh_casa or self.comido:
                return True  # Permite sair da casa ou entrar se estiver comido
            elif self.estado != self.COMIDO:
                return False  # Não permite entrar na casa sem estar comido
                
        return True
    
    def decidir_direcao(self, pacman_x, pacman_y, mapa):
        """Decide a próxima direção do fantasma com base em seu estado e personalidade"""
        # Abordagem simplificada que prioriza direções válidas
        
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
        
        # Etapa 1: Verificar todas as direções (exceto a oposta) 
        # para encontrar caminhos válidos
        direcoes_validas = []
        for direcao in ["up", "down", "left", "right"]:
            # Evitar direção oposta à atual para não ficar indo e voltando
            if direcao == direcao_oposta.get(self.direcao_atual) and len(direcoes_validas) > 0:
                continue
                
            # Fazer verificação mais simples: apenas uma pequena distância na direção escolhida
            passo = max(1, int(self.velocidade))
            
            # Calcular posição após o movimento
            nova_x, nova_y = self.x, self.y
            
            if direcao == "up":
                nova_y -= passo
            elif direcao == "down":
                nova_y += passo
            elif direcao == "left":
                nova_x -= passo
            elif direcao == "right":
                nova_x += passo
                
            # Verificar se é uma posição válida para movimento
            if self.pode_mover_para(nova_x, nova_y, mapa):
                # Calcular nova posição em termos de grid
                nova_col = int((nova_x + self.tile_size // 2) // self.tile_size)
                nova_row = int((nova_y + self.tile_size // 2) // self.tile_size)
                
                # Calcular distância da posição alvo
                distancia = self._calcular_distancia(nova_col, nova_row, target_x, target_y)
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
        
        # Se ainda não há direções válidas, escolher aleatoriamente
        # Isso só deve acontecer se o fantasma estiver completamente cercado por paredes
        if not direcoes_validas:
            print("AVISO: Fantasma completamente preso. Usando direção aleatória.")
            return random.choice(["up", "down", "left", "right"])
        
        # Comportamento baseado no estado
        if self.estado == self.VULNERAVEL:
            # Quando vulnerável, foge do Pacman (escolhe a direção mais distante)
            direcoes_validas.sort(key=lambda x: x[1], reverse=True)
            
            # Adicionar alguma aleatoriedade (30% de chance)
            if len(direcoes_validas) > 1 and random.random() < 0.3:
                return random.choice(direcoes_validas[:2])[0]  # Uma das duas melhores opções
            return direcoes_validas[0][0]  # Melhor opção
            
        elif self.estado == self.COMIDO:
            # Quando comido, vai direto para a casa (menor distância)
            direcoes_validas.sort(key=lambda x: x[1])
            return direcoes_validas[0][0]
            
        else:  # NORMAL
            direcoes_validas.sort(key=lambda x: x[1])  # Ordenar por distância crescente
            
            # Comportamento baseado na personalidade
            if self.personalidade == "perseguidor":
                # Perseguidor: segue o Pacman diretamente
                return direcoes_validas[0][0]
                
            elif self.personalidade == "emboscador":
                # Emboscador: mira à frente do Pacman, mas de forma direta
                return direcoes_validas[0][0]
                
            elif self.personalidade == "vagante":
                # Vagante: comportamento mais errático
                if len(direcoes_validas) > 1 and random.random() < 0.4:
                    return random.choice(direcoes_validas[:2])[0]  # Uma das duas melhores opções
                return direcoes_validas[0][0]
                
            else:  # "imprevisível"
                # Completamente aleatório entre direções válidas
                return random.choice(direcoes_validas)[0]
        
        # Fallback: continuar na direção atual ou escolher aleatoriamente
        return direcoes_validas[0][0] if direcoes_validas else self.direcao_atual
    
    def _calcular_alvo(self, pacman_x, pacman_y):
        """Calcula a posição alvo do fantasma com base no seu estado e personalidade"""
        pacman_col = int(pacman_x // self.tile_size)
        pacman_row = int(pacman_y // self.tile_size)
        
        # Verificar se está no spawn point e precisa sair
        ghost_col = int((self.x + self.tile_size // 2) // self.tile_size)
        ghost_row = int((self.y + self.tile_size // 2) // self.tile_size)
        
        # Calcular a direção atual do Pacman com base nas coordenadas
        try:
            # Tentar acessar a direção do módulo pacman (variável global)
            from pacman import direcao_pacman_global
            direcao_pacman = direcao_pacman_global
        except:
            # Se não conseguir, estimar com base na posição central do mapa
            centro_x = len(self.tile_size * 10)  # Estimativa do centro
            centro_y = len(self.tile_size * 10)
            
            # Estimar direção com base na distância do centro
            if abs(pacman_x - centro_x) > abs(pacman_y - centro_y):
                direcao_pacman = "left" if pacman_x < centro_x else "right"
            else:
                direcao_pacman = "up" if pacman_y < centro_y else "down"
        
        # Se estiver voltando para a casa após ser comido
        if self.estado == self.COMIDO:
            # Achar o centro da casa dos fantasmas
            return (self.posicao_inicio[0] // self.tile_size, 
                    self.posicao_inicio[1] // self.tile_size)
        
        # Se estiver no modo dispersar
        if self.modo == self.DISPERSAR:
            # Cada fantasma tem seu próprio canto para dispersar
            mapa_largura = 24  # Estimativa da largura do mapa
            mapa_altura = 24   # Estimativa da altura do mapa
            
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
            # Mira diretamente no Pacman (Blinky)
            return (pacman_col, pacman_row)
            
        elif self.personalidade == "emboscador":
            # Mira 4 casas à frente do Pacman na direção que ele está olhando (Pinky)
            offset_x, offset_y = 0, 0
            if direcao_pacman == "right":
                offset_x = 4
            elif direcao_pacman == "left":
                offset_x = -4
            elif direcao_pacman == "up":
                offset_y = -4
            else:  # down
                offset_y = 4
                
            # Retorna posição alvo 4 tiles à frente do Pacman
            return (pacman_col + offset_x, pacman_row + offset_y)
                
        elif self.personalidade == "vagante":
            # Mira em um ponto a uma distância média entre o Pacman e o canto (Inky)
            # Primeiro calcula posição 2 tiles à frente do Pacman
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
            
            # Encontrar posição no canto oposto ao fantasma
            ghost_col = int(self.x // self.tile_size)
            ghost_row = int(self.y // self.tile_size)
            
            # Calcular vetor entre a posição à frente e o fantasma
            vetor_x = pos_frente_x - ghost_col
            vetor_y = pos_frente_y - ghost_row
            
            # Dobrar o vetor para criar um efeito de "reflexão"
            alvo_x = pos_frente_x + vetor_x
            alvo_y = pos_frente_y + vetor_y
            
            return (alvo_x, alvo_y)
            
        else:  # "imprevisível" (Clyde)
            # Se estiver longe do Pacman, mira nele. Se estiver perto, foge para o canto
            distancia_ao_pacman = self._calcular_distancia(
                int(self.x // self.tile_size), int(self.y // self.tile_size),
                pacman_col, pacman_row
            )
            
            if distancia_ao_pacman > 8:  # Se estiver longe, persegue
                return (pacman_col, pacman_row)
            else:  # Se estiver perto, vai para o canto
                return (1, 24)  # Canto inferior esquerdo
    
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
        # VERSÃO ULTRA SIMPLIFICADA - só para fazer os fantasmas se moverem!
        
        # Atualizar contadores
        self.tempo_total += 1
        
        # Processar estado vulnerável
        if self.estado == self.VULNERAVEL:
            self.tempo_vulneravel -= 1
            if self.tempo_vulneravel <= 0:
                self.voltar_ao_normal()
        
        # Verificar se voltou para casa depois de comido
        if self.estado == self.COMIDO:
            dist_to_home = self._calcular_distancia(
                self.x // self.tile_size, self.y // self.tile_size,
                self.posicao_inicio[0] // self.tile_size, self.posicao_inicio[1] // self.tile_size
            )
            if dist_to_home < 2:
                self.x = self.posicao_inicio[0]
                self.y = self.posicao_inicio[1]
                self.voltar_ao_normal()
                self.comido = False
        
        # Usar o sistema de movimento complexo baseado em personalidade
        # Verificar se pode continuar na direção atual
        nova_x, nova_y = self.x, self.y
        
        if self.direcao_atual == "up":
            nova_y -= self.velocidade
        elif self.direcao_atual == "down":
            nova_y += self.velocidade
        elif self.direcao_atual == "left":
            nova_x -= self.velocidade
        elif self.direcao_atual == "right":
            nova_x += self.velocidade
        
        # Se não pode continuar na direção atual ou está em uma interseção, decidir nova direção
        em_intersecao = self._esta_em_intersecao(mapa)
        if not self.pode_mover_para(nova_x, nova_y, mapa) or em_intersecao:
            # Lista de direções possíveis
            direcoes = ["up", "down", "left", "right"]
            direcoes_validas = []
            
            # Definir direções opostas
            direcao_oposta = {
                "up": "down",
                "down": "up",
                "left": "right",
                "right": "left"
            }
            
            # Testar cada direção (evitar voltar na direção oposta se possível)
            for dir in direcoes:
                # Evitar direção oposta se houver outras opções
                if self.direcao_atual in direcao_oposta and dir == direcao_oposta[self.direcao_atual]:
                    continue
                    
                teste_x, teste_y = self.x, self.y
                
                if dir == "up":
                    teste_y -= self.velocidade
                elif dir == "down":
                    teste_y += self.velocidade
                elif dir == "left":
                    teste_x -= self.velocidade
                elif dir == "right":
                    teste_x += self.velocidade
                    
                if self.pode_mover_para(teste_x, teste_y, mapa):
                    direcoes_validas.append(dir)
            
            # Se não tiver direções válidas, incluir a direção oposta também
            if not direcoes_validas and self.direcao_atual in direcao_oposta:
                dir = direcao_oposta[self.direcao_atual]
                teste_x, teste_y = self.x, self.y
                
                if dir == "up":
                    teste_y -= self.velocidade
                elif dir == "down":
                    teste_y += self.velocidade
                elif dir == "left":
                    teste_x -= self.velocidade
                elif dir == "right":
                    teste_x += self.velocidade
                    
                if self.pode_mover_para(teste_x, teste_y, mapa):
                    direcoes_validas.append(dir)
            
            # Se encontrou direções válidas, escolher uma
            if direcoes_validas:
                # No modo normal, escolher direção mais próxima ao pacman
                if self.estado == self.NORMAL:
                    # Calcular alvo conforme personalidade
                    alvo_x, alvo_y = self._calcular_alvo(pacman_x, pacman_y)
                    
                    # Direcionar para o alvo
                    melhor_direcao = direcoes_validas[0]  # Valor padrão
                    melhor_distancia = float('inf')
                    
                    for dir in direcoes_validas:
                        teste_x, teste_y = self.x, self.y
                        
                        if dir == "up":
                            teste_y -= self.tile_size
                        elif dir == "down":
                            teste_y += self.tile_size
                        elif dir == "left":
                            teste_x -= self.tile_size
                        elif dir == "right":
                            teste_x += self.tile_size
                            
                        dist = self._calcular_distancia(
                            teste_x // self.tile_size, 
                            teste_y // self.tile_size,
                            alvo_x, alvo_y
                        )
                        
                        if dist < melhor_distancia:
                            melhor_distancia = dist
                            melhor_direcao = dir
                    
                    # Adicionar aleatoriedade para personalidades específicas
                    if self.personalidade in ["vagante", "imprevisível"] and random.random() < 0.3:
                        # 30% de chance de escolher direção aleatória
                        self.direcao_atual = random.choice(direcoes_validas)
                    else:
                        self.direcao_atual = melhor_direcao
                        
                # No estado vulnerável, mover aleatoriamente
                elif self.estado == self.VULNERAVEL:
                    self.direcao_atual = random.choice(direcoes_validas)
                    
                # Quando comido, voltar para casa
                elif self.estado == self.COMIDO:
                    casa_x = self.posicao_inicio[0] // self.tile_size
                    casa_y = self.posicao_inicio[1] // self.tile_size
                    
                    # Escolher direção mais próxima da casa
                    melhor_direcao = direcoes_validas[0]  # Valor padrão
                    melhor_distancia = float('inf')
                    
                    for dir in direcoes_validas:
                        teste_x, teste_y = self.x, self.y
                        
                        if dir == "up":
                            teste_y -= self.tile_size
                        elif dir == "down":
                            teste_y += self.tile_size
                        elif dir == "left":
                            teste_x -= self.tile_size
                        elif dir == "right":
                            teste_x += self.tile_size
                            
                        dist = self._calcular_distancia(
                            teste_x // self.tile_size, 
                            teste_y // self.tile_size,
                            casa_x, casa_y
                        )
                        
                        if dist < melhor_distancia:
                            melhor_distancia = dist
                            melhor_direcao = dir
                    
                    self.direcao_atual = melhor_direcao
            else:
                # Se todas as direções estão bloqueadas (situação extrema)
                # Forçar teleporte para o centro do tile atual
                tile_x = int(self.x // self.tile_size)
                tile_y = int(self.y // self.tile_size)
                self.x = tile_x * self.tile_size
                self.y = tile_y * self.tile_size
                print("AVISO: Fantasma completamente preso. Usando direção aleatória.")
        
        # Aplicar movimento
        if self.direcao_atual == "up":
            self.y -= self.velocidade
        elif self.direcao_atual == "down":
            self.y += self.velocidade
        elif self.direcao_atual == "left":
            self.x -= self.velocidade
        elif self.direcao_atual == "right":
            self.x += self.velocidade
        
        # Verificar portais
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
        tolerancia = 3  # pixels
        if abs(self.x + self.tile_size // 2 - centro_x) > tolerancia or \
           abs(self.y + self.tile_size // 2 - centro_y) > tolerancia:
            return False
            
        # Contar direções válidas
        direcoes_possiveis = 0
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
                
            # Verificar limites
            if nova_row < 0 or nova_row >= len(mapa) or nova_col < 0 or nova_col >= len(mapa[0]):
                continue
                
            # Se não é parede, é direção válida
            if mapa[nova_row][nova_col] != PAREDE:
                direcoes_possiveis += 1
                
        # Está em interseção se há mais de 2 direções possíveis
        # (mais de 2 significa que é uma interseção, 2 significa que é um corredor reto)
        return direcoes_possiveis > 2
