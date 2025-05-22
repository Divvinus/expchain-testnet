import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

import aiofiles
import json

class ContractError(Exception):
    """Base exception for contract-related errors"""
    pass

@dataclass(slots=True)
class BaseContract:
    address: str
    abi_file: str = "erc_20.json"
    
    _abi_cache: ClassVar[dict[str, tuple[list[dict[str, Any]], float]]] = {}
    _cache_lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _abi_path: ClassVar[Path] = Path("./abi")
    CACHE_TTL: ClassVar[int] = 3600

    async def get_abi(self) -> list[dict[str, Any]]:
        async with self._cache_lock:
            await self._validate_cache()
            return self._abi_cache[self.abi_file][0]
        
    async def _validate_cache(self) -> None:
        current_time = time.time()
        if (cached := self._abi_cache.get(self.abi_file)) and (current_time - cached[1]) < self.CACHE_TTL:
            return
        await self._load_abi_file(current_time)

    async def _load_abi_file(self, timestamp: float) -> None:
        file_path = self._abi_path / self.abi_file
        try:
            async with aiofiles.open(file_path, "rb") as f:
                content = await asyncio.to_thread(file_path.read_bytes)
                abi_data = json.loads(content)
                if not isinstance(abi_data, list):
                    raise ContractError(f"Invalid ABI structure in {file_path}")
                self._abi_cache[self.abi_file] = (abi_data, timestamp)
        except FileNotFoundError as e:
            raise ContractError(f"ABI file not found: {file_path}") from e
        except json.JSONDecodeError as e:
            raise ContractError(f"Invalid JSON in ABI file: {file_path}") from e

    @classmethod
    async def clear_cache(cls, abi_file: str | None = None) -> None:
        async with cls._cache_lock:
            if abi_file:
                cls._abi_cache.pop(abi_file, None)
            else:
                cls._abi_cache.clear()

@dataclass(slots=True)
class ERC20Contract(BaseContract):
    address: str = ""
    abi_file: str = "erc_20.json"

@dataclass(slots=True)
class BridgeSepoliaContract(BaseContract):
    address: str = "0x38C967856d17E900042Af447B3346bfF26C8ed4B"
    abi_file: str = "bridge.json"
    
@dataclass(slots=True)
class BridgeBscContract(BaseContract):
    address: str = "0xFbbc73da1f8a6C4b0344Ef1dB01BCb9AC36c3012"
    abi_file: str = "bridge.json"
    
@dataclass(slots=True)
class SwapContract(BaseContract):
    address: str = "0xB4c6A1e8A14e9Fe74c88b06275b747145DD41206"
    abi_file: str = "swap.json"
    
@dataclass(slots=True)
class TestnetBridgeContract(BaseContract):
    address: str = "0xfcA99F4B5186D4bfBDbd2C542dcA2ecA4906BA45"
    abi_file: str = "buy_sepolia.json"