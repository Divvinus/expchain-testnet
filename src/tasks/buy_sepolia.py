import aiohttp

from eth_abi import encode, decode
from typing import Self, Tuple

from src.wallet import Wallet
from src.logger import AsyncLogger
from src.models import Account, TestnetBridgeContract
from src.utils import show_trx_log, random_sleep
from bot_loader import config
from configs import (
    MAX_RETRY_ATTEMPTS,
    RETRY_SLEEP_RANGE,
    AMOUNT_SWAP_ETH_TO_SEPOLIA
)

class BuySepoliaModule(AsyncLogger, Wallet):
    def __init__(self, account: Account) -> None:
        Wallet.__init__(self, account.keypair, config.arbitrum_rpc, account.proxy)
        AsyncLogger.__init__(self)
        
    async def __aenter__(self) -> Self:
        await Wallet.__aenter__(self)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await Wallet.__aexit__(self, exc_type, exc_val, exc_tb)
        
    async def make_rpc_call(self, payload):
        async with aiohttp.ClientSession() as session:
            async with session.post("https://ethereum.publicnode.com/", json=payload) as response:
                return await response.json()
        
    async def get_swap_quote(self, amount_in_wei: int) -> int:
        weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        oft_address = "0xE71bDfE1Df69284f00EE185cf0d95d0c7680c0d4"
        
        try:
            encoded_params = encode(
                ['address', 'address', 'uint256', 'uint24', 'uint160'],
                [
                    weth_address,
                    oft_address,
                    amount_in_wei,
                    3000,
                    0
                ]
            ).hex()
            payload = [{
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{
                    "to": "0x61fFE014bA17989E743c5F6cB21bF9697530B21e",
                    "data": "0xc6a5026a" + encoded_params
                }, "latest"],
                "id": 1
            }]

            response = await self.make_rpc_call(payload)
            
            if not response or 'error' in response[0]:
                error_msg = response[0]['error']['message'] if response else 'Empty RPC response'
                raise ValueError(f"RPC Error: {error_msg}")

            result_hex = response[0]['result']
            
            result_bytes = bytes.fromhex(result_hex[2:])
            decoded = decode(
                ['uint256', 'uint160', 'uint32', 'uint32'],
                result_bytes
            )
            return decoded[0]

        except Exception as e:
            raise ValueError(f"Quote failed: {str(e)}") from e

    async def run_buy_sepolia(self) -> Tuple[bool, str]:
        await self.logger_msg(f"Buy $tETH for the amount: {AMOUNT_SWAP_ETH_TO_SEPOLIA} $ETH", "info", self.wallet_address)
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            await self.logger_msg(f"Attempt {attempt + 1} for {MAX_RETRY_ATTEMPTS}", "info", self.wallet_address)
            
            if AMOUNT_SWAP_ETH_TO_SEPOLIA <= 0:
                error_msg = "AMOUNT_SWAP_ETH_TO_SEPOLIA config setting is not valid, please fix the config and retry again"
                await self.logger_msg(error_msg, "error", self.wallet_address, method_name="run_buy_sepolia")
                return False, error_msg
            
            try:
                balance = await self.human_balance()
                if balance < AMOUNT_SWAP_ETH_TO_SEPOLIA:
                    error_msg = f"Not enough $ETH in the Arbitrum network to purchase $tETH. Required: {AMOUNT_SWAP_ETH_TO_SEPOLIA} $ETH. You have {balance} $ETH in your wallet"
                    await self.logger_msg(error_msg, "error", self.wallet_address, method_name="run_buy_sepolia")
                    return False, error_msg
                
                contract = await self.get_contract(TestnetBridgeContract())

                amount_in = self.to_wei(AMOUNT_SWAP_ETH_TO_SEPOLIA, "ether")
                amount_out = await self.get_swap_quote(amount_in)
                amount_out_min = int(amount_out * 0.98)
                
                tx_params = await self.build_transaction_params(
                    contract.functions.swapAndBridge(
                        amount_in, 
                        amount_out_min,
                        161, 
                        self.wallet_address,
                        self.wallet_address,
                        "0x0000000000000000000000000000000000000000",
                        b""
                    ),
                    value=amount_in + 5627000000000
                )

                status, result = await self._process_transaction(tx_params)
                
                await show_trx_log(self.wallet_address, "Buy $tETH", status, config.arbitrum_explorer, result)
                
                if status: return True, result
            
            except Exception as e:
                error_msg = f"Error Buy $tETH for the amount: {AMOUNT_SWAP_ETH_TO_SEPOLIA} $ETH: {str(e)}"
                await self.logger_msg(error_msg, "error", self.wallet_address, "run_buy_sepolia")
                
                if attempt == MAX_RETRY_ATTEMPTS - 1:
                    return False, error_msg                
                await random_sleep(self.wallet_address, *RETRY_SLEEP_RANGE)
                
        return False, f"Failed Buy $tETH for the amount: {AMOUNT_SWAP_ETH_TO_SEPOLIA} $ETH after {MAX_RETRY_ATTEMPTS} attempts"