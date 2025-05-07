import asyncio
import os
import sys
from typing import Callable

from src.console import Console
from src.task_manager import EXPchainBot
from bot_loader import config, progress, semaphore
from src.logger import AsyncLogger
from src.models import Account
from src.utils import get_address, random_sleep
from src.utils.send_tg_message import SendTgMessage
from src.utils.telegram_reporter import TelegramReporter
from route_manager import RouteManager, get_optimized_route


logger = AsyncLogger()


class ModuleProcessor:
    def __init__(self):
        self.console = Console()
        self.module_functions = self._load_module_functions()
        
        self.telegram_reporter = TelegramReporter()
        self.route_manager = RouteManager()
    
    @staticmethod
    def _load_module_functions() -> dict[str, Callable]:
        return {
            attr_name[8:]: getattr(EXPchainBot, attr_name)
            for attr_name in dir(EXPchainBot)
            if attr_name.startswith('process_')
        }
    
    async def process_account(
        self, 
        account: Account, 
        process_func: Callable
    ) -> tuple[bool, str]:
        address = get_address(account.keypair)
        
        async with semaphore:
            try:
                await self._apply_start_delay()
                    
                is_route = config.module == "auto_route"
                module_name = "auto_route" if is_route else None
                    
                result = await process_func(account)
                
                if is_route and isinstance(result, tuple):
                    if len(result) >= 3:
                        success, message, module_results = result[0], result[1], result[2]
                        await self._update_statistics(success)
                        self.telegram_reporter.add_result(account, success, message, 
                                                         module_results=module_results)
                        return success, message
                    else:
                        success, message = result[0], result[1]
                else:
                    success, message = self._process_result(result)
                
                await self._update_statistics(success)
                
                self.telegram_reporter.add_result(account, success, message, module=module_name)
                
                return success, message
                
            except Exception as e:
                progress.increment()
                error_msg = str(e)
                await logger.logger_msg(
                    f"Error: {error_msg}",
                    address=address,
                    type_msg="error", 
                    method_name="process_account"
                )
                
                self.telegram_reporter.add_result(account, False, error_msg, module=module_name)
                
                return False, error_msg
    
    async def _apply_start_delay(self) -> None:
        if getattr(config, 'delay_before_start', None) and config.delay_before_start.min > 0:
            await random_sleep(
                min_sec=config.delay_before_start.min, 
                max_sec=config.delay_before_start.max
            )
    
    def _process_result(self, result) -> tuple[bool, str]:
        if isinstance(result, tuple) and len(result) == 2:
            return result
        else:
            success = bool(result)
            message = "Successfully completed" if success else "Execution failed"
            return success, message
    
    async def _update_statistics(self, success: bool) -> None:
        if success:
            progress.success += 1
            
        progress.increment()
        
        success_rate = round(progress.success/progress.processed*100, 2) if progress.processed else 0
        log_message = (
            f"📊 Statistics: {progress.processed}/{progress.total} accounts processed | "
            f"✅ Success: {progress.success} ({success_rate}%)"
        )
        await logger.logger_msg(log_message, type_msg="info")
    
    async def send_stats_to_telegram(
        self, 
        account: Account, 
        messages: list[str]
    ) -> None:
        try:
            sender = SendTgMessage(account)
            await sender.send_tg_message(messages)
        except Exception as e:
            await logger.logger_msg(
                f"Error sending statistics to Telegram: {str(e)}", 
                type_msg="error",
                method_name="send_stats_to_telegram"
            )
    
    async def process_module(self, module_name: str) -> bool:
        if module_name == "exit":
            await logger.logger_msg("🔴 Exit program...", type_msg="info")
            return True
        
        if module_name == "auto_route":
            return await self._process_auto_route()
            
        process_func = self.module_functions.get(module_name)
        if not process_func:
            await logger.logger_msg(
                f"Module {module_name} is not implemented!", 
                type_msg="error",
                method_name="process_module"
            )
            return False
        
        self._initialize_progress_and_reporter(module_name)
        
        try:
            await self._process_accounts_in_batches(process_func)
            await self._show_final_stats()
            return False
            
        except Exception as e:
            address = self._get_first_account_address()
            await logger.logger_msg(
                f"Error executing module: {str(e)}",
                address=address,
                type_msg="error",
                method_name="process_module"
            )
            return False
    
    def _initialize_progress_and_reporter(self, module_name: str) -> None:
        progress.processed = 0
        progress.success = 0
        progress.total = len(config.accounts)
        self.telegram_reporter.clear()
        self.telegram_reporter.set_module(module_name)
    
    def _get_first_account_address(self) -> str:
        return get_address(config.accounts[0].keypair) if config.accounts else "Unknown"
    
    async def _process_auto_route(self) -> bool:
        route = await get_optimized_route()
        
        if not route:
            await logger.logger_msg(
                "Auto-route is empty or unavailable. Check the ROUTE_TASK configuration.",
                type_msg="error", method_name="_process_auto_route"
            )
            return False
        
        self._initialize_progress_and_reporter("auto_route")
        
        await logger.logger_msg(
            f"Starting auto-route: {', '.join(route)}", type_msg="info"
        )
        
        auto_route_func = self.module_functions.get("auto_route")
        if not auto_route_func:
            await logger.logger_msg(
                "Auto-route function not found. Check the route_manager integration.",
                type_msg="error", method_name="_process_auto_route"
            )
            return False
        
        sys.modules["module_processor_reporter"] = self.telegram_reporter
        
        await self._process_accounts_in_batches(auto_route_func)
        await self._show_final_stats()
        
        if "module_processor_reporter" in sys.modules:
            del sys.modules["module_processor_reporter"]
        
        return False
    
    async def _process_accounts_in_batches(self, process_func: Callable) -> None:
        batch_size = getattr(config, 'threads', len(config.accounts))
        
        for i in range(0, len(config.accounts), batch_size):
            batch_accounts = config.accounts[i:i + batch_size]
            batch_tasks = [
                self.process_account(account, process_func) 
                for account in batch_accounts
            ]
            
            try:
                await asyncio.gather(*batch_tasks)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                await logger.logger_msg(
                    f"Error processing batch: {str(e)}",
                    type_msg="error",
                    method_name="_process_accounts_in_batches"
                )
    
    async def _show_final_stats(self) -> None:
        if getattr(config, 'send_stats_to_telegram', False) and config.accounts:
            await self._send_report_to_telegram()
        else:
            await self._log_final_stats()
    
    async def _send_report_to_telegram(self) -> None:
        await self.telegram_reporter.send_report(config.accounts[0])
        await self._log_final_stats()
    
    async def _log_final_stats(self) -> None:
        success_percent = round(progress.success/progress.total*100, 2) if progress.total > 0 else 0
        error_count = progress.total - progress.success
        error_percent = round(100 - success_percent, 2) if progress.total > 0 else 0
        
        
        await logger.logger_msg(f"🏁 FINAL STATISTICS 🏁", type_msg="info")
        await logger.logger_msg(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", type_msg="info")
        await logger.logger_msg(f"✅ Success: {progress.success}/{progress.total} ({success_percent}%)", type_msg="info")
        await logger.logger_msg(f"❌ Errors: {error_count}/{progress.total} ({error_percent}%)", type_msg="info")
        await logger.logger_msg(f"⏱️ Total processed: {progress.processed}", type_msg="info")
        await logger.logger_msg(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", type_msg="info")
    
    async def cleanup(self) -> None:        
        current = asyncio.current_task()
        tasks_to_cancel = [
            t for t in asyncio.all_tasks() 
            if t is not current and not t.done()
        ]
        
        if not tasks_to_cancel:
            return
        
        for task in tasks_to_cancel:
            task.cancel()
        
        try:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        except Exception as e:
            await logger.logger_msg(
                f"Error during cleanup: {str(e)}", 
                type_msg="error",
                method_name="cleanup"
            )
    
    async def execute(self) -> bool:
        self.console.build()
        try:
            return await self.process_module(config.module)
        except Exception as e:
            await logger.logger_msg(
                f"Execution failed: {str(e)}",
                type_msg="error",
                method_name="execute"
            )
            return True
        finally:
            await self.cleanup()


async def main_loop() -> None:
    await logger.logger_msg("✅ The program has been started", type_msg="info")
    
    processor = None
    try:
        while True:
            progress.reset()
            try:
                if processor:
                    await processor.cleanup()
                processor = ModuleProcessor()
                
                exit_flag = await processor.execute()
                if exit_flag:
                    break
            except KeyboardInterrupt:
                await logger.logger_msg(
                    "🚨 Manual interruption!", 
                    type_msg="warning", 
                    method_name="main_loop"
                )
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                await logger.logger_msg(
                    f"Unknown error: {str(e)}", 
                    type_msg="error", 
                    method_name="main_loop"
                )
                
            input("\nPress Enter to return to the menu...")
            os.system("cls" if os.name == "nt" else "clear")
    finally:
        if processor:
            await processor.cleanup()

    await logger.logger_msg(
        "👋 Goodbye! The terminal is ready for commands.", 
        type_msg="info"
    ) 