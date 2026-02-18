import asyncio
import pygame

async def main():
    pygame.init()
    # 畫布尺寸：560x780
    screen = pygame.display.set_mode((560, 780))
    pygame.display.set_caption("烏鷺爭霸 - 修復版")
    clock = pygame.time.Clock()
    
    while True:
        # 1. 填滿棋盤底色 (黃褐色)
        screen.fill((220, 179, 92))
        
        # 2. 畫出棋盤線 (測試繪圖)
        for i in range(9):
            pygame.draw.line(screen, (0, 0, 0), (40, 40 + i * 60), (520, 40 + i * 60), 2)
            pygame.draw.line(screen, (0, 0, 0), (40 + i * 60, 40), (40 + i * 60, 520), 2)
        
        # 3. 在中央畫一個圓測試
        pygame.draw.circle(screen, (0, 0, 0), (280, 280), 30)
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

        # 關鍵：這行能防止 len(code)=0 的崩潰與 focus 問題
        await asyncio.sleep(0) 
        clock.tick(60)

if __name__ == "__main__":
    asyncio.run(main())
