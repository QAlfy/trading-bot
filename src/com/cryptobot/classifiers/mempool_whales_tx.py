import decimal
from typing import List

import pandas as pd
from com.cryptobot.classifiers.tx_classifier import TXClassifier
from com.cryptobot.schemas.tx import Tx
from com.cryptobot.utils.path import get_data_path


class MempoolWhaleTXClassifier(TXClassifier):
    def __init__(self):
        super().__init__()

        # load up the list of big wallets collected by com.cryptobot.extractors.TokenHoldersExtractor
        self.tokens_holders_df = pd.read_csv(get_data_path() + 'tokens_holders.csv')
        self.whales_addresses = list(
            map(lambda address: address.lower(), list(self.tokens_holders_df.address.unique())))

    def filter(self, items: List[Tx]) -> List[Tx]:
        return list(item for item in items if (
            str(item.sender).lower() in self.whales_addresses
            or str(item.receiver).lower() in self.whales_addresses
        ))
