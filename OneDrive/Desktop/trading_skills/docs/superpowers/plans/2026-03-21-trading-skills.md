# OpenClaw Trading Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create two OpenClaw skills (buy-signal, sell-signal) that implement the hybrid bi-directional leveraged/inverse ETF scalping strategy from the PDF spec.

**Architecture:** Each skill is a SKILL.md file with YAML frontmatter and markdown instructions that teach the OpenClaw agent deterministic trading rules + LLM-assisted adjustments. Skills communicate via a shared `trading_state.json` file and log decisions to `trading_log.jsonl`.

**Tech Stack:** OpenClaw SKILL.md format (YAML frontmatter + Markdown), python3 (for `ta` library indicator calculation referenced in instructions), Kiwoom Securities Open API (external, not implemented here)

**Spec:** `docs/superpowers/specs/2026-03-21-trading-skills-design.md`

---

## File Structure

```
trading_skills/
�뵜������ buy-signal/
�봻   �뵜������ SKILL.md                    # 留ㅼ닔 �뒪�궗 - 硫붿씤 �뒪�궗 �뙆�씪
�봻   �뵒������ references/
�봻       �뵒������ strategy.md             # 留ㅼ닔 �쟾�왂 李몄“ 臾몄꽌 (Agent�슜)
�뵜������ sell-signal/
�봻   �뵜������ SKILL.md                    # 留ㅻ룄 �뒪�궗 - 硫붿씤 �뒪�궗 �뙆�씪
�봻   �뵒������ references/
�봻       �뵒������ strategy.md             # 留ㅻ룄 �쟾�왂 李몄“ 臾몄꽌 (Agent�슜)
�뵜������ trading_state.json              # �뒪�궗 媛� 怨듭쑀 �긽�깭 �뀥�뵆由�
�뵜������ docs/
�봻   �뵒������ superpowers/
�봻       �뵜������ specs/
�봻       �봻   �뵒������ 2026-03-21-trading-skills-design.md
�봻       �뵒������ plans/
�봻           �뵒������ 2026-03-21-trading-skills.md  (this file)
�뵒������ [!!珥덇린諛�!!]�젅踰꾨━吏� �뼇諛⑺뼢 留ㅻℓ_臾쇳��湲� 理쒖쥌.pdf
```

---

### Task 1: Create shared trading state template

**Files:**
- Create: `trading_state.json`

This is the inter-skill communication file. Both skills read/write this file to coordinate.

- [ ] **Step 1: Create `trading_state.json`**

```json
{
  "daily_target_reached": false,
  "market_risk": false,
  "stop_loss_triggered": false,
  "eod_liquidation_mode": false,
  "circuit_breaker": false,
  "llm_take_profit_override": 0.6,
  "averaging_down_log": {},
  "last_updated": ""
}
```

The `averaging_down_log` tracks per-stock daily averaging-down counts: `{"122630": 1, "233740": 0}`.

- [ ] **Step 2: Verify JSON is valid**

Run: `python3 -c "import json; json.load(open('trading_state.json')); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add trading_state.json
git commit -m "feat: add trading_state.json inter-skill communication template"
```

---

### Task 2: Create buy-signal strategy reference

**Files:**
- Create: `buy-signal/references/strategy.md`

This file summarizes the buy-side strategy from the PDF so the Agent has all rules in context during execution. It must be precise and include all numeric parameters.

- [ ] **Step 1: Create directory**

```bash
mkdir -p buy-signal/references
```

- [ ] **Step 2: Write `buy-signal/references/strategy.md`**

