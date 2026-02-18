import numpy as np
import random

# ==========================================
# 1. 遊戲常數 (Constants)
# ==========================================
EMPTY, BLACK, WHITE = 0, 1, 2
BOARD_SIZE = 9
KOMI = 7.5  # 貼目

# ==========================================
# 2. 卡牌資料庫與變換邏輯 (Card Logic)
# ==========================================
class CardTransformer:
    def __init__(self):
        # (中文名, 能量, 相對座標, 張數, 鏡像支援)
        self.db = {
            # --- 基礎低費卡 ---
            "Stretch": ("長", 2, [(0,0), (1,0)], 3, False),
            "Diagonal": ("尖", 2, [(0,0), (1,1)], 3, False),
            "One-space Jump": ("一間跳", 1, [(0,0), (2,0)], 3, False),
            "Two-space Jump": ("二間跳", 1, [(0,0), (3,0)], 2, False),
            "Knight's Move": ("小飛", 1, [(0,0), (2,1)], 3, True),
            "Large Knight's Move": ("大飛", 1, [(0,0), (3,1)], 2, True),
            "Elephant's Move": ("象飛", 1, [(0,0), (2,2)], 2, False),
            "Double Diagonal": ("斜三", 2, [(0,0), (1,1), (2,2)], 2, False),
            
            # --- 修正：通用高費卡 (雙方各1張，皆為3費) ---
            "Tiger's Mouth": ("虎口", 3, [(0,0), (1,1), (-1,1)], 1, False),
            "Ponnuki": ("空心提", 3, [(0,0), (1,1), (-1,1), (0,2)], 1, False),
            "Bent Three": ("彎三", 3, [(0,0), (1,0), (0,1)], 1, True),
            "Straight Three": ("直三", 3, [(0,0), (1,0), (2,0)], 1, False),

            # --- 陣營專屬卡 (維持不變) ---
            "Dark Strike": ("黯擊", 3, [(0,0), (1,0), (2,0), (1,1)], 1, False), # 黑專屬
            "Sun Trample": ("踐日", 2, [(0,0), (1,0), (1,2)], 2, True),         # 黑專屬
            "Bright Flash": ("皓閃", 3, [(0,0), (1,1), (0,2), (1,3)], 1, True), # 白專屬
            "Moon Shard": ("碎月", 2, [(0,0), (1,1), (1,3)], 2, True)           # 白專屬
        }

    def rotate_90(self, coords):
        return [(c, -r) for r, c in coords]

    def flip_horizontal(self, coords):
        return [(r, -c) for r, c in coords]

    def get_all_variants(self, card_name):
        if card_name not in self.db: return []
        _, _, base_coords, _, can_flip = self.db[card_name]
        
        final_variants = []
        curr_seq = base_coords
        for _ in range(4):
            curr_seq = self.rotate_90(curr_seq)
            final_variants.append(curr_seq)
            if can_flip:
                final_variants.append(self.flip_horizontal(curr_seq))
        return final_variants

