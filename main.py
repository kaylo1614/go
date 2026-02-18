import random
import asyncio
import pygame
import sys

# ==========================================
# 1. 遊戲核心邏輯 (完全不依賴 Numpy，確保相容性)
# ==========================================
EMPTY, BLACK, WHITE = 0, 1, 2
BOARD_SIZE = 9
KOMI = 7.5

class CardTransformer:
    def __init__(self):
        self.db = {
            "Stretch": ("長", 2, [(0,0), (1,0)], 3, False),
            "Diagonal": ("尖", 2, [(0,0), (1,1)], 3, False),
            "One-space Jump": ("一間跳", 1, [(0,0), (2,0)], 3, False),
            "Two-space Jump": ("二間跳", 1, [(0,0), (3,0)], 2, False),
            "Knight's Move": ("小飛", 1, [(0,0), (2,1)], 3, True),
            "Large Knight's Move": ("大飛", 1, [(0,0), (3,1)], 2, True),
            "Elephant's Move": ("象飛", 1, [(0,0), (2,2)], 2, False),
            "Double Diagonal": ("斜三", 2, [(0,0), (1,1), (2,2)], 2, False),
            "Tiger's Mouth": ("虎口", 3, [(0,0), (1,1), (-1,1)], 1, False),
            "Ponnuki": ("空心提", 3, [(0,0), (1,1), (-1,1), (0,2)], 1, False),
            "Bent Three": ("彎三", 3, [(0,0), (1,0), (0,1)], 1, True),
            "Straight Three": ("直三", 3, [(0,0), (1,0), (2,0)], 1, False),
            "Dark Strike": ("黯擊", 3, [(0,0), (1,0), (2,0), (1,1)], 1, False),
            "Sun Trample": ("踐日", 2, [(0,0), (1,0), (1,2)], 2, True),
            "Bright Flash": ("皓閃", 3, [(0,0), (1,1), (0,2), (1,3)], 1, True),
            "Moon Shard": ("碎月", 2, [(0,0), (1,1), (1,3)], 2, True)
        }
    def rotate_90(self, coords): return [(c, -r) for r, c in coords]
    def flip_horizontal(self, coords): return [(r, -c) for r, c in coords]

class CardGoState:
    def __init__(self):
        self.board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_player = BLACK
        self.mana = {BLACK: 1, WHITE: 1}
        self.hand = {BLACK: [], WHITE: []}
        for _ in range(3): self.draw_card(BLACK); self.draw_card(WHITE)

    def draw_card(self, color):
        cards = ["Stretch", "Diagonal", "One-space Jump", "Tiger's Mouth"]
        if len(self.hand[color]) < 5:
            self.hand[color].append(random.choice(cards))

    def is_legal(self, r, c, color):
        return 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE and self.board[r][c] == EMPTY

# ==========================================
# 2. UI 渲染邏輯
# ==========================================
CELL_SIZE, MARGIN = 60, 40
V_W, V_H = 560, 780

async def main():
    pygame.init()
    screen = pygame.display.set_mode((V_W, V_H), pygame.RESIZABLE)
    game = CardGoState()
    font = pygame.font.Font(None, 24)
    clock = pygame.time.Clock()

    while True:
        screen.fill((220, 179, 92)) # 棋盤色
        # 畫棋盤線
        for i in range(BOARD_SIZE):
            pygame.draw.line(screen, (0,0,0), (MARGIN, MARGIN + i*CELL_SIZE), (V_W-MARGIN, MARGIN + i*CELL_SIZE))
            pygame.draw.line(screen, (0,0,0), (MARGIN + i*CELL_SIZE, MARGIN), (MARGIN + i*CELL_SIZE, V_W-MARGIN))
        
        # 畫棋子
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if game.board[r][c] != EMPTY:
                    color = (10,10,10) if game.board[r][c] == BLACK else (245,245,245)
                    pygame.draw.circle(screen, color, (MARGIN + c*CELL_SIZE, MARGIN + r*CELL_SIZE), 25)

        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return
            if event.type == pygame.MOUSEBUTTONDOWN:
                # 簡單落子邏輯
                mx, my = event.pos
                c, r = round((mx-MARGIN)/CELL_SIZE), round((my-MARGIN)/CELL_SIZE)
                if game.is_legal(r, c, game.current_player):
                    game.board[r][c] = game.current_player
                    game.current_player = WHITE if game.current_player == BLACK else BLACK

        await asyncio.sleep(0)
        clock.tick(60)

if __name__ == "__main__":
    asyncio.run(main())