```markdown
# 留ㅼ닔 �쟾�왂 李몄“ 臾몄꽌

## 嫄곕옒 醫낅ぉ

| 醫낅ぉ紐� | 肄붾뱶 | �쑀�삎 | �떆�옣 |
|---|---|---|---|
| KODEX �젅踰꾨━吏� | 122630 | �젅踰꾨━吏� | 肄붿뒪�뵾 |
| KODEX 肄붿뒪�떏150�젅踰꾨━吏� | 233740 | �젅踰꾨━吏� | 肄붿뒪�떏 |
| KODEX 200�꽑臾쇱씤踰꾩뒪2X | 252670 | �씤踰꾩뒪 | 肄붿뒪�뵾 |
| KODEX 肄붿뒪�떏150�꽑臾쇱씤踰꾩뒪 | 251340 | �씤踰꾩뒪 | 肄붿뒪�떏 |

## 紐⑤뱶 1: �씪諛� 留ㅼ닔 (�뒪罹섑븨)

- 湲곗�� 李⑦듃: 5遺꾨큺
- �떆洹몃꼸 議곌굔 (AND):
  - �뙆�씪蹂쇰┃ SAR: af=0.02, maxAF=0.2 �넂 留ㅼ닔 �떊�샇 (SAR�씠 媛�寃� �븘�옒濡� �쟾�솚)
  - RSI: Period=10, LPercent=30 �넂 怨쇰ℓ�룄 (RSI < 30)
- 醫낅ぉ �꽑�깮: �떆洹몃꼸 諛쒖깮 �떆�옣�쓽 �젅踰꾨━吏� ETF. �뼇履� �룞�떆 �넂 嫄곕옒�웾 �겙 履� �슦�꽑.
- �닔�웾: �삁�닔湲�(D+2)�쓽 50% / �쁽�옱媛� = 二쇱닔 (�젙�닔 �궡由�)
- 珥� �끂異� �븳�룄: �삁�닔湲덉쓽 100% 珥덇낵 湲덉�� (�젅踰꾨━吏�+�씤踰꾩뒪 �빀�궛)

## 紐⑤뱶 2: 臾쇳��湲� 留ㅼ닔

- �듃由ш굅: 蹂댁쑀 醫낅ぉ �룊媛��넀�떎瑜� >= -10%
- �닔�웾: �삁�닔湲덉쓽 30% / �쁽�옱媛�
- �젣�븳: 醫낅ぉ�떦 1�씪 1�쉶 (averaging_down_log �솗�씤)
- 議곌굔 (AND):
  - �뒪�넗罹먯뒪�떛 �뒳濡쒖슦 二쇰큺 (K=12, D=5): 留ㅼ닔 �떊�샇 (%K媛� %D瑜� �긽�뼢 �룎�뙆)
  - �뙆�씪蹂쇰┃ SAR �씪遊� (af=0.02, maxAF=0.2): 留ㅼ닔 �떊�샇

## 紐⑤뱶 3: �씤踰꾩뒪 �뿤吏� 留ㅼ닔

- �듃由ш굅: �젅踰꾨━吏� �룷吏��뀡 �룊媛��넀�떎瑜� >= -5%
- ����긽: �빐�떦 �떆�옣�쓽 �씤踰꾩뒪 ETF (肄붿뒪�뵾�넂252670, 肄붿뒪�떏�넂251340)
- 議곌굔 (AND):
  - �뒪�넗罹먯뒪�떛 �뒳濡쒖슦 二쇰큺 (K=12, D=5): 留ㅻ룄 �떊�샇 (%K媛� %D瑜� �븯�뼢 �룎�뙆)
  - �뙆�씪蹂쇰┃ SAR �씪遊�: 留ㅻ룄 �떊�샇 AND �뒪�넗罹먯뒪�떛 �뒳濡쒖슦 �씪遊� %K >= 83

## �옄湲� 愿�由�

- 珥� 嫄곕옒���湲�: �삁�닔湲덉쓽 50% �씠�궡
- 珥� �끂異� �븳�룄: �삁�닔湲덉쓽 100%
- �떦�씪 理쒕�� �넀�떎: -2% (�꽌�궥 釉뚮젅�씠而� 諛쒕룞 �넂 利됱떆 �쟾泥� 留ㅻℓ 以묐떒)

## 留ㅼ닔 李⑤떒 議곌굔

�떎�쓬 以� �븯�굹�씪�룄 true�씠硫� 留ㅼ닔 湲덉��:
- trading_state.json�쓽 `daily_target_reached` == true
- trading_state.json�쓽 `circuit_breaker` == true
- trading_state.json�쓽 `eod_liquidation_mode` == true
- �쁽�옱 �떆媛� >= 15:10
- �떆�꽭 �뜲�씠�꽣 30珥� �씠�긽 誘몄닔�떊

## LLM 蹂댁“ �젅�씠�뼱

寃곗젙濡좎쟻 議곌굔 異⑹” �썑, LLM�씠 �닔�웾�쓣 50%~100% 踰붿쐞�뿉�꽌 議곗젅:
- �쟾�씪 誘멸뎅 �떆�옣 湲됰씫 �넂 �닔�웾 異뺤냼
- �쇅援��씤/湲곌�� ���洹쒕え 留ㅻ룄 �넂 �닔�웾 異뺤냼
- �븙�옱 �돱�뒪 �넂 �닔�웾 異뺤냼
- �떆�옣 異⑷꺽 �씠踰ㅽ듃 �넂 �닔�웾 理쒖냼(50%)

LLM ����엫�븘�썐 (5珥� 珥덇낵) �떆: 寃곗젙濡좎쟻 寃곌낵 洹몃��濡� �떎�뻾 (�닔�웾 100%)
```

- [ ] **Step 3: Commit**

```bash
git add buy-signal/references/strategy.md
git commit -m "feat: add buy-signal strategy reference document"
```

---

### Task 3: Create buy-signal SKILL.md

**Files:**
- Create: `buy-signal/SKILL.md`

The main buy skill file. Contains YAML frontmatter + full markdown instructions for the OpenClaw agent.

- [ ] **Step 1: Write `buy-signal/SKILL.md`**

````markdown
---
name: buy-signal
description: "肄붿뒪�뵾/肄붿뒪�떏 �젅踰꾨━吏�쨌�씤踰꾩뒪 ETF �뼇諛⑺뼢 留ㅻℓ - 留ㅼ닔 �떆洹몃꼸 遺꾩꽍 諛� 二쇰Ц �뙆�씪誘명꽣 寃곗젙. 5遺꾨큺 �뙆�씪蹂쇰┃SAR+RSI 湲곕컲 �뒪罹섑븨, 臾쇳��湲�, �씤踰꾩뒪 �뿤吏� 留ㅼ닔瑜� �옄�룞 �뙋�떒�븳�떎."
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
    emoji: "�윋�"
---

# 留ㅼ닔 �떆洹몃꼸 �뒪�궗 (buy-signal)

肄붿뒪�뵾/肄붿뒪�떏 �젅踰꾨━吏�쨌�씤踰꾩뒪 ETF �뼇諛⑺뼢 �뒪罹섑븨 留ㅻℓ�쓽 留ㅼ닔 �뙋�떒�쓣 �닔�뻾�븳�떎.

## �떎�뻾 二쇨린

5遺꾨큺 罹붾뱾 留덇컧 �떆�젏留덈떎 1�쉶 �샇異� (�옣以� 09:00~15:10).
15:10 �씠�썑�뿉�뒗 �씠 �뒪�궗�쓣 �샇異쒗븯吏� �븡�뒗�떎.

