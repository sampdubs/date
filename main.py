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
couples = {}

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
            sio.emit('turn', {'sid': order[turn], 'log': players[order[turn]].name + '\'s turn'})

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

@sio.on('ask out')
def askout(sid, data):
    sio.emit('ask out', {'origin': sid, 'target': data['sid'], 'log': players[sid].name + ' asked out ' + players[data['sid']].name})
    print(sid, "asked out", data['sid'])

@sio.on('accept')
def accept(sid, data):
    sio.emit('accept', {'origin': sid, 'target': data['sid'], 'log': players[sid].name + ' and ' + players[data['sid']].name + ' are on a date.'})
    print(sid, "accepted", data['sid'])

@sio.on('trust exchange')
def trust_exchange(sid, data):
    players[sid].hand.remove(int(data['card']))
    sio.emit('trust exchange', {'origin': sid, 'target': data['target'], 'card': data['card'], 'log': players[sid].name + ' sent ' + players[data['target']].name + ' a trust card.'})
    print(sid, "sent", data['card'], "as a trust card to", data['target'])

@sio.on('second date invite')
def second_date_invite(sid, data):
    sio.emit('second date invite', {'origin': sid, 'target': data['target'], 'log': players[sid].name + ' invited ' + players[data['target']].name + ' to a second date.'})
    print(sid, "invited", data['target'], "to a second date")

@sio.on('no second date')
def no_second_date(sid, data):
    sio.emit('no second date', {'origin': sid, 'target': data['target'], 'log': players[sid].name + ' did not invite ' + players[data['target']].name + 'on a second date.'})
    print(sid, "did not invide", data['target'], "on a second date")

@sio.on('return trust')
def return_trust(sid, data):
    players[data['target']].hand.append(int(data['card']))
    sio.emit('return trust', {'origin': sid, 'target': data['target'], 'card': data['card'], 'log': players[sid].name + ' returned a trust card to ' + players[data['target']].name + '.'})
    print(sid, "returned", data['card'], "to", data['target'], "a trust card")

@sio.on('accept second date')
def accept_second_date(sid, data):
    players[sid].hand.append(int(data['card']))
    couples[sid] = data['target']
    couples[data['target']] = sid
    sio.emit('accept second date', {'origin': sid, 'target': data['target'], 'log': players[sid].name + ' accepted ' + players[data['target']].name + '\'s second date.'})
    print(sid, "accepted", data['target'], " second date invite")

@sio.on('reject second date')
def reject_second_date(sid, data):
    sio.emit('reject second date', {'origin': sid, 'target': data['target'], 'log': players[sid].name + ' rejected ' + players[data['target']].name + '\'s second date.'})
    print(sid, "rejected", data['target'], " second date invite")

if __name__ == '__main__':
    # initialize the app with flask and socketio
    app = socketio.WSGIApp(sio, app)
    print('started server')
    # start the server on localhost port 8080
    eventlet.wsgi.server(eventlet.listen(('', 8080)), app, log_output=False)