import asyncio
import sys
from pathlib import Path

import uvicorn

from agentbox.config import cfg
from agentbox.logging_setup import setup as setup_logging

# Resolve relative config paths to the project root (parent of src/).
# Works for editable installs (pip install -e).
_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_paths() -> None:
    if not Path(cfg.CA_DIR).is_absolute():
        cfg.CA_DIR = str(_PROJ_ROOT / cfg.CA_DIR)
    if not Path(cfg.DB_PATH).is_absolute():
        cfg.DB_PATH = str(_PROJ_ROOT / cfg.DB_PATH)


def _run() -> None:
    setup_logging()
    _resolve_paths()

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

    print(f"  AgentBox starting...")
    print(f"  Proxy : http://127.0.0.1:{cfg.PROXY_PORT}")
    print(f"  Web UI: http://localhost:{cfg.API_PORT}")
    print(f"  CA    : {cfg.CA_DIR}/agentbox-ca.crt")
    print(f"  To activate in a shell: source {_PROJ_ROOT}/scripts/activate.sh")
    print()

    async def _main() -> None:
        server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=cfg.API_PORT, log_level="warning"))
        tasks = [
            start_master(addon, cfg.PROXY_PORT),
            server.serve(),
        ]
        if cfg.TRANSPARENT_MODE:
            from agentbox.proxy.ebpf_stats import run_stats_loop
            stats_log = cfg.EBPF_STATS_LOG
            if not Path(stats_log).is_absolute():
                stats_log = str(_PROJ_ROOT / stats_log)
            tasks.append(run_stats_loop(stats_log))
        await asyncio.gather(*tasks)

    asyncio.run(_main())


def _ca_install() -> None:
    _resolve_paths()
    from agentbox.proxy.ca import ensure_ca
    ca_crt, _ = ensure_ca(Path(cfg.CA_DIR))
    print(f"CA certificate ready: {ca_crt}")
    print("Run scripts/install_ca.sh to register in system trust store.")