## �엯�젰 �뜲�씠�꽣

�씠 �뒪�궗�씠 �샇異쒕맆 �븣 �떎�쓬 �뜲�씠�꽣媛� �젣怨듬릺�뼱�빞 �븳�떎:

### �븘�닔 �뜲�씠�꽣
1. **5遺꾨큺 OHLCV �뜲�씠�꽣** (理쒓렐 100媛� 罹붾뱾) ��� 肄붿뒪�뵾/肄붿뒪�떏 �젅踰꾨━吏� ETF
2. **�뙆�씪蹂쇰┃ SAR 媛�** (af=0.02, maxAF=0.2) ��� 5遺꾨큺, �씪遊�, 二쇰큺
3. **RSI 媛�** (Period=10) ��� 5遺꾨큺
4. **�뒪�넗罹먯뒪�떛 �뒳濡쒖슦** (K=12, D=5) ��� �씪遊�, 二쇰큺
5. **蹂댁쑀 �룷吏��뀡 �젙蹂�** ��� 醫낅ぉ肄붾뱶, �닔�웾, �룊洹좊ℓ�닔媛�, �룊媛��넀�씡瑜�
6. **�삁�닔湲� (D+2 寃곗젣 �셿猷� �쁽湲�)**
7. **�떦�씪 �떎�쁽 �넀�씡 + 誘몄떎�쁽 �룊媛� �넀�씡**
8. **`trading_state.json` �쁽�옱 �긽�깭**

### 李멸퀬 �뜲�씠�꽣 (LLM 蹂댁“ �젅�씠�뼱�슜)
- �쟾�씪 誘멸뎅 �떆�옣 吏��닔 (�굹�뒪�떏, S&P500)
- �쇅援��씤/湲곌�� 留ㅻℓ �룞�뼢
- �떆�솴 �돱�뒪

## �뙋�떒 �봽濡쒖꽭�뒪

### STEP 0: 留ㅼ닔 李⑤떒 議곌굔 �솗�씤

�븘�옒 議곌굔 以� **�븯�굹�씪�룄 �빐�떦**�릺硫� 利됱떆 `hold` 異쒕젰�븯怨� 醫낅즺:
- `trading_state.json`�쓽 `daily_target_reached` == true
- `trading_state.json`�쓽 `circuit_breaker` == true
- `trading_state.json`�쓽 `eod_liquidation_mode` == true
- �쁽�옱 �떆媛� >= 15:10 KST
- �떆�꽭 �뜲�씠�꽣媛� 30珥� �씠�긽 吏��뿰/誘몄닔�떊
- �떦�씪 �떎�쁽 �넀�떎 + 誘몄떎�쁽 �룊媛� �넀�떎 �빀怨� <= �삁�닔湲덉쓽 -2% (�꽌�궥 釉뚮젅�씠而� 諛쒕룞)

�꽌�궥 釉뚮젅�씠而� 諛쒕룞 �떆:
1. `trading_state.json`�뿉 `circuit_breaker: true` 湲곕줉
2. `hold` 異쒕젰

### STEP 1: 寃곗젙濡좎쟻 �젅�씠�뼱 ��� 紐⑤뱶 �뙋蹂�

**紐⑤뱶 �슦�꽑�닚�쐞** (�쐞�뿉�꽌遺��꽣 癒쇱�� �룊媛�):

> **�꽕怨� 寃곗젙:** 紐⑤뱶 2(臾쇳��湲�, -10%)瑜� 紐⑤뱶 3(�뿤吏�, -5%)蹂대떎 癒쇱�� �룊媛��븳�떎. -10% �넀�떎 醫낅ぉ��� �뿤吏�蹂대떎 臾쇳��湲곌�� �슦�꽑�씠硫�, -5%~-10% 援ш컙��� �옄�뿰�뒪�읇寃� �뿤吏�濡� 泥섎━�맂�떎. 臾쇳��湲� 議곌굔(�뒪�넗罹먯뒪�떛+�뙆�씪蹂쇰┃) 誘몄땐議� �떆 紐⑤뱶 3�쑝濡� �뤃�뒪猷⑤맂�떎.

1. **紐⑤뱶 2 ��� 臾쇳��湲� 留ㅼ닔 �솗�씤**
   - 蹂댁쑀 醫낅ぉ 以� �룊媛��넀�떎瑜� >= -10%�씤 醫낅ぉ�씠 �엳�뒗媛�?
   - �빐�떦 醫낅ぉ�쓽 `averaging_down_log`�뿉�꽌 �삤�뒛 臾쇳��湲� �슏�닔媛� 0�씤媛�?
   - �뒪�넗罹먯뒪�떛 �뒳濡쒖슦 二쇰큺: 留ㅼ닔 �떊�샇 (%K媛� %D瑜� �긽�뼢 �룎�뙆)?
   - �뙆�씪蹂쇰┃ SAR �씪遊�: 留ㅼ닔 �떊�샇?
   - **紐⑤몢 YES �넂 紐⑤뱶 2 �떎�뻾**

2. **紐⑤뱶 3 ��� �씤踰꾩뒪 �뿤吏� 留ㅼ닔 �솗�씤**
   - �젅踰꾨━吏� 蹂댁쑀 醫낅ぉ 以� �룊媛��넀�떎瑜� >= -5%�씤 醫낅ぉ�씠 �엳�뒗媛�?
   - �뒪�넗罹먯뒪�떛 �뒳濡쒖슦 二쇰큺: 留ㅻ룄 �떊�샇 (%K媛� %D瑜� �븯�뼢 �룎�뙆)?
   - �뙆�씪蹂쇰┃ SAR �씪遊�: 留ㅻ룄 �떊�샇 **AND** �뒪�넗罹먯뒪�떛 �뒳濡쒖슦 �씪遊� %K >= 83?
   - **紐⑤몢 YES �넂 紐⑤뱶 3 �떎�뻾**

