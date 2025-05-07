from typing import Self

from src.api import BaseAPIClient, DiscordClient
from src.wallet import Wallet
from src.logger import AsyncLogger
from src.models import Account, CHAINS
from src.utils import random_sleep
from configs import (
    FAUCET_CHAINS,
    FAUCET_SLEEP_RANGE_BETWEEN_CHAINS,
    FAUCET_SLEEP_RANGE_BETWEEN_TOKENS,
    MAX_RETRY_ATTEMPTS,
    RETRY_SLEEP_RANGE
)


class FaucetModule(Wallet):
    logger = AsyncLogger()
    
    _HEADERS = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'origin': 'https://faucet.expchain.ai',
        'referer': 'https://faucet.expchain.ai/',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site'
    }
    
    def __init__(self, account: Account) -> None:
        Wallet.__init__(self, account.keypair, account.proxy)
        self.account = account
        self.api_client: BaseAPIClient | None = None
        self.headers = self._HEADERS.copy()

    async def __aenter__(self) -> Self:
        await Wallet.__aenter__(self)
        self.api_client = BaseAPIClient(
            base_url="https://faucet-api.expchain.ai",
            proxy=self.account.proxy
        )
        await self.api_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'api_client') and self.api_client:
            await self.api_client.__aexit__(exc_type, exc_val, exc_tb)
        await Wallet.__aexit__(self, exc_type, exc_val, exc_tb)
        
    async def request_faucet(self, chain_name: str, bearer_token: str, token_index: int = 0) -> tuple[bool, dict]:
        chain_config = CHAINS.get(chain_name)
        if not chain_config:
            raise ValueError(f"Unknown chain: {chain_name}")

        try:
            self.headers['authorization'] = f'Bearer {bearer_token}'
            
            json_data = {
                'token': token_index,
                'chain_id': chain_config.id,
                'to': self.wallet_address,
            }
            
            response = await self.api_client.send_request(
                request_type="POST",
                method="/api/faucet",
                json_data=json_data,
                headers=self.headers,
            )
            
            response_data = response.get("data")
            
            if response_data and response_data.get("message") == "Success":
                return True, response_data.get("data")
            else:
                return False, response_data
            
        except Exception as e:
            await self.logger.logger_msg(
                f"Error getting faucet token: {e}", type_msg="error",
                account_name=self.wallet_address, method_name="request_faucet"
            )
            return False, {"error": str(e)}        
    
    async def run(self) -> tuple[bool, str]:
        await self.logger.logger_msg(
            f"Processing request for faucet", type_msg="info",
            account_name=self.wallet_address
        )
        
        async with DiscordClient(self.account) as client:
            try:
                await self.logger.logger_msg(
                    f"Getting bearer token", type_msg="info",
                    account_name=self.wallet_address
                )
                bearer_token = await client.get_bearer_token()
                if not bearer_token:
                    return False, "Failed to get bearer token"
                
                await self.logger.logger_msg(
                    f"Bearer token received", type_msg="success",
                    account_name=self.wallet_address
                )
                
                for chain_name in FAUCET_CHAINS:
                    chain_config = CHAINS.get(chain_name)
                    token_names = list(chain_config.tokens.keys())
                    
                    for token_index, token_name in enumerate(token_names):
                        for attempt in range(MAX_RETRY_ATTEMPTS):
                            try:
                                token_info = f" ${token_name}" if len(token_names) > 1 else ""
                                await self.logger.logger_msg(
                                    f"Requesting faucet for {chain_name}{token_info} | Attempt {attempt + 1}",
                                    type_msg="info", account_name=self.wallet_address
                                )
                                success, response_data = await self.request_faucet(chain_name, bearer_token, token_index)
                                
                                if not success and isinstance(response_data, dict) and response_data.get('code') == 2004:
                                    token_label = f" {token_name}" if len(token_names) > 1 else ""
                                    await self.logger.logger_msg(
                                        f"You have already requested test token{token_label} today | {response_data.get('data')}", 
                                        type_msg="warning",
                                        account_name=self.wallet_address
                                    )
                                    break
                                
                                if success:
                                    token_label = f" ${token_name}" if len(token_names) > 1 else ""
                                    await self.logger.logger_msg(
                                        f"Successfully requested token{token_label} for {chain_name}", 
                                        type_msg="success",
                                        account_name=self.wallet_address
                                    )
                                else:
                                    token_label = f" ${token_name}" if len(token_names) > 1 else ""
                                    await self.logger.logger_msg(
                                        f"Failed to request token{token_label} for {chain_name}: {response_data}", 
                                        type_msg="warning",
                                        account_name=self.wallet_address
                                    )
                                break
                            
                            except Exception as e:
                                token_info = f" ${token_name}" if len(token_names) > 1 else ""
                                await self.logger.logger_msg(
                                    f"Error on {chain_name}{token_info}: {str(e)}", 
                                    type_msg="error",
                                    account_name=self.wallet_address, 
                                    method_name="process_wallet"
                                )
                                await random_sleep(self.wallet_address, *RETRY_SLEEP_RANGE)
                        
                        if token_index < len(token_names) - 1:
                            await random_sleep(self.wallet_address, *FAUCET_SLEEP_RANGE_BETWEEN_TOKENS)
                    
                    if chain_name != FAUCET_CHAINS[-1]:
                        await random_sleep(self.wallet_address, *FAUCET_SLEEP_RANGE_BETWEEN_CHAINS)
                        
                return True, "Success"
            
            except Exception as e:
                await self.logger.logger_msg(
                    f"Error processing wallet: {e}", type_msg="error",
                    account_name=self.wallet_address, method_name="process_wallet"
                )
                return False, str(e)