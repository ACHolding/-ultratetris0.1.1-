import os
import sys
import random
from array import array

# macOS/CoreAudio settings must be configured before importing Pygame.
if sys.platform == "darwin":
    os.environ.setdefault("SDL_AUDIODRIVER", "coreaudio")
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from pygame.locals import *


# ============================================================
# Configuration
# ============================================================

WIDTH = 800
HEIGHT = 600
FPS = 60

GRID_WIDTH = 10
GRID_HEIGHT = 20
CELL_SIZE = 28

BOARD_WIDTH = GRID_WIDTH * CELL_SIZE
BOARD_HEIGHT = GRID_HEIGHT * CELL_SIZE
BOARD_X = (WIDTH - BOARD_WIDTH) // 2
BOARD_Y = (HEIGHT - BOARD_HEIGHT) // 2

BACKGROUND = (7, 9, 18)
BOARD_BACKGROUND = (13, 17, 29)
GRID_COLOR = (28, 34, 52)
BORDER_COLOR = (100, 150, 235)
TEXT_COLOR = (235, 240, 255)
MUTED_TEXT = (140, 155, 185)
SELECTED_COLOR = (255, 225, 55)
GAME_OVER_COLOR = (255, 80, 80)

AUDIO_RATE = 48000


# ============================================================
# Pygame initialization
# ============================================================

pygame.mixer.pre_init(
    frequency=AUDIO_RATE,
    size=-16,
    channels=2,
    buffer=512
)

pygame.init()

if pygame.mixer.get_init() is None:
    try:
        pygame.mixer.init(
            frequency=AUDIO_RATE,
            size=-16,
            channels=2,
            buffer=512
        )
    except pygame.error as error:
        print(f"Audio initialization failed: {error}")

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ac's ultra tetris 0.1")

clock = pygame.time.Clock()

title_font = pygame.font.Font(None, 64)
large_font = pygame.font.Font(None, 42)
font = pygame.font.Font(None, 32)
small_font = pygame.font.Font(None, 23)


# ============================================================
# In-memory Korobeiniki audio
# ============================================================

def midi_frequency(note):
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def clamp_sample(value):
    return max(-32768, min(32767, int(value)))


