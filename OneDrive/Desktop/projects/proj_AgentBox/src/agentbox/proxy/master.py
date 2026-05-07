from pathlib import Path

from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

from agentbox.config import cfg
from agentbox.proxy.ca import ensure_ca


async def start_master(addon, listen_port: int) -> None:
    ca_dir = Path(cfg.CA_DIR)
    ensure_ca(ca_dir)

    if cfg.TRANSPARENT_MODE:
        # 1A-3/1A-5: transparent mode - bind 0.0.0.0, SNI filter to Anthropic only
        opts = Options(
            listen_host="0.0.0.0",
            listen_port=listen_port,
            mode=["transparent"],
            allow_hosts=[r"api\.anthropic\.com"],
            confdir=str(ca_dir),
            ssl_insecure=False,
        )
    else:
        opts = Options(
            listen_host="127.0.0.1",
            listen_port=listen_port,
            confdir=str(ca_dir),
            ssl_insecure=False,
        )

    master = DumpMaster(opts, with_termlog=False, with_dumper=False)
    master.addons.add(addon)
    await master.run()
