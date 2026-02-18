import random
import asyncio
import pygame
import sys

# ==========================================
# 1. 遊戲核心邏輯 (去 Numpy 化以提高網頁相容性)
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

    def get_all_variants(self, card_name):
        if card_name not in self.db: return []
        _, _, base_coords, _, can_flip = self.db[card_name]
        final_variants = []
        curr_seq = base_coords
        for _ in range(4):
            curr_seq = self.rotate_90(curr_seq)
            final_variants.append(curr_seq)
            if can_flip: final_variants.append(self.flip_horizontal(curr_seq))
        return final_variants

class CardGoState:
    def __init__(self):
        # 使用 Python 內建清單替代 numpy.zeros
        self.board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_player = BLACK
        self.mana = {BLACK: 1, WHITE: 1}
        self.decks, self.discards, self.hand = {BLACK: []}, {BLACK: []}, {BLACK: []}
        self.decks[WHITE], self.discards[WHITE], self.hand[WHITE] = [], [], []
        self._init_decks()
        self._deal_initial_hands()
        self.ko_snapshot = None
        self.turn_start_snapshot = [row[:] for row in self.board]
        self.turn_start_mana = {BLACK: 1, WHITE: 1}
        self.turn_start_hand = {BLACK: [], WHITE: []}

    def _init_decks(self):
        basics = ["Stretch"]*3 + ["Diagonal"]*3 + ["One-space Jump"]*3 + ["Two-space Jump"]*2 + ["Knight's Move"]*3 + ["Large Knight's Move"]*2 + ["Elephant's Move"]*2 + ["Double Diagonal"]*1
        advanced = ["Tiger's Mouth"]*1 + ["Ponnuki"]*1 + ["Bent Three"]*1 + ["Straight Three"]*1
        self.decks[BLACK] = basics + advanced + ["Dark Strike"]*1 + ["Sun Trample"]*2
        self.decks[WHITE] = basics + advanced + ["Bright Flash"]*1 + ["Moon Shard"]*2
        random.shuffle(self.decks[BLACK]); random.shuffle(self.decks[WHITE])

    def _deal_initial_hands(self):
        for _ in range(3): self.draw_card(BLACK); self.draw_card(WHITE)

    def draw_card(self, color):
        if len(self.hand[color]) >= 5: return
        if not self.decks[color]:
            if not self.discards[color]: return
            self.decks[color] = self.discards[color][:]; self.discards[color] = []
            random.shuffle(self.decks[color])
        self.hand[color].append(self.decks[color].pop())

    def is_legal(self, r, c, color):
        if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE): return False
        if self.board[r][c] != EMPTY: return False
        orig = [row[:] for row in self.board]
        self.board[r][c] = color
        self.process_capture(r, c)
        if self.ko_snapshot is not None and self.board == self.ko_snapshot:
            self.board = orig; return False
        has_lib = self.has_liberty(r, c)
        self.board = orig
        return has_lib

    def has_liberty(self, r, c):
        color = self.board[r][c]
        queue, visited = [(r, c)], {(r, c)}
        while queue:
            cr, cc = queue.pop(0)
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                    if self.board[nr][nc] == EMPTY: return True
                    if self.board[nr][nc] == color and (nr, nc) not in visited:
                        visited.add((nr, nc)); queue.append((nr, nc))
        return False

    def process_capture(self, r, c):
        opp = WHITE if self.board[r][c] == BLACK else BLACK
        for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and self.board[nr][nc] == opp:
                if not self.has_liberty(nr, nc):
                    q, v, color = [(nr, nc)], {(nr, nc)}, self.board[nr][nc]
                    while q:
                        cr, cc = q.pop(0); self.board[cr][cc] = EMPTY
                        for ddr, ddc in [(0,1),(0,-1),(1,0),(-1,0)]:
                            nnr, nnc = cr + ddr, cc + ddc
                            if 0 <= nnr < BOARD_SIZE and 0 <= nnc < BOARD_SIZE and self.board[nnr][nnc] == color and (nnr, nnc) not in v:
                                v.add((nnr, nnc)); q.append((nnr, nnc))

    def start_turn(self):
        self.turn_start_snapshot = [row[:] for row in self.board]
        self.turn_start_mana = self.mana.copy()
        self.turn_start_hand[BLACK], self.turn_start_hand[WHITE] = self.hand[BLACK][:], self.hand[WHITE][:]

    def execute_move(self, action_type='single'):
        self.ko_snapshot = [row[:] for row in self.turn_start_snapshot]
        if action_type == 'single':
            self.mana[self.current_player] = min(3, self.mana[self.current_player] + 1)
            self.draw_card(self.current_player)

    def switch_player(self): self.current_player = WHITE if self.current_player == BLACK else BLACK

# ==========================================
# 2. UI 設計
# ==========================================
CELL_SIZE, MARGIN = 60, 40
VIRTUAL_WIDTH = CELL_SIZE * (BOARD_SIZE - 1) + MARGIN * 2
PANEL_HEIGHT = 220
VIRTUAL_HEIGHT = VIRTUAL_WIDTH + PANEL_HEIGHT
BACKGROUND_COLOR, GRID_COLOR = (220, 179, 92), (0, 0, 0)
BLACK_STONE, WHITE_STONE = (10, 10, 10), (245, 245, 245)
CARD_W, CARD_H = 100, 130
CARD_BG_COLOR, CARD_BORDER_COLOR = (245, 235, 210), (60, 40, 20)
SELECTED_COLOR, DISCARD_SEL_COLOR = (255, 215, 0), (255, 80, 80)
MANA_COLOR = (65, 105, 225)

