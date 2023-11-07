import pygame
from pygame.locals import *
import math
import sys
import pygame.mixer
import random


# 画面サイズ
SCREEN = Rect(0, 0, 400, 400)


# バドルのクラス
class Paddle(pygame.sprite.Sprite):
    # コンストラクタ（初期化メソッド）
    def __init__(self, filename):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.rect = self.image.get_rect()
        self.rect.bottom = SCREEN.bottom - 20          # パドルのy座標

    def update(self):
        self.rect.centerx = pygame.mouse.get_pos()[0]  # マウスのx座標をパドルのx座標に
        self.rect.clamp_ip(SCREEN)                     # ゲーム画面内のみで移動


# ボールのクラス
class Ball(pygame.sprite.Sprite):
    # コンストラクタ（初期化メソッド）
    def __init__(self, filename, paddle, blocks, score, speed, angle_left, angle_right):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.rect = self.image.get_rect()
        self.dx = self.dy = 0  # ボールの速度
        self.paddle = paddle  # パドルへの参照
        self.blocks = blocks  # ブロックグループへの参照
        self.update = self.start # ゲーム開始状態に更新
        self.score = score
        self.hit = 0  # 連続でブロックを壊した回数
        self.speed = speed # ボールの初期速度
        self.angle_left = angle_left # パドルの反射方向(左端:135度）
        self.angle_right = angle_right # パドルの反射方向(右端:45度）
        self.is_bullet = False
        self.bullet_life_time = 0

        

    # ゲーム開始状態（マウスを左クリック時するとボール射出）
    def start(self):
        # ボールの初期位置(パドルの上)
        self.rect.centerx = self.paddle.rect.centerx
        self.rect.bottom = self.paddle.rect.top

        # 左クリックでボール射出
        if pygame.mouse.get_pressed()[0] == 1:
            self.dx = 0
            self.dy = -self.speed
            self.update = self.move

    # ボールの挙動
    def move(self):
        self.rect.centerx += self.dx
        self.rect.centery += self.dy

        # 壁との反射
        if self.rect.left < SCREEN.left:    # 左側
            self.rect.left = SCREEN.left
            self.dx = -self.dx              # 速度を反転
        if self.rect.right > SCREEN.right:  # 右側
            self.rect.right = SCREEN.right
            self.dx = -self.dx
        if self.rect.top < SCREEN.top:      # 上側
            self.rect.top = SCREEN.top
            self.dy = -self.dy

        # パドルとの反射(左端:135度方向, 右端:45度方向, それ以外:線形補間)
        # 2つのspriteが接触しているかどうかの判定
        if self.rect.colliderect(self.paddle.rect) and self.dy > 0:
            self.hit = 0                                # 連続ヒットを0に戻す
            (x1, y1) = (self.paddle.rect.left - self.rect.width, self.angle_left)
            (x2, y2) = (self.paddle.rect.right, self.angle_right)
            x = self.rect.left                          # ボールが当たった位置
            y = (float(y2-y1)/(x2-x1)) * (x - x1) + y1  # 線形補間
            angle = math.radians(y)                     # 反射角度
            self.dx = self.speed * math.cos(angle)
            self.dy = -self.speed * math.sin(angle)
            self.paddle_sound.play()                    # 反射音

        # ボールを落とした場合
        if self.rect.top > SCREEN.bottom:
            self.update = self.start                    # ボールを初期状態に
            self.score.subtract_life()

        # ボールと衝突したブロックリストを取得（Groupが格納しているSprite中から、指定したSpriteと接触しているものを探索）
        blocks_collided = pygame.sprite.spritecollide(self, self.blocks, True)
        if blocks_collided:  # 衝突ブロックがある場合
            for block in blocks_collided:
                if not self.is_bullet:
                    self.bound_on_block(block)

                self.block_sound.play()     # 効果音を鳴らす
                self.hit += 1               # 衝突回数
                self.score.add_score(self.hit * 10)   # 衝突回数に応じてスコア加点
                block.crush()

        if self.is_bullet:
            self.bullet_life_time -= 1

            if self.bullet_life_time <= 0:
                self.is_bullet = False
    
        # シフトキーを押しているかどうかをチェック
        keys = pygame.key.get_pressed()
    
        if keys[K_LSHIFT]:
            # シフトキーが押されている場合、ボールのサイズを変更
            self.change_size(15, 15)
        elif keys[K_RSHIFT]:
            self.change_size(20, 20)
            
    #追加機能 ボールのサイズを変更
    def change_size(self, x, y):
        self.image = pygame.transform.scale(self.image,(x, y))
        
    def bound_on_block(self, block):
        oldrect = self.rect
        # ボールが左からブロックへ衝突した場合
        if oldrect.left < block.rect.left and oldrect.right < block.rect.right:
            self.rect.right = block.rect.left
            self.dx = -self.dx

        # ボールが右からブロックへ衝突した場合
        if block.rect.left < oldrect.left and block.rect.right < oldrect.right:
            self.rect.left = block.rect.right
            self.dx = -self.dx

        # ボールが上からブロックへ衝突した場合
        if oldrect.top < block.rect.top and oldrect.bottom < block.rect.bottom:
            self.rect.bottom = block.rect.top
            self.dy = -self.dy

        # ボールが下からブロックへ衝突した場合
        if block.rect.top < oldrect.top and block.rect.bottom < oldrect.bottom:
            self.rect.top = block.rect.bottom
            self.dy = -self.dy

