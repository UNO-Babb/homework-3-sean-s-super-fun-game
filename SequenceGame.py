from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import itertools

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

# Game settings
board_size = 6
players = {
    1: {'color': 'red', 'score': 0},
    2: {'color': 'yellow', 'score': 0},
    3: {'color': 'blue', 'score': 0},
    4: {'color': 'green', 'score': 0},
}
turn_order = itertools.cycle(players.keys())
current_player = next(turn_order)

# Initializing the board
board = [['' for _ in range(board_size)] for _ in range(board_size)]
starting_positions = {
    1: (board_size - 1, board_size // 2),
    2: (board_size // 2, board_size - 1),
    3: (0, board_size // 2),
    4: (board_size // 2, 0),
}
for player, (row, col) in starting_positions.items():
    board[row][col] = players[player]['color']

def is_valid_move(row, col):
    """Check if a move is valid (adjacent to an existing tile)."""
    if board[row][col]:  # Spot is already occupied
        return False
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    for dr, dc in directions:
        nr, nc = row + dr, col + dc
        if 0 <= nr < board_size and 0 <= nc < board_size and board[nr][nc]:
            return True
    return False

def calculate_longest_sequence(color):
    """Calculate the longest uninterrupted sequence of tiles for a given color."""
    visited = [[False for _ in range(board_size)] for _ in range(board_size)]
    longest = 0

    def dfs(r, c, count):
        nonlocal longest
        visited[r][c] = True
        longest = max(longest, count)
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if (
                0 <= nr < board_size
                and 0 <= nc < board_size
                and not visited[nr][nc]
                and board[nr][nc] == color
            ):
                dfs(nr, nc, count + 1)

    for r in range(board_size):
        for c in range(board_size):
            if board[r][c] == color and not visited[r][c]:
                dfs(r, c, 1)

    return longest

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('make_move')
def handle_move(data):
    global current_player
    row, col = data['row'], data['col']

    if data['player'] != current_player:
        emit('invalid_move', {'message': "It's not your turn!"}, broadcast=False)
        return

    if is_valid_move(row, col):
        board[row][col] = players[current_player]['color']
        emit('update_board', {'board': board}, broadcast=True)

        # Check if the board is full
        if all(all(cell for cell in row) for row in board):
            # Calculate scores
            for player in players:
                players[player]['score'] += calculate_longest_sequence(players[player]['color'])
            emit('update_scores', {'scores': players}, broadcast=True)

            # Check for winner
            for player, info in players.items():
                if info['score'] >= 20:
                    emit('game_over', {'winner': player}, broadcast=True)
                    return

            # Reset the board
            reset_board()

        # Move to the next turn
        current_player = next(turn_order)
        emit('next_turn', {'current_player': current_player}, broadcast=True)
    else:
        emit('invalid_move', {'message': 'Invalid move!'}, broadcast=False)

def reset_board():
    global board
    board = [['' for _ in range(board_size)] for _ in range(board_size)]
    for player, (row, col) in starting_positions.items():
        board[row][col] = players[player]['color']
    emit('reset_board', {'board': board}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)

