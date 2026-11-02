import math
import random
from array import array

import pygame

pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()

# ---------- تنظیمات ----------
W, H = 600, 650
TOP = 70                     # نوار بالای صفحه
GRID = 560                   # اندازه‌ی ناحیه‌ی کارت‌ها
HIDE_DELAY = 800             # مدت نمایش دو کارت اشتباه (میلی‌ثانیه)

screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Memory Match")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)
small_font = pygame.font.SysFont(None, 24)
big_font = pygame.font.SysFont(None, 64)

BG = (30, 30, 30)
BACK = (60, 90, 160)
BACK_BORDER = (90, 130, 210)
FACE = (245, 245, 245)
MATCHED = (60, 60, 60)
WHITE = (255, 255, 255)
GRAY = (160, 160, 160)

# ۱۲ شکل (برای بزرگ‌ترین حالت، ۵×۵، به ۱۲ جفت نیاز داریم)
SYMBOLS = [
    ("circle",   (230, 70, 70)),
    ("square",   (0, 170, 110)),
    ("triangle", (240, 180, 50)),
    ("diamond",  (150, 80, 200)),
    ("plus",     (30, 140, 230)),
    ("ring",     (240, 120, 40)),
    ("star",     (220, 60, 150)),
    ("hexagon",  (40, 180, 180)),
    ("cross",    (110, 110, 125)),
    ("heart",    (200, 30, 60)),
    ("bolt",     (210, 160, 0)),
    ("pentagon", (100, 170, 50)),
]

# =====================================================
#                      صدا
# =====================================================
# همه‌ی صداها با کد ساخته می‌شن، پس به هیچ فایل صوتی نیاز نیست.
try:
    AUDIO = pygame.mixer.get_init() is not None
except pygame.error:
    AUDIO = False

if AUDIO:
    RATE, _, CHANNELS = pygame.mixer.get_init()
else:
    RATE, CHANNELS = 22050, 1

_tone_cache = {}


def tone(freq, dur, vol=0.4, decay=True):
    """یه نت ساده (موج سینوسی) برمی‌گردونه."""
    key = (freq, dur, vol, decay)
    if key in _tone_cache:
        return _tone_cache[key]
    n = int(RATE * dur)
    attack = max(1, int(RATE * 0.005))
    out = []
    for i in range(n):
        env = min(1.0, i / attack)
        if decay:
            env *= 1 - i / n
        ph = 2 * math.pi * freq * i / RATE
        out.append(vol * env * (math.sin(ph) + 0.25 * math.sin(2 * ph)))
    _tone_cache[key] = out
    return out


def sweep(f0, f1, dur, vol=0.25):
    """صدای لغزنده (از فرکانس f0 به f1) برای صدای اشتباه."""
    n = int(RATE * dur)
    out, ph = [], 0.0
    for i in range(n):
        ph += 2 * math.pi * (f0 + (f1 - f0) * i / n) / RATE
        out.append(vol * (1 - i / n) * (1.0 if math.sin(ph) >= 0 else -1.0))
    return out


def mix(parts, total):
    """چند صدا رو روی هم، با زمان شروع مشخص، ترکیب می‌کنه."""
    buf = [0.0] * int(RATE * total)
    for start, samples in parts:
        o = int(RATE * start)
        for i, s in enumerate(samples):
            if o + i < len(buf):
                buf[o + i] += s
    return buf


def to_sound(samples, volume=1.0):
    if not AUDIO:
        return None
    data = array("h")
    for s in samples:
        v = int(max(-1.0, min(1.0, s)) * 32767)
        for _ in range(CHANNELS):
            data.append(v)
    snd = pygame.mixer.Sound(buffer=data.tobytes())
    snd.set_volume(volume)
    return snd


def build_music():
    c4, d4, e4, g4, a4 = 261.63, 293.66, 329.63, 392.00, 440.00
    c5, d5, e5 = 523.25, 587.33, 659.25
    melody = [
        e4, g4, c5, g4,   a4, c5, e5, c5,   d5, c5, a4, g4,   g4, e4, d4, c4,
        c5, e5, d5, c5,   a4, c5, a4, e4,   d4, g4, a4, d5,   c5, g4, e4, c4,
    ]
    bass = [130.81, 110.0, 98.0, 130.81, 130.81, 110.0, 98.0, 130.81]
    note = 0.3
    parts = []
    for i, f in enumerate(melody):
        parts.append((i * note, tone(f, note, 0.30)))
    for i, f in enumerate(bass):
        parts.append((i * note * 4, tone(f, note * 4, 0.22)))
    return to_sound(mix(parts, len(melody) * note), 0.25)


