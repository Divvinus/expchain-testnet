from typing import Self
from urllib.parse import parse_qs, urlparse

from curl_cffi.requests import AsyncSession
from curl_cffi import requests

from src.exceptions.discord_exceptions import (
    DiscordClientError, DiscordAuthError, DiscordInvalidTokenError, 
    DiscordNetworkError
)
from src.wallet import Wallet
from src.logger import AsyncLogger
from src.models import Account, CHAINS
from src.utils import random_sleep, clean_bad_auth_tokens_discord
from configs import (
    FAUCET_CHAINS,
    FAUCET_SLEEP_RANGE_BETWEEN_CHAINS,
    FAUCET_SLEEP_RANGE_BETWEEN_TOKENS,
    MAX_RETRY_ATTEMPTS,
    RETRY_SLEEP_RANGE
)


class FaucetModule(Wallet):
    logger = AsyncLogger()
    
    _DISCORD_HEADERS_BASE = {
        'authority': 'discord.com',
        'accept': '*/*',
        'accept-language': 'ru,en-US;q=0.9,en;q=0.8',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'dnt': '1',
        'origin': 'https://discord.com',
        'pragma': 'no-cache',
        'referer': 'https://discord.com/oauth2/authorize?client_id=1324639318278406267&redirect_uri=https%3A%2F%2Ffaucet-api.expchain.ai%2Fapi%2Fv1%2Fdiscord%2Fcallback&response_type=code&scope=identify+email',
        'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'x-debug-options': 'bugReporterEnabled',
        'x-discord-locale': 'ru',
        'x-discord-timezone': 'America/New_York',
        'x-super-properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6InJ1IiwiaGFzX2NsaWVudF9tb2RzIjpmYWxzZSwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyOS4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTI5LjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6Imh0dHBzOi8vZXhwY2hhaW4ucG9seWhlZHJhLm5ldHdvcmsvIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiZXhwY2hhaW4ucG9seWhlZHJhLm5ldHdvcmsiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjo0MDI0MDIsImNsaWVudF9ldmVudF9zb3VyY2UiOm51bGwsImNsaWVudF9sYXVuY2hfaWQiOiIxMzY3MDQ4ZC0wMjA1LTQxMGItOTE1MC0zMjgzZTFjNzllZTQiLCJjbGllbnRfaGVhcnRiZWF0X3Nlc3Npb25faWQiOiIzOGVjNDE3NC1hYTk3LTQxN2UtYmI2Ni05MDRjYWYyOTBmYzciLCJjbGllbnRfYXBwX3N0YXRlIjoiZm9jdXNlZCJ9',
    }
    
    _FAUCET_HEADERS = {
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
    
    _OAUTH_PARAMS = {
        'client_id': '1324639318278406267',
        'response_type': 'code',
        'redirect_uri': 'https://faucet-api.expchain.ai/api/v1/discord/callback',
        'scope': 'identify email',
    }
    
    _DISCORD_JSON_DATA = {
        'guild_id': '1209630079936630824',
        'permissions': '0',
        'authorize': True,
        'integration_type': 0,
        'location_context': {
            'guild_id': '10000',
            'channel_id': '10000',
            'channel_type': 10000,
        },
        'dm_settings': {
            'allow_mobile_push': False,
        },
    }
    
    def __init__(self, account: Account) -> None:
        if not account.auth_tokens_discord:
            raise DiscordClientError("Discord token not provided")
            
        Wallet.__init__(self, account.keypair, account.proxy)
        self.account = account
        self.session: AsyncSession | None = None
        
        self.discord_headers = self._DISCORD_HEADERS_BASE.copy()
        self.discord_headers['authorization'] = account.auth_tokens_discord
        
        self.faucet_headers = self._FAUCET_HEADERS.copy()

    async def __aenter__(self) -> Self:
        await Wallet.__aenter__(self)
        
        self.session = AsyncSession(
            impersonate="chrome110",
            timeout=15,
            proxies={'http': self.account.proxy.as_url, 'https': self.account.proxy.as_url} if self.account.proxy else None,
            verify=False
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        await Wallet.__aexit__(self, exc_type, exc_val, exc_tb)

    async def get_bearer_token(self) -> str:
        try:
            resp = await self.session.post(
                url="https://discord.com/api/v9/oauth2/authorize",
                params=self._OAUTH_PARAMS,
                json=self._DISCORD_JSON_DATA,
                headers=self.discord_headers,
                allow_redirects=False
            )
            
            if resp.status_code in (401, 403):
                await clean_bad_auth_tokens_discord(self.account.auth_tokens_discord)
                raise DiscordInvalidTokenError("Invalid Discord token")
            
            data = resp.json()
            auth_code = parse_qs(urlparse(data['location']).query)['code'][0]
            
            resp = await self.session.get(
                url="https://faucet-api.expchain.ai/api/v1/discord/callback",
                params={'code': auth_code},
                headers={'Referer': 'https://discord.com/'},
                allow_redirects=False
            )
            
            if resp.status_code != 302:
                raise DiscordAuthError("Faucet auth failed")

            location = resp.headers['Location']
            bearer_token = parse_qs(urlparse(location).query)['msg'][0].split('/')[1]
            return bearer_token

        except KeyError as e:
            raise DiscordAuthError(f"Missing key in response: {str(e)}")
        except requests.RequestsError as e:
            raise DiscordNetworkError(f"Network error: {str(e)}")
        except Exception as e:
            raise DiscordClientError(f"Unexpected error: {str(e)}")
        
    async def request_faucet(self, chain_name: str, bearer_token: str, token_index: int = 0) -> tuple[bool, dict]:
        chain_config = CHAINS.get(chain_name)
        if not chain_config:
            raise ValueError(f"Unknown chain: {chain_name}")

        try:
            self.faucet_headers['authorization'] = f'Bearer {bearer_token}'
            
            json_data = {
                'token': token_index,
                'chain_id': chain_config.id,
                'to': self.wallet_address,
            }
            
            response = await self.session.post(
                url="https://faucet-api.expchain.ai/api/faucet",
                json=json_data,
                headers=self.faucet_headers,
            )
            
            response_data = response.json()
            
            if response_data and response_data.get("message") == "Success":
                return True, response_data.get("data")
            else:
                return False, response_data
            
        except requests.RequestsError as e:
            await self.logger.logger_msg(
                f"Network error getting faucet token: {e}", type_msg="error",
                account_name=self.wallet_address, method_name="request_faucet"
            )
            return False, {"error": str(e)}
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
        
        try:
            await self.logger.logger_msg(
                f"Getting bearer token", type_msg="info",
                account_name=self.wallet_address
            )
            bearer_token = await self.get_bearer_token()
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