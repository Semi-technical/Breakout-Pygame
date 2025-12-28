import pygame
import random
import math
import json
import os
import array
from enum import Enum

# --- CONFIGURATION & CONSTANTS ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
TITLE = "NEON BREAKOUT: Github Edition"
SAVE_FILE = "highscore.json"
CUSTOM_LEVEL_FILE = "custom_levels.json"

# Colors
WHITE = (255, 255, 255)
BLACK = (15, 15, 25)
RED = (255, 80, 80)
GREEN = (80, 255, 80)
BLUE = (80, 80, 255)
YELLOW = (255, 255, 80)
ORANGE = (255, 165, 0)
PURPLE = (147, 112, 219)
CYAN = (0, 255, 255)
GREY = (100, 100, 100)

COLORS_LIST = [RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, CYAN]

# Game Settings
PADDLE_WIDTH = 100
PADDLE_HEIGHT = 15
BALL_RADIUS = 8
BALL_SPEED_BASE = 6
BRICK_WIDTH = 78
BRICK_HEIGHT = 25
PARTICLE_COUNT = 15

# Powerup Types
class PowerType(Enum):
    MULTIBALL = 0
    BIG_PADDLE = 1
    LASER = 2
    SLOW_BALL = 3
    EXTRA_LIFE = 4

# --- UTILS ---
def load_high_score():
    if not os.path.exists(SAVE_FILE):
        return 0
    try:
        with open(SAVE_FILE, 'r') as f:
            data = json.load(f)
            return data.get("highscore", 0)
    except:
        return 0

def save_high_score(score):
    current = load_high_score()
    if score > current:
        with open(SAVE_FILE, 'w') as f:
            json.dump({"highscore": score}, f)
        return True
    return False

