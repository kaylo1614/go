import numpy as np
import random
import asyncio
import pygame

# ==========================================
# 1. 遊戲常數 (Constants)
# ==========================================
EMPTY, BLACK, WHITE = 0, 1, 2
BOARD_SIZE = 9
KOMI = 7.5
CELL_SIZE = 50
MARGIN = 40
BOARD_WIDTH = (BOARD_SIZE - 1) * CELL_SIZE + 2 * MARGIN
WINDOW_WIDTH = BOARD_WIDTH + 250  # 右側留給手牌與資訊
WINDOW_HEIGHT = BOARD_WIDTH + 100

# 顏色定義
COLOR_BOARD = (220, 179, 92)
COLOR_BLACK = (30, 30, 30)
COLOR_WHITE = (240, 240, 240)
COLOR_TEXT = (50, 50, 50)

# ==========================================
# 2. 邏輯類別 (你原本的邏輯)
# ==========================================
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
        self.board = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.int8)
        self.current_player = BLACK
        self.mana = {BLACK: 1, WHITE: 1}
        self.decks = {BLACK: [], WHITE: []}
        self.discards = {BLACK: [], WHITE: []}
        self.hand = {BLACK: [], WHITE: []}
        self._init_decks()
        self._deal_initial_hands()
        self.ko_snapshot = None

    def _init_decks(self):
        basics = ["Stretch"]*3 + ["Diagonal"]*3 + ["One-space Jump"]*3 + \
                 ["Two-space Jump"]*2 + ["Knight's Move"]*3 + ["Large Knight's Move"]*2 + \
                 ["Elephant's Move"]*2 + ["Double Diagonal"]*1
        advanced = ["Tiger's Mouth"]*1 + ["Ponnuki"]*1 + ["Bent Three"]*1 + ["Straight Three"]*1
        self.decks[BLACK] = basics + advanced + ["Dark Strike"]*1 + ["Sun Trample"]*2
        self.decks[WHITE] = basics + advanced + ["Bright Flash"]*1 + ["Moon Shard"]*2
        random.shuffle(self.decks[BLACK])
        random.shuffle(self.decks[WHITE])

    def _deal_initial_hands(self):
        for _ in range(3):
            self.draw_card(BLACK)
            self.draw_card(WHITE)

    def draw_card(self, color):
        if len(self.hand[color]) >= 5: return
        if not self.decks[color]:
            if not self.discards[color]: return
            self.decks[color] = self.discards[color][:]
            self.discards[color] = []
            random.shuffle(self.decks[color])
        self.hand[color].append(self.decks[color].pop())

# ==========================================
# 3. 繪圖與非同步主程式 (Added for Web)
# ==========================================
async def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("圍棋卡牌 - Card Go")
    font = pygame.font.SysFont("Arial", 20)
    
    game = CardGoState()
    running = True
    clock = pygame.time.Clock()

    while running:
        # A. 事件處理 (解決 MEDIA USER ACTION REQUIRED)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                # 簡單落子測試
                mx, my = pygame.mouse.get_pos()
                r = round((my - MARGIN) / CELL_SIZE)
                c = round((mx - MARGIN) / CELL_SIZE)
                if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
                    if game.board[r, c] == EMPTY:
                        game.board[r, c] = game.current_player
                        game.current_player = WHITE if game.current_player == BLACK else BLACK

        # B. 繪圖邏輯
        screen.fill((245, 245, 245))
        
        # 畫棋盤背景
        pygame.draw.rect(screen, COLOR_BOARD, (MARGIN-20, MARGIN-20, (BOARD_SIZE-1)*CELL_SIZE+40, (BOARD_SIZE-1)*CELL_SIZE+40))
        
        # 畫網格
        for i in range(BOARD_SIZE):
            pygame.draw.line(screen, (0,0,0), (MARGIN, MARGIN + i*CELL_SIZE), (MARGIN + (BOARD_SIZE-1)*CELL_SIZE, MARGIN + i*CELL_SIZE))
            pygame.draw.line(screen, (0,0,0), (MARGIN + i*CELL_SIZE, MARGIN), (MARGIN + i*CELL_SIZE, MARGIN + (BOARD_SIZE-1)*CELL_SIZE))

        # 畫棋子
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if game.board[r, c] == BLACK:
                    pygame.draw.circle(screen, COLOR_BLACK, (MARGIN + c*CELL_SIZE, MARGIN + r*CELL_SIZE), 18)
                elif game.board[r, c] == WHITE:
                    pygame.draw.circle(screen, COLOR_WHITE, (MARGIN + c*CELL_SIZE, MARGIN + r*CELL_SIZE), 18)
                    pygame.draw.circle(screen, (0,0,0), (MARGIN + c*CELL_SIZE, MARGIN + r*CELL_SIZE), 18, 1)

        # 顯示遊戲資訊 (側邊欄)
        info_x = BOARD_WIDTH + 20
        turn_text = font.render(f"Turn: {'BLACK' if game.current_player == BLACK else 'WHITE'}", True, COLOR_TEXT)
        screen.blit(turn_text, (info_x, 50))
        
        mana_text = font.render(f"Mana: {game.mana[game.current_player]}", True, COLOR_TEXT)
        screen.blit(mana_text, (info_x, 80))

        # 顯示手牌名稱
        hand_title = font.render("Hand Cards:", True, COLOR_TEXT)
        screen.blit(hand_title, (info_x, 150))
        for i, card in enumerate(game.hand[game.current_player]):
            card_text = font.render(f"{i+1}. {card}", True, (0, 100, 200))
            screen.blit(card_text, (info_x, 180 + i*30))

        # C. 關鍵更新
        pygame.display.flip()
        
        # 解決 DISCARD : focus 問題的關鍵行
        await asyncio.sleep(0) 
        clock.tick(60)

    pygame.quit()

# 啟動遊戲
if __name__ == "__main__":
    asyncio.run(main())
