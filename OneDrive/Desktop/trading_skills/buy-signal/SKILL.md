---
name: buy-signal
description: "코스피/코스닥 레버리지·인버스 ETF 양방향 매매 - 매수 시그널 분석 및 주문 파라미터 결정. 5분봉 파라볼릭SAR+RSI 기반 스캘핑, 물타기, 인버스 헤지 매수를 자동 판단한다."
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
    emoji: "📈"
---

# 매수 시그널 스킬 (buy-signal)

코스피/코스닥 레버리지·인버스 ETF 양방향 스캘핑 매매의 매수 판단을 수행한다.

## 실행 주기

5분봉 캔들 마감 시점마다 1회 호출 (장중 09:00~15:10).
15:10 이후에는 이 스킬을 호출하지 않는다.

## 입력 데이터

이 스킬이 호출될 때 다음 데이터가 제공되어야 한다:

### 필수 데이터
1. **5분봉 OHLCV 데이터** (최근 100개 캔들) — 코스피/코스닥 레버리지 ETF
2. **파라볼릭 SAR 값** (af=0.02, maxAF=0.2) — 5분봉, 일봉, 주봉
3. **RSI 값** (Period=10) — 5분봉
4. **스토캐스틱 슬로우** (K=12, D=5) — 일봉, 주봉
5. **보유 포지션 정보** — 종목코드, 수량, 평균매수가, 평가손익률
6. **예수금 (D+2 결제 완료 현금)**
7. **당일 실현 손익 + 미실현 평가 손익**
8. **`trading_state.json` 현재 상태**

### 참고 데이터 (LLM 보조 레이어용)
- 전일 미국 시장 지수 (나스닥, S&P500)
- 외국인/기관 매매 동향
- 시황 뉴스

## 판단 프로세스

### STEP 0: 매수 차단 조건 확인

아래 조건 중 **하나라도 해당**되면 즉시 `hold` 출력하고 종료:
- `trading_state.json`의 `daily_target_reached` == true
- `trading_state.json`의 `circuit_breaker` == true
- `trading_state.json`의 `eod_liquidation_mode` == true
- 현재 시각 >= 15:10 KST
- 시세 데이터가 30초 이상 지연/미수신
- 당일 실현 손실 + 미실현 평가 손실 합계 <= 예수금의 -2% (서킷 브레이커 발동)

**차단하지 않지만 참고하는 플래그:**
- `market_risk` == true → 차단 아님, STEP 3에서 LLM 수량 비율을 최소(0.5)로 강제 적용
- `stop_loss_triggered` == true → 차단 아님, STEP 1에서 물타기 모드 진입 조건 평가에 참고 (손절 직후 물타기 여부 판단)

서킷 브레이커 발동 시:
1. `trading_state.json`에 `circuit_breaker: true` 기록
2. `hold` 출력

### STEP 1: 결정론적 레이어 — 모드 판별

**모드 우선순위** (위에서부터 먼저 평가):

> **설계 결정:** 모드 2(물타기, -10%)를 모드 3(헤지, -5%)보다 먼저 평가한다. -10% 손실 종목은 헤지보다 물타기가 우선이며, -5%~-10% 구간은 자연스럽게 헤지로 처리된다. 물타기 조건(스토캐스틱+파라볼릭) 미충족 시 모드 3으로 폴스루된다.

1. **모드 2 — 물타기 매수 확인**
   - 보유 종목 중 평가손실률 >= -10%인 종목이 있는가?
   - 해당 종목의 `averaging_down_log`에서 오늘 물타기 횟수가 0인가?
   - 스토캐스틱 슬로우 주봉: 매수 신호 (%K가 %D를 상향 돌파)?
   - 파라볼릭 SAR 일봉: 매수 신호?
   - **모두 YES → 모드 2 실행**

2. **모드 3 — 인버스 헤지 매수 확인**
   - 레버리지 보유 종목 중 평가손실률 >= -5%인 종목이 있는가?
   - 스토캐스틱 슬로우 주봉: 매도 신호 (%K가 %D를 하향 돌파)?
   - 파라볼릭 SAR 일봉: 매도 신호 **AND** 스토캐스틱 슬로우 일봉 %K >= 83?
   - **모두 YES → 모드 3 실행**

3. **모드 1 — 일반 매수 (스캘핑) 확인**
   - 5분봉 파라볼릭 SAR: 매수 신호 (SAR이 가격 아래로 전환)?
   - 5분봉 RSI < 30 (과매도)?
   - **모두 YES → 모드 1 실행**

4. 어떤 모드도 해당 안 됨 → `hold` 출력

### STEP 2: 종목 및 수량 결정