# ==========================================
# 3. 遊戲狀態機 (State Machine)
# ==========================================
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

        # 快照與回溯
        self.ko_snapshot = None
        self.turn_start_snapshot = np.zeros((BOARD_SIZE, BOARD_SIZE), dtype=np.int8)
        self.turn_start_mana = {BLACK: 1, WHITE: 1}
        self.turn_start_hand = {BLACK: [], WHITE: []} 

    def _init_decks(self):
        # 1. 基礎通用卡 (Basic Commons)
        basics = ["Stretch"]*3 + ["Diagonal"]*3 + ["One-space Jump"]*3 + \
                 ["Two-space Jump"]*2 + ["Knight's Move"]*3 + ["Large Knight's Move"]*2 + \
                 ["Elephant's Move"]*2 + ["Double Diagonal"]*1
        
        # 2. 進階通用卡 (Advanced Commons) - 修正：雙方各1張
        advanced = ["Tiger's Mouth"]*1 + ["Ponnuki"]*1 + ["Bent Three"]*1 + ["Straight Three"]*1

        # 3. 陣營專屬卡 (Exclusives)
        # 移除已移至通用的卡牌
        black_exclusives = ["Dark Strike"]*1 + ["Sun Trample"]*2
        white_exclusives = ["Bright Flash"]*1 + ["Moon Shard"]*2

        # 組合牌庫
        self.decks[BLACK] = basics + advanced + black_exclusives
        self.decks[WHITE] = basics + advanced + white_exclusives
        
        # 洗牌
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
        card = self.decks[color].pop()
        self.hand[color].append(card)

    def is_legal(self, r, c, color):
        if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE): return False
        if self.board[r, c] != EMPTY: return False
        orig = self.board.copy()
        self.board[r, c] = color
        self.process_capture(r, c)
        if self.ko_snapshot is not None and np.array_equal(self.board, self.ko_snapshot):
            self.board = orig
            return False
        has_lib = self.has_liberty(r, c)
        self.board = orig
        return has_lib

    def has_liberty(self, r, c):
        color = self.board[r, c]
        queue, visited = [(r, c)], {(r, c)}
        while queue:
            curr_r, curr_c = queue.pop(0)
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr, nc = curr_r + dr, curr_c + dc
                if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                    if self.board[nr, nc] == EMPTY: return True
                    if self.board[nr, nc] == color and (nr, nc) not in visited:
                        visited.add((nr, nc)); queue.append((nr, nc))
        return False

    def process_capture(self, r, c):
        opp = WHITE if self.board[r, c] == BLACK else BLACK
        for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and self.board[nr, nc] == opp:
                if not self.has_liberty(nr, nc):
                    color = self.board[nr, nc]
                    q, v = [(nr, nc)], {(nr, nc)}
                    while q:
                        cr, cc = q.pop(0)
                        self.board[cr, cc] = EMPTY
                        for ddr, ddc in [(0,1),(0,-1),(1,0),(-1,0)]:
                            nnr, nnc = cr + ddr, cc + ddc
                            if 0 <= nnr < BOARD_SIZE and 0 <= nnc < BOARD_SIZE:
                                if self.board[nnr, nnc] == color and (nnr, nnc) not in v:
                                    v.add((nnr, nnc)); q.append((nnr, nnc))

    def start_turn(self):
        self.turn_start_snapshot = self.board.copy()
        self.turn_start_mana = self.mana.copy()
        self.turn_start_hand[BLACK] = self.hand[BLACK][:]
        self.turn_start_hand[WHITE] = self.hand[WHITE][:]

    def rollback(self):
        self.board = self.turn_start_snapshot.copy()
        self.mana = self.turn_start_mana.copy()
        self.hand[BLACK] = self.turn_start_hand[BLACK][:]
        self.hand[WHITE] = self.turn_start_hand[WHITE][:]

    def execute_move(self, action_type='card', used_card=None):
        self.ko_snapshot = self.turn_start_snapshot.copy()
        if action_type == 'card' and used_card:
            if used_card in self.hand[self.current_player]:
                self.hand[self.current_player].remove(used_card)
                self.discards[self.current_player].append(used_card)
        elif action_type == 'single':
            self.mana[self.current_player] = min(3, self.mana[self.current_player] + 1)
            self.draw_card(self.current_player)
        elif action_type == 'pass':
            pass 

    def switch_player(self):
        self.current_player = WHITE if self.current_player == BLACK else BLACK

    def trade_resources(self, discard_indices, target_resource):
        current_hand = self.hand[self.current_player]
        if len(discard_indices) != 2: return False
        if any(idx < 0 or idx >= len(current_hand) for idx in discard_indices): return False
        if len(set(discard_indices)) != 2: return False 

        cards_to_discard = []
        for idx in sorted(discard_indices, reverse=True):
            card = self.hand[self.current_player].pop(idx)
            cards_to_discard.append(card)
            self.discards[self.current_player].append(card)
        
        if target_resource == 'mana':
            self.mana[self.current_player] = min(3, self.mana[self.current_player] + 1)
        elif target_resource == 'card':
            self.draw_card(self.current_player)
            
        return True

    def remove_dead_group(self, r, c):
        target_color = self.board[r, c]
        if target_color == EMPTY: return
        q, group = [(r, c)], {(r, c)}
        while q:
            curr_r, curr_c = q.pop(0)
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr, nc = curr_r + dr, curr_c + dc
                if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                    if self.board[nr, nc] == target_color and (nr, nc) not in group:
                        group.add((nr, nc)); q.append((nr, nc))
        for gr, gc in group: self.board[gr, gc] = EMPTY

    def calculate_score(self):
        black_score, white_score = 0.0, 0.0
        visited_empty = set()
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                color = self.board[r, c]
                if color == BLACK: black_score += 1.0
                elif color == WHITE: white_score += 1.0
        
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if self.board[r, c] == EMPTY and (r, c) not in visited_empty:
                    region, borders = [], set()
                    q = [(r, c)]; visited_empty.add((r, c))
                    while q:
                        curr_r, curr_c = q.pop(0)
                        region.append((curr_r, curr_c))
                        for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                            nr, nc = curr_r + dr, curr_c + dc
                            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                                neighbor = self.board[nr, nc]
                                if neighbor == EMPTY and (nr, nc) not in visited_empty:
                                    visited_empty.add((nr, nc)); q.append((nr, nc))
                                elif neighbor != EMPTY: borders.add(neighbor)
                    area_size = len(region)
                    if borders == {BLACK}: black_score += area_size
                    elif borders == {WHITE}: white_score += area_size
                    else: black_score += area_size * 0.5; white_score += area_size * 0.5

        white_score += KOMI
        winner = f"黑方勝 (+{black_score - white_score:.1f})" if black_score > white_score else f"白方勝 (+{white_score - black_score:.1f})"
        return black_score, white_score, winner
