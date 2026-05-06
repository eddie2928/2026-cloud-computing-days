from pathlib import Path

from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

from agentbox.config import cfg
from agentbox.proxy.ca import ensure_ca


async def start_master(addon, listen_port: int) -> None:
    ca_dir = Path(cfg.CA_DIR)
    ensure_ca(ca_dir)

    opts = Options(
        listen_host="127.0.0.1",
        listen_port=listen_port,
        confdir=str(ca_dir),
        ssl_insecure=False,
    )
    master = DumpMaster(opts, with_termlog=False, with_dumper=False)
    master.addons.add(addon)
    await master.run()
