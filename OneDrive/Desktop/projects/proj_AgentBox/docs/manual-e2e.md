# Manual E2E Checklist — Task-7

수동 E2E 검증. 각 단계를 순서대로 실행하고 OK/FAIL을 기록한다.

| # | 단계 | 명령 / 확인 내용 | 결과 |
|---|---|---|---|
| 1 | 인프라 배포 | `./scripts/deploy.sh -auto-approve` 통과, `terraform output -raw app_public_ip` 비어있지 않음 | ☐ OK / ☐ FAIL |
| 2 | 로컬 셋업 | `agentbox set -y` 통과, 출력에 `Step 7a: proxy LISTEN OK`, `Step 7b: gRPC TCP OK`, `Step 7c: mTLS handshake OK` 3줄 모두 포함 | ☐ OK / ☐ FAIL |
| 3 | doctor 전체 점검 | `agentbox doctor` → D1~D9 9개 항목 모두 OK, exit 0 | ☐ OK / ☐ FAIL |
| 4 | HTTPS_PROXY 설정 | 새 터미널: `agentbox on`, `echo $HTTPS_PROXY` → `http://127.0.0.1:8080` | ☐ OK / ☐ FAIL |
| 5 | Claude Code 실행 | 또 다른 터미널 (별도 Claude Code): `claude` 실행 | ☐ OK / ☐ FAIL |
| 6 | 프록시 통과 확인 | Claude Code에 "ping" 등 임의 prompt 전송 | ☐ OK / ☐ FAIL |
| 7 | 대시보드 확인 | `http://localhost:8000/audit` 새 행 표시 (request_id, prompt 미리보기) | ☐ OK / ☐ FAIL |
| 8 | EC2 gRPC 로그 | `aws ssm send-command ... 'journalctl -u agentbox-grpc -n 50'` 출력에 `Inspect` RPC 로그 | ☐ OK / ☐ FAIL |
| 9 | 정리 | `agentbox off`, `agentbox destroy` → HTTPS_PROXY 해제 + 프록시 종료 | ☐ OK / ☐ FAIL |

## 검증 일시

- 날짜:
- 환경:
- 담당자:
