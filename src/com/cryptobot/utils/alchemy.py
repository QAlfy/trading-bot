import logging
from itertools import cycle
from threading import RLock
from urllib.error import HTTPError

from backoff import expo, on_exception
from com.cryptobot.config import Config
from com.cryptobot.utils.logger import PrettyLogger
from com.cryptobot.utils.request import FatalRequestException, HttpRequest
from ratelimit import RateLimitException, limits

request = HttpRequest()
settings = Config().get_settings()
max_threads = settings.runtime.classifiers.SwapClassifier.max_concurrent_threads
max_calls = int(50/max_threads)
period_per_thread = int(60/max_threads)
alchemy_api_keys = cycle(settings.web3.providers.alchemy.api_keys)
lock = RLock()
api_key = None


def get_working_key():
    global api_key
    global alchemy_api_keys
    global lock

    with lock:
        try:
            if api_key is None:
                api_key = next(alchemy_api_keys)
        except Exception as error:
            alchemy_logger.error(error)

            return api_key

        return api_key


@on_exception(expo, RateLimitException, max_tries=1, max_time=10)
@limits(calls=max_calls, period=period_per_thread)
def api_post(payload):
    global api_key

    try:
        response = request.post(settings.endpoints.alchemy.api.format(
            api_key=get_working_key()), payload)

        return response
    except HTTPError as error:
        api_key = None

        alchemy_logger.error(
            f'HTTPError: code {error.code}. Repeating (will try next api_key)...')

        return api_post(payload)
    except FatalRequestException as _error:
        api_key = None

        alchemy_logger.error(
            f'FatalRequestException: tried {_error.num_tries} time(s).')

        raise _error


alchemy_logger = PrettyLogger(HttpRequest.__name__, logging.INFO)
