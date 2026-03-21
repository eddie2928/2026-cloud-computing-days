---
name: sell-signal
description: "코스피/코스닥 레버리지·인버스 ETF 양방향 매매 - 매도 시그널 분석 및 주문 파라미터 결정. 0.6% 익절, 목표수익률 판단, 장마감 청산, 서킷브레이커를 자동 판단한다."
version: 0.1.0
metadata:
  openclaw:
    requires:
      env:
        - KIWOOM_APP_KEY
        - KIWOOM_APP_SECRET
      bins:
        - python3
    primaryEnv: KIWOOM_APP_KEY
    emoji: "📉"
---

# 매도 시그널 스킬 (sell-signal)

코스피/코스닥 레버리지·인버스 ETF 양방향 스캘핑 매매의 매도 판단을 수행한다.

## 실행 주기

5분봉 캔들 마감 시점마다 1회 호출 (장중 09:00~15:20).
매수 스킬(buy-signal)보다 먼저 호출되어야 한다 (플래그 선행 기록).
15:20 강제 청산 실행 후 더 이상 호출하지 않는다.

## 입력 데이터

### 필수 데이터
1. **보유 포지션 정보** — 종목코드, 수량, 평균매수가, 현재가, 평가손익률
2. **예수금 (D+2 결제 완료 현금)**
3. **당일 총 실현 손익**
4. **당일 미실현 평가 손익**
5. **당일 총 거래대금**
6. **현재 시각 (KST)**
7. **`trading_state.json` 현재 상태**

### 참고 데이터 (LLM 보조 레이어용)
- 코스피/코스닥 지수 등락률
- 외국인/기관 매매 동향
- 시황 뉴스

## 판단 프로세스

### STEP 0: 서킷 브레이커 확인

당일 실현 손실 + 미실현 평가 손실 합계가 예수금의 **-2% 이하**인지 확인:
- **YES → 서킷 브레이커 발동:**
  1. `trading_state.json`에 `circuit_breaker: true` 기록
  2. 보유 중인 **모든 종목**에 대해 `sell` + `circuit_breaker` 모드 출력
  3. 프로세스 종료

이미 `circuit_breaker: true`이고 보유 포지션이 없으면 → `hold` 출력.

### STEP 1: 장 마감 강제 청산 확인

- 현재 시각 >= **15:10** → `trading_state.json`에 `eod_liquidation_mode: true` 기록
- 현재 시각 >= **15:20** → 보유 중인 **모든 종목** 전량 시장가 매도 (`eod_liquidation` 모드)
- 이 규칙은 STEP 2~3보다 우선

### STEP 2: 결정론적 레이어 — 매도 모드 판별

**모드 1 — 익절 매도 (종목별 개별 평가):**

보유 종목 각각에 대해:
- 현재 익절 기준 = `trading_state.json`의 `llm_take_profit_override` (기본 0.6%)
- 현재가 >= 평균매수가 × (1 + 익절기준/100) ?
- **YES → 해당 종목 전량 매도 (`take_profit` 모드)**

**모드 2 — 목표수익률 도달 확인:**

- 당일 총 실현 수익 >= 당일 총 거래대금 × 0.004 ?
- **YES → `trading_state.json`에 `daily_target_reached: true` 기록**
- 보유 중인 포지션은 모드 1 익절 조건으로 계속 청산

### STEP 3: LLM 보조 레이어

결정론적 레이어 판단과 **병렬로** (최대 5초) 다음을 평가:

**A. 익절 기준 사전 조정 (0.6% 도달 전 종목에만 적용):**
- 급등 모멘텀 감지 (최근 3개 5분봉 연속 양봉 + 거래량 증가) → 0.8%~1.5%로 상향
- `trading_state.json`의 `llm_take_profit_override`에 기록
- **0.6% 이미 도달한 종목에는 적용 불가 — 즉시 매도 실행**

**B. 시장 위험 판단:**
- 코스피/코스닥 지수 -2% 이상 급락 → `trading_state.json`에 `market_risk: true`
- 외국인/기관 대규모 순매도 전환 → `market_risk: true`
- `market_risk: true` 시: 매수 스킬에 수량 최소화 신호 전달

**C. 손절 권고 (결정론적 레이어에 없는 추가 판단):**
- 시장 급락 + 보유 레버리지 포지션 손실 확대 중 → `stop_loss_triggered: true`
- 이 플래그는 매수 스킬의 물타기 모드 진입 판단에 참고됨

**LLM 타임아웃 (5초 초과) 시:** LLM 보조 판단 전체 스킵. 결정론적 결과만 실행. `llm_take_profit_override`는 이전 값 유지.

### STEP 4: 출력

매도할 종목이 있는 경우, **종목별로** JSON 출력:

```json
{
  "action": "sell",
  "mode": "take_profit|daily_target|eod_liquidation|circuit_breaker",
  "stock_code": "종목코드",
  "stock_name": "종목명",
  "quantity": 보유수량전체,
  "price_type": "market",
  "deterministic_signal": true,
  "llm_quantity_ratio": 1.0,
  "reasoning": "0.6% 익절 조건 달성. 현재가 XXX원, 평균매수가 XXX원, 수익률 +0.62%",
  "flags": {
    "daily_target_reached": false,
    "market_risk": false,
    "circuit_breaker": false,
    "eod_liquidation_mode": false
  }
}
```

복수 종목 매도 시 JSON 배열로 출력.

매도하지 않는 경우:

```json
{
  "action": "hold",
  "mode": "none",
  "stock_code": "",
  "stock_name": "",
  "quantity": 0,
  "price_type": "",
  "deterministic_signal": false,
  "llm_quantity_ratio": 0,
  "reasoning": "매도 조건 미충족. 보유 종목 X개, 최고 수익률 +0.3%",
  "flags": { ... }
}
```

### STEP 5: 로깅

모든 호출 결과를 `trading_log.jsonl`에 append:

```json
{
  "timestamp": "ISO8601+09:00",
  "skill": "sell-signal",
  "cycle": 호출순번,
  "deterministic_result": {"signals": [{"stock": "코드", "mode": "모드", "trigger": "조건"}]},
  "llm_adjustment": {"take_profit_override": 0.6, "market_risk": false, "reasoning": "이유"},
  "final_output": [{"action": "sell/hold", "stock_code": "코드", "quantity": 수량}],
  "flags": { ... }
}
```

### STEP 6: 상태 업데이트

매 호출 시 `trading_state.json`의 `last_updated`를 현재 시각으로 갱신.
장 시작 시 (09:00 첫 호출) 모든 플래그를 초기화:
- `daily_target_reached: false`
- `market_risk: false`
- `stop_loss_triggered: false`
- `eod_liquidation_mode: false`
- `circuit_breaker: false`
- `llm_take_profit_override: 0.6`
- `averaging_down_log: {}`

## 오류 처리

| 상황 | 대응 |
|---|---|
| 보유 포지션 데이터 미수신 | `hold` 출력, 로그에 에러 기록 |
| 키움 API 연결 끊김 | `hold` 출력 (기존 익절 주문은 서버측 유지) |
| LLM 타임아웃 (5초+) | LLM 스킵, 결정론적 결과만 실행 |
| trading_state.json 읽기 실패 | 안전 모드: 익절 매도만 실행 (기본 0.6%) |
