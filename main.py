
import pygame
import random
import json
import os
from datetime import datetime

pygame.init()

# ==================================================
# SETTINGS
# ==================================================

W, H = 700, 800
GRID = 660
TOP = 120
HIDE_DELAY = 800

screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Memory Match")
clock = pygame.time.Clock()

font = pygame.font.SysFont("Arial", 30)
small_font = pygame.font.SysFont("Arial", 21)
big_font = pygame.font.SysFont("Arial", 58)
name_font = pygame.font.SysFont("Arial", 28)

BG = (25, 27, 38)
BACK = (55, 85, 145)
BACK_BORDER = (100, 145, 220)
FACE = (245, 245, 245)
MATCHED = (65, 75, 85)
WHITE = (255, 255, 255)
GRAY = (170, 175, 190)
GREEN = (65, 210, 130)
RED = (240, 80, 80)
GOLD = (255, 195, 65)

# ==================================================
# EMOJIS
# ==================================================

EMOJIS = [
    "🐶", "🐱", "🐭", "🐹", "🐰",
    "🦊", "🐻", "🐼", "🐨", "🐯",
    "🦁", "🐮", "🐷", "🐸", "🐵",
    "🐔", "🐧", "🐦", "🦆", "🦅",
    "🦉", "🦇", "🐺", "🐗", "🐴",
    "🦄", "🐝", "🦋", "🐌", "🐞",
    "🍎", "🍌", "🍇", "🍉", "🍓",
    "🍒", "🍍", "🥝", "🍑", "🥑",
    "🚗", "🚕", "🚀", "✈️", "🚁",
    "🚲", "🏎️", "🚂", "🚢", "🛸"
]

# ==================================================
# DIFFICULTIES
# ==================================================

SIZES = [4, 6, 10]

TIME_LIMITS = {
    4: 60,
    6: 120,
    10: 300
}

# ==================================================
# LEADERBOARD SYSTEM
# ==================================================

LEADERBOARD_FILE = "leaderboard.json"

def load_leaderboard():

    if not os.path.exists(LEADERBOARD_FILE):
        return {"4": [], "6": [], "10": []}

    try:
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for n in SIZES:
            data.setdefault(str(n), [])

        return data

    except (json.JSONDecodeError, OSError):
        return {"4": [], "6": [], "10": []}


leaderboard = load_leaderboard()


def save_leaderboard():

    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(
            leaderboard,
            f,
            ensure_ascii=False,
            indent=4
        )