if AUDIO:
    SND_FLIP = to_sound(tone(700, 0.07, 0.4), 0.6)
    SND_MATCH = to_sound(mix([(0.00, tone(523.25, 0.15)),
                              (0.12, tone(659.25, 0.15)),
                              (0.24, tone(783.99, 0.30))], 0.6), 0.7)
    SND_WRONG = to_sound(sweep(300, 140, 0.35), 0.7)
    SND_WIN = to_sound(mix([(i * 0.15, tone(f, 0.35))
                            for i, f in enumerate([523.25, 659.25, 783.99, 1046.5, 1318.5])], 1.2), 0.8)
    MUSIC = build_music()
    MUSIC.play(loops=-1)
else:
    SND_FLIP = SND_MATCH = SND_WRONG = SND_WIN = MUSIC = None

music_on = True


def play(snd):
    if snd:
        snd.play()


def toggle_music():
    global music_on
    music_on = not music_on
    if MUSIC:
        MUSIC.set_volume(0.25 if music_on else 0.0)


# =====================================================
#                      رسم شکل‌ها
# =====================================================
def draw_symbol(kind, color, rect):
    cx, cy = rect.center
    s = rect.width
    r = int(s * 0.27)
    if kind == "circle":
        pygame.draw.circle(screen, color, (cx, cy), r)
    elif kind == "ring":
        pygame.draw.circle(screen, color, (cx, cy), r, max(4, int(s * 0.08)))
    elif kind == "square":
        pygame.draw.rect(screen, color, (cx - r, cy - r, 2 * r, 2 * r), border_radius=6)
    elif kind == "triangle":
        pygame.draw.polygon(screen, color, [(cx, cy - r), (cx - r, cy + r), (cx + r, cy + r)])
    elif kind == "diamond":
        d = int(r * 1.15)
        pygame.draw.polygon(screen, color, [(cx, cy - d), (cx + r, cy), (cx, cy + d), (cx - r, cy)])
    elif kind == "plus":
        t = r // 2
        pygame.draw.rect(screen, color, (cx - t, cy - r, 2 * t, 2 * r))
        pygame.draw.rect(screen, color, (cx - r, cy - t, 2 * r, 2 * t))
    elif kind == "cross":
        w = max(5, int(s * 0.1))
        pygame.draw.line(screen, color, (cx - r, cy - r), (cx + r, cy + r), w)
        pygame.draw.line(screen, color, (cx + r, cy - r), (cx - r, cy + r), w)
    elif kind == "star":
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rad = r * 1.2 if i % 2 == 0 else r * 1.2 * 0.45
            pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        pygame.draw.polygon(screen, color, pts)
    elif kind == "hexagon":
        pts = [(cx + r * 1.1 * math.cos(math.pi / 3 * i), cy + r * 1.1 * math.sin(math.pi / 3 * i)) for i in range(6)]
        pygame.draw.polygon(screen, color, pts)
    elif kind == "pentagon":
        pts = [(cx + r * 1.15 * math.cos(-math.pi / 2 + 2 * math.pi / 5 * i),
                cy + r * 1.15 * math.sin(-math.pi / 2 + 2 * math.pi / 5 * i)) for i in range(5)]
        pygame.draw.polygon(screen, color, pts)
    elif kind == "heart":
        rr = int(r * 0.55)
        y = cy - rr // 2
        pygame.draw.circle(screen, color, (cx - rr, y), rr)
        pygame.draw.circle(screen, color, (cx + rr, y), rr)
        pygame.draw.polygon(screen, color, [(cx - 2 * rr + 1, y + 2), (cx + 2 * rr - 1, y + 2),
                                            (cx, cy + int(r * 1.15))])
    elif kind == "bolt":
        pts = [(0.2, -1.1), (-0.6, 0.1), (-0.05, 0.1), (-0.2, 1.1), (0.6, -0.15), (0.05, -0.15)]
        pygame.draw.polygon(screen, color, [(cx + px * r, cy + py * r) for px, py in pts])


# =====================================================
#                    چیدمان و وضعیت
# =====================================================
N, GAP, CARD, X0 = 4, 15, 120, 20
cards = []
first = second = None
hide_at = 0
moves = 0
start_time = 0
end_time = None
state = "menu"               # "menu" یا "play"

