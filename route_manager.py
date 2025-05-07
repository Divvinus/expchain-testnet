import random
from typing import Any, Callable
import sys

from src.models import Account
from src.logger import AsyncLogger
from configs import ROUTE_TASK
from src.task_manager import EXPchainBot

logger = AsyncLogger()


class RouteManager:
    def __init__(self):
        self.module_functions = self._load_module_functions()
        
    @staticmethod
    def _load_module_functions() -> dict[str, Callable]:
        return {
            attr_name[8:]: getattr(EXPchainBot, attr_name)
            for attr_name in dir(EXPchainBot)
            if attr_name.startswith('process_')
        }
    
    def create_route(self, tasks: list[str]) -> list[str]:
        if not tasks:
            return []
        
        route = tasks.copy()
        
        has_faucet = 'faucet' in route
        if has_faucet:
            route.remove('faucet')
            
        random.shuffle(route)
        
        if has_faucet:
            route.insert(0, 'faucet')
            
        return route
    
    async def validate_route(self, route: list[str]) -> list[str]:
        valid_route = []
        for task in route:
            if task in self.module_functions:
                valid_route.append(task)
            else:
                await logger.logger_msg(
                    f"Task '{task}' is not implemented and will be skipped", type_msg="warning"
                )
                
        return valid_route
    
    async def execute_route(self, account: Account, route: list[str]) -> dict[str, Any]:
        results = {}
        
        for task_name in route:
            try:
                process_func = self.module_functions.get(task_name)
                if not process_func:
                    continue
            
                
                success, message = await process_func(account)
                
                results[task_name] = {
                    "success": success,
                    "message": message
                }
                    
            except Exception as e:
                error_msg = str(e)
                await logger.logger_msg(
                    f"Error executing task {task_name}: {error_msg}", type_msg="error"
                )
                results[task_name] = {
                    "success": False,
                    "message": f"Exception: {error_msg}"
                }
                
        return results


async def get_optimized_route() -> list[str]:
    route_manager = RouteManager()
      
    if not ROUTE_TASK:
        await logger.logger_msg(
            "ROUTE_TASK not found in configuration or empty", type_msg="warning"
        )
        return []
    
    route = route_manager.create_route(ROUTE_TASK)
    
    valid_route = await route_manager.validate_route(route)
    
    if len(valid_route) != len(route):
        await logger.logger_msg(
            f"Some tasks were excluded from the route. Original: {len(route)}, Valid: {len(valid_route)}",
            type_msg="warning"
        )
    
    return valid_route


async def process_route(account: Account) -> tuple[bool, str]:
    try:
        route = await get_optimized_route()
        
        if not route:
            return False, "Route is empty or unavailable"
        
        await logger.logger_msg(
            f"Start of route execution: {', '.join(route)}", type_msg="info"
        )
        
        route_manager = RouteManager()
        results = await route_manager.execute_route(account, route)
        
        success_count = sum(1 for res in results.values() if res.get("success"))
        total_count = len(results)
        
        success_rate = (success_count / total_count) * 100 if total_count else 0
        
        result_message = (
            f"Completed tasks: {success_count}/{total_count} ({success_rate:.1f}%)"
        )
        
        try:
            if "module_processor_reporter" in sys.modules:
                reporter = sys.modules["module_processor_reporter"]
                from src.utils.telegram_reporter import TelegramReporter
                
                if isinstance(reporter, TelegramReporter):
                    reporter.add_result(
                        account,
                        success_count > 0,
                        result_message,
                        module_results=results
                    )
        except Exception as e:
            await logger.logger_msg(
                f"Error updating reporter: {str(e)}", type_msg="warning"
            )
            
        return success_count > 0, result_message, results
        
    except Exception as e:
        error_msg = str(e)
        await logger.logger_msg(
            f"Error executing route: {error_msg}", type_msg="error"
        )
        return False, f"Error executing route: {error_msg}"


def integrate_route_processor():
    setattr(EXPchainBot, "process_auto_route", process_route)
    

integrate_route_processor()