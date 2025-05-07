import asyncio
import random
from decimal import Decimal
from typing import Any, Union, Self

from better_proxy import Proxy
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_typing import ChecksumAddress, HexStr
from pydantic import HttpUrl
from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.contract import AsyncContract
from web3.eth import AsyncEth
from web3.types import Nonce, TxParams
from web3.middleware import ExtraDataToPOAMiddleware

from src.exceptions.custom_exceptions import InsufficientFundsError, WalletError
from src.models.onchain_model import BaseContract, ERC20Contract
from src.logger import AsyncLogger


logger = AsyncLogger()
Account.enable_unaudited_hdwallet_features()


class BlockchainError(Exception):
    """
    Base class for blockchain-related errors.
    """
    
class Wallet(AsyncWeb3, Account):
    ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
    DEFAULT_TIMEOUT = 60
    MAX_RETRIES = 3
    
    def __init__(
        self, 
        keypair: str, 
        rpc_url: Union[HttpUrl, str], 
        proxy: Proxy | None = None,
        request_timeout: int = 30
    ) -> None:
        self._provider = AsyncHTTPProvider(
            str(rpc_url),
            request_kwargs={
                "proxy": proxy.as_url if proxy else None,
                "ssl": False,
                "timeout": request_timeout
            }
        )
            
        super().__init__(self._provider, modules={"eth": AsyncEth})
        
        self.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        self.keypair = self._initialize_account(keypair)
        self._contracts_cache: dict[str, AsyncContract] = {}
        self._is_closed = False
        
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def close(self):
        if self._is_closed:
            return
        
        try:
            if self._provider:
                if isinstance(self._provider, AsyncHTTPProvider):
                    await self._provider.disconnect()
                    await logger.logger_msg(
                        msg="Provider disconnected successfully", 
                        type_msg="debug", 
                        class_name=self.__class__.__name__, 
                        method_name="close"
                    )
                    
            self._contracts_cache.clear()
            
        except Exception as e:
            await logger.logger_msg(
                msg=f"Error during wallet cleanup: {str(e)}", 
                type_msg="warning", 
                class_name=self.__class__.__name__, 
                method_name="close"
            )
        finally:
            self._is_closed = True

    @staticmethod
    def _initialize_account(input_str: str) -> Account:
        input_str = input_str.strip()

        key_candidate = input_str.replace(" ", "")
        if key_candidate.startswith('0x'):
            key_body = key_candidate[2:]
        else:
            key_body = key_candidate

        if len(key_body) == 64 and all(c in '0123456789abcdefABCDEF' for c in key_body):
            keypair = '0x' + key_body if not key_candidate.startswith('0x') else key_candidate
            try:
                return Account.from_key(keypair)
            except ValueError:
                pass

        words = [word for word in input_str.split() if word]
        if len(words) in (12, 24):
            mnemonic = ' '.join(words)
            try:
                return Account.from_mnemonic(mnemonic)
            except ValueError as e:
                raise WalletError(f"Invalid mnemonic phrase: {e}")
        else:
            raise WalletError("Input must be a 12 or 24 word mnemonic phrase or a 64-character hexadecimal private key")

    @property
    def wallet_address(self):
        return self.keypair.address

    @property
    async def use_eip1559(self) -> bool:
        try:
            latest_block = await self.eth.get_block('latest')
            return 'baseFeePerGas' in latest_block
        except Exception as e:
            await logger.logger_msg(
                msg=f"Error checking EIP-1559 support: {e}", type_msg="error", 
                class_name=self.__class__.__name__, method_name="use_eip1559"
            )
            return False

    @staticmethod
    def _get_checksum_address(address: str) -> ChecksumAddress:
        return AsyncWeb3.to_checksum_address(address)   

    async def get_contract(self, contract: Union[BaseContract, str, object]) -> AsyncContract:
        if isinstance(contract, str):
            address = self._get_checksum_address(contract)
            if address not in self._contracts_cache:
                temp_contract = ERC20Contract(address="")
                abi = await temp_contract.get_abi()
                contract_instance = self.eth.contract(address=address, abi=abi)
                self._contracts_cache[address] = contract_instance
            return self._contracts_cache[address]
        
        if isinstance(contract, BaseContract):
            address = self._get_checksum_address(contract.address)
            if address not in self._contracts_cache:
                abi = await contract.get_abi()
                self._contracts_cache[address] = self.eth.contract(
                    address=address,
                    abi=abi
                )
            return self._contracts_cache[address]

        if hasattr(contract, "address") and hasattr(contract, "abi"):
            address = self._get_checksum_address(contract.address)
            if address not in self._contracts_cache:
                self._contracts_cache[address] = self.eth.contract(
                    address=address,
                    abi=contract.abi
                )
            return self._contracts_cache[address]

        raise TypeError("Invalid contract type: expected BaseContract, str, or contract-like object")

    async def token_balance(self, token_address: str) -> int:
        contract = await self.get_contract(token_address)
        return await contract.functions.balanceOf(
            self._get_checksum_address(self.keypair.address)
        ).call()

    def _is_native_token(self, token_address: str) -> bool:
        return token_address == self.ZERO_ADDRESS

    async def _get_cached_contract(self, token_address: str) -> AsyncContract:
        checksum_address = self._get_checksum_address(token_address)
        if checksum_address not in self._contracts_cache:
            self._contracts_cache[checksum_address] = await self.get_contract(checksum_address)
        return self._contracts_cache[checksum_address]

    async def convert_amount_to_decimals(self, amount: Decimal, token_address: str) -> int:
        checksum_address = self._get_checksum_address(token_address)
    
        if self._is_native_token(checksum_address):
            return self.to_wei(Decimal(str(amount)), 'ether')
        
        contract = await self._get_cached_contract(checksum_address)
        decimals = await contract.functions.decimals().call()
        return int(Decimal(str(amount)) * Decimal(10 ** decimals))
    
    async def convert_amount_from_decimals(self, amount: int, token_address: str) -> float:
        checksum_address = self._get_checksum_address(token_address)
    
        if self._is_native_token(checksum_address):
            return float(self.from_wei(amount, 'ether'))
        
        contract = await self._get_cached_contract(checksum_address)
        decimals = await contract.functions.decimals().call()
        return float(Decimal(amount) / Decimal(10 ** decimals))

    async def get_nonce(self) -> Nonce:
        for attempt in range(self.MAX_RETRIES):
            try:
                count = await self.eth.get_transaction_count(self.wallet_address, 'pending')
                return Nonce(count)
            except Exception as e:
                await logger.logger_msg(
                    msg=f"Failed to get nonce (attempt {attempt + 1}): {e}", type_msg="warning", 
                    class_name=self.__class__.__name__, method_name="get_nonce"
                )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(1)
                else:
                    raise RuntimeError(f"Failed to get nonce after {self.MAX_RETRIES} attempts") from e

    async def check_balance(self) -> bool:
        return await self.eth.get_balance(self.keypair.address)        

    async def human_balance(self) -> float:
        balance = await self.eth.get_balance(self.keypair.address)
        return float(self.from_wei(balance, "ether"))
    
    async def has_sufficient_funds_for_tx(self, transaction: TxParams) -> bool:
        try:
            balance = await self.eth.get_balance(self.keypair.address)
            required = int(transaction.get('value', 0))
            
            if balance < required:
                required_eth = self.from_wei(required, 'ether')
                balance_eth = self.from_wei(balance, 'ether')
                raise InsufficientFundsError(
                    f"Insufficient ETH balance. Required: {required_eth:.6f} ETH, Available: {balance_eth:.6f} ETH"
                )
                
            return True
            
        except ValueError as error:
            raise ValueError(f"Invalid transaction parameters: {str(error)}") from error
        except Exception as error:
            raise BlockchainError(f"Failed to check transaction availability: {str(error)}") from error

    async def get_signature(self, text: str, keypair: str | None = None) -> HexStr:
        try:
            signing_key = (
                self.from_key(keypair) 
                if keypair 
                else self.keypair
            )

            encoded = encode_defunct(text=text)
            signature = signing_key.sign_message(encoded).signature
            
            return HexStr(signature.hex())

        except Exception as error:
            raise ValueError(f"Signing failed: {str(error)}") from error

    async def _estimate_gas_params(
        self,
        tx_params: dict,
        gas_buffer: float = 1.2,
        gas_price_buffer: float = 1.05
    ) -> dict:
        try:
            gas_estimate = await self.eth.estimate_gas(tx_params)
            tx_params["gas"] = int(gas_estimate * gas_buffer)
            
            if await self.use_eip1559:
                latest_block = await self.eth.get_block('latest')
                base_fee = latest_block['baseFeePerGas']
                priority_fee = await self.eth.max_priority_fee
                
                tx_params.update({
                    "maxPriorityFeePerGas": int(priority_fee * gas_price_buffer),
                    "maxFeePerGas": int((base_fee * 2 + priority_fee) * gas_price_buffer)
                })
            else:
                tx_params["gasPrice"] = int(await self.eth.gas_price * gas_price_buffer)
                
            return tx_params
        except Exception as error:
            raise BlockchainError(f"Failed to estimate gas: {error}") from error

    async def build_transaction_params(
        self,
        contract_function: Any = None,
        to: str = None,
        value: int = 0,
        gas_buffer: float = 1.2,
        gas_price_buffer: float = 1.05,
        gas: int = None,
        gas_price: int = None,
        **kwargs
    ) -> dict:
        base_params = {
            "from": self.wallet_address,
            "nonce": await self.get_nonce(),
            "value": value,
            **kwargs
        }

        try:
            chain_id = await self.eth.chain_id
            base_params["chainId"] = chain_id
        except Exception as e:
            await self.logger_msg(
                msg=f"Failed to get chain_id: {e}", 
                type_msg="warning", 
                address=self.wallet_address,
                method_name="build_transaction_params"
            )

        if gas is not None:
            base_params["gas"] = gas
        
        if gas_price is not None:
            base_params["gasPrice"] = gas_price

        if contract_function is None:
            if to is None:
                raise ValueError("'to' address required for ETH transfers")
            base_params.update({"to": to})
            if gas is None or gas_price is None:
                return await self._estimate_gas_params(base_params, gas_buffer, gas_price_buffer)
            return base_params

        tx_params = await contract_function.build_transaction(base_params)
        if gas is None or gas_price is None:
            return await self._estimate_gas_params(tx_params, gas_buffer, gas_price_buffer)
        return tx_params

    async def _check_and_approve_token(
        self, 
        token_address: str, 
        spender_address: str, 
        amount: int
    ) -> tuple[bool, str]:
        try:
            token_contract = await self.get_contract(token_address)
            
            current_allowance = await token_contract.functions.allowance(
                self.wallet_address, 
                spender_address
            ).call()

            if current_allowance >= amount:
                return True, "Allowance already sufficient"

            approve_params = await self.build_transaction_params(
                contract_function=token_contract.functions.approve(spender_address, amount),
                gas=250_000,
                gas_price=40000000000
            )

            success, result = await self._process_transaction(approve_params)
            if not success:
                raise WalletError(f"Approval failed: {result}")

            return True, "Approval successful"

        except Exception as error:
            return False, f"Error during approval: {str(error)}"
        
    async def send_and_verify_transaction(self, transaction: Any) -> tuple[bool, str]:
        max_attempts = self.MAX_RETRIES
        current_attempt = 0
        last_error = None
        
        while current_attempt < max_attempts:
            tx_hash = None
            try:
                signed = self.keypair.sign_transaction(transaction)
                tx_hash = await self.eth.send_raw_transaction(signed.raw_transaction)
                
                receipt = await asyncio.wait_for(
                    self.eth.wait_for_transaction_receipt(tx_hash),
                    timeout=self.DEFAULT_TIMEOUT
                )
                
                if receipt["status"] == 1:
                    return True, tx_hash.hex()
                else:
                    return False, f"Transaction reverted. Hash: {tx_hash.hex()}"
                
            except asyncio.TimeoutError:
                if tx_hash:
                    await logger.logger_msg(
                        msg=f"Transaction sent but confirmation timed out. Hash: {tx_hash.hex()}", 
                        type_msg="warning", 
                        class_name=self.__class__.__name__, 
                        method_name="send_and_verify_transaction"
                    )
                    return False, f"PENDING:{tx_hash.hex()}"
                    
            except Exception as error:
                error_str = str(error)
                last_error = error
                current_attempt += 1
                
                if "NONCE_TOO_SMALL" in error_str or "nonce too low" in error_str.lower():
                    await logger.logger_msg(
                        msg=f"Nonce too small. Current: {transaction.get('nonce')}. Getting new nonce.", 
                        type_msg="warning", 
                        class_name=self.__class__.__name__, method_name="send_and_verify_transaction"
                    )
                    try:
                        new_nonce = await self.eth.get_transaction_count(self.wallet_address, 'pending')
                        if new_nonce <= transaction['nonce']:
                            new_nonce = transaction['nonce'] + 1
                        transaction['nonce'] = new_nonce
                        await logger.logger_msg(
                            msg=f"New nonce set: {new_nonce}", 
                            type_msg="debug", 
                            class_name=self.__class__.__name__, method_name="send_and_verify_transaction"
                        )
                    except Exception as nonce_error:
                        await logger.logger_msg(
                            msg=f"Error getting new nonce: {str(nonce_error)}", 
                            type_msg="error", 
                            class_name=self.__class__.__name__, method_name="send_and_verify_transaction"
                        )
                    delay = random.uniform(1, 3) * (2 ** current_attempt)
                    await asyncio.sleep(delay)
        
        return False, f"Failed to execute transaction after {max_attempts} attempts. Last error: {str(last_error)}"
    
    async def _process_transaction(self, transaction: Any) -> tuple[bool, str]:
        try:
            status, result = await self.send_and_verify_transaction(transaction)
            return status, result
        except Exception as error:
            return False, str(error)