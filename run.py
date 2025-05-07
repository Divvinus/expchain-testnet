import asyncio
import os
import sys

from module_processor import main_loop


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n\n🚨 The program has been stopped. The terminal is ready for commands.")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
    finally:
        if sys.platform != "win32":
            os.system("stty sane")
        print("👋 The program has ended. The terminal is ready for commands.")