import asyncio
import pygame

async def main():
    pygame.init()
    screen = pygame.display.set_mode((560, 780))
    clock = pygame.time.Clock()
    
    while True:
        screen.fill((220, 179, 92)) # 棋盤底色
        # 畫一條測試線
        pygame.draw.line(screen, (0, 0, 0), (40, 40), (520, 40), 5)
        # 畫一個測試圓
        pygame.draw.circle(screen, (0, 0, 0), (280, 390), 50)
        
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return

        await asyncio.sleep(0) # 這是解決黑色畫面的核心
        clock.tick(60)

if __name__ == "__main__":
    asyncio.run(main())
