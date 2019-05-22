#!/usr/bin/env python3
import requests
import time
import signal
import sys

from random import randint
import random
import copy
from random import choice
from multiprocessing import Pool, TimeoutError


class Game:
    x = [[0 for c in range(4)] for r in range(4)]
    c_score = 0
    copy_board = []

    def __init__(self, board, c_score):
        if board is None:
            self.x = self.new_board()
            self.c_score = c_score
        else:
            self.x = board
            self.c_score = c_score

    def count_zeroes(self):
        return sum([sum([1 for c in r if c == 0]) for r in self.x])

    def add_number(self):
        list_of_num = [2, 2, 2, 2, 4]
        num = random.choice(list_of_num)
        if self.count_zeroes() > 0:
            pos = randint(0, self.count_zeroes() - 1)
            for i in range(0, 4):
                for j in range(0, 4):
                    if self.x[i][j] == 0:
                        if pos == 0: self.x[i][j] = num
                        pos -= 1

    def gravity(self):
        changed = False
        for i in range(0, 4):
            for j in range(0, 4):
                k = i
                while k < 4 and self.x[k][j] == 0: k += 1
                if k != i and k < 4:
                    self.x[i][j], self.x[k][j] = self.x[k][j], 0
                    changed = True
        return changed

    def gravity_copy(self):
        changed = False
        for i in range(0, 4):
            for j in range(0, 4):
                k = i
                while k < 4 and self.copy_board[k][j] == 0: k += 1
                if k != i and k < 4:
                    self.copy_board[i][j], self.copy_board[k][j] = self.copy_board[k][j], 0
                    changed = True
        return changed

    def sum_up_copy(self):
        changed = False
        for i in range(0, 3):
            for j in range(0, 4):
                if self.copy_board[i][j] != 0 and self.copy_board[i][j] == self.copy_board[i + 1][j]:
                    self.copy_board[i][j] = 2 * self.copy_board[i][j]
                    self.copy_board[i + 1][j] = 0
                    changed = True
        return changed

    def sum_up(self):
        changed = False
        for i in range(0, 3):
            for j in range(0, 4):
                if self.x[i][j] != 0 and self.x[i][j] == self.x[i + 1][j]:
                    self.x[i][j] = 2 * self.x[i][j]
                    self.c_score = self.c_score + self.x[i][j]
                    self.x[i + 1][j] = 0
                    changed = True
        return changed

    def process_move(self, c):
        moves = "wasd"  # up, left, down, right
        for i in range(len(moves)):
            if moves[i] == c:
                self.rotate(i)
                changed = any([self.gravity(), self.sum_up(), self.gravity()])
                self.rotate(4 - i)
                self.copy_board = [row[:] for row in self.x]
                return changed
        return False

    def rotate(self, n):  # rotate 90 degrees n times
        for i in range(0, n):
            y = [row[:] for row in self.x]  # clone x
            for i in range(0, 4):
                for j in range(0, 4):
                    self.x[i][3 - j] = y[j][i]

    def rotate_copy(self, n):  # rotate 90 degrees n times
        for i in range(0, n):
            y = [row[:] for row in self.copy_board]  # clone x
            for i in range(0, 4):
                for j in range(0, 4):
                    self.copy_board[i][3 - j] = y[j][i]

    def process_move_copy(self, c):
        moves = "wasd"  # up, left, down, right
        for i in range(len(moves)):
            if moves[i] == c:
                self.rotate_copy(i)
                changed = any([self.gravity_copy(), self.sum_up_copy(), self.gravity_copy()])
                self.rotate_copy(4 - i)
                #self.copy_board = [row[:] for row in self.x]
                return changed
        return False

    def next_step_check(self):
        changed = any([self.process_move_copy("w"), self.process_move_copy("a"), self.process_move_copy("s"),
                       self.process_move_copy("d")])
        return changed

    def new_board(self):
        self.x = [[0 for c in range(4)] for r in range(4)]
        self.copy_board = self.x
        self.add_number()
        return self.x


#SERVER_URL = 'https://thegame-2048.herokuapp.com'
SERVER_URL = 'http://127.0.0.1:5000'
s = requests.Session()

def step(direction, u_id):
    game_state = s.post(SERVER_URL + '/api/play_the_game', json={
        'uId': u_id,
        'direction': direction
    }).json()
    return game_state

rounds = 0
high_score = 0
scores = 0

steps = ['w', 'a', 's', 'd']

def copy_grid(param):
    board, score = param
    return (copy.deepcopy(board), score)

def getBestMove(board, score, pool):
    grids = pool.map(copy_grid, map(lambda x: (board, score), range(300)))
    #for i in range(150):
    #    grids.append((copy.deepcopy(board), score))
    runs = pool.map(generateRun, grids)
    return getBestMoveForRuns(runs, pool)

def valid_moves(game):
    return [d for d in 'wasd' if copy.deepcopy(game).process_move(d)]

def generateRun(param):
    r = random.SystemRandom()
    grid, score = param
    g = Game(grid, score)
    m_options = valid_moves(g)
    if not m_options:
        return None
    s = r.choice(m_options)
    g.process_move(s)
    while m_options:
        x = r.choice(m_options)
        g.process_move(x)
        g.add_number()
        m_options = valid_moves(g)

    return {'initialMove': s, 'finalScore': g.c_score}

def get_avg_score(runs):
    total = 0
    for run in runs:
        total += run['finalScore']
    if runs:
        return {'move': runs[0]['initialMove'], 'avg_score': total / len(runs)}
    else:
        return None

def get_runs_for_move(param):
    move, runs = param
    return list(filter(lambda x: x and x['initialMove'] == move, runs))

def getBestMoveForRuns(runs, pool):
    res = pool.map(get_runs_for_move, [('w', runs), ('a', runs), ('s', runs), ('d', runs)])
    avg_scores = pool.map(get_avg_score, res)
    best = max(avg_scores, key=lambda x: x['avg_score'] if x else 0)

    if best:
        return best['move']
    return None

if __name__ == '__main__':
    pool = Pool()
    start_time = time.time()

    while True:
#        resp = requests.post(SERVER_URL + '/api/new_game', json={'team_name': 'fw_alg2_1'})
        resp = requests.get(SERVER_URL + '/api/new_game')
        current_state = resp.json()

        while not current_state.get('game_over', False):
            m = getBestMove(current_state['board'], current_state['c_score'], pool)
            if not m:
                break
            current_state = step(m, current_state['uId'])
        print('********************************')
        rounds += 1
        scores += current_state['c_score']
        if current_state['c_score'] > high_score:
            high_score = current_state['c_score']
        print(current_state['board'])
        print('Number of played rounds: {}'.format(rounds))
        print('High score: {}'.format(high_score))
        print('Avg score: {}'.format(scores / rounds))
        print('Total score: {}'.format(scores))
        if time.time() - start_time > 600:
            break
