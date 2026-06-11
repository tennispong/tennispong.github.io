import pygame
import sys
import random
import math

pygame.init()
WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tennis Pong")
clock = pygame.time.Clock()
pygame.mouse.set_visible(False)

# Colors
TENNIS_COURT = (40, 110, 70)
TENNIS_YELLOW = (210, 245, 60)
WHITE = (255, 255, 255)
SHADOW_COL = (20, 80, 45)
FRAME_COL = (220, 50, 50)
FRAME_SHINE = (255, 130, 130)
STRING_MAIN = (230, 230, 180)
STRING_CROSS = (200, 200, 140)
THROAT_COL = (200, 40, 40)
HANDLE_COL = (160, 100, 40)
GRIP_BASE = (35, 35, 35)
GRIP_BAND = (60, 60, 60)
BUTT_COL = (80, 80, 80)

# ── Racket geometry (all in "racket space": head right, grip left) ──────────
HEAD_W     = 40
HEAD_H     = 62
NECK_LEN   = 18
HANDLE_LEN = 58
HANDLE_W   = 10
GRIP_LEN   = 28
FRAME_W    = 5
SURF_SIZE  = 260
# In racket-space the grip (pivot) is at the LEFT end of the handle.
# We put it at SURF_SIZE//2, SURF_SIZE//2 for easy rotation.
# Head center is roughly at (pivot_x + HANDLE_LEN + NECK_LEN + HEAD_W//2, pivot_y).
PIVOT_X = SURF_SIZE // 2   # grip end = rotation pivot
PIVOT_Y = SURF_SIZE // 2
HEAD_CX = PIVOT_X + HANDLE_LEN + NECK_LEN + HEAD_W // 2 - 4  # approx head centre x

# swing angles: 0 = racket pointing right (head away from player, ready)
# pivot-based so the HEAD sweeps a real arc
IDLE_ANGLE   =   0
WINDUP_ANGLE =  65    # pulled back (clockwise from p1's view)
STRIKE_ANGLE = -95    # whipped through (counter-clockwise)
FOLLOW_ANGLE =  -45   # resting

WINDUP_F  = 5
STRIKE_F  = 4
FOLLOW_F  = 20

ball_radius = 12
player1_x = 6
player1_y = HEIGHT // 2
player2_x = WIDTH - 6
player2_y = HEIGHT // 2
ai_speed  = 16

ball_x, ball_y = WIDTH // 2, HEIGHT // 2
ball_speed_x, ball_speed_y = 6 * random.choice((1,-1)), 6 * random.choice((1,-1))
score1 = score2 = 0
font       = pygame.font.SysFont("Arial", 40, bold=True)
small_font = pygame.font.SysFont("Arial", 16)

p1_phase = p2_phase = 'idle'
p1_angle = p2_angle = 0.0
p1_pt    = p2_pt    = 0
p1_dir   = p2_dir   = 1


# ── helpers ─────────────────────────────────────────────────────────────────
def lerp(a, b, t): return a + (b-a)*t
def ease_out(t):   return 1-(1-t)**3
def ease_in(t):    return t*t*t


def update_swing(phase, angle, pt, sd):
    pt += 1
    if phase == 'windup':
        t = min(pt/WINDUP_F, 1.0)
        angle = lerp(IDLE_ANGLE, sd*WINDUP_ANGLE, ease_in(t))
        if pt >= WINDUP_F: phase, pt = 'strike', 0
    elif phase == 'strike':
        t = min(pt/STRIKE_F, 1.0)
        angle = lerp(sd*WINDUP_ANGLE, sd*STRIKE_ANGLE, ease_out(t))
        if pt >= STRIKE_F: phase, pt = 'follow', 0
    elif phase == 'follow':
        t = min(pt/FOLLOW_F, 1.0)
        angle = lerp(sd*STRIKE_ANGLE, IDLE_ANGLE, ease_out(t))
        if pt >= FOLLOW_F: phase, pt, angle = 'idle', 0, 0.0
    else:
        angle = 0.0
    return phase, angle, pt


def trigger_swing(sd):
    return 'windup', 0.0, 0, sd


