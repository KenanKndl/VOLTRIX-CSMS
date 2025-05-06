import logging
from colorama import init, Fore, Style, Back

init(autoreset=True)

# Modül bazlı renk eşlemesi
MODULE_COLOR_MAP = {
    'Main': Fore.GREEN,
    'EV-ISO15118': Fore.MAGENTA,
    'EVSE-ISO15118': Fore.BLUE,
    'ChargePoint': Fore.YELLOW,
    'CentralSystem': Fore.CYAN,
}

# Seviyeye göre simge (opsiyonel)
LEVEL_SYMBOL_MAP = {
    'INFO': 'ℹ️',
    'WARNING': '⚠️',
    'ERROR': '❌',
    'DEBUG': '🐞',
    'CRITICAL': '💥'
}

class ColorFormatter(logging.Formatter):
    def format(self, record):
        module_color = MODULE_COLOR_MAP.get(record.name, Fore.WHITE)
        level_symbol = LEVEL_SYMBOL_MAP.get(record.levelname, '')
        reset = Style.RESET_ALL

        log_fmt = f"{module_color}[%(asctime)s] [{record.levelname}] %(name)s: {level_symbol} %(message)s{reset}"
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(ColorFormatter())
        logger.addHandler(handler)

    return logger
