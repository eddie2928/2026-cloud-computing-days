import sys
from pathlib import Path
from loguru import logger


def setup(log_dir: str | Path = "logs") -> None:
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    logger.add(
        log_path / "agentbox.log",
        level="DEBUG",
        rotation="10 MB",
        retention=5,
        serialize=True,
    )