# --- AUDIO SYSTEM ---
class SoundManager:
    def __init__(self):
        self.sounds = {}
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            self.sounds['paddle_hit'] = self.generate_beep(440, 0.1)     # A4
            self.sounds['brick_hit'] = self.generate_beep(523, 0.05)     # C5
            self.sounds['wall_hit'] = self.generate_beep(200, 0.05)      # Low thud
            self.sounds['powerup'] = self.generate_beep(880, 0.15)       # High beep
            self.sounds['die'] = self.generate_noise(0.5)                # White noise
        except Exception as e:
            print(f"Sound system warning: {e}")

    def generate_beep(self, frequency, duration):
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        buffer = array.array('h') 
        period = sample_rate // frequency
        for i in range(n_samples):
            value = 32767 if (i // (period // 2)) % 2 == 0 else -32768
            decay = 1.0 - (i / n_samples)
            buffer.append(int(value * decay * 0.3))
        return pygame.mixer.Sound(buffer)

    def generate_noise(self, duration):
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        buffer = array.array('h')
        for i in range(n_samples):
            value = random.randint(-32768, 32767)
            decay = 1.0 - (i / n_samples)
            buffer.append(int(value * decay * 0.3))
        return pygame.mixer.Sound(buffer)

    def play(self, name):
        if name in self.sounds:
            self.sounds[name].play()

# --- CLASSES ---

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 6)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(20, 40)
        self.size = random.randint(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size = max(0, self.size - 0.1)

    def draw(self, surface):
        if self.life > 0:
            alpha = int((self.life / 40) * 255)
            s = pygame.Surface((int(self.size*2), int(self.size*2)), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (int(self.size), int(self.size)), int(self.size))
            surface.blit(s, (int(self.x - self.size), int(self.y - self.size)))

class Powerup:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 20, 20)
        self.type = random.choice(list(PowerType))
        self.vy = 3
        self.color = WHITE
        self.active = True
        
        if self.type == PowerType.MULTIBALL: self.color = CYAN
        elif self.type == PowerType.BIG_PADDLE: self.color = GREEN
        elif self.type == PowerType.LASER: self.color = RED
        elif self.type == PowerType.SLOW_BALL: self.color = ORANGE
        elif self.type == PowerType.EXTRA_LIFE: self.color = PURPLE

    def update(self):
        self.rect.y += self.vy
        if self.rect.top > SCREEN_HEIGHT:
            self.active = False

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=5)
        font = pygame.font.Font(None, 20)
        letter = self.type.name[0]
        text = font.render(letter, True, BLACK)
        surface.blit(text, (self.rect.centerx - text.get_width()//2, self.rect.centery - text.get_height()//2))

class Laser:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x - 2, y, 4, 15)
        self.vy = -8
        self.active = True

    def update(self):
        self.rect.y += self.vy
        if self.rect.bottom < 0:
            self.active = False

    def draw(self, surface):
        pygame.draw.rect(surface, RED, self.rect)

class Ball:
    def __init__(self, x, y, speed_mult=1.0):
        self.rect = pygame.Rect(x - BALL_RADIUS, y - BALL_RADIUS, BALL_RADIUS * 2, BALL_RADIUS * 2)
        self.dx = random.choice([-1, 1]) * 4
        self.dy = -4
        self.speed = BALL_SPEED_BASE * speed_mult
        self.active = True
        self.stuck_to_paddle = True
        self.offset_x = 0
        self.trail = []  # TRAIL EFFECT

    def launch(self):
        self.stuck_to_paddle = False
        self.dy = -abs(self.speed)
        self.dx = random.uniform(-2, 2)
    
    def normalize_velocity(self):
        vel = math.hypot(self.dx, self.dy)
        if vel == 0: return
        scale = self.speed / vel
        self.dx *= scale
        self.dy *= scale

    def update(self, paddle):
        # Update Trail
        self.trail.append((self.rect.centerx, self.rect.centery))
        if len(self.trail) > 8:
            self.trail.pop(0)

        wall_hit = False

        if self.stuck_to_paddle:
            self.rect.centerx = paddle.rect.centerx + self.offset_x
            self.rect.bottom = paddle.rect.top
        else:
            self.rect.x += self.dx
            self.rect.y += self.dy
            self.normalize_velocity()

            # Wall Collisions
            if self.rect.left <= 0:
                self.rect.left = 0
                self.dx *= -1
                wall_hit = True
            if self.rect.right >= SCREEN_WIDTH:
                self.rect.right = SCREEN_WIDTH
                self.dx *= -1
                wall_hit = True
            if self.rect.top <= 0:
                self.rect.top = 0
                self.dy *= -1
                wall_hit = True
            
            if self.rect.top > SCREEN_HEIGHT:
                self.active = False
        
        return wall_hit

    def draw(self, surface):
        # Draw Trail
        for i, pos in enumerate(self.trail):
            alpha = int((i / len(self.trail)) * 100)
            radius = int(BALL_RADIUS * (i / len(self.trail)))
            s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*WHITE, alpha), (radius, radius), radius)
            surface.blit(s, (pos[0] - radius, pos[1] - radius))

        pygame.draw.circle(surface, WHITE, self.rect.center, BALL_RADIUS)

class Brick:
    def __init__(self, x, y, color):
        self.rect = pygame.Rect(x, y, BRICK_WIDTH, BRICK_HEIGHT)
        self.color = color
        self.active = True
        self.has_powerup = random.random() < 0.15

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=3)
        pygame.draw.rect(surface, (255, 255, 255, 50), self.rect, 2)