3. **紐⑤뱶 1 ��� �씪諛� 留ㅼ닔 (�뒪罹섑븨) �솗�씤**
   - 5遺꾨큺 �뙆�씪蹂쇰┃ SAR: 留ㅼ닔 �떊�샇 (SAR�씠 媛�寃� �븘�옒濡� �쟾�솚)?
   - 5遺꾨큺 RSI < 30 (怨쇰ℓ�룄)?
   - **紐⑤몢 YES �넂 紐⑤뱶 1 �떎�뻾**

4. �뼱�뼡 紐⑤뱶�룄 �빐�떦 �븞 �맖 �넂 `hold` 異쒕젰

### STEP 2: 醫낅ぉ 諛� �닔�웾 寃곗젙

**紐⑤뱶 1 (�뒪罹섑븨):**
- 醫낅ぉ: �떆洹몃꼸 諛쒖깮 �떆�옣�쓽 �젅踰꾨━吏� ETF (肄붿뒪�뵾�넂122630, 肄붿뒪�떏�넂233740)
- �뼇履� �룞�떆 諛쒖깮 �떆: �빐�떦 罹붾뱾�쓽 嫄곕옒�웾�씠 �겙 醫낅ぉ �꽑�깮
- 湲곕낯 �닔�웾 = floor(�삁�닔湲� 횞 0.5 / �쁽�옱媛�)
- 珥� �끂異� �븳�룄 �솗�씤: 湲곗〈 �룷吏��뀡 �룊媛�湲덉븸 + �떊洹� 留ㅼ닔 湲덉븸 <= �삁�닔湲� 횞 1.0

**紐⑤뱶 2 (臾쇳��湲�):**
- 醫낅ぉ: �룊媛��넀�떎 -10% �씠�긽�씤 蹂댁쑀 醫낅ぉ怨� �룞�씪
- 湲곕낯 �닔�웾 = floor(�삁�닔湲� 횞 0.3 / �쁽�옱媛�)

**紐⑤뱶 3 (�씤踰꾩뒪 �뿤吏�):**
- 醫낅ぉ: �넀�떎 以묒씤 �젅踰꾨━吏��쓽 諛섎�� �씤踰꾩뒪 ETF (肄붿뒪�뵾 �젅踰꾨━吏� �넀�떎�넂252670, 肄붿뒪�떏 �젅踰꾨━吏� �넀�떎�넂251340)
- 湲곕낯 �닔�웾 = floor(�삁�닔湲� 횞 0.3 / �쁽�옱媛�)
  > **�꽕怨� 寃곗젙:** �뒪�럺��� �뿤吏� �닔�웾�쓣 紐낆떆�븯吏� �븡�쓬. 臾쇳��湲곗�� �룞�씪�븳 30%瑜� �쟻�슜�븯�뿬 �씪愿��꽦 �쑀吏�.

### STEP 3: LLM 蹂댁“ �젅�씠�뼱 ��� �닔�웾 議곗젅

寃곗젙濡좎쟻 �젅�씠�뼱媛� 留ㅼ닔 �떊�샇瑜� �솗�씤�븳 �썑, �떎�쓬 李멸퀬 �뜲�씠�꽣瑜� 遺꾩꽍�븯�뿬 **�닔�웾 鍮꾩쑉(quantity_ratio)�쓣 0.5~1.0 踰붿쐞�뿉�꽌 寃곗젙**�븳�떎:

**�룊媛� 湲곗��:**
- �쟾�씪 誘멸뎅 �떆�옣 (�굹�뒪�떏/S&P500)�씠 -1% �씠�긽 �븯�씫 �넂 鍮꾩쑉 �븯�뼢 (0.6~0.7)
- �쇅援��씤/湲곌���씠 �떦�씪 �닚留ㅻ룄 �쟾�솚 �넂 鍮꾩쑉 �븯�뼢 (0.7~0.8)
- �븙�옱 �돱�뒪 (湲덈━ �씤�긽, 吏��젙�븰�쟻 由ъ뒪�겕 �벑) �넂 鍮꾩쑉 �븯�뼢 (0.5~0.7)
- �떆�옣 異⑷꺽 �씠踰ㅽ듃 (�꽌�궥釉뚮젅�씠而�, �쟾�웳 �벑) �넂 鍮꾩쑉 理쒖냼 (0.5)
- 紐⑤뱺 李멸퀬 �뜲�씠�꽣媛� 以묐┰/湲띿젙�쟻 �넂 鍮꾩쑉 1.0

**�젣�빟 議곌굔:**
- 理쒖냼 鍮꾩쑉: 0.5 (�젅��� 0.5 誘몃쭔�쑝濡� 以꾩씪 �닔 �뾾�쓬)
- 理쒕�� 鍮꾩쑉: 1.0
- LLM �쓳�떟 ����엫�븘�썐: 5珥�. 珥덇낵 �떆 鍮꾩쑉 = 1.0�쑝濡� 怨좎젙�븯怨� 寃곗젙濡좎쟻 寃곌낵 洹몃��濡� �떎�뻾.

**理쒖쥌 �닔�웾** = floor(湲곕낯 �닔�웾 횞 quantity_ratio)

### STEP 4: 異쒕젰

JSON �삎�떇�쑝濡� 異쒕젰:

```json
{
  "action": "buy",
  "mode": "scalping|averaging_down|hedge",
  "stock_code": "醫낅ぉ肄붾뱶",
  "stock_name": "醫낅ぉ紐�",
  "quantity": 理쒖쥌�닔�웾,
  "price_type": "market",
  "deterministic_signal": true,
  "llm_quantity_ratio": 0.85,
  "reasoning": "寃곗젙濡좎쟻 �뙋�떒 洹쇨굅 + LLM 議곗젙 �씠�쑀",
  "flags": {
    "daily_target_reached": false,
    "market_risk": false,
    "circuit_breaker": false,
    "eod_liquidation_mode": false
  }
}
```

留ㅼ닔�븯吏� �븡�뒗 寃쎌슦:

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
  "reasoning": "留ㅼ닔 議곌굔 誘몄땐議� �삉�뒗 李⑤떒 議곌굔 �빐�떦",
  "flags": { ... }
}
```

### STEP 5: 濡쒓퉭

紐⑤뱺 �샇異� 寃곌낵瑜� `trading_log.jsonl`�뿉 append:

```json
{
  "timestamp": "ISO8601+09:00",
  "skill": "buy-signal",
  "cycle": �샇異쒖닚踰�,
  "deterministic_result": {"signal": true/false, "mode": "紐⑤뱶", "stock": "肄붾뱶", "base_quantity": �닔�웾},
  "llm_adjustment": {"quantity_ratio": 鍮꾩쑉, "reasoning": "�씠�쑀"},
  "final_output": {"action": "buy/hold", "stock_code": "肄붾뱶", "quantity": 理쒖쥌�닔�웾},
  "flags": { ... }
}
```

### STEP 6: �긽�깭 �뾽�뜲�씠�듃

臾쇳��湲� 留ㅼ닔 �떎�뻾 �떆 `trading_state.json`�쓽 `averaging_down_log`�뿉 �빐�떦 醫낅ぉ 移댁슫�듃 +1 湲곕줉.
`last_updated` �븘�뱶瑜� �쁽�옱 �떆媛곸쑝濡� 媛깆떊.

## �삤瑜� 泥섎━

| �긽�솴 | ����쓳 |
|---|---|
| �떆�꽭 �뜲�씠�꽣 30珥�+ 吏��뿰 | `hold` 異쒕젰 |
| �궎��� API �뿰寃� �걡源� | `hold` 異쒕젰, 濡쒓렇�뿉 �뿉�윭 湲곕줉 |
| LLM ����엫�븘�썐 (5珥�+) | LLM �뒪�궢, quantity_ratio = 1.0 |
| trading_state.json �씫湲� �떎�뙣 | �븞�쟾 紐⑤뱶: `hold` 異쒕젰 |
| 遺�遺� 泥닿껐 諛쒖깮 | �떎�쓬 �궗�씠�겢�뿉�꽌 �옱�룊媛� |
````

- [ ] **Step 2: Validate YAML frontmatter**

Run: `python3 -c "import yaml; data=yaml.safe_load(open('buy-signal/SKILL.md').read().split('---')[1]); print(data['name'], data['version'])"`
Expected: `buy-signal 0.1.0`

- [ ] **Step 3: Commit**

```bash
git add buy-signal/
git commit -m "feat: add buy-signal OpenClaw skill with strategy reference"
```

---

### Task 4: Create sell-signal strategy reference

**Files:**
- Create: `sell-signal/references/strategy.md`

- [ ] **Step 1: Create directory**

```bash
mkdir -p sell-signal/references
```

- [ ] **Step 2: Write `sell-signal/references/strategy.md`**

```markdown
# 留ㅻ룄 �쟾�왂 李몄“ 臾몄꽌

## 嫄곕옒 醫낅ぉ

| 醫낅ぉ紐� | 肄붾뱶 | �쑀�삎 |
|---|---|---|
| KODEX �젅踰꾨━吏� | 122630 | 肄붿뒪�뵾 �젅踰꾨━吏� |
| KODEX 肄붿뒪�떏150�젅踰꾨━吏� | 233740 | 肄붿뒪�떏 �젅踰꾨━吏� |
| KODEX 200�꽑臾쇱씤踰꾩뒪2X | 252670 | 肄붿뒪�뵾 �씤踰꾩뒪 |
| KODEX 肄붿뒪�떏150�꽑臾쇱씤踰꾩뒪 | 251340 | 肄붿뒪�떏 �씤踰꾩뒪 |

## 紐⑤뱶 1: �씡�젅 留ㅻ룄

- 議곌굔: 蹂댁쑀 醫낅ぉ �쁽�옱媛� >= �룊洹좊ℓ�닔媛� 횞 (1 + �씡�젅湲곗��)
- 湲곕낯 �씡�젅 湲곗��: +0.6%
- LLM �궗�쟾 議곗젙 �떆: 0.6% ~ 1.5% 踰붿쐞
- �닔�웾: �쟾�웾 留ㅻ룄
- ����긽: �젅踰꾨━吏�/�씤踰꾩뒪 援щ텇 �뾾�씠 紐⑤뱺 蹂댁쑀 醫낅ぉ�뿉 媛쒕퀎 �쟻�슜

## 紐⑤뱶 2: 紐⑺몴�닔�씡瑜� �룄�떖

- 議곌굔: �떦�씪 珥� �떎�쁽 �닔�씡 >= 珥� 嫄곕옒���湲� 횞 0.004 (0.4%)
- �룞�옉:
  1. trading_state.json�뿉 `daily_target_reached: true` 湲곕줉
  2. 蹂댁쑀 以묒씤 �룷吏��뀡��� 紐⑤뱶 1 �씡�젅 議곌굔�쑝濡� 媛쒕퀎 泥��궛 怨꾩냽

