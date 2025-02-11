import asyncio
import json
from typing import List

from com.cryptobot.classifiers.tx import TXClassifier
from com.cryptobot.config import Config
from com.cryptobot.events.consumer import EventsConsumerMixin
from com.cryptobot.events.producer import EventsProducerMixin
from com.cryptobot.extractors.extractor import Extractor
from com.cryptobot.schemas.tx import Tx
from com.cryptobot.utils.python import get_class_by_fullname
from com.cryptobot.utils.tx_queue import TXQueue
from com.cryptobot.utils.network import fetch_fake_mempool_txs

from jsonpickle import encode


class FakeMempoolExtractor(Extractor, EventsProducerMixin):
    def __init__(self, classifiers_paths=None):
        for base_class in FakeMempoolExtractor.__bases__:
            if base_class == EventsProducerMixin:
                base_class.__init__(self, queue=TXClassifier.__name__)
            else:
                base_class.__init__(self, __name__)

        self.settings = Config().get_settings()
        self.cached_txs = TXQueue()
        self.classifiers = []
        self.alchemy_api_keys = iter(self.settings.web3.providers.alchemy.api_keys)

        classifiers_paths = ['com.cryptobot.classifiers.tx.TXClassifier'] + \
            (
                Config().get_settings().runtime.extractors.mempool.classifiers if classifiers_paths is None
            else classifiers_paths
        )

        for clf in classifiers_paths:
            cls = get_class_by_fullname(clf)

            self.classifiers.append(cls)

    def listen(self):
        self.logger.info('Monitoring the fake mempool...')

        # setup classifiers
        self.ondemand_classifiers = [
            cls(cache=self.cached_txs) for cls in self.classifiers if not issubclass(cls, EventsConsumerMixin)]
        self.consumers_classifiers = [
            cls for cls in self.classifiers if issubclass(cls, EventsConsumerMixin)]

        for consumer in self.consumers_classifiers:
            settings = getattr(Config().get_settings(
            ).runtime.classifiers, consumer.__name__)
            max_concurrent_threads = getattr(
                settings, 'max_concurrent_threads') if settings is not None else 1

            for i in range(0, max_concurrent_threads):
                consumer(cache=self.cached_txs).consume()

        # start listening
        asyncio.run(self.get_pending_txs())

    async def get_pending_txs(self):
        while True:
            try:
                mempool_txs = fetch_fake_mempool_txs()

                self.process_txs(mempool_txs)
            except Exception as error:
                self.logger.error(error)
            finally:
                await asyncio.sleep(1)

    def process_txs(self, txs):
        # initialize on demand classifiers
        for ondemand in self.ondemand_classifiers:
            mempool_txs: List[Tx] = ondemand.classify(txs)

        if len(mempool_txs) > 0:
            self.publish(
                list(map(lambda tx: encode(tx, max_depth=3), mempool_txs)))

    def run(self):
        self.listen()
