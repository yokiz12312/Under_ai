import torch
import ctypes
from ctypes import wintypes

import mss
import time
import numpy as np
import pygame as pg

import pyautogui
import socket

from collections import deque
import random as rnd


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
episode_reward = 0
episode = 0

gamma = 0.99
batch_size = 32
learning_rate = 0.0001

epsilon = 1.0
epsilon_min = 0.1
epsilon_decay = 0.9995

target_update = 100
learn_step = 0


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

target_layer1 = torch.nn.Linear(57600, 128)
target_relu = torch.nn.ReLU()
target_layer2 = torch.nn.Linear(128, 64)
target_layer3 = torch.nn.Linear(64, 5)

target_layer1.load_state_dict(layer1.state_dict())
target_layer2.load_state_dict(layer2.state_dict())
target_layer3.load_state_dict(layer3.state_dict())

optimizer = torch.optim.Adam(
    list(layer1.parameters()) +
    list(layer2.parameters()) +
    list(layer3.parameters()),
    lr=learning_rate
)

loss_fn = torch.nn.SmoothL1Loss()

replay_buffer = deque(maxlen=10000)


def save_model():
    torch.save(
        {
            "layer1": layer1.state_dict(),
            "layer2": layer2.state_dict(),
            "layer3": layer3.state_dict(),
            "epsilon": epsilon,
            "episode": episode
        },
        "yo_battle_dqn.pth"
    )


try:
    with mss.MSS() as sct:

        last_reward_time = time.time()

        done = False

        while True:
            reward = 0

            for event in pg.event.get():
                if event.type == pg.QUIT:
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

            if rnd.random() < epsilon:
                action = rnd.randrange(5)
            else:
                action = torch.argmax(output).item()

            do_action(action)

            time.sleep(0.0333)

            try:
                while True:
                    message, address = ai_socket.recvfrom(1024)

                    if message == b"HIT":
                        reward -= 2

                    elif message == b"DEATH":
                        done = True

            except BlockingIOError:
                pass

            next_state, _ = get_state(sct)

            current_time = time.time()

            if current_time - last_reward_time >= 1:
                reward += 0.1
                last_reward_time = current_time

            transition = (
                state,
                action,
                reward,
                next_state,
                done
            )

            replay_buffer.append(transition)

            if len(replay_buffer) >= batch_size:

                batch = rnd.sample(
                    replay_buffer,
                    batch_size
                )

                states, actions, rewards, next_states, dones = zip(*batch)

                states = torch.stack(states)
                actions = torch.tensor(
                    actions,
                    dtype=torch.long
                )
                rewards = torch.tensor(
                    rewards,
                    dtype=torch.float32
                )
                next_states = torch.stack(next_states)
                dones = torch.tensor(
                    dones,
                    dtype=torch.float32
                )

                output = layer1(states)
                output = relu(output)
                output = layer2(output)
                output = layer3(output)

                q_selected = output.gather(
                    1,
                    actions.unsqueeze(1)
                ).squeeze(1)

                with torch.no_grad():

                    next_output = target_layer1(next_states)
                    next_output = target_relu(next_output)
                    next_output = target_layer2(next_output)
                    next_output = target_layer3(next_output)

                    max_next_q = next_output.max(1).values

                    target = rewards + (
                        gamma *
                        max_next_q *
                        (1 - dones)
                    )

                loss = loss_fn(
                    q_selected,
                    target
                )

                optimizer.zero_grad()

                loss.backward()

                optimizer.step()

                learn_step += 1

                if learn_step % target_update == 0:
                    target_layer1.load_state_dict(
                        layer1.state_dict()
                    )

                    target_layer2.load_state_dict(
                        layer2.state_dict()
                    )

                    target_layer3.load_state_dict(
                        layer3.state_dict()
                    )

                print("loss =", loss.item())

            total_reward += reward
            episode_reward += reward

            if done:
                episode += 1

                print(
                    "episode =",
                    episode,
                    "episode_reward =",
                    round(episode_reward, 2)
                )

                episode_reward = 0
                total_reward = 0
                done = False
                last_reward_time = time.time()

            epsilon = max(
                epsilon_min,
                epsilon * epsilon_decay
            )

            print("action =", action)
            print("reward =", reward)
            print("done =", done)
            print("epsilon =", epsilon)
            print("buffer =", len(replay_buffer))
            print("total_reward =", round(total_reward, 2))

            pg.display.flip()

except KeyboardInterrupt:
    pass

except SystemExit:
    pass

finally:
    save_model()
    ai_socket.close()
    pg.quit()