class GoUI:
    def __init__(self, game_state):
        self.virtual_surface = pygame.Surface((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))
        self.game = game_state
        self.tf = CardTransformer()
        # 修正：字型改用預設，增加相容性
        self.card_font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 28)
        self.mana_font = pygame.font.Font(None, 28)
        self.scale_factor = 1.0

    def draw_all(self, screen, selected_id, possible_variants, step_idx, origin, mode, discard_selection, has_acted):
        self.virtual_surface.fill(BACKGROUND_COLOR)
        for i in range(BOARD_SIZE):
            pygame.draw.line(self.virtual_surface, GRID_COLOR, (MARGIN, MARGIN + i * CELL_SIZE), (VIRTUAL_WIDTH - MARGIN, MARGIN + i * CELL_SIZE))
            pygame.draw.line(self.virtual_surface, GRID_COLOR, (MARGIN + i * CELL_SIZE, MARGIN), (MARGIN + i * CELL_SIZE, VIRTUAL_WIDTH - MARGIN))
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if self.game.board[r][c] != EMPTY:
                    color = BLACK_STONE if self.game.board[r][c] == BLACK else WHITE_STONE
                    pygame.draw.circle(self.virtual_surface, color, (MARGIN + c * CELL_SIZE, MARGIN + r * CELL_SIZE), 25)

        panel_y = VIRTUAL_WIDTH
        pygame.draw.rect(self.virtual_surface, (50, 50, 55), (0, panel_y, VIRTUAL_WIDTH, PANEL_HEIGHT))
        curr_p = self.game.current_player
        status = f"{'Black' if curr_p==BLACK else 'White'} | Mana:{self.game.mana[curr_p]} | Cards:{len(self.game.hand[curr_p])}"
        self.virtual_surface.blit(self.card_font.render(status, True, (255, 255, 255)), (20, panel_y + 10))

        hand_y = panel_y + 80
        for i, card_id in enumerate(self.game.hand[curr_p]):
            self.draw_card_visual(20 + i * 110, hand_y, card_id, (selected_id == card_id), (i in discard_selection))

        sw, sh = screen.get_size()
        self.scale_factor = min(sw / VIRTUAL_WIDTH, sh / VIRTUAL_HEIGHT)
        scaled = pygame.transform.scale(self.virtual_surface, (int(VIRTUAL_WIDTH * self.scale_factor), int(VIRTUAL_HEIGHT * self.scale_factor)))
        screen.blit(scaled, ((sw - scaled.get_width()) // 2, (sh - scaled.get_height()) // 2))

    def draw_card_visual(self, x, y, card_id, is_selected, is_discard_sel):
        name_cn, cost, shape, _, _ = self.tf.db[card_id]
        rect = pygame.Rect(x, y, CARD_W, CARD_H)
        color = SELECTED_COLOR if is_selected else (DISCARD_SEL_COLOR if is_discard_sel else CARD_BORDER_COLOR)
        pygame.draw.rect(self.virtual_surface, CARD_BG_COLOR, rect, border_radius=8)
        pygame.draw.rect(self.virtual_surface, color, rect, width=3, border_radius=8)
        # 注意：預設字型可能無法顯示中文，若需顯示中文建議之後上傳 .ttf 字型檔
        self.virtual_surface.blit(self.card_font.render(card_id[:6], True, (0,0,0)), (x+10, y+10))

    def get_board_pos(self, m_pos, sw, sh):
        sf = min(sw / VIRTUAL_WIDTH, sh / VIRTUAL_HEIGHT)
        vx = (m_pos[0] - (sw - VIRTUAL_WIDTH * sf) // 2) / sf
        vy = (m_pos[1] - (sh - VIRTUAL_HEIGHT * sf) // 2) / sf
        c = round((vx - MARGIN) / CELL_SIZE)
        r = round((vy - MARGIN) / CELL_SIZE)
        return (r, c) if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE else None

# ==========================================
# 3. 主程式
# ==========================================
async def main():
    pygame.init()
    screen = pygame.display.set_mode((VIRTUAL_WIDTH, VIRTUAL_HEIGHT), pygame.RESIZABLE)
    game = CardGoState()
    ui = GoUI(game)
    
    sel_id, current_mode, possible_variants, step_idx, origin_pos = None, "single", [], 0, None
    discard_selection, has_acted = set(), False
    clock = pygame.time.Clock()

    while True:
        ui.draw_all(screen, sel_id, possible_variants, step_idx, origin_pos, current_mode, discard_selection, has_acted)
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                sw, sh = screen.get_size()
                b_pos = ui.get_board_pos(event.pos, sw, sh)
                if b_pos and not has_acted:
                    r, c = b_pos
                    if game.is_legal(r, c, game.current_player):
                        game.start_turn()
                        game.board[r][c] = game.current_player
                        game.process_capture(r, c)
                        game.execute_move(action_type='single')
                        has_acted = True
                
                if event.pos[1] > sh * 0.8: 
                    game.switch_player()
                    has_acted = False

        await asyncio.sleep(0)
        clock.tick(60)

if __name__ == "__main__":
    asyncio.run(main())
