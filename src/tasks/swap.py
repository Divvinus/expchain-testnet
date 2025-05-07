import random

from typing import Self

from src.wallet import Wallet
from src.logger import AsyncLogger
from src.models import Account, SwapContract
from src.utils import show_trx_log, random_sleep
from bot_loader import config
from configs import (
    MAX_RETRY_ATTEMPTS,
    RETRY_SLEEP_RANGE,
    SWAP_TOKENS,
    SWAP_SLEEP_RANGE_BETWEEN,
    RANDOM_PERCENTAGE_SWAP
)

class SwapModule(AsyncLogger, Wallet):
    def __init__(self, account: Account) -> None:
        Wallet.__init__(self, account.keypair, config.expchain_rpc, account.proxy)
        AsyncLogger.__init__(self)
        self.tokens_dict = {}
        
    async def __aenter__(self) -> Self:
        await Wallet.__aenter__(self)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await Wallet.__aexit__(self, exc_type, exc_val, exc_tb)
        
    async def token_filtering(self) -> dict:
        await self.logger_msg(
            msg=f"Filtering tokens",
            type_msg="info", address=self.wallet_address
        )
        tokens_dict = {}
        for token_name, token_address in SWAP_TOKENS.items():
            if token_name == "tZKJ":
                balance = await self.eth.get_balance(self.wallet_address)
                if balance > 0:
                    tokens_dict[token_name] = balance
            else:
                balance = await self.token_balance(token_address)
                if balance > 0:
                    tokens_dict[token_name] = balance
        return tokens_dict
    
    async def calculate_amount(
        self,
        token_name: str
    ) -> tuple[bool, str | int]:   
        await self.logger_msg(
            msg=f"Calculating the number of tokens for swap",
            type_msg="info", address=self.wallet_address
        )
        
        if "tZKJ" not in self.tokens_dict or self.tokens_dict["tZKJ"] <= 0:
            return False, "Insufficient native balance"
        
        balance = self.tokens_dict.get(token_name, 0)
        if balance <= 0:
            return False, f"Not enough tokens {token_name}"
        
        random_percentage = random.uniform(*RANDOM_PERCENTAGE_SWAP)
        amount = int(balance * (random_percentage / 100))
        return True, amount
    
    def get_swap_params(
        self, 
        source_token: str, 
        destination_token: str
    ) -> tuple[list[str], list[list[str]]] | tuple[bool, str]:
        if source_token == "tZKJ" and destination_token == "WZKJ":
            route = [
                "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                "0xAfF9b70ea121071Deb9540e3675486b3A465e223",
                "0xAfF9b70ea121071Deb9540e3675486b3A465e223",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params = [
                [
                    0,
                    0,
                    8,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
            
        elif source_token == "tZKJ" and destination_token == "crvUSD":
            route = [
                "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                "0xAfF9b70ea121071Deb9540e3675486b3A465e223",
                "0xAfF9b70ea121071Deb9540e3675486b3A465e223",
                "0xb0E352504C342d046aD3822bFca9d09D13F35C94",
                "0xf00436c8142E29cAd81a6F1F9Ec7d5e17DCfa5d9",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params =  [
                [
                    0,
                    0,
                    8,
                    0
                ],
                [
                    0,
                    3,
                    1,
                    10
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
        
        elif source_token == "tZKJ" and destination_token == "ETH":
            route = [
                "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                "0xAfF9b70ea121071Deb9540e3675486b3A465e223",
                "0xAfF9b70ea121071Deb9540e3675486b3A465e223",
                "0xcC40150B09Efc12dB2fbd17640340a90B25D5FFc",
                "0xa966BDF2e0088eb921A39d6ff684b60388Fc277e",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params = [
                [
                    0,
                    0,
                    8,
                    0
                ],
                [
                    0,
                    1,
                    1,
                    10
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
        
        elif source_token == "tZKJ" and destination_token == "USDT":
            route = [
                "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                "0xAfF9b70ea121071Deb9540e3675486b3A465e223",
                "0xAfF9b70ea121071Deb9540e3675486b3A465e223",
                "0x5c19dDC491F425276e7E09cb30BEd0D024Fba252",
                "0xf4e77b64cFac6B5e4F5B958dBE2558F8b342aC8D",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params = [
                [
                    0,
                    0,
                    8,
                    0
                ],
                [
                    1,
                    0,
                    1,
                    10
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
        
        elif source_token == "tZKJ" and destination_token == "USDC":
            route = [
                "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
                "0xAfF9b70ea121071Deb9540e3675486b3A465e223",
                "0xAfF9b70ea121071Deb9540e3675486b3A465e223",
                "0xAa404332D331a2EdA21BD8C18303643Fb89398B2",
                "0x09BE71c8Ff0594F051aa1953671420057634a83D",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params = [
                [
                    0,
                    0,
                    8,
                    0
                ],
                [
                    2,
                    1,
                    1,
                    10
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
        
        elif source_token == "WZKJ" and destination_token == "crvUSD":
            route = [
                "0xAfF9b70ea121071Deb9540e3675486b3A465e223",
                "0xb0E352504C342d046aD3822bFca9d09D13F35C94",
                "0xf00436c8142E29cAd81a6F1F9Ec7d5e17DCfa5d9",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params = [
                [
                    0,
                    3,
                    1,
                    10
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
        
        elif source_token == "WZKJ" and destination_token == "ETH":
            route = [
                "0xAfF9b70ea121071Deb9540e3675486b3A465e223",
                "0xcC40150B09Efc12dB2fbd17640340a90B25D5FFc",
                "0xa966BDF2e0088eb921A39d6ff684b60388Fc277e",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params = [
                [
                    0,
                    1,
                    1,
                    10
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
        
        elif source_token == "WZKJ" and destination_token == "USDT":
            route = [
                "0xAfF9b70ea121071Deb9540e3675486b3A465e223",
                "0x5c19dDC491F425276e7E09cb30BEd0D024Fba252",
                "0xf4e77b64cFac6B5e4F5B958dBE2558F8b342aC8D",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params = [
                [
                    1,
                    0,
                    1,
                    10
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
        
        elif source_token == "WZKJ" and destination_token == "USDC":
            route = [
                "0xAfF9b70ea121071Deb9540e3675486b3A465e223",
                "0xAa404332D331a2EdA21BD8C18303643Fb89398B2",
                "0x09BE71c8Ff0594F051aa1953671420057634a83D",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params = [
                [
                    2,
                    1,
                    1,
                    10
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
        
        elif source_token == "crvUSD" and destination_token == "ETH":
            route = [
                "0xf00436c8142E29cAd81a6F1F9Ec7d5e17DCfa5d9",
                "0x4B36884081748D3E9dA190922C25115a51D4850E",
                "0xa966BDF2e0088eb921A39d6ff684b60388Fc277e",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params = [
                [
                    1,
                    0,
                    1,
                    10
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
        
        elif source_token == "crvUSD" and destination_token == "USDT":
            route = [
                "0xf00436c8142E29cAd81a6F1F9Ec7d5e17DCfa5d9",
                "0x999FCd2B15B5DC9F800830bE464306431d0Da121",
                "0xf4e77b64cFac6B5e4F5B958dBE2558F8b342aC8D",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params = [
                [
                    1,
                    0,
                    1,
                    10
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
        
        elif source_token == "crvUSD" and destination_token == "USDC":
            route = [
                "0xf00436c8142E29cAd81a6F1F9Ec7d5e17DCfa5d9",
                "0x2dB7309d2C6a2883B50997f231a3d314098d8c6D",
                "0x09BE71c8Ff0594F051aa1953671420057634a83D",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params = [
                [
                    1,
                    2,
                    1,
                    10
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
        
        elif source_token == "ETH" and destination_token == "USDT":
            route = [
                "0xa966BDF2e0088eb921A39d6ff684b60388Fc277e",
                "0xEfd75011ea84410cBbAA9F64768523dd9A3c0012",
                "0xf4e77b64cFac6B5e4F5B958dBE2558F8b342aC8D",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params = [
                [
                    1,
                    0,
                    1,
                    10
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
        
        elif source_token == "ETH" and destination_token == "USDC":
            route = [
                "0xa966BDF2e0088eb921A39d6ff684b60388Fc277e",
                "0x081FE366E47388684ff1F6D3d89501a5Acd1E9c2",
                "0x09BE71c8Ff0594F051aa1953671420057634a83D",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params = [
                [
                    0,
                    1,
                    1,
                    10
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
        
        elif source_token == "USDT" and destination_token == "USDC":
            route = [
                "0xf4e77b64cFac6B5e4F5B958dBE2558F8b342aC8D",
                "0x55841C66D0960020f2A2A921573fcF4b1e18bf48",
                "0x09BE71c8Ff0594F051aa1953671420057634a83D",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000"
            ]
            swap_params = [
                [
                    0,
                    1,
                    1,
                    10
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ],
                [
                    0,
                    0,
                    0,
                    0
                ]
            ]
        
        else:
            return False, "Invalid swap pair"
        
        return route, swap_params
            
    async def swap_tokens(self, source_token: str, destination_token: str, reversed_attempt: bool = False) -> tuple[bool, str]:
        token_source_address = SWAP_TOKENS.get(source_token)
        swap_contract = await self.get_contract(SwapContract())
        
        status, amount_to_swap = await self.calculate_amount(source_token)
        if not status:
            return False, amount_to_swap
            
        if source_token != "tZKJ":
            await self.logger_msg(
                msg=f"Attempting to approve the token", type_msg="info", address=self.wallet_address
            )
            
            try:
                status, approve_result = await self._check_and_approve_token(
                    token_source_address,
                    swap_contract.address,
                    amount_to_swap
                )
                if not status:
                    if any(gas_error in approve_result for gas_error in [
                        "Failed to estimate gas", 
                        "gas required exceeds allowance",
                        "insufficient funds for gas",
                        "insufficient funds for gas * price + value"
                    ]):
                        error_msg = f"High gas in the network. Top up the address with tokens or wait for the gas to decrease in the network."
                        return False, error_msg
                    return False, approve_result
            except Exception as e:
                error_str = str(e)
                if any(gas_error in error_str for gas_error in [
                    "Failed to estimate gas", 
                    "gas required exceeds allowance",
                    "insufficient funds for gas",
                    "insufficient funds for gas * price + value"
                ]):
                    error_msg = f"High gas in the network. Top up the address with tokens or wait for the gas to decrease in the network."
                    return False, error_msg
                return False, str(e)
            
            await self.logger_msg(
                msg=f"Token successfully approved for swap",
                type_msg="success", address=self.wallet_address
            )
            
        result = self.get_swap_params(source_token, destination_token)
        
        if isinstance(result[0], bool) and not result[0]:
            if result[1] == "Invalid swap pair" and not reversed_attempt:
                await self.logger_msg(
                    msg=f"No data for the pair {source_token} to {destination_token}, trying to swap tokens",
                    type_msg="info", address=self.wallet_address
                )
                return await self.swap_tokens(destination_token, source_token, reversed_attempt=True)
            return False, result[1]
        
        route, swap_params = result
        
        try:
            min_dy = await swap_contract.functions.get_dy(route, swap_params, amount_to_swap).call()
            
            tx_params = await self.build_transaction_params(
                swap_contract.functions.exchange(
                    route, 
                    swap_params, 
                    amount_to_swap, 
                    min_dy
                ),
                gas=250_000,
                gas_price=40000000000,
                value=amount_to_swap if source_token == "tZKJ" else 0                
            )
            
            return await self._process_transaction(tx_params)
                
        except Exception as e:
            error_str = str(e)
            if any(gas_error in error_str for gas_error in [
                "Failed to estimate gas", 
                "gas required exceeds allowance",
                "insufficient funds for gas",
                "insufficient funds for gas * price + value"
            ]):
                error_msg = f"High gas in the network. Top up the address with tokens or wait for the gas to decrease in the network."
                return False, error_msg
            return False, str(e)
            
    async def run(self) -> tuple[bool, str]:
        await self.logger_msg(
            msg="Start swap",
            type_msg="info",
            address=self.wallet_address
        )
        
        self.tokens_dict: dict[str, any] = await self.token_filtering()
        if not self.tokens_dict or len(self.tokens_dict) < 2:
            await self.logger_msg(
                msg="Insufficient tokens to swap",
                type_msg="warning",
                address=self.wallet_address,
                method_name="run"
            )
            return False, "Insufficient tokens to swap"
        
        token_names: list[str] = list(self.tokens_dict.keys())
        already_swapped_pairs: set[str] = set()
        successful_swaps: int = 0
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            await self.logger_msg(
                msg=f"Attempt {attempt + 1} of {MAX_RETRY_ATTEMPTS}",
                type_msg="info",
                address=self.wallet_address
            )
            
            if len(already_swapped_pairs) >= len(token_names) * (len(token_names) - 1) // 2:
                break
            
            token1, token2 = self._get_unique_pair(token_names, already_swapped_pairs)
            if token1 is None or token2 is None:
                break
            
            pair_key = self._get_pair_key(token1, token2)
            already_swapped_pairs.add(pair_key)
            
            try:
                await self.logger_msg(
                    msg=f"Attempting to swap {token1} to {token2}",
                    type_msg="info",
                    address=self.wallet_address
                )
                
                status, result = await self.swap_tokens(token1, token2)
                
                if (result == "Insufficient native balance" or 
                    "gas in the network" in result or 
                    "High gas in the network" in result or
                    "Not enough tokens" in result):
                    await self.logger_msg(
                        msg=f"Operation canceled: {result}", 
                        type_msg="warning",
                        address=self.wallet_address
                    )
                    return False, result
                
                await show_trx_log(
                    address=self.wallet_address,
                    trx_type=f"Swap {token1} to {token2}",
                    status=status,
                    explorer=config.expchain_explorer,
                    result=result
                )
                
                if status:
                    await self.logger_msg(
                        msg=f"Swap {token1} to {token2} successful",
                        type_msg="success",
                        address=self.wallet_address
                    )
                    successful_swaps += 1   
                else:
                    await self.logger_msg(
                        msg=f"Swap {token1} to {token2} failed",
                        type_msg="error",
                        address=self.wallet_address
                    )
                
                await random_sleep(self.wallet_address, *SWAP_SLEEP_RANGE_BETWEEN)
            
            except Exception:
                await random_sleep(self.wallet_address, *RETRY_SLEEP_RANGE)
        
        if successful_swaps > 0:
            await self.logger_msg(
                msg=f"Swap module completed: {successful_swaps} successful swaps",
                type_msg="success",
                address=self.wallet_address
            )
            return True, f"Completed {successful_swaps} successful swaps"
        else:
            await self.logger_msg(
                msg="Swap module completed without successful swaps",
                type_msg="warning",
                address=self.wallet_address
            )
            return False, "No successful swaps"

    def _get_unique_pair(self, token_names: list[str], already_swapped_pairs: set[str]) -> tuple[str, str]:
        max_attempts = len(token_names) * (len(token_names) - 1) // 2
        for _ in range(max_attempts):
            token1, token2 = random.sample(token_names, 2)
            pair_key = self._get_pair_key(token1, token2)
            if pair_key not in already_swapped_pairs:
                return token1, token2
        return None, None

    def _get_pair_key(self, token1: str, token2: str) -> str:
        return f"{token1}_{token2}" if token1 < token2 else f"{token2}_{token1}"