class RetroAudio:
    def __init__(self):
        self.available = pygame.mixer.get_init() is not None
        self.loaded = False
        self.status = "NOT STARTED"

        self.music = None
        self.effects = {}
        self.music_channel = None

        if self.available:
            pygame.mixer.set_num_channels(12)
            pygame.mixer.set_reserved(1)
            self.music_channel = pygame.mixer.Channel(0)

            print(
                "Audio device:",
                pygame.mixer.get_init()
            )
        else:
            self.status = "NO AUDIO DEVICE"

    @staticmethod
    def append_frame(output, value, channels):
        sample = clamp_sample(value)

        for _ in range(channels):
            output.append(sample)

    def make_tone(
        self,
        start_frequency,
        end_frequency,
        duration,
        volume=0.2,
        duty=0.5
    ):
        mixer_info = pygame.mixer.get_init()

        if mixer_info is None:
            return None

        sample_rate, _, channels = mixer_info
        sample_count = max(1, int(sample_rate * duration))

        output = array("h")
        phase = 0.0

        for index in range(sample_count):
            progress = index / sample_count

            frequency = (
                start_frequency
                + (end_frequency - start_frequency)
                * progress
            )

            phase = (
                phase + frequency / sample_rate
            ) % 1.0

            pulse = 1.0 if phase < duty else -1.0

            attack = min(
                1.0,
                index / max(1, int(sample_rate * 0.004))
            )

            release = (1.0 - progress) ** 1.8
            envelope = attack * release

            value = (
                32767
                * volume
                * pulse
                * envelope
            )

            self.append_frame(
                output,
                value,
                channels
            )

        return pygame.mixer.Sound(
            buffer=output.tobytes()
        )

    def make_korobeiniki(self):
        mixer_info = pygame.mixer.get_init()

        if mixer_info is None:
            return None

        sample_rate, _, channels = mixer_info
        unit_duration = 0.20

        section_a = [
            (76, 2), (71, 1), (72, 1), (74, 2),
            (72, 1), (71, 1), (69, 2), (69, 1),
            (72, 1), (76, 2), (74, 1), (72, 1),
            (71, 3), (72, 1), (74, 2), (76, 2),
            (72, 2), (69, 2), (69, 4)
        ]

        section_b = [
            (74, 3), (77, 1), (81, 2), (79, 1),
            (77, 1), (76, 3), (72, 1), (76, 2),
            (74, 1), (72, 1), (71, 2), (71, 1),
            (72, 1), (74, 2), (76, 2), (72, 2),
            (69, 2), (69, 4)
        ]

        melody = section_a + section_b

        bass_notes = [
            45, 52, 48, 52,
            45, 52, 48, 52,
            41, 48, 43, 50
        ]

        output = array("h")

        melody_phase = 0.0
        harmony_phase = 0.0
        bass_phase = 0.0
        beat_index = 0

        for note, units in melody:
            frequency = midi_frequency(note)
            harmony_frequency = midi_frequency(note - 12)

            bass_note = bass_notes[
                beat_index % len(bass_notes)
            ]
            bass_frequency = midi_frequency(bass_note)

            duration = units * unit_duration
            sample_count = max(
                1,
                int(sample_rate * duration)
            )

            for index in range(sample_count):
                progress = index / sample_count

                melody_phase = (
                    melody_phase + frequency / sample_rate
                ) % 1.0

                harmony_phase = (
                    harmony_phase
                    + harmony_frequency / sample_rate
                ) % 1.0

                bass_phase = (
                    bass_phase
                    + bass_frequency / sample_rate
                ) % 1.0

                pulse_one = (
                    1.0
                    if melody_phase < 0.25
                    else -1.0
                )

                pulse_two = (
                    1.0
                    if harmony_phase < 0.50
                    else -1.0
                )

                triangle = (
                    4.0 * abs(bass_phase - 0.5) - 1.0
                )

                attack = min(
                    1.0,
                    index
                    / max(1, int(sample_rate * 0.006))
                )

                if progress < 0.84:
                    release = 1.0
                else:
                    release = max(
                        0.0,
                        (1.0 - progress) / 0.16
                    )

                mixed = (
                    pulse_one * 0.55
                    + pulse_two * 0.17
                    + triangle * 0.28
                )

                value = (
                    32767
                    * 0.20
                    * mixed
                    * attack
                    * release
                )

                self.append_frame(
                    output,
                    value,
                    channels
                )

            beat_index += units

        return pygame.mixer.Sound(
            buffer=output.tobytes()
        )

    def load(self):
        if self.loaded or not self.available:
            return

        self.status = "BUILDING AUDIO"

        try:
            self.music = self.make_korobeiniki()

            self.effects = {
                "move": self.make_tone(
                    250, 210, 0.035, 0.08, 0.25
                ),
                "rotate": self.make_tone(
                    350, 620, 0.075, 0.13, 0.25
                ),
                "hard_drop": self.make_tone(
                    300, 65, 0.13, 0.18, 0.50
                ),
                "lock": self.make_tone(
                    125, 80, 0.065, 0.13, 0.50
                ),
                "line_clear": self.make_tone(
                    520, 1250, 0.24, 0.18, 0.25
                ),
                "game_over": self.make_tone(
                    390, 55, 0.70, 0.20, 0.25
                )
            }

            self.effects = {
                name: sound
                for name, sound in self.effects.items()
                if sound is not None
            }

            if self.music is not None:
                self.music.set_volume(0.72)

            self.loaded = True
            self.status = "KOROBEINIKI READY"

            print(
                "Korobeiniki generated successfully in RAM."
            )

        except Exception as error:
            self.status = "AUDIO ERROR"
            print(f"Audio generation failed: {error}")

    def play(self, name):
        sound = self.effects.get(name)

        if sound is not None:
            sound.play()

    def play_music(self):
        if (
            self.music is None
            or self.music_channel is None
        ):
            return

        self.music_channel.stop()
        self.music_channel.unpause()
        self.music_channel.play(
            self.music,
            loops=-1
        )

    def stop_music(self):
        if self.music_channel is not None:
            self.music_channel.stop()

    def pause_music(self):
        if self.music_channel is not None:
            self.music_channel.pause()

    def resume_music(self):
        if self.music_channel is not None:
            self.music_channel.unpause()


audio = RetroAudio()


# ============================================================
# Tetris objects
# ============================================================

class TetrisBoard:
    def __init__(self):
        self.grid = [
            [0 for _ in range(GRID_WIDTH)]
            for _ in range(GRID_HEIGHT)
        ]

        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False


class Piece:
    def __init__(self, shape, color):
        self.shape = [row[:] for row in shape]
        self.color = color

        self.x = (
            GRID_WIDTH // 2
            - len(self.shape[0]) // 2
        )
        self.y = -2


