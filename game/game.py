import pygame as pg
import random 

pg.init()


screen = pg.display.set_mode((800, 600))
pg.display.set_caption("YO_BATTLE")
clock = pg.time.Clock()


battle_area = pg.Rect(250,150,300,250)
player = pg.Rect(350, 300, 20, 20)
bullet = pg.Rect(300, 100, 10, 10)

font = pg.font.Font(None, 30)

hp = 20
max_hp = 20
last_hit = 0
restarts = 0

def reset_game():
    player = pg.Rect(350, 300, 20,20)
    hp = max_hp

    bullets = []

    for i in range(10):
        bullet = pg.Rect(random.randint(battle_area.left, battle_area.right - 10),battle_area.top,10,10)
        bullets.append(bullet)
    return player, hp, bullets


running = True

player, hp, bullets = reset_game()

while running:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False

    screen.fill((0,0,0))



    if hp <= 0:
        restarts += 1
        player, hp, bullets = reset_game()

    pg.draw.rect(screen, (100,100,100),(350,425,200,20))
    pg.draw.rect(screen, (0,255,0),(350,425,int(200* hp/max_hp),20))

    text_restart = font.render(f"{restarts}", True, (255, 255, 255))
    text = font.render(f"HP: {hp}/{max_hp}", True, (255, 255, 255))
    screen.blit(text, (250, 425))
    screen.blit(text_restart, (50, 500))

    pg.draw.rect(screen, (255,255,255), battle_area, 3)

    keys = pg.key.get_pressed()

    for bullet in bullets:
        if bullet.y <= 387:
            bullet.y += 3
        else:
            bullet.y = random.randint(50, 150)
            bullet.x = random.randint(battle_area.left, battle_area.right - bullet.width)

    if keys[pg.K_LEFT]:
        player.x -= 5

    if keys[pg.K_RIGHT]:
        player.x += 5

    if keys[pg.K_UP]:
        player.y -= 5

    if keys[pg.K_DOWN]:
        player.y += 5

    player.x = max(battle_area.left + 3, min(player.x, battle_area.right - 3 - player.width))
    player.y = max(battle_area.top + 3, min(player.y, battle_area.bottom - 3 - player.height))

        
    pg.draw.rect(screen, (255,0,0), player)
    for bullet in bullets:
     pg.draw.rect(screen, (255, 255, 255), bullet)
     if player.colliderect(bullet):
            now = pg.time.get_ticks()

            if player.colliderect(bullet) and now - last_hit >= 500:
                hp -= 1
                last_hit = now
            bullet.y = 150
            bullet.x = random.randint(battle_area.left, battle_area.right - bullet.width)

    pg.display.flip()
    clock.tick(60)

pg.quit()