SIZES = [2, 4, 5]
BUTTONS = [pygame.Rect((W - 300) // 2, 230 + i * 95, 300, 70) for i in range(len(SIZES))]


def setup_layout(n):
    global N, GAP, CARD, X0
    N = n
    GAP = 15 if n <= 4 else 10
    CARD = (GRID - GAP * (n - 1)) // n
    X0 = (W - (n * CARD + GAP * (n - 1))) // 2


def card_rect(i):
    r, c = divmod(i, N)
    return pygame.Rect(X0 + c * (CARD + GAP), TOP + r * (CARD + GAP), CARD, CARD)


def new_game(n=None):
    global cards, first, second, hide_at, moves, start_time, end_time
    if n:
        setup_layout(n)
    pairs = (N * N) // 2
    deck = SYMBOLS[:pairs] * 2
    random.shuffle(deck)
    cards = [{"kind": k, "color": c, "revealed": False, "matched": False} for k, c in deck]
    if (N * N) % 2 == 1:                         # تعداد خانه‌ها فرده (۵×۵): خونه‌ی وسط خالی می‌مونه
        cards.insert((N * N) // 2, None)
    first = second = None
    hide_at = 0
    moves = 0
    start_time = pygame.time.get_ticks()
    end_time = None


def all_matched():
    return all(c is None or c["matched"] for c in cards)


def click_card(i):
    global first, second, hide_at, moves, end_time
    card = cards[i]
    if card is None or card["revealed"] or card["matched"] or second is not None:
        return

    card["revealed"] = True
    play(SND_FLIP)
    if first is None:
        first = i
        return

    second = i
    moves += 1
    if cards[first]["kind"] == cards[second]["kind"]:
        cards[first]["matched"] = cards[second]["matched"] = True
        first = second = None
        if all_matched():
            end_time = pygame.time.get_ticks()
            play(SND_WIN)
        else:
            play(SND_MATCH)
    else:
        play(SND_WRONG)
        hide_at = pygame.time.get_ticks() + HIDE_DELAY


# =====================================================
#                        رسم صفحه‌ها
# =====================================================
def draw_centered(text, f, color, y):
    surf = f.render(text, True, color)
    screen.blit(surf, surf.get_rect(center=(W // 2, y)))


def draw_menu():
    screen.fill(BG)
    draw_centered("Memory Match", big_font, WHITE, 100)
    draw_centered("Choose the board size", font, GRAY, 170)
    mouse = pygame.mouse.get_pos()
    for n, rect in zip(SIZES, BUTTONS):
        hover = rect.collidepoint(mouse)
        pygame.draw.rect(screen, BACK_BORDER if hover else BACK, rect, border_radius=14)
        pygame.draw.rect(screen, WHITE, rect, 3, border_radius=14)
        draw_centered(f"{n} x {n}", font, WHITE, rect.centery)
    draw_centered("(or press 2, 4 or 5)", small_font, GRAY, 540)
    draw_centered("5 x 5 has 25 cells, so the center cell stays empty", small_font, GRAY, 570)


def draw_game():
    screen.fill(BG)

    now = end_time if end_time else pygame.time.get_ticks()
    secs = (now - start_time) // 1000
    screen.blit(font.render(f"Moves: {moves}", True, WHITE), (20, 25))
    t = font.render(f"Time: {secs}s", True, WHITE)
    screen.blit(t, (W - 20 - t.get_width(), 25))
    draw_centered("R restart | ESC menu | M music", small_font, GRAY, 38)

    radius = int(CARD * 0.1)
    for i, card in enumerate(cards):
        if card is None:
            continue
        rect = card_rect(i)
        if card["matched"]:
            pygame.draw.rect(screen, MATCHED, rect, border_radius=radius)
            draw_symbol(card["kind"], tuple(v // 2 for v in card["color"]), rect)
        elif card["revealed"]:
            pygame.draw.rect(screen, FACE, rect, border_radius=radius)
            draw_symbol(card["kind"], card["color"], rect)
        else:
            pygame.draw.rect(screen, BACK, rect, border_radius=radius)
            pygame.draw.rect(screen, BACK_BORDER, rect, 4, border_radius=radius)

    if end_time:
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))
        draw_centered("You won!", big_font, WHITE, H // 2 - 50)
        draw_centered(f"{moves} moves in {secs}s", font, WHITE, H // 2 + 10)
        draw_centered("R: play again | ESC: menu", font, WHITE, H // 2 + 55)


# =====================================================
#                       حلقه‌ی اصلی
# =====================================================
def start(n):
    global state
    new_game(n)
    state = "play"


running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_m:
                toggle_music()
            elif state == "menu":
                for n, key in [(2, pygame.K_2), (4, pygame.K_4), (5, pygame.K_5)]:
                    if event.key == key:
                        start(n)
            elif state == "play":
                if event.key == pygame.K_r:
                    new_game()
                elif event.key == pygame.K_ESCAPE:
                    state = "menu"

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if state == "menu":
                for n, rect in zip(SIZES, BUTTONS):
                    if rect.collidepoint(event.pos):
                        start(n)
            elif state == "play" and not end_time:
                for i in range(len(cards)):
                    if card_rect(i).collidepoint(event.pos):
                        click_card(i)
                        break

    # برگردوندن دو کارت اشتباه بعد از تأخیر
    if state == "play" and second is not None and pygame.time.get_ticks() >= hide_at:
        cards[first]["revealed"] = False
        cards[second]["revealed"] = False
        first = second = None

    if state == "menu":
        draw_menu()
    else:
        draw_game()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()