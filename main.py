from flask import Flask, render_template
import eventlet, socketio
from player import Player
from random import shuffle

app = Flask(__name__)
sio = socketio.Server()

players = {}
playing = False
order = []
turn = 0

@app.route('/')
def login():
    if not playing:
        return render_template('login.html')
    return "Sorry, the game is already in progress."

@app.route('/waiting/<id>')
def waiting(id):
    return render_template('waiting.html', players=players.values(), id=id)

@app.route('/play/<id>')
def play(id):
    return render_template('game.html', players=[player for player in players.values() if player.sid != id], id=id, hand=", ".join(sorted(map(str, players[id].hand))))

@sio.on('new player')
def new_player(sid, data):
    if data['name'] in [player.name for player in players.values()]:
        sio.emit('name taken', room=sid)
        return
    player = Player(data['name'], sid)
    players[sid] = player
    print('New player:', player.name)
    sio.emit('new player', {'name': player.name, 'sid': player.sid})

@sio.on('change sid 1')
def change_sid1(sid, data):
    if data['old'] in players:
        players[data['old']].sid = sid
        players[sid] = players[data['old']]
        del players[data['old']]
        print('Player sid changed:', players[sid].name)
        sio.emit('change sid', {'name': players[sid].name, 'sid': players[sid].sid, 'old': data['old']})

@sio.on('change sid 2')
def change_sid2(sid, data):
    if data['old'] in players:
        players[data['old']].sid = sid
        players[sid] = players[data['old']]
        del players[data['old']]
        print('Player sid changed:', players[sid].name)
        sio.emit('change sid', {'name': players[sid].name, 'sid': players[sid].sid, 'old': data['old']})
        order.append(sid)
        if len(order) == len(players):
            # All players have joined, start the game
            print('Starting game, order:', order)
            sio.emit('order', {'order': [{'name': players[sid].name, 'sid': sid} for sid in order]})
            sio.emit('turn', {'sid': order[turn]})


@sio.on('ready')
def ready(sid, data):
    players[sid].setReady(data['ready'])
    print('Player', players[sid].name, 'is ready:', players[sid].ready)
    sio.emit('ready', {'name': players[sid].name, 'sid': players[sid].sid, 'ready': players[sid].ready})
    if all(player.ready for player in players.values()):
        cards = list(range(1, len(players) + 1)) * 4
        for player in players.values():
            shuffle(cards)
            player.dealHand([cards.pop() for _ in range(4)])
            print('Dealt hand', player.hand,'to', player.name)
        global playing
        playing = True
        sio.emit('all ready')

if __name__ == '__main__':
    # initialize the app with flask and socketio
    app = socketio.Middleware(sio, app)
    print('started server')
    # start the server on localhost port 8080
    eventlet.wsgi.server(eventlet.listen(('', 8080)), app, log_output=False)