# ブロックのクラス
class Block(pygame.sprite.Sprite):
    def __init__(self, filename, x, y, paddle, balls):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.rect = self.image.get_rect()
        # ブロックの左上座標
        self.rect.left = SCREEN.left + x * self.rect.width
        self.rect.top = SCREEN.top + y * self.rect.height

        self.paddle = paddle
        self.balls = balls

        # アイテムドロップ確率
        self.drop_rate = 0.9

    # 一定確率でアイテムをドロップする関数
    def crush(self):
        if random.random() < self.drop_rate:
            Item("item.png", self.rect.centerx, self.rect.centery, self.paddle, self.balls)

#敵キャラクターのクラス 
class Enemy(pygame.sprite.Sprite):
    def __init__(self, filename, x, y, paddle: Paddle):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.image = pygame.transform.rotozoom(self.image,0,0.2)
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.speed = 4  # 敵キャラクターの移動速度
        self.last_beam_time = 0  # 最後にビームを放った時間の初期値
        self.paddle = paddle

    def update(self,):
        # 敵キャラクターを左右に移動
        self.rect.x += self.speed
        # 画面端に達したら反転
        if self.rect.left < SCREEN.left or self.rect.right > SCREEN.right:
            self.speed = -self.speed
        
        # 一定の間隔でビームを放つ
        current_time = pygame.time.get_ticks()
        if current_time - self.last_beam_time > 2500:
            # ビームを放つ処理
            beam = Beam("beam.png", self.rect.centerx, self.rect.bottom, self.paddle)
            self.last_beam_time = current_time  # タイマーをリセット      

#ビームのクラス
class Beam(pygame.sprite.Sprite):
    def __init__(self, filename, x, y, paddle: Paddle):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.image = pygame.transform.rotozoom(self.image,0,0.1)
        self.image_forward = pygame.transform.flip(self.image, True, False)
        self.image_backward = pygame.transform.flip(self.image_forward, True, False)
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.speed = 5  # ビームの移動速度
        self.paddle = paddle

    def update(self):
        # ビームを↓方向に移動
        self.rect.y += self.speed

        # 画面外に出たら自動で削除
        if self.rect.bottom < 0:
            self.kill()

        if self.rect.colliderect(self.paddle.rect):
            print("<**********************************>")
            print("-----------Game Over-----------")
            print("------モンスターにやられました")
            print("<**********************************>")
            pygame.quit()

            sys.exit()
        
    


# ドロップアイテムのクラス
class Item(pygame.sprite.Sprite):
    def __init__(self, filename, x: int, y: int, paddle: Paddle, balls: pygame.sprite.Group):
        # アイテムタイプのリスト
        ITEM_TYPES = [
            "increase_balls",
            "bullet_ball"
        ]

        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.image.load(filename).convert()
        self.rect = self.image.get_rect()
        self.rect.center = x, y
        self.paddle = paddle
        self.balls = balls
        self.dy = 1   # アイテム落下速度

        self.type = random.choice(ITEM_TYPES)

    def update(self):
        self.rect.centery += self.dy

        # パドルと衝突していたら、アイテムを獲得して、sprtieを削除
        if self.rect.colliderect(self.paddle.rect) and self.dy > 0:
            self.gain()
            self.kill()

        # パドルが画面の外に出たら、sprtieを削除
        if self.rect.centery > SCREEN.bottom:
            self.kill()

    # アイテムを獲得すると呼ばれる関数
    def gain(self):
        if self.type == "increase_balls":
            print("increase_balls")
        elif self.type == "bullet_ball":
            for ball in self.balls:
                ball.is_bullet = True
                ball.bullet_life_time = 200

        # spriteを削除
        self.kill()


