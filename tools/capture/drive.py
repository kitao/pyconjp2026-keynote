"""Shared parts for capturing the demo. The game code itself is left alone.

- Pilot: produces the left/right input. Rather than a fixed sweep, it decides
  every few frames whether to move away from a threatening meteor or drift
  back towards the middle, so the play reads as a person at the keys.
- Rec: drops the first frames before recording. Recording from frame one would
  show the evenly spaced opening pattern every time the GIF loops.
"""

import pyxel

THINK_EVERY = 5  # Frames between decisions; deciding every frame jitters
LOOKAHEAD = 45  # How many frames ahead to look; a person watches the top of the screen
SAFE = 22  # Clearance that counts as safe enough to stay put
MOVE_COST = 0.30  # Penalty per pixel travelled; a person will not sprint to the edge
MIN_MOVE = 6  # Ignore moves smaller than this, which removes one-frame twitches
DEADZONE = 3  # Stop on arrival; at 0 it oscillates over a single pixel
PLAYER_Y = 104


class Pilot:
    """Dodging that reads as a person playing.

    Fleeing the nearest meteor every frame looks frantic once the screen fills
    up. A person picks a safe spot, moves there, and then stays until it stops
    being safe, so that is the shape here: choose a target, stop on arrival,
    choose again when the spot turns dangerous.
    """

    def __init__(self):
        self.target = None
        self.next_think = 0

    def input(self, frame, x, enemies):
        moving = self.target is not None and abs(self.target - x) > DEADZONE
        # Do not reconsider while moving. Once a person starts, they finish the
        # move; rethinking every frame shifts the target a few pixels at a time
        # and produces an endless series of tiny corrections.
        if not moving and frame >= self.next_think:
            self.next_think = frame + THINK_EVERY
            if self.target is None or self._clearance(x, enemies) < SAFE:
                t = self._pick(x, enemies)
                # Do not move for a negligible gain
                self.target = t if abs(t - x) >= MIN_MOVE else x
        if self.target is None:
            return 0
        d = self.target - x
        if abs(d) <= DEADZONE:
            return 0
        return 1 if d > 0 else -1

    def _clearance(self, cx, enemies):
        """Horizontal clearance from the meteors still to arrive, if we stand at cx."""
        clear = 999
        for ex, ey in enemies:
            t = (PLAYER_Y - ey) / 2  # Frames until it reaches the player's row
            if 0 <= t <= LOOKAHEAD:
                clear = min(clear, abs(ex - cx))
        return clear

    def _pick(self, x, enemies):
        best, best_score = x, -1e9
        for cx in range(0, 153, 4):
            # Cap the clearance. Without a cap it runs to the edge of the
            # screen for a slightly wider gap even when it is already safe.
            score = min(self._clearance(cx, enemies), 44) - abs(cx - x) * MOVE_COST
            if score > best_score:
                best_score, best = score, cx
        return best


class Rec:
    """Skip the opening frames, then record a fixed number of them."""

    def __init__(self, out, skip, frames, scale):
        self.out = out
        self.skip = skip
        self.frames = frames
        self.scale = scale
        self.n = 0

    def tick(self):
        self.n += 1
        if self.n == self.skip:
            pyxel.reset_screencast()
        return self.n < self.skip + self.frames

    def save(self):
        pyxel.screencast(self.out, scale=self.scale)
