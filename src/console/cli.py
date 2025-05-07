import inquirer

from inquirer.themes import GreenPassion
from art import text2art
from colorama import Fore
from bot_loader import config

from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text


class Console:
    __slots__ = ("rich_console",)

    MODULES = (
        "🚰 Faucet",
        "🎢 Bridge BSC",
        "🏞️  Bridge Sepolia",
        "🔄 Swap",
        "🔄 Auto-route",
        "🚪 Exit",
    )
    MODULES_DATA = (
        ("🚰 Faucet", "faucet"),
        ("🎢 Bridge BSC", "bridge_bsc"),
        ("🏞️  Bridge Sepolia", "bridge_sepolia"),
        ("🔄 Swap", "swap"),
        ("🔄 Auto-route", "auto_route"),
        ("🚪 Exit", "exit"),
    )

    def __init__(self):
        self.rich_console = RichConsole()

    def show_dev_info(self):
        print("\033c", end="")

        styled_title = Text(text2art("EXPchain", font="doom"), style="cyan")
        content = Text.assemble(
            styled_title,
            "\n👉 Channel: https://t.me/divinus_xyz 💬\n",
            "\n👉 GitHub: https://github.com/Divvinus 💻\n"
        )

        panel = Panel(
            content,
            border_style="yellow",
            expand=False,
            title="[bold green]Welcome[/bold green]",
            subtitle="[italic]Powered by Divinus[/italic]",
        )
        self.rich_console.print(panel)
        print()

    @staticmethod
    def prompt(data):
        return inquirer.prompt(data, theme=GreenPassion())

    def get_module(self):
        answers = self.prompt([
            inquirer.List(
                "module",
                message=Fore.LIGHTBLACK_EX + "Select the module",
                choices=self.MODULES,
            ),
        ])
        selected = answers.get("module")
        return dict(self.MODULES_DATA)[selected]

    def display_info(self):
        table = Table(title="System Configuration", box=box.ROUNDED)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Accounts", str(len(config.accounts)))
        table.add_row("Threads", str(config.threads))
        table.add_row(
            "Delay before start",
            f"{config.delay_before_start.min}-{config.delay_before_start.max} sec",
        )
        
        self.rich_console.print(
            Panel(
                table,
                expand=False,
                border_style="green",
                title="[bold yellow]System Information[/bold yellow]",
                subtitle="[italic]Use arrow keys to navigate[/italic]",
            )
        )

    def build(self):
        self.show_dev_info()
        self.display_info()
        config.module = self.get_module()