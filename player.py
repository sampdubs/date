class Player:
    def __init__(self, name, sid):
        self.name = name
        self.sid = sid
        self.cards = []
        self.ready = False
    
    def setReady(self, ready):
        self.ready = ready
    
    def dealHand(self, hand):
        self.cards = hand