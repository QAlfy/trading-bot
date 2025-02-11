from enum import Enum

from com.cryptobot.schemas.address import Address
from com.cryptobot.schemas.schema import Schema
from com.cryptobot.utils.network import get_contract


class TxType(Enum):
    UNCLASSIFIED = 0
    SWAP = 1


class Tx(Schema):
    def __init__(self, timestamp, block_number, hash, _from, to, gas, gas_price, value, input, decoded_input=None, _type=TxType.UNCLASSIFIED, raw = None):
        super().__init__()

        self.timestamp = timestamp
        self.block_number = block_number
        self.hash = hash.lower() if type(hash) == str else hash
        # underscore (reserved keyword)
        self.sender: Address = _from
        self.receiver: Address = to
        self.gas = gas
        self.gas_price = gas_price
        self.value = int(value, 0) if type(value) == str else value
        self.type = _type
        self.raw = raw
        self.input = input
        self.decoded_input = decoded_input

    @property
    def __key__(self):
        return (self.hash)

    def decode_input(self):
        if self.input is None:
            return None

        try:
            contract = get_contract(self.receiver.address)

            if contract is None:
                return None

            func_obj, func_params = contract.decode_function_input(self.input)
            self.decoded_input = {'func_obj': func_obj, 'func_params': func_params}

            return self.decoded_input
        except Exception as error:
            pass

    def __iter__(self):
        return vars(self).iteritems()

    def from_dict(dict_obj):
        return Tx(dict_obj['timestamp'], dict_obj['block_number'], dict_obj['hash'], dict_obj['sender'], dict_obj['receiver'],
                  dict_obj['gas'], dict_obj['gas_price'], dict_obj['value'], dict_obj['input'])
