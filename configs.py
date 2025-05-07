# ---------------------------------- Extra ----------------------------------
SHUFFLE_WALLETS = True  # True/False Shuffle wallets before use

# --------------------------------- General ---------------------------------
MAX_RETRY_ATTEMPTS = 5  # Number of retry attempts for failed requests
RETRY_SLEEP_RANGE = (3, 9)  # (min, max) in seconds

# --------------------------------- Faucet ---------------------------------
FAUCET_CHAINS = ['EXPchain', 'Sepolia', 'BSC']
FAUCET_SLEEP_RANGE_BETWEEN_CHAINS = (30, 60)  # (min, max) in seconds
FAUCET_SLEEP_RANGE_BETWEEN_TOKENS = (10, 30)  # (min, max) in seconds

# --------------------------------- Bridge ---------------------------------
BRIDGE_CHAINS = ['Sepolia', 'BSC']
DEST_CHAIN = 'EXPchain'
BRIDGE_SLEEP_RANGE_BETWEEN_CHAINS = (10, 30)  # (min, max) in seconds
RANDOM_PERCENTAGE_BRIDGE = (10, 35)  # (min, max) in percentage

# --------------------------------- Swap ---------------------------------
SWAP_TOKENS = {
    "tZKJ": "0x0000000000000000000000000000000000000000",
    "crvUSD": "0xf00436c8142E29cAd81a6F1F9Ec7d5e17DCfa5d9",
    "ETH": "0xa966BDF2e0088eb921A39d6ff684b60388Fc277e",
    "USDT": "0xf4e77b64cFac6B5e4F5B958dBE2558F8b342aC8D",
    "USDC": "0x09BE71c8Ff0594F051aa1953671420057634a83D",
    "WZKJ": "0xAfF9b70ea121071Deb9540e3675486b3A465e223"
}
SWAP_SLEEP_RANGE_BETWEEN = (10, 30)  # (min, max) in seconds
RANDOM_PERCENTAGE_SWAP = (10, 35)  # (min, max) in percentage

# -------------------------- Route --------------------------
ROUTE_TASK = [
    'faucet',
    'bridge_sepolia',
    'bridge_bsc',
    'swap',
]

"""
Modules for route generation:
    - faucet                   Requesting tokens from the faucet
    - bridge_sepolia           Bridging tokens to Sepolia
    - bridge_bsc               Bridging tokens to BSC
    - swap                     Swapping tokensы
"""