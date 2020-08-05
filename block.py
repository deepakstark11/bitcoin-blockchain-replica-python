from time import time

from utility.printable import Printable


class Block(Printable):
    def __init__(self, index, previous_hash, transanctions, proof, time=time()):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = time
        self.transanctions = transanctions
        self.proof = proof
