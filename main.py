from flask import Flask, render_template
import eventlet, socketio
from player import Player
from random import shuffle
from time import sleep

app = Flask(__name__)
sio = socketio.Server()

players = {}
playing = False
order = []
turn = 0

def next_turn():
    sleep(0.1)
    global turn
    turn = (turn + 1) % len(order)
    sio.emit('turn', {'sid': order[turn], 'log': players[order[turn]].name + '\'s turn'})
    print(order[turn] + '\'s turn')

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
    return render_template('game.html', players=[player for player in players.values() if player.sid != id], id=id, hand=", ".join(sorted(map(str, players[id].hand))), thisPlayer=players[id].name)

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
            print(order[turn] + '\'s turn')
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

@sio.on('reject')
def reject(sid, data):
    sio.emit('reject', {'origin': sid, 'target': data['sid'], 'log': players[sid].name + ' rejected ' + players[data['sid']].name + '\'s date.'})
    print(sid, "rejected", data['sid'])
    next_turn()

@sio.on('trust exchange')
def trust_exchange(sid, data):
    players[sid].hand.remove(int(data['card']))
    players[data['target']].setTrust(int(data['card']))
    sio.emit('trust exchange', {'origin': sid, 'target': data['target'], 'card': data['card'], 'log': players[sid].name + ' sent ' + players[data['target']].name + ' a trust card.'})
    print(sid, "sent", data['card'], "as a trust card to", data['target'])

@sio.on('second date invite')
def second_date_invite(sid, data):
    sio.emit('second date invite', {'origin': sid, 'target': data['target'], 'log': players[sid].name + ' invited ' + players[data['target']].name + ' to a second date.'})
    print(sid, "invited", data['target'], "to a second date")

@sio.on('no second date')
def no_second_date(sid, data):
    sio.emit('no second date', {'origin': sid, 'target': data['target'], 'log': players[sid].name + ' did not invite ' + players[data['target']].name + ' on a second date.'})
    print(sid, "did not invite", data['target'], "on a second date")
    next_turn()

@sio.on('return trust')
def return_trust(sid, data):
    players[data['target']].hand.append(int(data['card']))
    players[sid].deleteTrust()
    sio.emit('return trust', {'origin': sid, 'target': data['target'], 'card': data['card'], 'log': players[sid].name + ' returned a trust card to ' + players[data['target']].name + '.'})
    print(sid, "returned", data['card'], "to", data['target'], "a trust card")

@sio.on('accept second date')
def accept_second_date(sid, data):
    players[sid].addTrustToHand()
    players[data['target']].addTrustToHand()
    sio.emit('accept second date', {'origin': sid, 'target': data['target'], 'log': players[sid].name + ' accepted ' + players[data['target']].name + '\'s second date.'})
    print(sid, "accepted", data['target'], "second date invite")
    next_turn()

@sio.on('reject second date')
def reject_second_date(sid, data):
    sio.emit('reject second date', {'origin': sid, 'target': data['target'], 'log': players[sid].name + ' rejected ' + players[data['target']].name + '\'s second date.'})
    print(sid, "rejected", data['target'], "second date invite")
    next_turn()

@sio.on('preghost')
def preghost(sid, data):
    sio.emit('preghost', {'origin': sid, 'target': data['target'], 'log': players[sid].name + ' ghosted ' + players[data['target']].name + '.'})
    print(sid, "preghosted", data['target'])

@sio.on('ghost')
def ghost(sid, data):
    players[sid].addTrustToHand()
    sio.emit('ghost', {'origin': sid, 'target': data['target'], 'log': players[sid].name + ' ghosted ' + players[data['target']].name + '.'})
    print(sid, "ghosted", data['target'])
    if data['done']:
        next_turn()

@sio.on('follow through')
def follow_through(sid, data):
    sio.emit('follow through', {'log': players[sid].name + ' followed through with ' + players[data['target']].name + '.'})
    print(sid, "followed through with", data['target'])

@sio.on('win single')
def win_solo(sid, data):
    sio.emit('win', {'log': '<b>' + players[sid].name + ' won single with a set of ' + data['card'] + 's.</b>'})
    print(sid, "won single with a set of", data['card'] + 's')

@sio.on('declare set')
def declare_set(sid, data):
    sio.emit('declare set', {'origin': sid, 'target': data['target'], 'hand': data['hand'], 'log': players[sid].name + ' declared a set with' + players[data['target']].name + '.'})
    print(sid, "declared with", data['target'], "hand:", data['hand'])

@sio.on('win')
def win(sid, data):
    sio.emit('win', {'winners': [sid, data['target']], 'log': '<b>' + players[sid].name + ' and ' + players[data['target']].name + ' won with a set of ' + data['card'] + 's.</b>'})
    print(sid, "and", data['target'], "won with a set of", data['card'] + 's')

@sio.on('lose')
def lose(sid, data):
    sio.emit('lose', {'losers': [sid, data['target']], 'log': '<b>' + players[sid].name + ' and ' + players[data['target']].name + ' lost by falsly declaring a set.</b>'})
    global turn
    next_player = order[(turn + 1) % len(order)]
    if next_player == data['target']:
        next_player = order[(turn + 2) % len(order)]
    order.remove(sid)
    order.remove(data['target'])
    print(sid, "and", data['target'], "lost")
    print(order)
    if len(order) > 1:
        turn = order.index(next_player) - 1
        next_turn()
    elif len(order) == 1:
        sio.emit('win', {'winners': [order[0]], 'log': '<b>' + players[order[0]].name + ' won because they were the last one standing.</b>'})
        print(order[0], "won by default")
    else:
        sio.emit('game over', {'log': '<b>Game over. Everyone is out.</b>'})
        print('game over')


if __name__ == '__main__':
    # initialize the app with flask and socketio
    app = socketio.WSGIApp(sio, app)
    print('started server')
    # start the server on localhost port 8080
    eventlet.wsgi.server(eventlet.listen(('', 8080)), app, log_output=False, debug=True)