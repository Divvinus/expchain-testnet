from typing import Any
from dataclasses import dataclass, field
from collections import defaultdict

from src.models import Account
from src.utils import get_address
from src.utils.send_tg_message import SendTgMessage
from src.logger import AsyncLogger

logger = AsyncLogger()

@dataclass
class AccountResult:
    address: str
    success: bool
    message: str
    module_results: dict[str, dict[str, Any]] = field(default_factory=dict)

class TelegramReporter:
    def __init__(self):
        self.account_results: dict[str, AccountResult] = {}
        self.module_name: str = ""
    
    def set_module(self, module_name: str) -> None:
        self.module_name = module_name
    
    def add_result(self, account: Account, success: bool, message: str, 
                  module: str = None, module_results: dict[str, Any] = None) -> None:
        address = get_address(account.keypair)

        if address in self.account_results:
            result = self.account_results[address]
            result.success = success
            result.message = message
            
            if module_results:
                result.module_results.update(module_results)
            elif module:
                result.module_results[module] = {
                    "success": success,
                    "message": message
                }
        else:
            module_data = {}
            if module_results:
                module_data = module_results
            elif module:
                module_data = {
                    module: {
                        "success": success,
                        "message": message
                    }
                }
                
            self.account_results[address] = AccountResult(
                address=address,
                success=success,
                message=message,
                module_results=module_data
            )
    
    async def send_report(self, report_account: Account) -> None:
        if not self.account_results:
            return

        success_count = sum(1 for result in self.account_results.values() if result.success)
        total_count = len(self.account_results)
        success_percent = round(success_count / total_count * 100, 2) if total_count > 0 else 0
        error_count = total_count - success_count
        
        messages = [
            f"{'='*40}",
            f"📊 REPORT: {self.module_name.upper()} 📊",
            f"{'='*40}",
            f"▶️ TOTAL STATISTICS:",
            f"✅ Success: {success_count}/{total_count} ({success_percent}%)",
            f"❌ Failed: {error_count}/{total_count} ({round(100-success_percent, 2)}%)",
            f"{'_'*40}"
        ]
        
        if self.module_name == "auto_route" and self.account_results:
            all_modules = set()
            for result in self.account_results.values():
                all_modules.update(result.module_results.keys())
            
            if all_modules:
                messages.append("\n📈 STATISTICS BY MODULES:")
                
                for module in sorted(all_modules):
                    module_success = 0
                    module_total = 0
                    module_errors = defaultdict(int)
                    
                    for address, result in self.account_results.items():
                        if module in result.module_results:
                            module_total += 1
                            mod_result = result.module_results[module]
                            
                            if mod_result.get("success", False):
                                module_success += 1
                            else:
                                error_msg = mod_result.get("message", "Unknown error")
                                module_errors[error_msg] += 1
                    
                    module_success_percent = round(module_success / module_total * 100, 2) if module_total > 0 else 0
                    
                    status_emoji = "🟢" if module_success == module_total else "🔴" if module_success == 0 else "🟡"
                    
                    messages.append(f"\n{status_emoji} MODULE: {module.upper()}")
                    messages.append(f"   ✔️ Success: {module_success}/{module_total} ({module_success_percent}%)")
                    
                    if module_errors:
                        messages.append(f"   ✖️ Errors ({len(module_errors)} types):")
                        
                        sorted_errors = sorted(module_errors.items(), key=lambda x: x[1], reverse=True)
                        for error_msg, count in sorted_errors:
                            messages.append(f"      • {error_msg} ({count} accounts)")
        
        messages.append(f"{'='*40}")
        
        try:
            sender = SendTgMessage(report_account)
            await sender.send_tg_message(messages)
        except Exception as e:
            await logger.logger_msg(
                f"Error sending statistics to Telegram: {str(e)}", 
                type_msg="error",
                method_name="send_report"
            )
    
    def clear(self) -> None:
        self.account_results.clear()