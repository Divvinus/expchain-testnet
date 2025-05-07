from dataclasses import dataclass, field

@dataclass
class ChainConfig:
    name: str
    id: int
    name_native_token: str
    tokens: dict[str, str] = field(default_factory=dict)

CHAINS: dict[str, ChainConfig] = {
    'EXPchain': ChainConfig(
        name='EXPchain',
        id=18880,
        name_native_token='tZKJ',
        tokens={
            "tZKJ": "0x0000000000000000000000000000000000000000",
            "crvUSD": "0xf00436c8142E29cAd81a6F1F9Ec7d5e17DCfa5d9",
            "ETH": "0xa966BDF2e0088eb921A39d6ff684b60388Fc277e",
            "USDT": "0xf4e77b64cFac6B5e4F5B958dBE2558F8b342aC8D",
            "USDC": "0x09BE71c8Ff0594F051aa1953671420057634a83D",
        }
    ),
    'Sepolia': ChainConfig(
        name='Sepolia',
        id=11155111,
        name_native_token='ETH',
        tokens={
            "tZKJ": "0x465C15e9e2F3837472B0B204e955c5205270CA9E"
        }
    ),
    'BSC': ChainConfig(
        name='BSC',
        id=97,
        name_native_token='BNB',
        tokens={
            "tZKJ": "0xbBF8F565995c3fDF890120e6AbC48c4f818b03c2"
        }
    )
}