## 紐⑤뱶 3: �옣 留덇컧 媛뺤젣 泥��궛

- 15:10: trading_state.json�뿉 `eod_liquidation_mode: true` 湲곕줉 (留ㅼ닔 李⑤떒)
- 15:20: 誘몄씡�젅 蹂댁쑀 �룷吏��뀡 �쟾�웾 �떆�옣媛� 留ㅻ룄
- �씠 洹쒖튃��� 紐⑤뱺 留ㅻ룄 議곌굔蹂대떎 �슦�꽑

## 紐⑤뱶 4: �꽌�궥 釉뚮젅�씠而�

- 議곌굔: �떦�씪 �떎�쁽 �넀�떎 + 誘몄떎�쁽 �룊媛� �넀�떎 <= �삁�닔湲� 횞 -0.02 (-2%)
- �룞�옉:
  1. 誘몄껜寃� 留ㅼ닔 二쇰Ц �쟾泥� 痍⑥냼
  2. 蹂댁쑀 �룷吏��뀡 �쟾�웾 �떆�옣媛� 留ㅻ룄
  3. trading_state.json�뿉 `circuit_breaker: true` 湲곕줉
  4. �떦�씪 留ㅻℓ 醫낅즺

## LLM 蹂댁“ �젅�씠�뼱

LLM��� 0.6% �룄�떖 �쟾�뿉留� �씡�젅 湲곗���쓣 �긽�뼢 議곗젙 媛��뒫 (0.6%~1.5%):
- 湲됰벑 紐⑤찘��� 媛먯�� �넂 1.0%~1.5%濡� �긽�뼢
- 0.6% �룄�떖 �썑�뿉�뒗 臾댁“嫄� 利됱떆 留ㅻ룄 (LLM 媛쒖엯 遺덇��)

