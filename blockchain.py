from functools import reduce
import hashlib as hl
from collections import OrderedDict
import requests
import json
import pickle

# Import two functions from our hash_util.py file. Omit the ".py" in the import
from utility.hash_util import hash_block

from block import Block

from transanction import Transanction

from utility.verification import Verification

from wallet import Wallet


# The reward we give to miners (for creating a new block)
MINING_REWARD = 10


class Blockchain:
    def __init__(self, public_key, node_id):
        # Our starting block for the blockchain
        genesis_block = Block(0, '', [], 100, 0)
        # Initializing our (empty) blockchain list
        self.__chain = [genesis_block]
        # Unhandled transanctions
        self.__open_transanctions = []
        self.public_key = public_key
        self.__peer_nodes = set()
        self.node_id = node_id
        self.resolve_conflicts = False
        self.load_data()

    def get_chain(self):
        return self.__chain

    def get_open_transanctions(self):
        return self.__open_transanctions

    def load_data(self):
        try:
            """Initialize blockchain + open transanctions data from a file."""
            with open('blockchain-{}.txt'.format(self.node_id), mode='r') as f:
                # file_content = pickle.loads(f.read())
                file_content = f.readlines()
                # blockchain = file_content['chain']
                # open_transanctions = file_content['ot']
                blockchain = json.loads(file_content[0][:-1])
                # We need to convert  the loaded data because transanctions should use OrderedDict
                updated_blockchain = []
                for block in blockchain:
                    converted_tx = [Transanction(
                        tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in block['transanctions']]
                    updated_block = Block(
                        block['index'], block['previous_hash'], converted_tx, block['proof'], block['timestamp'])
                    updated_blockchain.append(updated_block)
                self.__chain = updated_blockchain
                open_transanctions = json.loads(file_content[1][:-1])
                # We need to convert  the loaded data because transanctions should use OrderedDict
                updated_transanctions = []
                for tx in open_transanctions:
                    updated_transanction = Transanction(
                        tx['sender'], tx['recipient'], tx['signature'], tx['amount'])
                    updated_transanctions.append(updated_transanction)
                self.__open_transanctions = updated_transanctions
                peer_nodes = json.loads(file_content[2])
                self.__peer_nodes = set(peer_nodes)
        except (IOError, IndexError):
            print("Handled Exception...")

    def save_data(self):
        """Save blockchain + open transanctions snapshot to a file."""
        try:
            with open('blockchain-{}.txt'.format(self.node_id), mode='w') as f:
                saveable_chain = [block.__dict__ for block in [Block(block_el.index, block_el.previous_hash, [
                    tx.__dict__ for tx in block_el.transanctions], block_el.proof, block_el.timestamp) for block_el in self.__chain]]
                f.write(json.dumps(saveable_chain))
                f.write('\n')
                saveable_tx = [tx.__dict__ for tx in self.__open_transanctions]
                f.write(json.dumps(saveable_tx))
                f.write('\n')
                f.write(json.dumps(list(self.__peer_nodes)))
                # save_data = {
                #     'chain': blockchain,
                #     'ot': open_transanctions
                # }
                # f.write(pickle.dumps(save_data))
            # print('Saving failed!')
        except IOError:
            print("Saving failed!!")

    def proof_of_work(self):
        """Generate a proof of work for the open transanctions, the hash of the previous block and a random number (which is guessed until it fits)."""
        last_block = self.__chain[-1]
        last_hash = hash_block(last_block)
        proof = 0
        # Try different PoW numbers and return the first valid one
        while not Verification.valid_proof(self.__open_transanctions, last_hash, proof):
            proof += 1
        return proof

    def get_balance(self, sender=None):
        """Calculate and return the balance for a participant.
        """
        if sender == None:
            if self.public_key == None:
                return None
            participant = self.public_key
        else:
            participant = sender

        # Fetch a list of all sent coin amounts for the given person (empty lists are returned if the person was NOT the sender)
        # This fetches sent amounts of transanctions that were already included in blocks of the blockchain
        tx_sender = [[tx.amount for tx in block.transanctions
                      if tx.sender == participant] for block in self.__chain]
        # Fetch a list of all sent coin amounts for the given person (empty lists are returned if the person was NOT the sender)
        # This fetches sent amounts of open transanctions (to avoid double spending)
        open_tx_sender = [tx.amount
                          for tx in self.__open_transanctions if tx.sender == participant]
        tx_sender.append(open_tx_sender)
        print(tx_sender)
        amount_sent = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt)
                             if len(tx_amt) > 0 else tx_sum + 0, tx_sender, 0)
        # This fetches received coin amounts of transanctions that were already included in blocks of the blockchain
        # We ignore open transanctions here because you shouldn't be able to spend coins before the transanction was confirmed + included in a block
        tx_recipient = [[tx.amount for tx in block.transanctions
                         if tx.recipient == participant] for block in self.__chain]
        amount_received = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt)
                                 if len(tx_amt) > 0 else tx_sum + 0, tx_recipient, 0)
        # Return the total balance
        return amount_received - amount_sent

    def get_last_blockchain_value(self):
        """ Returns the last value of the current blockchain. """
        if len(self.__chain) < 1:
            return None
        return self.__chain[-1]

    # This function accepts two arguments.
    # One required one (transanction_amount) and one optional one (last_transanction)
    # The optional one is optional because it has a default value => [1]

    def add_transanction(self, recipient, sender, signature, amount=1.0, is_receiving=False):
        """ Append a new value as well as the last blockchain value to the blockchain.

        Arguments:
            :sender: The sender of the coins.
            :recipient: The recipient of the coins.
            :amount: The amount of coins sent with the transanction (default = 1.0)
        """
        # transanction = {
        #     'sender': sender,
        #     'recipient': recipient,
        #     'amount': amount
        # }
        transanction = Transanction(sender, recipient, signature, amount)

        if Verification.verify_transanction(transanction, self.get_balance):
            self.__open_transanctions.append(transanction)
            self.save_data()
            if not is_receiving:
                for node in self.__peer_nodes:
                    url = 'http://{}/broadcast-transanction'.format(node)
                    try:
                        response = requests.post(url, json={
                            'sender': sender, 'recipient': recipient, 'amount': amount, 'signature': signature})
                        if response.status_code == 400 or response.status_code == 500:
                            print('Transanction declined, needs resolving')
                            return False
                    except requests.ConnectionError:
                        continue

            return True
        return False

    def mine_block(self):
        """Create a new block and add open transanctions to it."""
        # Fetch the currently last block of the blockchain
        if self.public_key == None:
            return None
        last_block = self.__chain[-1]
        # Hash the last block (=> to be able to compare it to the stored hash value)
        hashed_block = hash_block(last_block)
        proof = self.proof_of_work()
        # Miners should be rewarded, so let's create a reward transanction
        # reward_transanction = {
        #     'sender': 'MINING',
        #     'recipient': owner,
        #     'amount': MINING_REWARD
        # }
        reward_transanction = Transanction(
            'MINING', self.public_key, '', MINING_REWARD)
        # Copy transanction instead of manipulating the original open_transanctions list
        # This ensures that if for some reason the mining should fail, we don't have the reward transanction stored in the open transanctions
        copied_transanctions = self.__open_transanctions[:]
        for tx in copied_transanctions:
            if not Wallet.verify_transanction(tx):
                return None

        copied_transanctions.append(reward_transanction)
        block = Block(len(self.__chain), hashed_block,
                      copied_transanctions, proof)
        self.__chain.append(block)
        self.__open_transanctions = []
        self.save_data()
        for node in self.__peer_nodes:
            url = 'http://{}/broadcast-block'.format(node)
            converted_block = block.__dict__.copy()
            converted_block['transanctions'] = [
                tx.__dict__ for tx in converted_block['transanctions']]
            try:
                response = requests.post(url, json={'block': converted_block})
                if response.status_code == 400 or response.status_code == 500:
                    print('Block declined, needs resolving')
                if response.status_code == 409:
                    self.resolve_conflicts = True
            except requests.exceptions.ConnectionError:
                continue
        return block

    def add_block(self, block):
        transanctions = [Transanction(
            tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in block['transanctions']]
        proof_is_valid = Verification.valid_proof(
            transanctions[:-1], block['previous_hash'], block['proof'])
        hashes_match = hash_block(self.__chain[-1]) == block['previous_hash']
        if not proof_is_valid or not hashes_match:
            return False
        converted_block = Block(
            block['index'], block['previous_hash'], transanctions, block['proof'], block['timestamp'])
        self.__chain.append(converted_block)
        stored_transanctions = self.__open_transanctions[:]
        for itx in block['transanctions']:
            for opentx in stored_transanctions:
                if opentx.sender == itx['sender'] and opentx.recipient == itx['recipient'] and opentx.amount == itx['amount'] and opentx.signature == itx['signature']:
                    try:
                        self.__open_transanctions.remove(opentx)
                    except ValueError:
                        print('Item was already removed')
        self.save_data()
        return True

    def resolve(self):
        winner_chain = self.__chain
        replace = False
        for node in self.__peer_nodes:
            url = 'http://{}/chain'.format(node)
            try:
                response = requests.get(url)
                node_chain = response.json()
                node_chain = [Block(block['index'], block['previous_hash'], [Transanction(
                    tx['sender'], tx['recipient'], tx['signature'], tx['amount']) for tx in block['transanctions']],
                    block['proof'], block['timestamp']) for block in node_chain]
                node_chain_length = len(node_chain)
                local_chain_length = len(winner_chain)
                if node_chain_length > local_chain_length and Verification.verify_chain(node_chain):
                    winner_chain = node_chain
                    replace = True
            except requests.exceptions.ConnectionError:
                continue
        self.resolve_conflicts = False
        self.__chain = winner_chain
        if replace:
            self.__open_transanctions = []
        self.save_data()
        return replace

    def add_peer_node(self, node):
        """Adds a new node to the peer node set.

        Arguments:The node url which should be added"""
        self.__peer_nodes.add(node)
        self.save_data()

    def remove_peer_node(self, node):
        """Removes a node from the peer node set.

        Arguments:The node url which should be removed"""
        self.__peer_nodes.discard(node)
        self.save_data()

    def get_peer_nodes(self):
        """Return a list of all connected peer nodes."""
        return list(self.__peer_nodes)
