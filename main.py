import asyncio
import pygame

async def main():
    pygame.init()
    # 設定畫布大小 (560x780)
    screen = pygame.display.set_mode((560, 780))
    pygame.display.set_caption("烏鷺爭霸 - 測試版")
    
    clock = pygame.time.Clock()
    
    while True:
        # 1. 填滿棋盤底色
        screen.fill((220, 179, 92))
        
        # 2. 畫出簡單網格 (測試繪圖)
        for i in range(9):
            # 橫線
            pygame.draw.line(screen, (0, 0, 0), (40, 40 + i * 60), (520, 40 + i * 60), 2)
            # 直線
            pygame.draw.line(screen, (0, 0, 0), (40 + i * 60, 40), (40 + i * 60, 520), 2)
        
        # 3. 畫一個測試圓形
        pygame.draw.circle(screen, (0, 0, 0), (280, 280), 30)
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

        # 關鍵：解決 DISCARD : focus 與網頁卡死的關鍵
        await asyncio.sleep(0) 
        clock.tick(60)

if __name__ == "__main__":
    asyncio.run(main())
