import functools
import operator
import traceback
from typing import List

from jsonpickle import encode

from com.cryptobot.config import Config
from com.cryptobot.utils.redis_mixin import RedisMixin
from com.cryptobot.schemas.schema import Schema
from com.cryptobot.schemas.token import Token
from com.cryptobot.utils.ethereum import is_contract
from com.cryptobot.utils.pandas import get_address_details
from com.cryptobot.utils.request import HttpRequest

request = HttpRequest()
settings = Config().get_settings()


class AddressBalance(Schema):
    def __init__(self, token: Token, qty: int = 0):
        super().__init__()

        self.token = token
        self.qty = qty
        self.qty_usd = (qty/10**token.decimals) * \
            token.price_usd if token.price_usd is not None \
            and token.decimals is not None else float(0)


class AddressPortfolioStats(Schema):
    def __init__(self, balance: AddressBalance, total_usd: float = 0) -> None:
        super().__init__()

        self.balance = balance
        self.total_usd = total_usd
        self.allocation_percent = (
            self.balance.qty_usd*100)/self.total_usd \
            if self.balance.qty_usd != 0 and self.total_usd != 0 else float(0)

    def __str__(self):
        return str({
            'token_symbol': self.balance.token.symbol,
            'token_address': self.balance.token.address,
            'qty': self.balance.qty,
            'qty_usd': self.balance.qty_usd,
            'total_usd': self.total_usd,
            'allocation_percent': self.allocation_percent
        })


class Address(Schema, RedisMixin):
    def __init__(self, address):
        for base_class in Address.__bases__:
            base_class.__init__(self)

        self.address = address.lower()

    def __hash__(self):
        return hash(self.address)

    def metadata(self) -> dict:
        return get_address_details(self.address)

    def is_contract(self):
        return is_contract(self.address)

    def __str__(self):
        return self.address

    def balances(self) -> List[AddressBalance]:
        cached_balances = self.get('balances')
        balances = [] if cached_balances is None else cached_balances

        if len(balances) > 0:
            return balances

        try:
            page_key = None

            while True:
                params = [self.address, 'erc20']

                if page_key is not None:
                    params.append({'pageKey': page_key})

                payload = {
                    'id': 1,
                    'jsonrpc': '2.0',
                    'method': 'alchemy_getTokenBalances',
                    'params': params
                }

                print(f'Fetching balances for {self.address} (pageKey: {page_key})')

                response = request.post(settings.endpoints.alchemy.api.format(
                    api_key=settings.web3.providers.alchemy.api_key), payload)
                page_key = response.get('result', {}).get('pageKey', None)
                tokens_balances = response.get('result', {}).get('tokenBalances', None)

                if tokens_balances is not None:
                    for balance in tokens_balances:
                        token_balance = balance.get('tokenBalance', '0')
                        qty = int(token_balance, 0) if token_balance != '0x' else 0

                        if qty == 0:
                            continue

                        token = Token(address=balance['contractAddress'])
                        address_balance = AddressBalance(token, qty)

                        balances.append(address_balance)
                else:
                    print(f'No balances for {self.address}.')

                if page_key is None:
                    break
        except Exception as error:
            print(error)
            print(traceback.format_exc())
        finally:
            if len(balances) > 0:
                self.set('balances', balances,
                         ttl=settings.runtime.schemas.address.balances_cache_timeout)

            return balances

    def portfolio_stats(self) -> List[AddressPortfolioStats]:
        stats: List[AddressPortfolioStats] = []

        try:
            balances = self.balances()

            print(f'Retrieved {len(balances)} balance(s) for {self.address}')

            total_usd = functools.reduce(
                operator.add, [
                    balance.qty_usd
                    for balance in balances if balance.qty_usd is not None],
                0
            ) if len(balances) > 0 else 0

            for balance in balances:
                stats.append(AddressPortfolioStats(balance, total_usd))
        except Exception as error:
            print(error)
            print(traceback.format_exc())
        finally:
            return stats