**모드 1 (스캘핑):**
- 종목: 시그널 발생 시장의 레버리지 ETF (코스피→122630, 코스닥→233740)
- 양쪽 동시 발생 시: 해당 ETF의 현재 5분봉 캔들 거래량이 큰 종목 선택
- 기본 수량 = floor(예수금 × 0.5 / 현재가)
- 총 노출 한도 확인: 기존 포지션 평가금액 + 신규 매수 금액 <= 예수금 × 1.0

**모드 2 (물타기):**
- 종목: 평가손실 -10% 이상인 보유 종목과 동일. 복수 종목 해당 시 손실률이 가장 큰(가장 부정적인) 종목 우선.
- 기본 수량 = floor(예수금 × 0.3 / 현재가)
- 총 노출 한도 확인: 기존 포지션 평가금액 + 신규 매수 금액 <= 예수금 × 1.0

**모드 3 (인버스 헤지):**
- 종목: 손실 중인 레버리지의 반대 인버스 ETF (코스피 레버리지 손실→252670, 코스닥 레버리지 손실→251340)
- 기본 수량 = floor(예수금 × 0.3 / 현재가)
- 총 노출 한도 확인: 기존 포지션 평가금액 + 신규 매수 금액 <= 예수금 × 1.0
  > **설계 결정:** 스펙은 헤지 수량을 명시하지 않음. 물타기와 동일한 30%를 적용하여 일관성 유지.

**공통: 수량이 0 이하인 경우** → 예수금 부족으로 판단, `hold` 출력 (reasoning: "예수금 부족으로 매수 불가")

### STEP 3: LLM 보조 레이어 — 수량 조절

결정론적 레이어가 매수 신호를 확인한 후, 다음 참고 데이터를 분석하여 **수량 비율(quantity_ratio)을 0.5~1.0 범위에서 결정**한다:

**평가 기준:**
- 전일 미국 시장 (나스닥/S&P500)이 -1% 이상 하락 → 비율 하향 (0.6~0.7)
- 외국인/기관이 당일 순매도 전환 → 비율 하향 (0.7~0.8)
- 악재 뉴스 (금리 인상, 지정학적 리스크 등) → 비율 하향 (0.5~0.7)
- 시장 충격 이벤트 (서킷브레이커, 전쟁 등) → 비율 최소 (0.5)
- 모든 참고 데이터가 중립/긍정적 → 비율 1.0

**제약 조건:**
- 최소 비율: 0.5 (절대 0.5 미만으로 줄일 수 없음)
- 최대 비율: 1.0
- LLM 응답 타임아웃: 5초. 초과 시 비율 = 1.0으로 고정하고 결정론적 결과 그대로 실행.

**최종 수량** = floor(기본 수량 × quantity_ratio)

### STEP 4: 출력

JSON 형식으로 출력:

```json
{
  "action": "buy",
  "mode": "scalping|averaging_down|hedge",
  "stock_code": "종목코드",
  "stock_name": "종목명",
  "quantity": 최종수량,
  "price_type": "market",
  "deterministic_signal": true,
  "llm_quantity_ratio": 0.85,
  "reasoning": "결정론적 판단 근거 + LLM 조정 이유",
  "flags": {
    "daily_target_reached": false,
    "market_risk": false,
    "circuit_breaker": false,
    "eod_liquidation_mode": false
  }
}
```

매수하지 않는 경우:

```json
{
  "action": "hold",
  "mode": "none",
  "stock_code": "",
  "stock_name": "",
  "quantity": 0,
  "price_type": "",
  "deterministic_signal": false,
  "llm_quantity_ratio": 0.0,
  "reasoning": "매수 조건 미충족 또는 차단 조건 해당",
  "flags": { ... }
}
```

### STEP 5: 로깅

모든 호출 결과를 `trading_log.jsonl`에 append:

```json
{
  "timestamp": "ISO8601+09:00",
  "skill": "buy-signal",
  "cycle": 호출순번,
  "deterministic_result": {"signal": true/false, "mode": "모드", "stock": "코드", "base_quantity": 수량},
  "llm_adjustment": {"quantity_ratio": 비율, "reasoning": "이유"},
  "final_output": {"action": "buy/hold", "stock_code": "코드", "quantity": 최종수량},
  "flags": { ... }
}
```

### STEP 6: 상태 업데이트

물타기 매수 실행 시 `trading_state.json`의 `averaging_down_log`에 해당 종목 카운트 +1 기록.
`last_updated` 필드를 현재 시각으로 갱신.

## 오류 처리

| 상황 | 대응 |
|---|---|
| 시세 데이터 30초+ 지연 | `hold` 출력 |
| 키움 API 연결 끊김 | `hold` 출력, 로그에 에러 기록 |
| LLM 타임아웃 (5초+) | LLM 스킵, quantity_ratio = 1.0 |
| trading_state.json 읽기 실패 | 안전 모드: `hold` 출력 |
| 부분 체결 발생 | 다음 사이클에서 재평가 |
