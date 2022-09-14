class Player:
    def __init__(self, name, sid):
        self.name = name
        self.sid = sid
        self.hand = []
        self.trust = None
        self.ready = False
    
    def setReady(self, ready):
        self.ready = ready
    
    def dealHand(self, hand):
        self.hand = hand
    
    def setTrust(self, trust):
        self.trust = trust

    def addTrustToHand(self):
        self.hand.append(self.trust)
        self.deleteTrust()
    
    def deleteTrust(self):
        self.trust = None