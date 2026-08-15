"""The meteor-dodging game built on slides 23-27.

The code is identical to what appears on the slides. Art and sound live in
game.pyxres in this folder.

    pyxel run game.py     (arrow keys to move; touching a meteor ends the game)
"""
import pyxel

pyxel.init(160, 120)
pyxel.load("game.pyxres")
pyxel.gen_bgm(7, 0, 3, 0, play=True)
x = 76
enemies = [[pyxel.rndi(0, 152), -i * 16] for i in range(16)]
game_over = False

while True:
    pyxel.blt(0, 0, 0, 0, 0, 160, 120)

    if pyxel.btn(pyxel.KEY_LEFT) and not game_over:
        x -= 2
    if pyxel.btn(pyxel.KEY_RIGHT) and not game_over:
        x += 2

    for enemy in enemies:
        if not game_over:
            enemy[1] += 2
            if enemy[1] > 120:
                enemy[0], enemy[1] = pyxel.rndi(0, 152), -8
            if abs(enemy[0] - x) < 8 and abs(enemy[1] - 104) < 8:
                pyxel.play(3, 0)
                game_over = True
        pyxel.blt(enemy[0], enemy[1], 0, 8, 120, 8, 8, 0)

    pyxel.blt(x, 104, 0, 0, 120, 8, 8, 0)
    pyxel.flip()
