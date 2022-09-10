class Player:
    def __init__(self, name, sid):
        self.name = name
        self.sid = sid
        self.hand = []
        self.ready = False
    
    def setReady(self, ready):
        self.ready = ready
    
    def dealHand(self, hand):
        self.hand = hand