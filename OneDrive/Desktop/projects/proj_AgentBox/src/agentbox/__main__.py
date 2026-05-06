import asyncio
import sys

import uvicorn

from agentbox.config import cfg
from agentbox.logging_setup import setup as setup_logging


def _run() -> None:
    setup_logging()
    # Anchor relative paths to CWD at startup so they stay consistent.
    from pathlib import Path
    if not Path(cfg.CA_DIR).is_absolute():
        cfg.CA_DIR = str(Path.cwd() / cfg.CA_DIR)
    if not Path(cfg.DB_PATH).is_absolute():
        cfg.DB_PATH = str(Path.cwd() / cfg.DB_PATH)

    from agentbox.api.server import create_app
    from agentbox.proxy.master import start_master
    from agentbox.proxy.addon import AgentBoxAddon
    from agentbox.api.hitl import HITLQueue
    from agentbox.api.ws import WSHub

    hitl_queue = HITLQueue()
    ws_hub = WSHub()

    app = create_app(hitl_queue=hitl_queue, ws_hub=ws_hub)
    addon = AgentBoxAddon()
    addon.hitl_queue = hitl_queue
    addon.ws_hub = ws_hub
    addon.storage_path = cfg.DB_PATH

    async def _main() -> None:
        server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=cfg.API_PORT, log_level="warning"))
        await asyncio.gather(
            start_master(addon, cfg.PROXY_PORT),
            server.serve(),
        )

    asyncio.run(_main())


def _ca_install() -> None:
    from pathlib import Path
    from agentbox.proxy.ca import ensure_ca
    ca_crt, _ = ensure_ca(Path(cfg.CA_DIR))
    print(f"CA certificate ready: {ca_crt}")
    print("Run scripts/install_ca.sh to register in system trust store.")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(prog="agentbox", description="AgentBox local MITM sandbox")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("run", help="Start proxy + API server")
    sub.add_parser("ca", help="Ensure CA certificate exists")
    args = parser.parse_args()

    if args.cmd == "run":
        _run()
    elif args.cmd == "ca":
        _ca_install()
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