# ── draw one racket ──────────────────────────────────────────────────────────
# pivot_screen = screen pos of the grip end (rotation pivot)
# swing_deg    = rotation around pivot (0 = head pointing right)
# flip         = True for AI (head pointing left)
def draw_racket(surface, pivot_sx, pivot_sy, swing_deg, flip=False):
    rs = pygame.Surface((SURF_SIZE, SURF_SIZE), pygame.SRCALPHA)
    px, py = PIVOT_X, PIVOT_Y   # pivot inside the surface

    hcx = px + HANDLE_LEN + NECK_LEN + HEAD_W//2 - 4
    hcy = py

    head_rect  = pygame.Rect(hcx - HEAD_W//2, hcy - HEAD_H//2, HEAD_W, HEAD_H)
    inner_rect = head_rect.inflate(-FRAME_W*2, -FRAME_W*2)

    # shadow
    pygame.draw.ellipse(rs, (0,0,0,50), head_rect.inflate(-2,-2).move(2,3))

    # frame
    pygame.draw.ellipse(rs, FRAME_COL, head_rect, FRAME_W+1)
    for th in range(FRAME_W,0,-1):
        c = tuple(min(255, v+th*5) for v in FRAME_COL)
        pygame.draw.ellipse(rs, c, head_rect.inflate(-FRAME_W*2+th*2,-FRAME_W*2+th*2), 1)
    pygame.draw.ellipse(rs, FRAME_COL, head_rect, FRAME_W)
    pygame.draw.arc(rs, FRAME_SHINE, head_rect.inflate(-2,-2),
                    math.radians(100), math.radians(200), 2)

    # strings
    clip = pygame.Surface((SURF_SIZE, SURF_SIZE), pygame.SRCALPHA)
    pygame.draw.ellipse(clip, (255,255,255,255), inner_rect)
    ss = pygame.Surface((SURF_SIZE, SURF_SIZE), pygame.SRCALPHA)
    for i in range(1, 8):
        sx = inner_rect.left + i * inner_rect.width // 8
        pygame.draw.line(ss, STRING_MAIN, (sx, inner_rect.top+2), (sx, inner_rect.bottom-2), 1)
    for i in range(1, 10):
        sy = inner_rect.top + i * inner_rect.height // 10
        pygame.draw.line(ss, STRING_CROSS, (inner_rect.left+2, sy), (inner_rect.right-2, sy), 1)
    ss.blit(clip, (0,0), special_flags=pygame.BLEND_RGBA_MIN)
    rs.blit(ss, (0,0))

    # throat Y
    tx = hcx - HEAD_W//2
    te = tx - NECK_LEN
    pygame.draw.line(rs, THROAT_COL, (tx, hcy-9), (te+2, hcy-3), 4)
    pygame.draw.line(rs, THROAT_COL, (tx, hcy+9), (te+2, hcy+3), 4)
    pygame.draw.circle(rs, THROAT_COL, (te, hcy), 5)

    # handle (runs from te leftward to px)
    handle_end = px
    pts = [
        (te,          hcy - HANDLE_W//2 - 1),
        (handle_end+4, hcy - HANDLE_W//2),
        (handle_end,   hcy - HANDLE_W//2 + 2),
        (handle_end,   hcy + HANDLE_W//2 - 2),
        (handle_end+4, hcy + HANDLE_W//2),
        (te,           hcy + HANDLE_W//2 + 1),
    ]
    pygame.draw.polygon(rs, HANDLE_COL, pts)
    pygame.draw.line(rs, (200,150,80),
                     (te-2, hcy - HANDLE_W//2 + 1),
                     (handle_end+6, hcy - HANDLE_W//2 + 1), 1)

    # grip
    gx = handle_end + 4
    toggle = True
    while gx < handle_end + 4 + GRIP_LEN:
        col = GRIP_BAND if toggle else GRIP_BASE
        pygame.draw.rect(rs, col, (gx, hcy-HANDLE_W//2, 5, HANDLE_W))
        gx += 8; toggle = not toggle
    pygame.draw.rect(rs, (20,20,20), (handle_end+4, hcy-HANDLE_W//2, GRIP_LEN, HANDLE_W), 1)

    # butt cap
    pygame.draw.ellipse(rs, BUTT_COL,   (handle_end-3, hcy-HANDLE_W//2-2, 8, HANDLE_W+4))
    pygame.draw.ellipse(rs, (120,120,120),(handle_end-2, hcy-HANDLE_W//2-1, 6, HANDLE_W+2), 1)

    # ── rotate around pivot point ──
    if flip:
        rs = pygame.transform.flip(rs, True, False)
        # after horizontal flip, pivot moves to (SURF_SIZE - PIVOT_X, PIVOT_Y)
        rot_pivot_x = SURF_SIZE - PIVOT_X
    else:
        rot_pivot_x = PIVOT_X

    rotated = pygame.transform.rotate(rs, -swing_deg)
    rw, rh = rotated.get_size()

    # find where the pivot ended up in the rotated surface
    # pygame.transform.rotate rotates about the centre of the surface
    cx_old = rot_pivot_x - SURF_SIZE//2
    cy_old = PIVOT_Y      - SURF_SIZE//2
    rad = math.radians(swing_deg)
    cx_new = cx_old*math.cos(rad) - cy_old*math.sin(rad)
    cy_new = cx_old*math.sin(rad) + cy_old*math.cos(rad)
    px_in_rot = rw//2 + cx_new
    py_in_rot = rh//2 + cy_new

    # blit so the pivot lands exactly on (pivot_sx, pivot_sy)
    surface.blit(rotated, (pivot_sx - px_in_rot, pivot_sy - py_in_rot))


def get_head_center(pivot_sx, pivot_sy, swing_deg, flip=False):
    """Screen position of the racket head centre, for hitbox."""
    dx = HEAD_CX - PIVOT_X
    dy = 0
    if flip: dx = -dx
    rad = math.radians(swing_deg)
    hx = pivot_sx + dx*math.cos(rad) - dy*math.sin(rad)
    hy = pivot_sy + dx*math.sin(rad) + dy*math.cos(rad)
    return hx, hy


def get_hitbox(pivot_sx, pivot_sy, swing_deg, flip=False):
    hx, hy = get_head_center(pivot_sx, pivot_sy, swing_deg, flip)
    return pygame.Rect(hx-22, hy-34, 44, 68)


def reset_ball():
    global ball_x, ball_y, ball_speed_x, ball_speed_y
    ball_x, ball_y = WIDTH//2, HEIGHT//2
    ball_speed_x = 6 * random.choice((1,-1))
    ball_speed_y = 6 * random.choice((1,-1))


# ── main loop ────────────────────────────────────────────────────────────────
max_speed = 24

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()

    mx, my = pygame.mouse.get_pos()
    prev_x = player1_x
    prev_y = player1_y
    player1_x = max(6, min(WIDTH//2 - 100, mx))
    player1_y = max(40, min(HEIGHT-40, my))
    vx = player1_x - prev_x
    vy = player1_y - prev_y
    mouse_speed = math.hypot(vx, vy)

    # AI - simulate ball path to where head of AI racket is (pivot - 92)
    ai_head_x = player2_x - 92
    if ball_speed_x > 0:
        sim_x, sim_y = ball_x, ball_y
        sim_vx, sim_vy = ball_speed_x, ball_speed_y
        for _ in range(600):
            sim_x += sim_vx
            sim_y += sim_vy
            if sim_y - ball_radius <= 0:      sim_y = ball_radius;         sim_vy =  abs(sim_vy)
            if sim_y + ball_radius >= HEIGHT:  sim_y = HEIGHT - ball_radius; sim_vy = -abs(sim_vy)
            if sim_x >= ai_head_x:
                break
        target_y = sim_y
    else:
        target_y = HEIGHT // 2
    dy = target_y - player2_y
    if abs(dy) > 2:
        player2_y += min(ai_speed, abs(dy)) * (1 if dy > 0 else -1)
    player2_y = max(40, min(HEIGHT - 40, player2_y))

    # ball
    ball_x += ball_speed_x
    ball_y += ball_speed_y
    if ball_y - ball_radius <= 0:   ball_y = ball_radius;         ball_speed_y =  abs(ball_speed_y)
    if ball_y + ball_radius >= HEIGHT: ball_y = HEIGHT-ball_radius; ball_speed_y = -abs(ball_speed_y)
    ball_speed_x = max(-max_speed, min(max_speed, ball_speed_x))
    ball_speed_y = max(-max_speed, min(max_speed, ball_speed_y))

    # collisions
    ball_rect = pygame.Rect(ball_x-ball_radius, ball_y-ball_radius, ball_radius*2, ball_radius*2)
    p1_box = get_hitbox(player1_x, player1_y, p1_angle, flip=False)
    p2_box = get_hitbox(player2_x, player2_y, p2_angle, flip=True)

    if ball_rect.colliderect(p1_box) and ball_speed_x < 0:
        boost = 1.06 + (mouse_speed/8)*0.08
        ball_speed_x =  abs(ball_speed_x) * boost
        ball_speed_y += vy * 0.3
        sd = 1 if vy >= 0 else -1
        p1_phase, p1_angle, p1_pt, p1_dir = trigger_swing(sd)

    if ball_rect.colliderect(p2_box) and ball_speed_x > 0:
        boost = 1.05 + (abs(ball_speed_y)/10)*0.04
        ball_speed_x = -abs(ball_speed_x) * boost
        p2_phase, p2_angle, p2_pt, p2_dir = trigger_swing(random.choice([1,-1]))

    # advance swings
    p1_phase, p1_angle, p1_pt = update_swing(p1_phase, p1_angle, p1_pt, p1_dir)
    p2_phase, p2_angle, p2_pt = update_swing(p2_phase, p2_angle, p2_pt, p2_dir)

    # scoring
    if ball_x < 0:      score2 += 1; reset_ball()
    elif ball_x > WIDTH: score1 += 1; reset_ball()

    # ── render ───────────────────────────────────────────────────────────────
    screen.fill(TENNIS_COURT)

    for y in range(0, HEIGHT, 40):
        pygame.draw.rect(screen, WHITE, (WIDTH//2-2, y, 4, 20))
    pygame.draw.rect(screen, WHITE, (0,0,WIDTH,HEIGHT), 6)

    zone = pygame.Surface((WIDTH//2, HEIGHT), pygame.SRCALPHA)
    zone.fill((255,255,255,10))
    screen.blit(zone, (0,0))

    # draw rackets pivoting at grip
    draw_racket(screen, player1_x, player1_y, p1_angle, flip=False)
    draw_racket(screen, player2_x, player2_y, p2_angle, flip=True)

    # ball shadow + ball
    pygame.draw.ellipse(screen, SHADOW_COL,
                        (int(ball_x)-ball_radius+5, int(ball_y)+ball_radius-4,
                         ball_radius*2, ball_radius))
    pygame.draw.circle(screen, TENNIS_YELLOW, (int(ball_x), int(ball_y)), ball_radius)
    pygame.draw.arc(screen, (170,200,20),
                    (int(ball_x)-ball_radius+3, int(ball_y)-ball_radius+3,
                     (ball_radius-3)*2, (ball_radius-3)*2),
                    math.radians(20), math.radians(160), 2)
    pygame.draw.arc(screen, (170,200,20),
                    (int(ball_x)-ball_radius+3, int(ball_y)-ball_radius+3,
                     (ball_radius-3)*2, (ball_radius-3)*2),
                    math.radians(200), math.radians(340), 2)

    score_text = font.render(f"{score1}  {score2}", True, WHITE)
    screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 15))

    speed = abs(ball_speed_x)
    bar_w = int((speed/max_speed)*80)
    pygame.draw.rect(screen, (200,200,200), (WIDTH//2-40, HEIGHT-16, 80, 6), 1)
    pygame.draw.rect(screen, TENNIS_YELLOW,  (WIDTH//2-40, HEIGHT-16, bar_w, 6))

    hint = small_font.render("Move mouse anywhere on left half", True, (180,230,180))
    screen.blit(hint, (10, HEIGHT-22))

    pygame.display.flip()
    clock.tick(60)