class Paddle:
    def __init__(self):
        self.width = PADDLE_WIDTH
        self.height = PADDLE_HEIGHT
        self.rect = pygame.Rect(SCREEN_WIDTH // 2 - self.width // 2, SCREEN_HEIGHT - 40, self.width, self.height)
        self.speed = 8
        self.color = CYAN
        
        self.laser_active = False
        self.big_active = False
        self.powerup_timer = 0
        self.shoot_timer = 0

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed
        
        if self.rect.left < 0: self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH: self.rect.right = SCREEN_WIDTH

        if self.powerup_timer > 0:
            self.powerup_timer -= 1
            if self.powerup_timer == 0:
                self.reset_powerups()
        
        if self.laser_active and keys[pygame.K_SPACE]:
            if self.shoot_timer <= 0:
                self.shoot_timer = 20
                return True
            else:
                self.shoot_timer -= 1
        elif self.shoot_timer > 0:
            self.shoot_timer -= 1
        return False

    def activate_powerup(self, p_type):
        self.powerup_timer = 600
        if p_type == PowerType.BIG_PADDLE:
            self.big_active = True
            self.rect.width = PADDLE_WIDTH * 1.5
            self.rect.x -= (PADDLE_WIDTH * 0.25)
            self.color = GREEN
        elif p_type == PowerType.LASER:
            self.laser_active = True
            self.color = RED

    def reset_powerups(self):
        self.laser_active = False
        self.big_active = False
        center = self.rect.centerx
        self.rect.width = PADDLE_WIDTH
        self.rect.centerx = center
        self.color = CYAN

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=5)
        if self.laser_active:
            pygame.draw.rect(surface, RED, (self.rect.left, self.rect.top-5, 5, 5))
            pygame.draw.rect(surface, RED, (self.rect.right-5, self.rect.top-5, 5, 5))

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.Font(None, 74)
        self.font_small = pygame.font.Font(None, 36)
        
        self.sound_manager = SoundManager()
        self.highscore = load_high_score()
        self.state = "MENU" # MENU, PLAYING, GAMEOVER, PAUSED
        self.fullscreen = False
        
        self.reset_game()

    def reset_game(self):
        self.lives = 3
        self.score = 0
        self.level = 1
        self.combo = 1
        self.ball_speed_mult = 1.0
        self.reset_level(new_pattern=True)

    def generate_level(self):
        bricks = []
        
        # Check Custom Level on Level 1
        if self.level == 1 and os.path.exists(CUSTOM_LEVEL_FILE):
            try:
                with open(CUSTOM_LEVEL_FILE, 'r') as f:
                    data = json.load(f)
                    level_data = data.get("custom_level", [])
                    for b_data in level_data:
                        r, c, color_idx = b_data["r"], b_data["c"], b_data["color_idx"]
                        bx = c * (BRICK_WIDTH + 2) + 2
                        by = 60 + r * (BRICK_HEIGHT + 2)
                        if 0 <= color_idx < len(COLORS_LIST):
                            bricks.append(Brick(bx, by, COLORS_LIST[color_idx]))
                    print("Custom level loaded!")
                    return bricks
            except Exception as e:
                print(f"Error loading custom level: {e}")

        # Procedural Generation
        rows = 4 + (self.level // 2)
        cols = 10
        start_y = 60
        pattern_type = self.level % 4
        
        for r in range(rows):
            for c in range(cols):
                bx = c * (BRICK_WIDTH + 2) + 2
                by = start_y + r * (BRICK_HEIGHT + 2)
                color = COLORS_LIST[r % len(COLORS_LIST)]
                
                add_brick = True
                if pattern_type == 1:
                    if (r + c) % 2 == 0: add_brick = False
                elif pattern_type == 2:
                    if c < r or c >= cols - r: add_brick = False
                elif pattern_type == 3:
                    if random.random() < 0.2: add_brick = False

                if add_brick:
                    bricks.append(Brick(bx, by, color))
        return bricks

    def reset_level(self, new_pattern=False):
        self.paddle = Paddle()
        self.balls = [Ball(SCREEN_WIDTH//2, SCREEN_HEIGHT - 60, self.ball_speed_mult)]
        self.powerups = []
        self.particles = []
        self.lasers = []
        if new_pattern:
            self.bricks = self.generate_level()

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_F11:
                    self.fullscreen = not self.fullscreen
                    if self.fullscreen:
                        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
                    else:
                        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                
                if self.state == "MENU" and event.key == pygame.K_SPACE:
                    self.state = "PLAYING"
                    self.reset_game()
                
                elif self.state == "GAMEOVER" and event.key == pygame.K_SPACE:
                    self.state = "MENU"

                elif self.state == "PLAYING":
                    if event.key == pygame.K_p: # PAUSE
                        self.state = "PAUSED"
                    elif event.key == pygame.K_SPACE:
                        for b in self.balls:
                            if b.stuck_to_paddle:
                                b.launch()
                
                elif self.state == "PAUSED":
                    if event.key == pygame.K_p:
                        self.state = "PLAYING"

        return True

    def spawn_particles(self, x, y, color):
        for _ in range(PARTICLE_COUNT):
            self.particles.append(Particle(x, y, color))

    def check_collisions(self):
        # 1. Paddle shoots laser
        if self.paddle.update():
            self.lasers.append(Laser(self.paddle.rect.left + 5, self.paddle.rect.top))
            self.lasers.append(Laser(self.paddle.rect.right - 5, self.paddle.rect.top))

        # 2. Lasers
        for laser in self.lasers[:]:
            laser.update()
            if not laser.active:
                if laser in self.lasers: # <--- SAFETY CHECK
                    self.lasers.remove(laser)
                continue
            
            hit_index = laser.rect.collidelist([b.rect for b in self.bricks])
            if hit_index != -1:
                brick = self.bricks.pop(hit_index)
                self.spawn_particles(brick.rect.centerx, brick.rect.centery, brick.color)
                self.score += (10 * self.combo) 
                self.combo += 1
                self.sound_manager.play('brick_hit')
                
                self.handle_brick_break(brick)
                
                # FIX: Check if laser is still in list before removing
                # (Level reset might have cleared it)
                if laser in self.lasers: 
                    self.lasers.remove(laser)

        # 3. Balls
        for ball in self.balls[:]:
            if ball.update(self.paddle):
                self.sound_manager.play('wall_hit')

            # Paddle
            if ball.rect.colliderect(self.paddle.rect) and ball.dy > 0:
                self.sound_manager.play('paddle_hit')
                self.combo = 1 # RESET COMBO
                
                relative_intersect_x = (self.paddle.rect.centerx - ball.rect.centerx)
                normalized_intersect = relative_intersect_x / (self.paddle.width / 2)
                bounce_angle = normalized_intersect * (5 * math.pi / 12)
                
                speed = ball.speed
                ball.dx = speed * -math.sin(bounce_angle)
                ball.dy = -speed * math.cos(bounce_angle)
            
            # Brick
            hit_index = ball.rect.collidelist([b.rect for b in self.bricks])
            if hit_index != -1:
                brick = self.bricks.pop(hit_index)
                self.spawn_particles(brick.rect.centerx, brick.rect.centery, brick.color)
                
                self.score += (10 * self.combo)
                self.combo += 1 # INCREASE COMBO
                
                self.sound_manager.play('brick_hit')
                self.handle_brick_break(brick)
                
                b_rect = brick.rect
                if (ball.rect.centerx < b_rect.left or ball.rect.centerx > b_rect.right):
                    ball.dx *= -1
                else:
                    ball.dy *= -1

            if not ball.active:
                self.balls.remove(ball)

        # 4. Powerups
        for p in self.powerups[:]:
            p.update()
            if p.rect.colliderect(self.paddle.rect):
                self.sound_manager.play('powerup')
                self.apply_powerup(p.type)
                self.powerups.remove(p)
            elif not p.active:
                self.powerups.remove(p)

    def handle_brick_break(self, brick):
        if brick.has_powerup:
            self.powerups.append(Powerup(brick.rect.centerx, brick.rect.centery))
        if len(self.bricks) == 0:
            self.next_level()

    def apply_powerup(self, p_type):
        if p_type == PowerType.MULTIBALL:
            if len(self.balls) > 0:
                base = self.balls[0]
                for _ in range(2):
                    b = Ball(base.rect.centerx, base.rect.centery, self.ball_speed_mult)
                    b.stuck_to_paddle = False
                    b.dx = random.choice([-3, 3])
                    b.dy = -4
                    self.balls.append(b)
        elif p_type == PowerType.SLOW_BALL:
            for b in self.balls:
                b.speed *= 0.7
        elif p_type == PowerType.EXTRA_LIFE:
            self.lives += 1
        else:
            self.paddle.activate_powerup(p_type)

    def next_level(self):
        self.level += 1
        self.ball_speed_mult += 0.1
        self.reset_level(new_pattern=True)

    def draw_ui(self):
        pygame.draw.rect(self.screen, (30, 30, 50), (0, 0, SCREEN_WIDTH, 40))
        
        score_text = self.font_small.render(f"Score: {self.score}", True, WHITE)
        level_text = self.font_small.render(f"Level: {self.level}", True, WHITE)
        lives_text = self.font_small.render(f"Lives: {self.lives}", True, WHITE)
        
        self.screen.blit(score_text, (20, 10))
        self.screen.blit(level_text, (SCREEN_WIDTH//2 - level_text.get_width()//2, 10))
        self.screen.blit(lives_text, (SCREEN_WIDTH - 120, 10))

        if self.combo > 1:
            combo_text = self.font_small.render(f"COMBO x{self.combo}!", True, YELLOW)
            self.screen.blit(combo_text, (SCREEN_WIDTH//2 - combo_text.get_width()//2, 50))

    def run(self):
        running = True
        while running:
            self.screen.fill(BLACK)
            running = self.handle_input()
            
            if self.state == "MENU":
                title = self.font_large.render("NEON BREAKOUT", True, CYAN)
                sub = self.font_small.render("Press SPACE to Start", True, WHITE)
                hi = self.font_small.render(f"High Score: {self.highscore}", True, YELLOW)
                
                self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 200))
                self.screen.blit(sub, (SCREEN_WIDTH//2 - sub.get_width()//2, 300))
                self.screen.blit(hi, (SCREEN_WIDTH//2 - hi.get_width()//2, 350))
                
                if random.random() < 0.1:
                    self.spawn_particles(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), random.choice(COLORS_LIST))
                
            elif self.state == "PLAYING":
                self.check_collisions()
                
                if len(self.balls) == 0:
                    self.sound_manager.play('die')
                    self.lives -= 1
                    if self.lives <= 0:
                        save_high_score(self.score)
                        self.highscore = load_high_score()
                        self.state = "GAMEOVER"
                    else:
                        self.balls = [Ball(SCREEN_WIDTH//2, SCREEN_HEIGHT - 60, self.ball_speed_mult)]
                        self.paddle.reset_powerups()
                        self.combo = 1

                for p in self.particles[:]:
                    p.update()
                    p.draw(self.screen)
                    if p.life <= 0: self.particles.remove(p)

                self.paddle.draw(self.screen)
                for b in self.bricks: b.draw(self.screen)
                for b in self.balls: b.draw(self.screen)
                for p in self.powerups: p.draw(self.screen)
                for l in self.lasers: l.draw(self.screen)
                
                self.draw_ui()

            elif self.state == "PAUSED":
                # Draw game static
                self.paddle.draw(self.screen)
                for b in self.bricks: b.draw(self.screen)
                for b in self.balls: b.draw(self.screen)
                
                # Overlay
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 150))
                self.screen.blit(overlay, (0,0))
                
                pause_text = self.font_large.render("PAUSED", True, WHITE)
                sub_text = self.font_small.render("Press P to Resume", True, GREY)
                self.screen.blit(pause_text, (SCREEN_WIDTH//2 - pause_text.get_width()//2, SCREEN_HEIGHT//2 - 20))
                self.screen.blit(sub_text, (SCREEN_WIDTH//2 - sub_text.get_width()//2, SCREEN_HEIGHT//2 + 40))

            elif self.state == "GAMEOVER":
                t1 = self.font_large.render("GAME OVER", True, RED)
                t2 = self.font_small.render(f"Final Score: {self.score}", True, WHITE)
                t3 = self.font_small.render("Press SPACE for Menu", True, GREY)
                
                self.screen.blit(t1, (SCREEN_WIDTH//2 - t1.get_width()//2, 200))
                self.screen.blit(t2, (SCREEN_WIDTH//2 - t2.get_width()//2, 280))
                self.screen.blit(t3, (SCREEN_WIDTH//2 - t3.get_width()//2, 330))

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()

if __name__ == "__main__":
    Game().run()