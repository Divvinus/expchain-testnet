from src.tasks import *
from src.models import Account


class EXPchainBot:
    @staticmethod
    async def process_faucet(account: Account) -> tuple[bool, str]:
        async with FaucetModule(account) as faucet:
            return await faucet.run()

    @staticmethod
    async def process_bridge_sepolia(account: Account) -> tuple[bool, str]:
        async with BridgeSepoliaModule(account) as bridge:
            return await bridge.run()

    @staticmethod
    async def process_bridge_bsc(account: Account) -> tuple[bool, str]:
        async with BridgeBscModule(account) as bridge:
            return await bridge.run()

    @staticmethod
    async def process_swap(account: Account) -> tuple[bool, str]:
        async with SwapModule(account) as swap:
            return await swap.run()
        
    @staticmethod
    async def process_buy_sepolia(account: Account) -> tuple[bool, str]:
        async with BuySepoliaModule(account) as buy_sepolia:
            return await buy_sepolia.run_buy_sepolia()