SHAPES = [
    [[1, 1, 1, 1]],

    [[1, 0, 0],
     [1, 1, 1]],

    [[0, 0, 1],
     [1, 1, 1]],

    [[1, 1],
     [1, 1]],

    [[0, 1, 1],
     [1, 1, 0]],

    [[0, 1, 0],
     [1, 1, 1]],

    [[1, 1, 0],
     [0, 1, 1]]
]

COLORS = [
    (0, 225, 255),
    (45, 90, 255),
    (255, 145, 30),
    (255, 225, 30),
    (60, 220, 80),
    (175, 70, 240),
    (245, 55, 65)
]


def create_piece():
    index = random.randrange(len(SHAPES))
    return Piece(SHAPES[index], COLORS[index])


def restart_game():
    return TetrisBoard(), create_piece()


def check_collision(
    board,
    piece,
    offset_x=0,
    offset_y=0,
    shape=None
):
    test_shape = shape or piece.shape

    for row, shape_row in enumerate(test_shape):
        for col, occupied in enumerate(shape_row):
            if not occupied:
                continue

            x = piece.x + col + offset_x
            y = piece.y + row + offset_y

            if x < 0 or x >= GRID_WIDTH:
                return True

            if y >= GRID_HEIGHT:
                return True

            if y >= 0 and board.grid[y][x] != 0:
                return True

    return False


def lock_piece(board, piece):
    for row, shape_row in enumerate(piece.shape):
        for col, occupied in enumerate(shape_row):
            if not occupied:
                continue

            x = piece.x + col
            y = piece.y + row

            if y < 0:
                board.game_over = True
            elif 0 <= x < GRID_WIDTH:
                board.grid[y][x] = piece.color


def clear_lines(board):
    remaining = [
        row for row in board.grid
        if not all(cell != 0 for cell in row)
    ]

    cleared = GRID_HEIGHT - len(remaining)

    for _ in range(cleared):
        remaining.insert(
            0,
            [0 for _ in range(GRID_WIDTH)]
        )

    board.grid = remaining

    if cleared:
        points = {
            1: 100,
            2: 300,
            3: 500,
            4: 800
        }

        board.score += points[cleared] * board.level
        board.lines += cleared
        board.level = 1 + board.lines // 10

        audio.play("line_clear")

    return cleared


def rotate_shape(shape, clockwise=True):
    if clockwise:
        return [
            list(row)
            for row in zip(*shape[::-1])
        ]

    return [
        list(row)
        for row in zip(*shape)
    ][::-1]


def try_rotate(board, piece, clockwise=True):
    rotated = rotate_shape(
        piece.shape,
        clockwise
    )

    for kick_x in (0, -1, 1, -2, 2):
        if not check_collision(
            board,
            piece,
            offset_x=kick_x,
            shape=rotated
        ):
            piece.x += kick_x
            piece.shape = rotated
            audio.play("rotate")
            return True

    return False


def hard_drop(board, piece):
    distance = 0

    while not check_collision(
        board,
        piece,
        offset_y=1
    ):
        piece.y += 1
        distance += 1

    board.score += distance * 2
    audio.play("hard_drop")


def finish_piece(board, piece):
    lock_piece(board, piece)
    audio.play("lock")
    clear_lines(board)

    new_piece = create_piece()

    if board.game_over or check_collision(
        board,
        new_piece
    ):
        board.game_over = True
        audio.stop_music()
        audio.play("game_over")

    return new_piece


# ============================================================
# Rendering
# ============================================================

def draw_block(surface, color, x, y):
    rectangle = pygame.Rect(
        x,
        y,
        CELL_SIZE,
        CELL_SIZE
    )

    pygame.draw.rect(
        surface,
        color,
        rectangle.inflate(-2, -2),
        border_radius=4
    )

    highlight = tuple(
        min(255, value + 55)
        for value in color
    )

    shadow = tuple(
        max(0, value - 65)
        for value in color
    )

    pygame.draw.line(
        surface,
        highlight,
        (x + 4, y + 4),
        (x + CELL_SIZE - 5, y + 4),
        2
    )

    pygame.draw.line(
        surface,
        shadow,
        (x + 4, y + CELL_SIZE - 4),
        (x + CELL_SIZE - 4, y + CELL_SIZE - 4),
        2
    )


def get_ghost_y(board, piece):
    ghost_y = piece.y

    while not check_collision(
        board,
        piece,
        offset_y=(ghost_y - piece.y) + 1
    ):
        ghost_y += 1

    return ghost_y


