import logging
import redis
from com.cryptobot.config import Config
from jsonpickle import encode, decode
from threading import RLock
from rsmq.cmd.utils import encode_message, decode_message

from com.cryptobot.utils.logger import PrettyLogger

settings = Config().get_settings()
redis_instance = redis.Redis(host=settings.redis.host, port=settings.redis.port, db=0)


class RedisMixin():
    lock = RLock()

    def __init__(self):
        self.logger = PrettyLogger(__name__, logging.INFO)

    def get(self, key):
        with self.lock:
            value = None

            try:
                key = f'{self.__hash__()}-{key}'
                value = redis_instance.get(key)
                value = decode(decode_message(value)) if value != None else None
            except Exception as error:
                self.logger.error(error)

                return None

            return value

    def set(self, key, value, ttl=None):
        with self.lock:
            try:
                key = f'{self.__hash__()}-{key}'
                value = encode_message(encode(value))
                is_set = redis_instance.set(key, value, ex=ttl)
            except Exception as error:
                self.logger.error(error)

            return is_set
