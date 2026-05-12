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


def _destroy() -> None:
    import subprocess
    _resolve_paths()
    port = cfg.PROXY_PORT
    result = subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)
    if result.returncode == 0:
        print(f"[agentbox] 프록시 프로세스 종료 완료 (:{port})")
    else:
        print(f"[agentbox] :{port} 에서 실행 중인 프로세스가 없습니다.")


def _reset() -> None:
    import subprocess
    import time
    _resolve_paths()
    port = cfg.PROXY_PORT
    result = subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)
    if result.returncode == 0:
        print(f"[agentbox] 기존 프로세스 종료 (:{port}). 재시작 중...")
        time.sleep(0.5)
    log_file = _PROJ_ROOT / "logs" / "agentbox-run.log"
    (_PROJ_ROOT / "logs").mkdir(parents=True, exist_ok=True)
    with open(log_file, "w") as lf:
        proc = subprocess.Popen(
            ["agentbox", "run"],
            stdout=lf,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    (_PROJ_ROOT / ".agentbox.pid").write_text(str(proc.pid))
    print(f"[agentbox] 프록시 백그라운드 재시작 완료 (pid {proc.pid})")
    print(f"[agentbox] 로그: {log_file}")


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

    _FOOTER = "\nMade by JeonMyeongHwan"

    parser = argparse.ArgumentParser(
        prog="agentbox",
        description=(
            "AgentBox -- AI 에이전트 트래픽을 MITM으로 가로채고,\n"
            "Bedrock으로 프롬프트를 검사하며, Zero-Knowledge 코드 접근을 강제하는 로컬 샌드박스."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "────────────────────────────────────────────────────────────\n"
            "일반적인 사용 흐름\n"
            "────────────────────────────────────────────────────────────\n"
            "  # 1. 최초 셋업 (한 번만)\n"
            "  agentbox set [-y]\n\n"
            "  # 2. 프로젝트 암호화 및 S3 등록 (프로젝트마다)\n"
            "  agentbox init ./myrepo [-y]\n\n"
            "  # 3. shell 에서 프록시 활성화 (새 터미널마다, source 필요)\n"
            "  agentbox on\n"
            "  agentbox off\n\n"
            "  # 4. 프록시 관리\n"
            "  agentbox reset    # 기존 프로세스 종료 후 재시작\n"
            "  agentbox destroy  # 프로세스 종료만\n"
            "  agentbox status   # 현재 상태 진단\n"
            "────────────────────────────────────────────────────────────\n"
            + _FOOTER
        ),
    )

    sub = parser.add_subparsers(dest="cmd", metavar="<command>")

    # ── set ──────────────────────────────────────────────────────────
    p_set = sub.add_parser(
        "set",
        help="[최초 셋업] deps + CA + shell 통합 + 프록시 백그라운드 시작 (통합 명령)",
        description=(
            "최초 1회 실행하는 통합 셋업 명령. 아래 5단계를 순서대로 수행하며 모두 idempotent.\n\n"
            "  1. 의존성 점검  : sops, aws CLI, boto3, pyyaml — 누락 시 자동 설치\n"
            "  2. 환경변수 점검: AWS_REGION, PROJECT_NAME — 미설정 시 ~/.bashrc 에 추가\n"
            "  3. CA 인증서    : certs/agentbox-ca.crt + mitmproxy-ca.pem 생성 (없을 때만)\n"
            "  4. Shell 통합   : agentbox on/off 함수를 ~/.bashrc 에 등록\n"
            "  5. 프록시 시작  : agentbox run 을 백그라운드로 실행 (이미 실행 중이면 생략)\n\n"
            "완료 후 대시보드: http://localhost:8000"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Made by JeonMyeongHwan",
    )
    p_set.add_argument("-y", "--yes", action="store_true", help="모든 확인 프롬프트 자동 수락")
    p_set.add_argument("--skip-deps-install", action="store_true", help="의존성 확인은 하되 설치는 생략")

    # ── init ─────────────────────────────────────────────────────────
    p_init = sub.add_parser(
        "init",
        help="[프로젝트 등록] 소스 암호화 → S3 업로드 → EC2/gRPC 연결 확인",
        description=(
            "프로젝트 디렉터리를 Zero-Knowledge 검사 환경에 등록하는 명령.\n\n"
            "  1. 필수 도구 확인 (sops, aws CLI, Python 패키지)\n"
            "  2. AWS 자격증명 / Terraform 출력값 감지\n"
            "  3. SOPS+KMS 로 소스 파일 암호화 후 S3 업로드\n"
            "  4. MCP EC2 health 엔드포인트 확인\n"
            "  5. Bedrock 인스펙터 gRPC 연결 확인\n"
            "  6. AgentBox 대시보드 URL 출력\n\n"
            "로그: logs/agentbox-init-<timestamp>.log"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "예시:\n"
            "  agentbox init ./myrepo\n"
            "  agentbox init ./myrepo --project-id proj42 -y\n"
            "  agentbox init ./myrepo --skip-deps\n\n"
            "Made by JeonMyeongHwan"
        ),
    )
    p_init.add_argument("dir", metavar="DIR", help="암호화 및 업로드할 프로젝트 디렉터리 경로")
    p_init.add_argument("--project-id", metavar="ID", default=None,
                        help="프로젝트 식별자 (기본값: 디렉터리 이름)")
    p_init.add_argument("--skip-deps", action="store_true",
                        help="의존성 점검 생략 (sops, aws CLI, Python 패키지)")
    p_init.add_argument("-y", "--yes", action="store_true",
                        help="의존성 설치 확인 프롬프트 자동 수락")

    # ── run ──────────────────────────────────────────────────────────
    sub.add_parser(
        "run",
        help="[프록시 실행] mitmproxy + 대시보드 서버를 포그라운드로 시작",
        description=(
            "mitmproxy MITM 프록시와 FastAPI 대시보드를 포그라운드로 동시 실행.\n\n"
            "  Proxy  : http://127.0.0.1:<PROXY_PORT>  (기본 8080)\n"
            "  Web UI : http://localhost:<API_PORT>     (기본 8000)\n\n"
            "Claude Code 트래픽을 프록시로 라우팅하려면:\n"
            "  export HTTPS_PROXY=http://127.0.0.1:8080\n"
            "또는 'agentbox on' 을 사용하세요 (agentbox set 이후 사용 가능)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Made by JeonMyeongHwan",
    )

    # ── reset ─────────────────────────────────────────────────────────
    sub.add_parser(
        "reset",
        help="[재시작] 기존 agentbox 프로세스를 종료하고 run 을 다시 실행",
        description=(
            "PROXY_PORT(기본 8080)에서 실행 중인 agentbox 프로세스를 fuser 로 종료한 뒤\n"
            "agentbox run 을 포그라운드로 다시 실행합니다.\n\n"
            "  실행 중인 프로세스가 없으면 바로 run 을 시작합니다."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Made by JeonMyeongHwan",
    )

    # ── destroy ───────────────────────────────────────────────────────
    sub.add_parser(
        "destroy",
        help="[프로세스 종료] 실행 중인 agentbox 프록시 프로세스만 종료 (재시작 없음)",
        description=(
            "PROXY_PORT(기본 8080)에서 실행 중인 agentbox 프로세스를 fuser 로 종료합니다.\n"
            "재시작 없이 종료만 합니다.\n\n"
            "  재시작이 필요하면: agentbox reset"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Made by JeonMyeongHwan",
    )

    # ── ca ────────────────────────────────────────────────────────────
    sub.add_parser(
        "ca",
        help="[CA 관리] 로컬 CA 인증서 생성 또는 확인",
        description=(
            "CA_DIR 에 AgentBox CA 인증서(agentbox-ca.crt, mitmproxy-ca.pem)가\n"
            "없으면 생성하고, 있으면 경로만 출력합니다.\n\n"
            "시스템 trust store 등록은 별도로 필요합니다:\n"
            "  bash scripts/install_ca.sh"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Made by JeonMyeongHwan",
    )

    # ── setup ─────────────────────────────────────────────────────────
    sub.add_parser(
        "setup",
        help="[Shell 통합] agentbox on/off 함수를 ~/.bashrc 에 등록",
        description=(
            "~/.bashrc 에 agentbox on/off shell 함수를 추가합니다 (idempotent).\n\n"
            "  agentbox on  -- HTTPS_PROXY 설정, 프록시 미실행 시 백그라운드 자동 시작\n"
            "  agentbox off -- HTTPS_PROXY 해제, 백그라운드 프록시 종료\n\n"
            "실행 후 반드시 shell 을 재로드하세요:\n"
            "  source ~/.bashrc"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Made by JeonMyeongHwan",
    )

    # ── status ────────────────────────────────────────────────────────
    # on / off (public shell wrappers)
    sub.add_parser(
        "on",
        help="[shell] HTTPS_PROXY 설정 (eval 패턴, ~/.bashrc 함수에서 호출)",
        description=(
            "HTTPS_PROXY 및 NODE_EXTRA_CA_CERTS 를 현재 shell 에 설정합니다.",
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Made by JeonMyeongHwan",
    )
    sub.add_parser(
        "off",
        help="[shell] HTTPS_PROXY 해제 (eval 패턴, ~/.bashrc 함수에서 호출)",
        description=(
            "HTTPS_PROXY 및 NODE_EXTRA_CA_CERTS 를 현재 shell 에서 해제합니다.",
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Made by JeonMyeongHwan",
    )
    sub.add_parser(
        "_on",
        help=argparse.SUPPRESS,
        description="eval "" 으로 호출됨",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub.add_parser(
        "_off",
        help=argparse.SUPPRESS,
        description="eval "" 으로 호출됨",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    p_status = sub.add_parser(
        "status",
        help="[진단] 현재 AgentBox 런타임 상태 출력",
        description=(
            "읽기 전용 진단 명령. 아래 항목을 출력합니다:\n\n"
            "  - 대시보드 URL 및 프록시 포트\n"
            "  - 의존성(sops, aws CLI) 설치 여부\n"
            "  - 프록시 활성화 여부 (HTTPS_PROXY 환경변수)\n"
            "  - 마지막 agentbox init 정보\n"
            "  - EC2/gRPC 연결 상태"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Made by JeonMyeongHwan",
    )
    p_status.add_argument("--json", action="store_true", help="JSON 형식으로 출력")

    args = parser.parse_args()

    if args.cmd == "set":
        from agentbox.set_cmd import run_set
        sys.exit(run_set(args))
    elif args.cmd == "init":
        from agentbox.init_cmd import init
        sys.exit(init(args.dir, args.project_id, args.skip_deps, args.yes))
    elif args.cmd == "run":
        _run()
    elif args.cmd == "reset":
        _reset()
    elif args.cmd == "destroy":
        _destroy()
    elif args.cmd in ("on", "_on"):
        from agentbox._activate import on_command
        sys.exit(on_command())
    elif args.cmd in ("off", "_off"):
        from agentbox._activate import off_command
        sys.exit(off_command())
    elif args.cmd == "ca":
        _ca_install()
    elif args.cmd == "setup":
        _setup_shell()
    elif args.cmd == "status":
        from agentbox.status_cmd import run_status
        sys.exit(run_status(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