def draw_overlay(heading, subheading):
    overlay = pygame.Surface(
        (WIDTH, HEIGHT),
        pygame.SRCALPHA
    )
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    heading_image = large_font.render(
        heading,
        True,
        GAME_OVER_COLOR
    )

    subheading_image = small_font.render(
        subheading,
        True,
        TEXT_COLOR
    )

    screen.blit(
        heading_image,
        heading_image.get_rect(
            center=(WIDTH // 2, HEIGHT // 2 - 28)
        )
    )

    screen.blit(
        subheading_image,
        subheading_image.get_rect(
            center=(WIDTH // 2, HEIGHT // 2 + 24)
        )
    )


def render_menu(selection):
    screen.fill(BACKGROUND)

    for y in range(0, HEIGHT, 32):
        pygame.draw.line(
            screen,
            (10, 22, 44),
            (0, y),
            (WIDTH, y)
        )

    title = title_font.render(
        "AC'S ULTRA TETRIS",
        True,
        (80, 205, 255)
    )

    subtitle = small_font.render(
        "VERSION 0.1 • KOROBEINIKI EDITION",
        True,
        SELECTED_COLOR
    )

    screen.blit(
        title,
        title.get_rect(
            center=(WIDTH // 2, 145)
        )
    )

    screen.blit(
        subtitle,
        subtitle.get_rect(
            center=(WIDTH // 2, 195)
        )
    )

    options = [
        "PLAY",
        "EXIT GAME"
    ]

    for index, option in enumerate(options):
        selected = index == selection

        color = (
            SELECTED_COLOR
            if selected
            else TEXT_COLOR
        )

        prefix = "▶  " if selected else "   "

        image = large_font.render(
            prefix + option,
            True,
            color
        )

        screen.blit(
            image,
            image.get_rect(
                center=(
                    WIDTH // 2,
                    305 + index * 70
                )
            )
        )

    help_image = small_font.render(
        "UP/DOWN: SELECT     ENTER: CONFIRM",
        True,
        MUTED_TEXT
    )

    silent_image = small_font.render(
        "MAIN MENU SILENT • MUSIC STARTS AFTER PLAY",
        True,
        (95, 125, 170)
    )

    screen.blit(
        help_image,
        help_image.get_rect(
            center=(WIDTH // 2, 500)
        )
    )

    screen.blit(
        silent_image,
        silent_image.get_rect(
            center=(WIDTH // 2, 540)
        )
    )


def render_loading():
    screen.fill(BACKGROUND)

    heading = large_font.render(
        "BUILDING KOROBEINIKI",
        True,
        (80, 205, 255)
    )

    detail = small_font.render(
        "Generating audio directly in RAM...",
        True,
        TEXT_COLOR
    )

    screen.blit(
        heading,
        heading.get_rect(
            center=(WIDTH // 2, HEIGHT // 2 - 25)
        )
    )

    screen.blit(
        detail,
        detail.get_rect(
            center=(WIDTH // 2, HEIGHT // 2 + 25)
        )
    )

    pygame.display.flip()


def render_game(board, piece, paused):
    screen.fill(BACKGROUND)

    board_rectangle = pygame.Rect(
        BOARD_X,
        BOARD_Y,
        BOARD_WIDTH,
        BOARD_HEIGHT
    )

    pygame.draw.rect(
        screen,
        BOARD_BACKGROUND,
        board_rectangle
    )

    for row in range(GRID_HEIGHT):
        for col in range(GRID_WIDTH):
            x = BOARD_X + col * CELL_SIZE
            y = BOARD_Y + row * CELL_SIZE

            pygame.draw.rect(
                screen,
                GRID_COLOR,
                (x, y, CELL_SIZE, CELL_SIZE),
                1
            )

            cell = board.grid[row][col]

            if cell:
                draw_block(screen, cell, x, y)

    if not board.game_over:
        ghost_y = get_ghost_y(board, piece)

        for row, shape_row in enumerate(piece.shape):
            for col, occupied in enumerate(shape_row):
                if not occupied:
                    continue

                y = ghost_y + row

                if y >= 0:
                    ghost_rectangle = pygame.Rect(
                        BOARD_X
                        + (piece.x + col) * CELL_SIZE
                        + 5,
                        BOARD_Y
                        + y * CELL_SIZE
                        + 5,
                        CELL_SIZE - 10,
                        CELL_SIZE - 10
                    )

                    pygame.draw.rect(
                        screen,
                        (85, 90, 110),
                        ghost_rectangle,
                        2,
                        border_radius=3
                    )

        for row, shape_row in enumerate(piece.shape):
            for col, occupied in enumerate(shape_row):
                if not occupied:
                    continue

                y = piece.y + row

                if y >= 0:
                    draw_block(
                        screen,
                        piece.color,
                        BOARD_X
                        + (piece.x + col) * CELL_SIZE,
                        BOARD_Y
                        + y * CELL_SIZE
                    )

    pygame.draw.rect(
        screen,
        BORDER_COLOR,
        board_rectangle,
        3
    )

    heading = font.render(
        "ULTRA TETRIS",
        True,
        TEXT_COLOR
    )
    screen.blit(heading, (20, 28))

    left_panel = [
        f"SCORE {board.score}",
        f"LINES {board.lines}",
        f"LEVEL {board.level}",
        "",
        "AUDIO",
        audio.status
    ]

    for index, line in enumerate(left_panel):
        color = (
            SELECTED_COLOR
            if line == "AUDIO"
            else TEXT_COLOR
        )

        image = small_font.render(
            line,
            True,
            color
        )

        screen.blit(
            image,
            (20, 90 + index * 30)
        )

    right_x = BOARD_X + BOARD_WIDTH + 28

    controls = [
        "← → Move",
        "↓ Soft drop",
        "Z/X Rotate",
        "Space Drop",
        "P Pause",
        "Esc Menu"
    ]

    for index, line in enumerate(controls):
        image = small_font.render(
            line,
            True,
            TEXT_COLOR
        )

        screen.blit(
            image,
            (right_x, BOARD_Y + 25 + index * 38)
        )

    if paused:
        draw_overlay(
            "PAUSED",
            "Press P to continue"
        )

    if board.game_over:
        draw_overlay(
            "GAME OVER",
            "R: Restart     Esc: Main menu"
        )


# ============================================================
# Main loop
# ============================================================

def main():
    running = True
    state = "menu"
    menu_selection = 0

    board, active_piece = restart_game()

    paused = False
    fall_timer = 0

    while running:
        delta_time = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

            elif event.type == KEYDOWN:
                if state == "menu":
                    if event.key in (K_UP, K_w):
                        menu_selection = (
                            menu_selection - 1
                        ) % 2

                    elif event.key in (K_DOWN, K_s):
                        menu_selection = (
                            menu_selection + 1
                        ) % 2

                    elif event.key in (K_RETURN, K_SPACE):
                        if menu_selection == 0:
                            render_loading()
                            audio.load()

                            board, active_piece = restart_game()
                            paused = False
                            fall_timer = 0
                            state = "game"

                            audio.play_music()
                        else:
                            running = False

                    elif event.key == K_ESCAPE:
                        running = False

                elif state == "game":
                    if event.key == K_ESCAPE:
                        audio.stop_music()
                        paused = False
                        state = "menu"

                    elif event.key == K_r:
                        board, active_piece = restart_game()
                        paused = False
                        fall_timer = 0
                        audio.play_music()

                    elif (
                        event.key == K_p
                        and not board.game_over
                    ):
                        paused = not paused

                        if paused:
                            audio.pause_music()
                        else:
                            audio.resume_music()

                    elif not paused and not board.game_over:
                        if event.key == K_LEFT:
                            if not check_collision(
                                board,
                                active_piece,
                                offset_x=-1
                            ):
                                active_piece.x -= 1
                                audio.play("move")

                        elif event.key == K_RIGHT:
                            if not check_collision(
                                board,
                                active_piece,
                                offset_x=1
                            ):
                                active_piece.x += 1
                                audio.play("move")

                        elif event.key == K_DOWN:
                            if not check_collision(
                                board,
                                active_piece,
                                offset_y=1
                            ):
                                active_piece.y += 1
                                board.score += 1

                        elif event.key in (K_UP, K_x):
                            try_rotate(
                                board,
                                active_piece,
                                clockwise=True
                            )

                        elif event.key == K_z:
                            try_rotate(
                                board,
                                active_piece,
                                clockwise=False
                            )

                        elif event.key == K_SPACE:
                            hard_drop(
                                board,
                                active_piece
                            )

                            active_piece = finish_piece(
                                board,
                                active_piece
                            )

                            fall_timer = 0

        if (
            state == "game"
            and not paused
            and not board.game_over
        ):
            fall_timer += delta_time

            fall_delay = max(
                75,
                700 - (board.level - 1) * 55
            )

            if fall_timer >= fall_delay:
                fall_timer = 0

                if check_collision(
                    board,
                    active_piece,
                    offset_y=1
                ):
                    active_piece = finish_piece(
                        board,
                        active_piece
                    )
                else:
                    active_piece.y += 1

        if state == "menu":
            render_menu(menu_selection)
        else:
            render_game(
                board,
                active_piece,
                paused
            )

        pygame.display.flip()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAC's Ultra Tetris stopped.")
    finally:
        audio.stop_music()
        pygame.quit()