異붽�� LLM �뙋�떒:
- 吏��닔 -2% �씠�긽 湲됰씫 �넂 �젅踰꾨━吏� �넀�젅 沅뚭퀬 (market_risk �뵆�옒洹�)
- �옣 留덇컧 �엫諛� (14:50+) �넂 誘몄씡�젅 �룷吏��뀡 �젙由� 沅뚭퀬
- �쇅援��씤/湲곌�� ���洹쒕え 留ㅻ룄 �쟾�솚 �넂 議곌린 泥��궛 沅뚭퀬
```

- [ ] **Step 3: Commit**

```bash
git add sell-signal/references/strategy.md
git commit -m "feat: add sell-signal strategy reference document"
```

---

### Task 5: Create sell-signal SKILL.md

**Files:**
- Create: `sell-signal/SKILL.md`

````markdown
---
name: sell-signal
description: "肄붿뒪�뵾/肄붿뒪�떏 �젅踰꾨━吏�쨌�씤踰꾩뒪 ETF �뼇諛⑺뼢 留ㅻℓ - 留ㅻ룄 �떆洹몃꼸 遺꾩꽍 諛� 二쇰Ц �뙆�씪誘명꽣 寃곗젙. 0.6% �씡�젅, 紐⑺몴�닔�씡瑜� �뙋�떒, �옣留덇컧 泥��궛, �꽌�궥釉뚮젅�씠而ㅻ�� �옄�룞 �뙋�떒�븳�떎."
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
    emoji: "�윋�"
---

# 留ㅻ룄 �떆洹몃꼸 �뒪�궗 (sell-signal)

肄붿뒪�뵾/肄붿뒪�떏 �젅踰꾨━吏�쨌�씤踰꾩뒪 ETF �뼇諛⑺뼢 �뒪罹섑븨 留ㅻℓ�쓽 留ㅻ룄 �뙋�떒�쓣 �닔�뻾�븳�떎.

## �떎�뻾 二쇨린

5遺꾨큺 罹붾뱾 留덇컧 �떆�젏留덈떎 1�쉶 �샇異� (�옣以� 09:00~15:20).
留ㅼ닔 �뒪�궗(buy-signal)蹂대떎 癒쇱�� �샇異쒕릺�뼱�빞 �븳�떎 (�뵆�옒洹� �꽑�뻾 湲곕줉).
15:20 媛뺤젣 泥��궛 �떎�뻾 �썑 �뜑 �씠�긽 �샇異쒗븯吏� �븡�뒗�떎.

## �엯�젰 �뜲�씠�꽣

### �븘�닔 �뜲�씠�꽣
1. **蹂댁쑀 �룷吏��뀡 �젙蹂�** ��� 醫낅ぉ肄붾뱶, �닔�웾, �룊洹좊ℓ�닔媛�, �쁽�옱媛�, �룊媛��넀�씡瑜�
2. **�삁�닔湲� (D+2 寃곗젣 �셿猷� �쁽湲�)**
3. **�떦�씪 珥� �떎�쁽 �넀�씡**
4. **�떦�씪 誘몄떎�쁽 �룊媛� �넀�씡**
5. **�떦�씪 珥� 嫄곕옒���湲�**
6. **�쁽�옱 �떆媛� (KST)**
7. **`trading_state.json` �쁽�옱 �긽�깭**

### 李멸퀬 �뜲�씠�꽣 (LLM 蹂댁“ �젅�씠�뼱�슜)
- 肄붿뒪�뵾/肄붿뒪�떏 吏��닔 �벑�씫瑜�
- �쇅援��씤/湲곌�� 留ㅻℓ �룞�뼢
- �떆�솴 �돱�뒪

## �뙋�떒 �봽濡쒖꽭�뒪

### STEP 0: �꽌�궥 釉뚮젅�씠而� �솗�씤

�떦�씪 �떎�쁽 �넀�떎 + 誘몄떎�쁽 �룊媛� �넀�떎 �빀怨꾧�� �삁�닔湲덉쓽 **-2% �씠�븯**�씤吏� �솗�씤:
- **YES �넂 �꽌�궥 釉뚮젅�씠而� 諛쒕룞:**
  1. `trading_state.json`�뿉 `circuit_breaker: true` 湲곕줉
  2. 蹂댁쑀 以묒씤 **紐⑤뱺 醫낅ぉ**�뿉 ����빐 `sell` + `circuit_breaker` 紐⑤뱶 異쒕젰
  3. �봽濡쒖꽭�뒪 醫낅즺

�씠誘� `circuit_breaker: true`�씠怨� 蹂댁쑀 �룷吏��뀡�씠 �뾾�쑝硫� �넂 `hold` 異쒕젰.

### STEP 1: �옣 留덇컧 媛뺤젣 泥��궛 �솗�씤

- �쁽�옱 �떆媛� >= **15:10** �넂 `trading_state.json`�뿉 `eod_liquidation_mode: true` 湲곕줉
- �쁽�옱 �떆媛� >= **15:20** �넂 蹂댁쑀 以묒씤 **紐⑤뱺 醫낅ぉ** �쟾�웾 �떆�옣媛� 留ㅻ룄 (`eod_liquidation` 紐⑤뱶)
- �씠 洹쒖튃��� STEP 2~3蹂대떎 �슦�꽑

### STEP 2: 寃곗젙濡좎쟻 �젅�씠�뼱 ��� 留ㅻ룄 紐⑤뱶 �뙋蹂�

**紐⑤뱶 1 ��� �씡�젅 留ㅻ룄 (醫낅ぉ蹂� 媛쒕퀎 �룊媛�):**

蹂댁쑀 醫낅ぉ 媛곴컖�뿉 ����빐:
- �쁽�옱 �씡�젅 湲곗�� = `trading_state.json`�쓽 `llm_take_profit_override` (湲곕낯 0.6%)
- �쁽�옱媛� >= �룊洹좊ℓ�닔媛� 횞 (1 + �씡�젅湲곗��/100) ?
- **YES �넂 �빐�떦 醫낅ぉ �쟾�웾 留ㅻ룄 (`take_profit` 紐⑤뱶)**

**紐⑤뱶 2 ��� 紐⑺몴�닔�씡瑜� �룄�떖 �솗�씤:**

- �떦�씪 珥� �떎�쁽 �닔�씡 >= �떦�씪 珥� 嫄곕옒���湲� 횞 0.004 ?
- **YES �넂 `trading_state.json`�뿉 `daily_target_reached: true` 湲곕줉**
- 蹂댁쑀 以묒씤 �룷吏��뀡��� 紐⑤뱶 1 �씡�젅 議곌굔�쑝濡� 怨꾩냽 泥��궛

### STEP 3: LLM 蹂댁“ �젅�씠�뼱

寃곗젙濡좎쟻 �젅�씠�뼱 �뙋�떒怨� **蹂묐젹濡�** (理쒕�� 5珥�) �떎�쓬�쓣 �룊媛�:

**A. �씡�젅 湲곗�� �궗�쟾 議곗젙 (0.6% �룄�떖 �쟾 醫낅ぉ�뿉留� �쟻�슜):**
- 湲됰벑 紐⑤찘��� 媛먯�� (理쒓렐 3媛� 5遺꾨큺 �뿰�냽 �뼇遊� + 嫄곕옒�웾 利앷��) �넂 0.8%~1.5%濡� �긽�뼢
- `trading_state.json`�쓽 `llm_take_profit_override`�뿉 湲곕줉
- **0.6% �씠誘� �룄�떖�븳 醫낅ぉ�뿉�뒗 �쟻�슜 遺덇�� ��� 利됱떆 留ㅻ룄 �떎�뻾**

**B. �떆�옣 �쐞�뿕 �뙋�떒:**
- 肄붿뒪�뵾/肄붿뒪�떏 吏��닔 -2% �씠�긽 湲됰씫 �넂 `trading_state.json`�뿉 `market_risk: true`
- �쇅援��씤/湲곌�� ���洹쒕え �닚留ㅻ룄 �쟾�솚 �넂 `market_risk: true`
- `market_risk: true` �떆: 留ㅼ닔 �뒪�궗�뿉 �닔�웾 理쒖냼�솕 �떊�샇 �쟾�떖

**C. �넀�젅 沅뚭퀬 (寃곗젙濡좎쟻 �젅�씠�뼱�뿉 �뾾�뒗 異붽�� �뙋�떒):**
- �떆�옣 湲됰씫 + 蹂댁쑀 �젅踰꾨━吏� �룷吏��뀡 �넀�떎 �솗��� 以� �넂 `stop_loss_triggered: true`
- �씠 �뵆�옒洹몃뒗 留ㅼ닔 �뒪�궗�쓽 臾쇳��湲� 紐⑤뱶 吏꾩엯 �뙋�떒�뿉 李멸퀬�맖

**LLM ����엫�븘�썐 (5珥� 珥덇낵) �떆:** LLM 蹂댁“ �뙋�떒 �쟾泥� �뒪�궢. 寃곗젙濡좎쟻 寃곌낵留� �떎�뻾. `llm_take_profit_override`�뒗 �씠�쟾 媛� �쑀吏�.

### STEP 4: 異쒕젰

留ㅻ룄�븷 醫낅ぉ�씠 �엳�뒗 寃쎌슦, **醫낅ぉ蹂꾨줈** JSON 異쒕젰:

```json
{
  "action": "sell",
  "mode": "take_profit|daily_target|eod_liquidation|circuit_breaker",
  "stock_code": "醫낅ぉ肄붾뱶",
  "stock_name": "醫낅ぉ紐�",
  "quantity": 蹂댁쑀�닔�웾�쟾泥�,
  "price_type": "market",
  "deterministic_signal": true,
  "llm_quantity_ratio": 1.0,
  "reasoning": "0.6% �씡�젅 議곌굔 �떖�꽦. �쁽�옱媛� XXX�썝, �룊洹좊ℓ�닔媛� XXX�썝, �닔�씡瑜� +0.62%",
  "flags": {
    "daily_target_reached": false,
    "market_risk": false,
    "circuit_breaker": false,
    "eod_liquidation_mode": false
  }
}
```

蹂듭닔 醫낅ぉ 留ㅻ룄 �떆 JSON 諛곗뿴濡� 異쒕젰.

留ㅻ룄�븯吏� �븡�뒗 寃쎌슦:

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
  "reasoning": "留ㅻ룄 議곌굔 誘몄땐議�. 蹂댁쑀 醫낅ぉ X媛�, 理쒓퀬 �닔�씡瑜� +0.3%",
  "flags": { ... }
}
```

