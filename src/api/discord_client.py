from typing import Self
from urllib.parse import parse_qs, urlparse

from aiohttp import ClientSession, ClientTimeout, ClientError

from src.exceptions.discord_exceptions import (
    DiscordClientError, DiscordAuthError, DiscordInvalidTokenError, 
    DiscordNetworkError
)
from src.models import Account
from src.utils import clean_bad_auth_tokens_discord


class DiscordClient:
    _HEADERS_BASE = {
        'authority': 'discord.com',
        'accept': '*/*',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'origin': 'https://discord.com',
        'referer': 'https://discord.com/oauth2/authorize?client_id=1324639318278406267&redirect_uri=https%3A%2F%2Ffaucet-api.expchain.ai%2Fapi%2Fv1%2Fdiscord%2Fcallback&response_type=code&scope=identify+email',
        'x-super-properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6InJ1IiwiaGFzX2NsaWVudF9tb2RzIjpmYWxzZSwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyOS4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTI5LjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjM5MjQzMSwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0=',
    }
    
    _OAUTH_PARAMS = {
        'client_id': '1324639318278406267',
        'response_type': 'code',
        'redirect_uri': 'https://faucet-api.expchain.ai/api/v1/discord/callback',
        'scope': 'identify email',
    }
    
    _JSON_DATA = {
        'permissions': '0',
        'authorize': True,
        'integration_type': 0,
        'location_context': {
            'guild_id': '10000',
            'channel_id': '10000',
            'channel_type': 10000,
        },
    }

    def __init__(self, account: Account):
        if not account.auth_tokens_discord:
            raise DiscordClientError("Discord token not provided")
        
        self.auth_tokens_discord = account.auth_tokens_discord
        self.proxy = account.proxy.as_url if account.proxy else None
        self.session = None

        self._headers = self._HEADERS_BASE.copy()
        self._headers['authorization'] = self.auth_tokens_discord

    async def __aenter__(self) -> Self:
        self.session = ClientSession(
            timeout=ClientTimeout(total=15),
            trust_env=True,
            proxy=self.proxy
        )
        return self

    async def __aexit__(self, *_) -> None:
        await self.session.close()

    async def get_bearer_token(self) -> str:
        try:
            async with self.session.post(
                url="https://discord.com/api/v9/oauth2/authorize",
                params=self._OAUTH_PARAMS,
                json=self._JSON_DATA,
                headers=self._headers,
                allow_redirects=False
            ) as resp:
                if resp.status in (401, 403):
                    await clean_bad_auth_tokens_discord(self.auth_tokens_discord)
                    raise DiscordInvalidTokenError("Invalid Discord token")
                
                data = await resp.json()
                auth_code = parse_qs(urlparse(data['location']).query)['code'][0]

            async with self.session.get(
                url="https://faucet-api.expchain.ai/api/v1/discord/callback",
                params={'code': auth_code},
                headers={'Referer': 'https://discord.com/'},
                allow_redirects=False
            ) as resp:
                if resp.status != 302:
                    raise DiscordAuthError("Faucet auth failed")

                location = resp.headers['Location']
                bearer_token = parse_qs(urlparse(location).query)['msg'][0].split('/')[1]
                return bearer_token

        except KeyError as e:
            raise DiscordAuthError(f"Missing key in response: {str(e)}")
        except ClientError as e:
            raise DiscordNetworkError(f"Network error: {str(e)}")
        except Exception as e:
            raise DiscordClientError(f"Unexpected error: {str(e)}")