def _setup_shell() -> None:
    _resolve_paths()
    scripts_dir = _PROJ_ROOT / "scripts"
    bashrc = Path.home() / ".bashrc"

    marker = "# AgentBox shell integration"
    integration = f"""
{marker}
unalias agentbox 2>/dev/null
agentbox() {{
    case "$1" in
        on)  source {scripts_dir}/activate.sh ;;
        off) source {scripts_dir}/deactivate.sh ;;
        *)   command agentbox "$@" ;;
    esac
}}
"""
    content = bashrc.read_text() if bashrc.exists() else ""
    if marker in content:
        print("Shell integration already installed in ~/.bashrc")
        return
    with open(bashrc, "a") as f:
        f.write(integration)
    print("Shell integration added to ~/.bashrc")
    print("Run:  source ~/.bashrc")
    print("Then: agentbox on   # activate proxy")
    print("      agentbox off  # deactivate proxy")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="agentbox",
        description=(
            "AgentBox -- local MITM sandbox that intercepts AI agent traffic,\n"
            "inspects prompts via Bedrock, and enforces zero-knowledge code access."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  agentbox run                        # start proxy (port 8080) + web UI (port 8000)\n"
            "  agentbox ca                         # generate/verify CA certificate\n"
            "  agentbox setup                      # install shell on/off helpers into ~/.bashrc\n"
            "  agentbox init ./myrepo              # encrypt & upload myrepo, verify EC2\n"
            "  agentbox init ./myrepo -y           # same, auto-accept dependency installs\n"
            "  agentbox init ./myrepo --project-id proj42\n"
            "\n"
            "After 'agentbox setup', reload your shell and use:\n"
            "  agentbox on   # activate proxy (sets http_proxy / https_proxy)\n"
            "  agentbox off  # deactivate proxy"
        ),
    )

    sub = parser.add_subparsers(dest="cmd", metavar="<command>")

    sub.add_parser(
        "run",
        help="Start proxy + web UI server",
        description=(
            "Start the mitmproxy MITM proxy and the FastAPI web UI server.\n\n"
            "  Proxy  listens on http://127.0.0.1:<PROXY_PORT>  (default 8080)\n"
            "  Web UI listens on http://localhost:<API_PORT>     (default 8000)\n\n"
            "Set HTTPS_PROXY=http://127.0.0.1:8080 (or run 'agentbox on') to\n"
            "route AI agent traffic through the sandbox."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub.add_parser(
        "ca",
        help="Generate / verify the local CA certificate",
        description=(
            "Ensure the AgentBox CA certificate exists in the configured CA_DIR.\n\n"
            "Run scripts/install_ca.sh afterwards to register the certificate in\n"
            "the system trust store so TLS interception works without warnings."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub.add_parser(
        "setup",
        help="Install agentbox on/off shell helpers into ~/.bashrc",
        description=(
            "Append shell functions to ~/.bashrc that let you type:\n\n"
            "  agentbox on   -- set http_proxy / https_proxy to route through the proxy\n"
            "  agentbox off  -- unset those variables\n\n"
            "This is a one-time operation; re-running it is safe (idempotent).\n"
            "Remember to run 'source ~/.bashrc' or open a new terminal afterwards."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    p_set = sub.add_parser(
        "set",
        help="Unified environment setup (deps + CA + env + bashrc integration)",
        description=(
            "Pre-check the environment before using agentbox.\n\n"
            "Steps performed (idempotent):\n"
            "  1. Check sops, aws CLI, boto3, pyyaml — auto-install on prompt\n"
            "  2. Check AWS_REGION / PROJECT_NAME — add to ~/.bashrc if missing\n"
            "  3. Generate CA cert if missing (calls 'agentbox ca' internally)\n"
            "  4. Register 'agentbox on/off' shell helpers in ~/.bashrc\n\n"
            "Activation stays manual: run 'agentbox on' in each shell where\n"
            "you want the proxy enabled."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_set.add_argument("-y", "--yes", action="store_true", help="Auto-accept all prompts")
    p_set.add_argument("--skip-deps-install", action="store_true", help="Check deps but don't install")

    p_status = sub.add_parser(
        "status",
        help="Print current AgentBox runtime state (URL, deps, proxy, last init, connectivity)",
        description=(
            "Read-only diagnostic. Prints 5 status lines and a 'Made by' footer.\n"
            "Use --json for machine-readable output."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_status.add_argument("--json", action="store_true", help="Output as JSON")

    p_init = sub.add_parser(
        "init",
        help="Encrypt + upload a project, verify EC2, print dashboard URL",
        description=(
            "Prepare a local project directory for zero-knowledge inspection:\n\n"
            "  1. Check required tools (sops, aws CLI) and Python packages\n"
            "  2. Detect AWS credentials / Terraform outputs\n"
            "  3. Encrypt source files with SOPS and upload to S3\n"
            "  4. Verify the MCP server health endpoint on EC2\n"
            "  5. Verify gRPC connectivity to the Bedrock inspector\n"
            "  6. Print the AgentBox dashboard URL\n\n"
            "Logs are written to logs/agentbox-init-<timestamp>.log."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  agentbox init ./myrepo\n"
            "  agentbox init ./myrepo --project-id proj42 -y\n"
            "  agentbox init ./myrepo --skip-deps"
        ),
    )
    p_init.add_argument(
        "dir",
        metavar="DIR",
        help="Path to the project directory to encrypt and upload",
    )
    p_init.add_argument(
        "--project-id",
        metavar="ID",
        default=None,
        help="Override the project identifier (default: directory name)",
    )
    p_init.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip dependency checks (sops, aws CLI, Python packages)",
    )
    p_init.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Auto-accept all dependency install prompts without asking",
    )
    args = parser.parse_args()

    if args.cmd == "run":
        _run()
    elif args.cmd == "ca":
        _ca_install()
    elif args.cmd == "setup":
        _setup_shell()
    elif args.cmd == "set":
        from agentbox.set_cmd import run_set
        sys.exit(run_set(args))
    elif args.cmd == "status":
        from agentbox.status_cmd import run_status
        sys.exit(run_status(args))
    elif args.cmd == "init":
        from agentbox.init_cmd import init
        sys.exit(init(args.dir, args.project_id, args.skip_deps, args.yes))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
