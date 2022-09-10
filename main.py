from flask import Flask, render_template
import eventlet, socketio
from player import Player
from random import choice

app = Flask(__name__)
sio = socketio.Server()

players = {}

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/waiting/<id>')
def waiting(id):
    return render_template('waiting.html', players=players.values(), id=id)

@app.route('/play/<id>')
def play(id):
    return render_template('game.html', players=players.values(), id=id, hand=players[id].hand)

@sio.on('new player')
def new_player(sid, data):
    player = Player(data['name'], sid)
    players[sid] = player
    print('New player:', player.name)
    sio.emit('new player', {'name': player.name, 'sid': player.sid})

@sio.on('change sid')
def change_sid(sid, data):
    if data['old'] in players:
        players[data['old']].sid = sid
        players[sid] = players[data['old']]
        del players[data['old']]
        print('Player sid changed:', players[sid].name)
        sio.emit('change sid', {'name': players[sid].name, 'sid': players[sid].sid, 'old': data['old']})

@sio.on('ready')
def ready(sid, data):
    players[sid].setReady(data['ready'])
    print('Player', players[sid].name, 'is ready:', players[sid].ready)
    sio.emit('ready', {'name': players[sid].name, 'sid': players[sid].sid, 'ready': players[sid].ready})
    if all(player.ready for player in players.values()):
        cards = list(range(1, len(players) + 1)) * 4
        for player in players.values():
            player.dealHand([choice(cards) for _ in range(4)])
            sio.emit('deal hand', {'hand': player.hand}, room=sid)
            print('Dealt hand', player.hand,'to', player.name)

if __name__ == '__main__':
    # initialize the app with flask and socketio
    app = socketio.Middleware(sio, app)
    print('started server')
    # start the server on localhost port 8080
    eventlet.wsgi.server(eventlet.listen(('', 8080)), app, log_output=False)