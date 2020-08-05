from uuid import uuid4

from blockchain import Blockchain

from utility.verification import Verification

from wallet import Wallet


class Node:
    def __init__(self):
        #self.id = str(uuid4())
        self.wallet = Wallet()
        self.wallet.create_keys()
        self.blockchain = Blockchain(self.wallet.public_key)

    def get_transanction_value(self):
        """ Returns the input of the user (a new transanction amount) as a float. """
        # Get the user input, transform it from a string to a float and store it in user_input
        tx_recipient = input('Enter the recipient of the transanction: ')
        tx_amount = float(input('Your transanction amount please: '))
        return tx_recipient, tx_amount

    def get_user_choice(self):
        """Prompts the user for its choice and return it."""
        user_input = input('Your choice: ')
        return user_input

    def print_blockchain_elements(self):
        """ Output all blocks of the blockchain. """
        # Output the blockchain list to the console
        for block in self.blockchain.get_chain():
            print('Outputting Block')
            print(block)
        else:
            print('-' * 20)

    def listen_for_input(self):
        waiting_for_input = True
        # A while loop for the user input interface
        # It's a loop that exits once waiting_for_input becomes False or when break is called
        while waiting_for_input:
            print('Please choose')
            print('1: Add a new transanction value')
            print('2: Mine a new block')
            print('3: Output the blockchain blocks')
            print('4: Check transanction validity')
            print('5: Create Wallet')
            print('6: Load Wallet')
            print('7: Save Keys')
            print('q: Quit')
            user_choice = self.get_user_choice()
            if user_choice == '1':
                tx_data = self.get_transanction_value()
                recipient, amount = tx_data
                # Add the transanction amount to the blockchain
                signature = self.wallet.sign_transanction(
                    self.wallet.public_key, recipient, amount)
                if self.blockchain.add_transanction(recipient, self.wallet.public_key, signature, amount=amount):
                    print('Added transanction!')
                else:
                    print('Transanction failed!')
                print(self.blockchain.get_open_transanctions())
            elif user_choice == '2':
                if not self.blockchain.mine_block():
                    print('Mining Failed Got No Wallet')
            elif user_choice == '3':
                self.print_blockchain_elements()
            elif user_choice == '4':
                if Verification.verify_transanctions(self.blockchain.get_open_transanctions(), self.blockchain.get_balance):
                    print('All transanctions are valid')
                else:
                    print('There are invalid transanctions')
            elif user_choice == '5':
                self.wallet.create_keys()
                self.blockchain = Blockchain(self.wallet.public_key)

            elif user_choice == '6':
                self.wallet.load_keys()
                self.blockchain = Blockchain(self.wallet.public_key)

            elif user_choice == '7':
                self.wallet.save_keys()

            elif user_choice == 'q':
                # This will lead to the loop to exist because it's running condition becomes False
                waiting_for_input = False
            else:
                print('Input was invalid, please pick a value from the list!')

            if not Verification.verify_chain(self.blockchain.get_chain()):
                self.print_blockchain_elements()
                print('Invalid blockchain!')
                # Break out of the loop
                break
            print('Balance of {}: {:6.2f}'.format(
                self.wallet.public_key, self.blockchain.get_balance()))
        else:
            print('User left!')

        print('Done!')


node = Node()
node.listen_for_input()