# スコアのクラス
class Score():
    
    def __init__(self, x, y, initial_lives, screen):
        self.sysfont = pygame.font.SysFont(None, 20)
        self.score = 0
        self.lives = initial_lives
        (self.x, self.y) = (x, y)
        self.game_over = False
        self.screen = screen
    def draw(self, screen):
        img = self.sysfont.render(f"SCORE: {self.score} | LIVES: {self.lives}" , True, (255,255,250))
        screen.blit(img, (self.x, self.y))

    def add_score(self, x):
        self.score += x

    def subtract_life(self: pygame.sprite):
        self.lives -= 1
        if self.lives <= 0:
            self.lives = 0
            print("<**********************************>")
            print("-----------Game Over-----------")
            print("------→ライフが0になりました")
            print("<**********************************>")
            pygame.quit()
            sys.exit()
            

    

def main():
    pygame.init()
    pygame.mixer.init(44100)
    screen = pygame.display.set_mode(SCREEN.size)
    Ball.paddle_sound = pygame.mixer.Sound(
        "flashing.mp3")    # パドルにボールが衝突した時の効果音取得
    Ball.block_sound = pygame.mixer.Sound(
        "flying_pan.mp3")    # ブロックにボールが衝突した時の効果音取得
    Ball.gameover_sound = pygame.mixer.Sound(
        "badend1.mp3")    # ゲームオーバー時の効果音取得
    # 描画用のスプライトグループ
    group = pygame.sprite.RenderUpdates()

    # 衝突判定用のスプライトグループ
    blocks = pygame.sprite.Group()
    balls = pygame.sprite.Group()

    # スプライトグループに追加
    Paddle.containers = group
    Ball.containers = group, balls
    Block.containers = group, blocks
    Item.containers = group

    # パドルの作成
    paddle = Paddle("paddle.png")

    

    # ブロックの作成(14*10)
    for x in range(1, 15):
        for y in range(1, 11):
            Block("block.png", x, y, paddle, balls)

    # スコアを画面(10, 10)に表示
    score = Score(10, 10, 2, screen)#命を2にする

    # ボールを作成
    Ball("ball.png",paddle, blocks, score, 5, 135, 45)

    clock = pygame.time.Clock()

    # スプライトグループの初期化
    enemies = pygame.sprite.Group()
    beams = pygame.sprite.Group()

    # スプライトグループに追加
    Enemy.containers = group, enemies
    Beam.containers = group, beams

    # 敵キャラクターの初期化（適切な座標を指定してください）
    Enemy("enemy.png", x, y, paddle)

    # ビームの初期化（適切な座標を指定してください）
    # beams = Beam("beam.png", x, y)
    

    

    

    
    while (1):
        pygame.display.flip()
        pygame.display.update()
        clock.tick(60)      # フレームレート(60fps)
        screen.fill((0,20,0))
        # 全てのスプライトグループを更新
        group.update()
        # 全てのスプライトグループを描画
        group.draw(screen)
        # スコアを描画
        score.draw(screen)
        # 画面更新
        # 描画用のスプライトグループ（敵キャラクターとビームを含む）
        #enemies = pygame.sprite.Group()
        #beams = pygame.sprite.Group()

        # スプライトグループに追加
        #Enemy.containers = group, enemies
        #Beam.containers = group, beams

        # メインのゲームループ内で以下のように敵キャラクターとビームを更新と描画します：

        # 敵キャラクターとビームの更新と描画
        #enemies.update()
        #enemies.draw(screen)
        #beams.update()
        #beams.draw(screen)
        pygame.display.flip()

        pygame.display.update()
        clock = pygame.time.Clock()

        # キーイベント（終了）
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN and event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()
                



if __name__ == "__main__":
    main()