### STEP 5: 濡쒓퉭

紐⑤뱺 �샇異� 寃곌낵瑜� `trading_log.jsonl`�뿉 append:

```json
{
  "timestamp": "ISO8601+09:00",
  "skill": "sell-signal",
  "cycle": �샇異쒖닚踰�,
  "deterministic_result": {"signals": [{"stock": "肄붾뱶", "mode": "紐⑤뱶", "trigger": "議곌굔"}]},
  "llm_adjustment": {"take_profit_override": 0.6, "market_risk": false, "reasoning": "�씠�쑀"},
  "final_output": [{"action": "sell/hold", "stock_code": "肄붾뱶", "quantity": �닔�웾}],
  "flags": { ... }
}
```

### STEP 6: �긽�깭 �뾽�뜲�씠�듃

留� �샇異� �떆 `trading_state.json`�쓽 `last_updated`瑜� �쁽�옱 �떆媛곸쑝濡� 媛깆떊.
�옣 �떆�옉 �떆 (09:00 泥� �샇異�) 紐⑤뱺 �뵆�옒洹몃�� 珥덇린�솕:
- `daily_target_reached: false`
- `market_risk: false`
- `stop_loss_triggered: false`
- `eod_liquidation_mode: false`
- `circuit_breaker: false`
- `llm_take_profit_override: 0.6`
- `averaging_down_log: {}`

## �삤瑜� 泥섎━

| �긽�솴 | ����쓳 |
|---|---|
| 蹂댁쑀 �룷吏��뀡 �뜲�씠�꽣 誘몄닔�떊 | `hold` 異쒕젰, 濡쒓렇�뿉 �뿉�윭 湲곕줉 |
| �궎��� API �뿰寃� �걡源� | `hold` 異쒕젰 (湲곗〈 �씡�젅 二쇰Ц��� �꽌踰꾩륫 �쑀吏�) |
| LLM ����엫�븘�썐 (5珥�+) | LLM �뒪�궢, 寃곗젙濡좎쟻 寃곌낵留� �떎�뻾 |
| trading_state.json �씫湲� �떎�뙣 | �븞�쟾 紐⑤뱶: �씡�젅 留ㅻ룄留� �떎�뻾 (湲곕낯 0.6%) |
````

- [ ] **Step 2: Validate YAML frontmatter**

Run: `python3 -c "import yaml; data=yaml.safe_load(open('sell-signal/SKILL.md').read().split('---')[1]); print(data['name'], data['version'])"`
Expected: `sell-signal 0.1.0`

- [ ] **Step 3: Commit**

```bash
git add sell-signal/
git commit -m "feat: add sell-signal OpenClaw skill with strategy reference"
```

---

### Task 6: Verify complete skill structure

- [ ] **Step 1: Verify directory structure**

```bash
find buy-signal sell-signal trading_state.json -type f | sort
```

Expected output:
```
buy-signal/SKILL.md
buy-signal/references/strategy.md
sell-signal/SKILL.md
sell-signal/references/strategy.md
trading_state.json
```

- [ ] **Step 2: Verify both SKILL.md files have valid frontmatter**

```bash
python3 -c "
import yaml
for skill in ['buy-signal', 'sell-signal']:
    with open(f'{skill}/SKILL.md') as f:
        content = f.read()
    fm = content.split('---')[1]
    data = yaml.safe_load(fm)
    assert data['name'] == skill, f'name mismatch: {data[\"name\"]}'
    assert data['version'] == '0.1.0'
    assert 'KIWOOM_APP_KEY' in data['metadata']['openclaw']['requires']['env']
    print(f'{skill}: OK')
print('All validations passed')
"
```

Expected: Both skills pass validation.

- [ ] **Step 3: Verify trading_state.json**

```bash
python3 -c "import json; d=json.load(open('trading_state.json')); assert 'circuit_breaker' in d; assert 'averaging_down_log' in d; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Final commit with all files**

```bash
git add -A
git status
# If any unstaged files remain, add them
git commit -m "feat: complete OpenClaw trading skills - buy-signal and sell-signal"
```
