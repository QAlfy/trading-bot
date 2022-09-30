from web3 import Web3

w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/f3dbb404662d4016b0e95237873038c4'))


def is_contract(address: str):
    address = Web3.toChecksumAddress(address.lower())
    code = w3.eth.get_code(address)

    return code != b''
