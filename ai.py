import torch
import ctypes
from ctypes import wintypes

import mss
import time
import numpy as np
import pygame as pg

import pyautogui
import socket

pg.init()

ai_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ai_socket.bind(("127.0.0.1", 5000))
ai_socket.setblocking(False)

user32 = ctypes.windll.user32

VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28

reward = 0
total_reward = 0


def press_key(key):
    user32.keybd_event(key, 0, 0, 0)
    time.sleep(0.032)
    user32.keybd_event(key, 0, 2, 0)


def do_action(action):
    if action == 0:
        press_key(VK_LEFT)

    elif action == 1:
        press_key(VK_RIGHT)

    elif action == 2:
        press_key(VK_UP)

    elif action == 3:
        press_key(VK_DOWN)

    elif action == 4:
        pass


rect = wintypes.RECT()

user32 = ctypes.windll.user32
window = user32.FindWindowW(None, "YO_BATTLE")

user32.GetClientRect(window, ctypes.byref(rect))

point = wintypes.POINT(0, 0)
user32.ClientToScreen(window, ctypes.byref(point))

monitor = {
    "left": point.x,
    "top": point.y,
    "width": rect.right - rect.left,
    "height": rect.bottom - rect.top
}

screen = pg.display.set_mode(
    (monitor["width"], monitor["height"])
)


def get_state(sct):
    screenshot = sct.grab(monitor)

    image = np.array(screenshot)

    rgb_image = image[:, :, [2, 1, 0]]
    rgb_image = np.transpose(rgb_image, (1, 0, 2))

    surface = pg.surfarray.make_surface(rgb_image)

    small_surface = pg.transform.scale(
        surface,
        (160, 120)
    )

    small_image = pg.surfarray.array3d(small_surface)

    normalized_image = small_image / 255.0

    flatten_image = normalized_image.flatten()

    tensor_image = torch.from_numpy(flatten_image).float()

    return tensor_image, small_surface


layer1 = torch.nn.Linear(57600, 128)
relu = torch.nn.ReLU()
layer2 = torch.nn.Linear(128, 64)
layer3 = torch.nn.Linear(64, 5)


with mss.MSS() as sct:

    last_reward_time = time.time()

    done = False

    while True:
        reward = 0

        current_time = time.time()

        if current_time - last_reward_time >= 1:
            reward += 0.1
            last_reward_time = current_time

        try:
            message, address = ai_socket.recvfrom(1024)

            if message == b"HIT":
                reward -= 2
                print("reward = ", reward)

            elif message == b"DEATH":
                done = True
                print("done = ", done)

        except BlockingIOError:
            pass

        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                raise SystemExit

        state, small_surface = get_state(sct)

        display_surface = pg.transform.scale(
            small_surface,
            (monitor["width"], monitor["height"])
        )

        screen.fill((0, 0, 0))
        screen.blit(display_surface, (0, 0))

        output = layer1(state)
        output = relu(output)
        output = layer2(output)
        output = layer3(output)

        action = torch.argmax(output).item()
        do_action(action)

        next_state, _ = get_state(sct)

        transform = {
            state,
            action,
            reward,
            next_state,
            done
            }

        print(action)
        print(output)
        print(output.shape)

        pg.display.flip()

        total_reward += reward
        print("total_reward = ", total_reward)

        time.sleep(0.0333)