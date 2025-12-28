import pygame
import json
import os

# CONFIG
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BRICK_WIDTH = 78
BRICK_HEIGHT = 25
COLS = 10
ROWS = 14
SAVE_FILE = "custom_levels.json"

# COLORS
BLACK = (15, 15, 25)
WHITE = (255, 255, 255)
colors = [
    (255, 80, 80),   # Red
    (255, 165, 0),   # Orange
    (255, 255, 80),  # Yellow
    (80, 255, 80),   # Green
    (80, 80, 255),   # Blue
    (147, 112, 219), # Purple
    (0, 255, 255)    # Cyan
]

class Editor:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Level Editor - 1-7: Color, Click: Place/Remove, S: Save")
        self.clock = pygame.time.Clock()
        self.grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.current_color_idx = 0
        self.font = pygame.font.SysFont("Arial", 18)

    def draw_grid(self):
        for r in range(ROWS):
            for c in range(COLS):
                rect = pygame.Rect(c * (BRICK_WIDTH + 2) + 2, 60 + r * (BRICK_HEIGHT + 2), BRICK_WIDTH, BRICK_HEIGHT)
                pygame.draw.rect(self.screen, (30, 30, 40), rect, 1) # Outline
                
                # Draw active brick
                if self.grid[r][c] is not None:
                    color = colors[self.grid[r][c]]
                    pygame.draw.rect(self.screen, color, rect)

    def save_level(self):
        # Convert grid to simple list of dicts
        level_data = []
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] is not None:
                    level_data.append({
                        "r": r, 
                        "c": c, 
                        "color_idx": self.grid[r][c]
                    })
        
        with open(SAVE_FILE, 'w') as f:
            json.dump({"custom_level": level_data}, f)
        print("Level saved to custom_levels.json!")

    def run(self):
        running = True
        while running:
            self.screen.fill(BLACK)
            
            # Instructions
            text = f"Selected Color: {self.current_color_idx + 1}"
            col_surf = self.font.render(text, True, colors[self.current_color_idx])
            self.screen.blit(col_surf, (10, 10))
            self.screen.blit(self.font.render("Press S to Save", True, WHITE), (200, 10))
            
            self.draw_grid()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # Keyboard: Select Colors and Save
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_s:
                        self.save_level()
                    if pygame.K_1 <= event.key <= pygame.K_7:
                        self.current_color_idx = event.key - pygame.K_1

                # Mouse: Paint Bricks
                if pygame.mouse.get_pressed()[0]: # Left click
                    mx, my = pygame.mouse.get_pos()
                    # Convert mouse to grid coords
                    if my > 60:
                        c = (mx - 2) // (BRICK_WIDTH + 2)
                        r = (my - 60) // (BRICK_HEIGHT + 2)
                        
                        if 0 <= r < ROWS and 0 <= c < COLS:
                            self.grid[r][c] = self.current_color_idx
                
                # Mouse: Erase (Right Click)
                if pygame.mouse.get_pressed()[2]: 
                    mx, my = pygame.mouse.get_pos()
                    if my > 60:
                        c = (mx - 2) // (BRICK_WIDTH + 2)
                        r = (my - 60) // (BRICK_HEIGHT + 2)
                        if 0 <= r < ROWS and 0 <= c < COLS:
                            self.grid[r][c] = None

            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

if __name__ == "__main__":
    Editor().run()