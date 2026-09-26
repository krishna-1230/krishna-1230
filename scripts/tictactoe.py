#!/usr/bin/env python3
"""Community Tic-Tac-Toe played through GitHub issues.

Visitors are X and always move first; the AI answers as O. The game state
lives in game/state.json and the board is rendered into README.md between
the TTT markers.

Usage:
    ISSUE_TITLE="ttt|move|5" PLAYER=octocat python scripts/tictactoe.py
    python scripts/tictactoe.py --render      # re-render README only

Prints the issue comment (markdown) to stdout.
"""
import json
import os
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "game" / "state.json"
README = ROOT / "README.md"
REPO = "krishna-1230/krishna-1230"
START, END = "<!-- TTT:START -->", "<!-- TTT:END -->"

LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
MISTAKE_RATE = 0.2  # chance the AI plays a random move, so humans can actually win
SYMBOL = {"X": "❌", "O": "⭕"}
EMPTY = "🟦"


def new_state():
    return {
        "game": 1,
        "board": [" "] * 9,
        "stats": {"human": 0, "ai": 0, "draw": 0},
        "players": {},
        "recent": [],
        "last_result": None,
    }


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return new_state()


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def outcome(board):
    for a, b, c in LINES:
        if board[a] != " " and board[a] == board[b] == board[c]:
            return board[a]
    return "draw" if " " not in board else None


def minimax(board, player):
    """Score from O's point of view: 1 = O wins, -1 = X wins, 0 = draw."""
    result = outcome(board)
    if result == "O":
        return 1
    if result == "X":
        return -1
    if result == "draw":
        return 0
    scores = []
    for i in range(9):
        if board[i] == " ":
            board[i] = player
            scores.append(minimax(board, "X" if player == "O" else "O"))
            board[i] = " "
    return max(scores) if player == "O" else min(scores)


def ai_move(board):
    free = [i for i in range(9) if board[i] == " "]
    if random.random() < MISTAKE_RATE:
        return random.choice(free)
    scored = []
    for i in free:
        board[i] = "O"
        scored.append((minimax(board, "X"), i))
        board[i] = " "
    best = max(s for s, _ in scored)
    return random.choice([i for s, i in scored if s == best])


def issue_link(title):
    body = "Just press **Create** — no need to change anything. The bot plays your move and answers in about a minute."
    return f"https://github.com/{REPO}/issues/new?title={quote(title, safe='')}&body={quote(body, safe='')}"


def ascii_board(board):
    rows = [" | ".join(c if c != " " else str(r * 3 + i + 1) for i, c in enumerate(board[r * 3:r * 3 + 3])) for r in range(3)]
    return "```\n " + "\n---+---+---\n ".join(rows) + "\n```"


def finish(state, result, player):
    stats, board = state["stats"], state["board"]
    final = ascii_board(board)
    if result == "X":
        stats["human"] += 1
        state["players"][player] = state["players"].get(player, 0) + 1
        state["last_result"] = f"Game #{state['game']}: @{player} beat the AI 🏆"
        msg = f"### 🏆 You beat the AI!\n\n{final}\n\nYou're on the leaderboard now. A fresh board is up — go again?"
    elif result == "O":
        stats["ai"] += 1
        state["last_result"] = f"Game #{state['game']}: the AI won after @{player}'s move 🤖"
        msg = f"### 🤖 The AI wins this round.\n\n{final}\n\nA fresh board is up — revenge?"
    else:
        stats["draw"] += 1
        state["last_result"] = f"Game #{state['game']}: draw, @{player} held the line 🤝"
        msg = f"### 🤝 It's a draw.\n\n{final}\n\nA fresh board is up."
    state["game"] += 1
    state["board"] = [" "] * 9
    return msg


def play(state, title, player):
    title = title.strip()
    if title == "ttt|new":
        state["board"] = [" "] * 9
        state["recent"].insert(0, {"player": player, "move": "new game", "at": now()})
        state["recent"] = state["recent"][:5]
        return "### 🔄 Board reset. Your move!"

    match = re.fullmatch(r"ttt\|move\|([1-9])", title)
    if not match:
        return None, "Hmm, I couldn't read that move. Use the links in the README to play."
    cell = int(match.group(1)) - 1
    board = state["board"]
    if board[cell] != " ":
        return None, f"Square {cell + 1} is already taken — someone got there first. Pick another one from the README!"

    board[cell] = "X"
    state["recent"].insert(0, {"player": player, "move": f"X on {cell + 1}", "at": now()})
    state["recent"] = state["recent"][:5]

    result = outcome(board)
    if result:
        return finish(state, result, player)

    reply = ai_move(board)
    board[reply] = "O"
    result = outcome(board)
    if result:
        return finish(state, result, player)

    return f"### ✅ You played {cell + 1}, the AI answered with {reply + 1}.\n\n{ascii_board(board)}\n\nThe board in the README is updated — anyone can make the next move."


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def render(state):
    board = state["board"]
    rows = []
    for r in range(3):
        cells = []
        for i in range(r * 3, r * 3 + 3):
            if board[i] == " ":
                cells.append(f'<td align="center"><a href="{issue_link(f"ttt|move|{i + 1}")}"><h1>{EMPTY}</h1></a></td>')
            else:
                cells.append(f'<td align="center"><h1>{SYMBOL[board[i]]}</h1></td>')
        rows.append("  <tr>" + "".join(cells) + "</tr>")

    s = state["stats"]
    out = [
        START,
        f'<p align="center"><b>Game #{state["game"]}</b> · you are ❌, my AI is ⭕ · click any 🟦 to make a move</p>',
        '<table align="center">',
        *rows,
        "</table>",
        "",
        f'<p align="center">Humans <b>{s["human"]}</b> · AI <b>{s["ai"]}</b> · Draws <b>{s["draw"]}</b>'
        f' · <a href="{issue_link("ttt|new")}">reset board</a></p>',
    ]
    if state["last_result"]:
        out.append(f'<p align="center"><sub>{state["last_result"]}</sub></p>')

    out.append("")
    out.append("<details>")
    out.append("<summary><b>🏅 Leaderboard & recent moves</b></summary>")
    out.append("")
    leaders = sorted(state["players"].items(), key=lambda kv: -kv[1])[:5]
    out.append("| 🏅 Beat the AI | Wins |")
    out.append("|---|---|")
    if leaders:
        out += [f"| [@{p}](https://github.com/{p}) | {w} |" for p, w in leaders]
    else:
        out.append("| *nobody yet, be the first* | – |")
    out.append("")
    out.append("| Recent moves | Player | Date |")
    out.append("|---|---|---|")
    if state["recent"]:
        out += [f"| {m['move']} | [@{m['player']}](https://github.com/{m['player']}) | {m['at']} |" for m in state["recent"]]
    else:
        out.append("| *no moves yet* | – | – |")
    out.append("")
    out.append("</details>")
    out.append(END)

    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    README.write_text(pattern.sub(lambda _: "\n".join(out), text), encoding="utf-8")


def main():
    state = load_state()
    if "--render" in sys.argv:
        save_state(state)
        render(state)
        return

    player = os.environ.get("PLAYER", "")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", player):
        print("Couldn't identify the player.")
        return

    result = play(state, os.environ.get("ISSUE_TITLE", ""), player)
    if isinstance(result, tuple):  # rejected move: comment only, no state change
        print(result[1])
        return

    save_state(state)
    render(state)
    print(result + "\n\n[⬅ Back to the board](https://github.com/krishna-1230#-tictactoe---vs-ai)")


if __name__ == "__main__":
    main()