def add_score(name, size, elapsed, moves):

    key = str(size)

    record = {
        "name": name,
        "time": elapsed,
        "moves": moves,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    leaderboard[key].append(record)

    # زمان کمتر، سپس حرکت کمتر
    leaderboard[key].sort(
        key=lambda x: (x["time"], x["moves"])
    )

    # فقط 10 رکورد برتر
    leaderboard[key] = leaderboard[key][:10]

    save_leaderboard()


# ==================================================
# GAME VARIABLES
# ==================================================

state = "menu"

player_name = ""
name_active = True

N = 4
GAP = 8
CARD = 100
X0 = 20

cards = []

first = None
second = None

moves = 0
start_time = 0
end_time = None

time_limit = 60
game_result = None
score_saved = False

hide_at = 0

# ==================================================
# BUTTONS
# ==================================================

name_box = pygame.Rect(150, 220, 400, 55)

difficulty_buttons = {
    4: pygame.Rect(180, 330, 340, 65),
    6: pygame.Rect(180, 420, 340, 65),
    10: pygame.Rect(180, 510, 340, 65)
}

leaderboard_button = pygame.Rect(180, 620, 340, 60)

# ==================================================
# LAYOUT
# ==================================================

def setup_layout(n):

    global N, GAP, CARD, X0

    N = n

    GAP = 15 if n == 4 else (8 if n == 6 else 4)

    CARD = (GRID - GAP * (n - 1)) // n

    X0 = (W - (n * CARD + GAP * (n - 1))) // 2


def card_rect(i):

    row, col = divmod(i, N)

    return pygame.Rect(
        X0 + col * (CARD + GAP),
        TOP + row * (CARD + GAP),
        CARD,
        CARD
    )


# ==================================================
# NEW GAME
# ==================================================

def new_game(n):

    global cards, first, second
    global moves, start_time, end_time
    global time_limit, game_result
    global hide_at, score_saved

    setup_layout(n)

    pairs = (N * N) // 2

    deck = EMOJIS[:pairs] * 2

    random.shuffle(deck)

    cards = [
        {
            "emoji": emoji,
            "revealed": False,
            "matched": False
        }
        for emoji in deck
    ]

    first = None
    second = None

    moves = 0

    start_time = pygame.time.get_ticks()
    end_time = None

    time_limit = TIME_LIMITS[N]

    game_result = None
    hide_at = 0
    score_saved = False


def start_game(n):

    global state

    if not player_name.strip():
        return

    new_game(n)

    state = "play"


# ==================================================
# CARD LOGIC
# ==================================================

def all_matched():

    return all(c["matched"] for c in cards)


def click_card(i):

    global first, second
    global moves, hide_at
    global end_time, game_result
    global score_saved

    card = cards[i]

    if (
        card["revealed"]
        or card["matched"]
        or second is not None
    ):
        return

    card["revealed"] = True

    if first is None:

        first = i
        return

    second = i
    moves += 1

    if cards[first]["emoji"] == cards[second]["emoji"]:

        cards[first]["matched"] = True
        cards[second]["matched"] = True

        first = None
        second = None

        if all_matched():

            end_time = pygame.time.get_ticks()
            game_result = "win"

            save_score_once()

    else:

        hide_at = pygame.time.get_ticks() + HIDE_DELAY


# ==================================================
# SAVE SCORE
# ==================================================

def save_score_once():

    global score_saved

    if score_saved:
        return

    elapsed = (
        pygame.time.get_ticks() - start_time
    ) // 1000

    add_score(
        player_name.strip(),
        N,
        elapsed,
        moves
    )

    score_saved = True


# ==================================================
# DRAW HELPERS
# ==================================================

def draw_centered(text, f, color, y):

    surface = f.render(str(text), True, color)

    screen.blit(
        surface,
        surface.get_rect(center=(W // 2, y))
    )


def draw_text(text, x, y, color=WHITE, f=None):

    if f is None:
        f = font

    surface = f.render(str(text), True, color)

    screen.blit(surface, (x, y))


def draw_emoji(emoji, rect):

    size = max(14, int(CARD * 0.58))

    emoji_font = pygame.font.SysFont(
        "Segoe UI Emoji",
        size
    )

    surface = emoji_font.render(emoji, True, WHITE)

    screen.blit(
        surface,
        surface.get_rect(center=rect.center)
    )


# ==================================================
# MENU
# ==================================================

def draw_menu():

    screen.fill(BG)

    draw_centered(
        "MEMORY MATCH",
        big_font,
        WHITE,
        100
    )

    draw_centered(
        "Enter your name",
        font,
        GRAY,
        180
    )

    # Name input
    color = GREEN if name_active else BACK_BORDER

    pygame.draw.rect(
        screen,
        (40, 43, 58),
        name_box,
        border_radius=10
    )

    pygame.draw.rect(
        screen,
        color,
        name_box,
        2,
        border_radius=10
    )

    shown_name = player_name if player_name else "Your name..."

    draw_centered(
        shown_name,
        name_font,
        WHITE if player_name else GRAY,
        name_box.centery
    )

    draw_centered(
        "Choose difficulty",
        font,
        GRAY,
        295
    )

    names = {
        4: "EASY  -  4 x 4  -  60s",
        6: "MEDIUM  -  6 x 6  -  120s",
        10: "HARD  -  10 x 10  -  300s"
    }

    mouse = pygame.mouse.get_pos()

    for n, rect in difficulty_buttons.items():

        hover = rect.collidepoint(mouse)

        pygame.draw.rect(
            screen,
            BACK_BORDER if hover else BACK,
            rect,
            border_radius=12
        )

        draw_centered(
            names[n],
            font,
            WHITE,
            rect.centery
        )

    hover = leaderboard_button.collidepoint(mouse)

    pygame.draw.rect(
        screen,
        (135, 95, 35) if hover else (100, 75, 35),
        leaderboard_button,
        border_radius=12
    )

    draw_centered(
        "LEADERBOARD  🏆",
        font,
        WHITE,
        leaderboard_button.centery
    )

    draw_centered(
        "Press L to see leaderboard",
        small_font,
        GRAY,
        720
    )


# ==================================================
# LEADERBOARD SCREEN
# ==================================================

def draw_leaderboard():

    screen.fill(BG)

    draw_centered(
        "LEADERBOARD",
        big_font,
        GOLD,
        65
    )

    draw_centered(
        "TOP 10 PLAYERS",
        small_font,
        GRAY,
        115
    )

    # Three difficulty sections
    section_y = 155

    for n in SIZES:

        draw_centered(
            f"{n} x {n}  -  {['EASY', 'MEDIUM', 'HARD'][SIZES.index(n)]}",
            font,
            GREEN,
            section_y
        )

        section_y += 38

        records = leaderboard[str(n)]

        if not records:

            draw_centered(
                "No records yet!",
                small_font,
                GRAY,
                section_y
            )

            section_y += 35

        else:

            for rank, record in enumerate(records[:5], 1):

                name = str(record.get("name", "Player"))[:12]
                seconds = record.get("time", 0)
                player_moves = record.get("moves", 0)

                line = (
                    f"{rank}. {name:<12} "
                    f"{seconds}s  |  {player_moves} moves"
                )

                draw_centered(
                    line,
                    small_font,
                    GOLD if rank == 1 else WHITE,
                    section_y
                )

                section_y += 29

        section_y += 22

    draw_centered(
        "ESC: Back to menu",
        small_font,
        GRAY,
        765
    )


# ==================================================
# GAME SCREEN
# ==================================================

def draw_game():

    screen.fill(BG)

    now = (
        end_time
        if end_time is not None
        else pygame.time.get_ticks()
    )

    elapsed = (now - start_time) // 1000

    remaining = max(0, time_limit - elapsed)

    # Header
    draw_text(
        f"Player: {player_name[:12]}",
        15,
        12,
        WHITE,
        small_font
    )

    draw_text(
        f"Moves: {moves}",
        15,
        48,
        WHITE,
        small_font
    )

    timer_color = RED if remaining <= 10 else GREEN

    timer_text = font.render(
        f"{remaining}s",
        True,
        timer_color
    )

    screen.blit(
        timer_text,
        (W - timer_text.get_width() - 20, 25)
    )

    # Cards
    for i, card in enumerate(cards):

        rect = card_rect(i)

        radius = max(2, int(CARD * 0.08))

        if card["matched"]:

            pygame.draw.rect(
                screen,
                MATCHED,
                rect,
                border_radius=radius
            )

            draw_emoji(card["emoji"], rect)

        elif card["revealed"]:

            pygame.draw.rect(
                screen,
                FACE,
                rect,
                border_radius=radius
            )

            draw_emoji(card["emoji"], rect)

        else:

            pygame.draw.rect(
                screen,
                BACK,
                rect,
                border_radius=radius
            )

            pygame.draw.rect(
                screen,
                BACK_BORDER,
                rect,
                2,
                border_radius=radius
            )

    # End screen
    if end_time is not None:

        overlay = pygame.Surface(
            (W, H),
            pygame.SRCALPHA
        )

        overlay.fill((0, 0, 0, 205))

        screen.blit(overlay, (0, 0))

        if game_result == "win":

            draw_centered(
                "YOU WON!",
                big_font,
                GREEN,
                H // 2 - 65
            )

            draw_centered(
                "Score saved to leaderboard!",
                small_font,
                GOLD,
                H // 2 - 15
            )

        else:

            draw_centered(
                "TIME'S UP!",
                big_font,
                RED,
                H // 2 - 65
            )

        draw_centered(
            f"Player: {player_name}",
            font,
            WHITE,
            H // 2 + 30
        )

        draw_centered(
            f"Moves: {moves}",
            font,
            WHITE,
            H // 2 + 75
        )

        draw_centered(
            "R: Play again | ESC: Menu",
            small_font,
            WHITE,
            H // 2 + 130
        )


# ==================================================
# MAIN LOOP
# ==================================================

running = True

while running:

    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False

        elif event.type == pygame.KEYDOWN:

            # MENU
            if state == "menu":

                if name_active:

                    if event.key == pygame.K_BACKSPACE:

                        player_name = player_name[:-1]

                    elif event.key == pygame.K_RETURN:

                        name_active = False

                    elif event.unicode.isprintable():

                        if len(player_name) < 16:
                            player_name += event.unicode

                if event.key == pygame.K_l:

                    state = "leaderboard"

                elif event.key == pygame.K_ESCAPE:

                    name_active = False

                elif not name_active:

                    if event.key == pygame.K_4:
                        start_game(4)

                    elif event.key == pygame.K_6:
                        start_game(6)

                    elif event.key == pygame.K_0:
                        start_game(10)

            # GAME
            elif state == "play":

                if event.key == pygame.K_r:

                    new_game(N)

                elif event.key == pygame.K_ESCAPE:

                    state = "menu"
                    name_active = False

            # LEADERBOARD
            elif state == "leaderboard":

                if event.key == pygame.K_ESCAPE:

                    state = "menu"

        # MOUSE
        elif event.type == pygame.MOUSEBUTTONDOWN:

            if event.button == 1:

                if state == "menu":

                    if name_box.collidepoint(event.pos):

                        name_active = True

                    else:

                        name_active = False

                        for n, rect in difficulty_buttons.items():

                            if rect.collidepoint(event.pos):
                                start_game(n)

                        if leaderboard_button.collidepoint(event.pos):

                            state = "leaderboard"

                elif state == "play" and end_time is None:

                    for i in range(len(cards)):

                        if card_rect(i).collidepoint(event.pos):

                            click_card(i)
                            break

    # ==================================================
    # HIDE WRONG CARDS
    # ==================================================

    if (
        state == "play"
        and second is not None
        and pygame.time.get_ticks() >= hide_at
    ):

        cards[first]["revealed"] = False
        cards[second]["revealed"] = False

        first = None
        second = None

    # ==================================================
    # TIMER
    # ==================================================

    if state == "play" and end_time is None:

        elapsed = (
            pygame.time.get_ticks() - start_time
        ) // 1000

        if elapsed >= time_limit:

            end_time = pygame.time.get_ticks()
            game_result = "lose"

            first = None
            second = None

    # ==================================================
    # DRAW
    # ==================================================

    if state == "menu":

        draw_menu()

    elif state == "play":

        draw_game()

    elif state == "leaderboard":

        draw_leaderboard()

    pygame.display.flip()

    clock.tick(60)


pygame.quit()
