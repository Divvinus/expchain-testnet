import random
from abc import ABC, abstractmethod
from typing import Self

from src.wallet import Wallet
from src.logger import AsyncLogger
from src.models import Account, BridgeSepoliaContract, BridgeBscContract, CHAINS
from src.utils import show_trx_log, random_sleep
from bot_loader import config
from configs import (
    RANDOM_PERCENTAGE_BRIDGE, 
    DEST_CHAIN,
    MAX_RETRY_ATTEMPTS,
    RETRY_SLEEP_RANGE
)


class BaseBridgeModule(AsyncLogger, Wallet, ABC):
    def __init__(self, account: Account, rpc_url: str) -> None:
        Wallet.__init__(self, account.keypair, rpc_url, account.proxy)
        AsyncLogger.__init__(self)
        
    async def __aenter__(self) -> Self:
        await Wallet.__aenter__(self)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await Wallet.__aexit__(self, exc_type, exc_val, exc_tb)

    @property
    @abstractmethod
    def source_chain(self) -> str:
        pass
    
    @property
    @abstractmethod
    def explorer_url(self) -> str:
        pass
    
    @abstractmethod
    async def get_bridge_contract(self):
        pass

    async def calculate_amount(
        self, token_address: str, token_name: str, source_chain: str
    ) -> tuple[bool, str | int]:   
        await self.logger_msg(
            msg=f"Calculating the number of tokens for bridge",
            type_msg="info", address=self.wallet_address
        )
        
        if not await self.check_balance():
            return False, "Insufficient native balance"
        
        balance = await self.token_balance(token_address)
        if balance <= 0:
            return False, f"Not enough tokens {token_name} on the chain {source_chain}"
        
        random_percentage = random.uniform(*RANDOM_PERCENTAGE_BRIDGE)
        amount = int(balance * (random_percentage / 100))
        return True, amount

    async def _analyze_transaction_error(self, error: Exception) -> str:
        """Analyze transaction error and return more informative message."""
        error_str = str(error)
        
        if "{'code': -32002" in error_str and "timed out" in error_str:
            return "Network timeout: RPC node may be overloaded or unavailable"
        
        if "insufficient funds for gas" in error_str:
            return f"High gas in the network {self.source_chain}. Please top up the address with tokens or wait for the gas to decrease in the network."
        
        if "execution reverted" in error_str:
            return f"Transaction execution reverted by the blockchain"
        
        if "cannot estimate gas" in error_str.lower():
            return "Cannot estimate gas: transaction may fail or require more gas"
        
        return str(error)

    async def bridge_from_chain(
        self, token_name: str
    ) -> tuple[bool, str]:
        
        bridge_contract = await self.get_bridge_contract()
        token_address = CHAINS[self.source_chain].tokens.get(token_name)
        if not token_address:
            return False, f"Token {token_name} not found on the chain {self.source_chain}"
        
        try:
            status, amount_to_bridge = await self.calculate_amount(token_address, token_name, self.source_chain)
            if not status:
                return False, amount_to_bridge
            
            await self.logger_msg(
                msg=f"Attempting to approve the token", type_msg="info", address=self.wallet_address
            )

            approved, approve_result = await self._check_and_approve_token(
                token_address,
                bridge_contract.address,
                amount_to_bridge
            )
            if not approved:
                return False, f"Failed to approve token: {approve_result}"
            
            await self.logger_msg(
                msg=f"Token successfully approved for bridge",
                type_msg="success", address=self.wallet_address
            )
            
            tx_params = await self.build_transaction_params(
                bridge_contract.functions.transferToken(
                    131, 
                    1, 
                    amount_to_bridge, 
                    self.wallet_address
                ),
                value=self.to_wei(0.002, 'ether')
            )

            status, result = await self._process_transaction(tx_params)
            if status:
                await show_trx_log(
                    self.wallet_address,
                    f"Transferred {self.from_wei(amount_to_bridge, 'ether')} {token_name} from {self.source_chain} to {DEST_CHAIN}",
                    status, self.explorer_url, result
                )
                return True, result
            
            if result.startswith("PENDING:"):
                tx_hash = result[8:]
                return False, f"Transaction is pending (timeout). Hash: {tx_hash}"
            
            return False, result

        except Exception as e:
            return False, await self._analyze_transaction_error(e)

    async def run(self) -> tuple[bool, str]:
        for attempt in range(MAX_RETRY_ATTEMPTS): 
            await self.logger_msg(
                msg=f"Start bridge | Attempt {attempt + 1}",
                type_msg="info",
                address=self.wallet_address
            )        
        
            status, result = await self.bridge_from_chain("tZKJ")
            if status:
                return True, result
            
            if any(msg in result for msg in ["Insufficient native balance", "High gas in the network", "Not enough tokens"]):
                await self.logger_msg(
                    msg=f"Operation canceled: {result}", 
                    type_msg="warning",
                    address=self.wallet_address
                )
                return False, result
            
            if "timed out" in result or "request timed out" in result:
                await self.logger_msg(
                    msg=f"Network timeout detected: RPC node may be overloaded or unavailable. Try again later or use a different RPC endpoint.", 
                    type_msg="warning",
                    address=self.wallet_address
                )
                
                if attempt == MAX_RETRY_ATTEMPTS - 1:
                    return False, "Network timeout: RPC node overloaded or unavailable"
                
                await self.logger_msg(
                    msg=f"Waiting longer before retry due to network issues...", 
                    type_msg="info",
                    address=self.wallet_address
                )
                await random_sleep(self.wallet_address, *[r*2 for r in RETRY_SLEEP_RANGE])
                continue
            
            await self.logger_msg(
                msg=f"Bridge from {self.source_chain} failed | Error: {result}", type_msg="error",
                address=self.wallet_address, method_name="run"
            )
            
            await random_sleep(self.wallet_address, *RETRY_SLEEP_RANGE)
            
        return False, result


class BridgeSepoliaModule(BaseBridgeModule):
    def __init__(self, account: Account) -> None:
        super().__init__(account, config.sepolia_rpc)
    
    @property
    def source_chain(self) -> str:
        return 'Sepolia'
    
    @property
    def explorer_url(self) -> str:
        return config.sepolia_explorer
    
    async def get_bridge_contract(self):
        return await self.get_contract(BridgeSepoliaContract())


class BridgeBscModule(BaseBridgeModule):
    def __init__(self, account: Account) -> None:
        super().__init__(account, config.bsc_rpc)
    
    @property
    def source_chain(self) -> str:
        return 'BSC'
    
    @property
    def explorer_url(self) -> str:
        return config.bsc_explorer
    
    async def get_bridge_contract(self):
        return await self.get_contract(BridgeBscContract())