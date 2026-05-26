---
name: days-design
description: >
  Use this skill whenever creating or modifying any frontend UI in the Days app —
  new pages (frontend/src/pages/), new components (frontend/src/components/),
  buttons, inputs, text, cards, modals, or any inline style. Enforces the Days
  design system: soft sage green + cream paper, Pretendard typography, CSS
  variable tokens, and calm entry animations. Do NOT skip this skill when
  writing new TSX/JSX.
user-invocable: true
---

# Days · Design System — Production Code Guide

모든 새 페이지·컴포넌트·버튼·텍스트를 작성할 때 이 가이드를 따른다.
하드코딩된 hex 색상·픽셀 폰트·임의 shadow 값을 절대 쓰지 않는다.
**CSS 변수를 항상 `var(--…)` 형태로 참조한다.**

---

## 1. 색상 토큰 (CSS variables — `frontend/src/index.css`)

```
/* Sage (primary brand green) */
--sage-ink      #2e3b1f   // 최심도 텍스트, 타이틀
--sage-forest   #475a33   // 버튼 hover, h2/h3
--sage-leaf     #7d9d6a   // primary 버튼 bg, 링크, focus border
--sage-fern     #a2ba8d   // 보조 강조
--sage-mist     #c8dfca   // disabled 버튼 bg
--sage-wash     #e3f2e4   // 선택된 섹션 bg, active chip
--sage-cloud    #ebefe8   // 연한 구분 배경
--sage-paper    #f0f4e5   // 연한 카드 배경

/* Paper / cream */
--paper-bone    #fcf6ec   // 페이지 기본 배경
--paper-pure    #ffffff   // 카드·모달 표면
--paper-soft    #fdfbf5   // 카드 보조 표면

/* Ink (text) */
--ink-deep      #1f2818   // 바디 텍스트 최심
--ink-body      #3d4a30   // 일반 바디 텍스트
--ink-meta      #6e7a5e   // 보조 텍스트, placeholder
--ink-hint      #9ba590   // 힌트, 비활성 레이블
--ink-soft      #c5ccb8   // 최약 텍스트

/* Lines */
--line          #ddded0   // 기본 구분선·보더
--line-faint    #efeee5   // 가장 연한 구분선
--line-strong   #c2c8b3   // 강한 구분선

/* Semantic */
--accent-clay   #b5573b   // 에러·경고 텍스트
--accent-clay-soft #f3ddd2 // 에러 배경

/* Shadow */
--shadow-1      elevation 1 (hover 전 정지 상태)
--shadow-2      elevation 2 (버튼, 기본 부유)
--shadow-3      elevation 3 (카드·모달)
--shadow-card   카드 전용 은은한 그림자
--shadow-press  inset — 버튼 press 상태
--shadow-ring   focus ring (sage 기반, 파란 브라우저 링 대체 필수)

/* Motion */
--ease-out      cubic-bezier(0.16,1,0.3,1)    // 빠른 진입
--ease-soft     cubic-bezier(0.34,1.16,0.64,1) // 살짝 튀는 elastic
--ease-in       cubic-bezier(0.7,0,0.84,0)
--dur-1  140ms   --dur-2  240ms   --dur-3  380ms   --dur-4  600ms
```

---

## 2. 타이포그래피

폰트 패밀리: 반드시 `var(--font-sans)` (Pretendard) 사용.
`font` shorthand 형식: `'weight size/line-height var(--font-sans)'`

| 용도 | 예시 |
|------|------|
| 페이지 타이틀 | `font: '700 30px/1.25 var(--font-sans)'`, `color: var(--sage-ink)`, `letterSpacing: '-0.02em'` |
| 섹션 헤딩 | `font: '600 17px/1.2 var(--font-sans)'`, `color: var(--ink-deep)`, `letterSpacing: '-0.01em'` |
| 카드 헤딩 | `font: '600 18px/1.2 var(--font-sans)'`, `color: var(--ink-deep)` |
| 바디 텍스트 | `font: '400 15px/1.65 var(--font-sans)'`, `color: var(--ink-body)` |
| 레이블 | `font: '500 13px/1 var(--font-sans)'`, `color: var(--ink-meta)` |
| 보조/캡션 | `font: '400 12px/1.4 var(--font-sans)'`, `color: var(--ink-hint)` |
| 에러 메시지 | `font: '400 13px/1.4 var(--font-sans)'`, `color: var(--accent-clay)` |

---

## 3. 컴포넌트 레시피

### 3-1. 버튼

**Primary (pill, 채워짐)**
```tsx
<button
  style={{
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
    padding: '12px 20px',
    borderRadius: 999, border: 0,
    background: disabled ? 'var(--sage-mist)' : hover ? 'var(--sage-forest)' : 'var(--sage-leaf)',
    color: 'var(--paper-pure)',
    font: '600 15px/1 var(--font-sans)', letterSpacing: '0.01em',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.6 : 1,
    boxShadow: disabled ? 'none' : press ? 'var(--shadow-press)' : 'var(--shadow-2)',
    transform: press ? 'scale(0.97) translateY(1px)' : 'none',
    transition: 'background var(--dur-1) var(--ease-out), box-shadow var(--dur-1), transform var(--dur-1) var(--ease-soft)',
  }}
/>
```

**Outline (외곽선만)**
```tsx
<button
  style={{
    display: 'inline-flex', alignItems: 'center', gap: 6,
    padding: '10px 20px',
    borderRadius: 999, border: '1.5px solid var(--sage-leaf)',
    background: 'transparent', color: 'var(--sage-forest)',
    font: '500 14px/1 var(--font-sans)', cursor: 'pointer',
    transition: 'background var(--dur-1) var(--ease-out)',
  }}
/>
```

**Ghost (텍스트형)**
```tsx
<button
  style={{
    background: 'none', border: 0,
    color: 'var(--ink-meta)', font: '400 14px/1 var(--font-sans)',
    cursor: 'pointer',
    transition: 'color var(--dur-1) var(--ease-out)',
  }}
/>
```

---

### 3-2. 카드

```tsx
<div
  style={{
    background: 'var(--paper-pure)',
    border: '1px solid var(--line)',
    borderRadius: 24,
    padding: '28px 28px 24px',    // 모달급 카드
    // 또는 padding: '20px 20px 16px'  // 작은 카드
    boxShadow: 'var(--shadow-3)',  // 카드는 shadow-3, 작은 것은 shadow-card
  }}
/>
```

---

### 3-3. 인풋 (텍스트 입력)

```tsx
<input
  style={{
    padding: '12px 16px',
    borderRadius: 999,
    border: `1.5px solid ${focused ? 'var(--sage-leaf)' : 'var(--line)'}`,
    background: 'var(--paper-bone)',
    font: '400 15px/1.4 var(--font-sans)', color: 'var(--ink-deep)',
    outline: 'none',
    boxShadow: focused ? 'var(--shadow-ring)' : 'none',
    transition: 'border-color 160ms var(--ease-out), box-shadow 160ms var(--ease-out)',
  }}
/>
```

---

### 3-4. 페이지 레이아웃

**풀페이지 (로그인·온보딩형)**
```tsx
<div
  style={{
    width: '100%', minHeight: '100vh',
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    padding: '48px 24px',
    background: 'var(--paper-bone)',
    animation: 'days-fade-in 600ms var(--ease-out) both',
  }}
/>
```

**bg-clouds (히어로·배경 블롭)**
```tsx
background: `
  radial-gradient(circle at 78% 22%, rgba(255,255,255,0.85) 0%, rgba(255,255,255,0) 18%),
  radial-gradient(ellipse 480px 320px at 18% 78%, var(--cloud-1) 0%, transparent 55%),
  radial-gradient(ellipse 360px 260px at 88% 88%, var(--cloud-2) 0%, transparent 55%),
  radial-gradient(ellipse 280px 220px at 12% 28%, var(--cloud-3) 0%, transparent 55%),
  linear-gradient(180deg, var(--paper-bone) 0%, var(--sage-wash) 100%)
`
```

**콘텐츠 최대 너비**: 카드·폼 `maxWidth: 400`, 모달 `maxWidth: 440`

---

### 3-5. 모달 / 다이얼로그

```tsx
{/* 오버레이 */}
<div
  onClick={onClose}
  style={{
    position: 'fixed', inset: 0,
    background: 'rgba(30,28,24,0.45)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: '24px 16px', zIndex: 9999,
    animation: 'days-fade-in 200ms var(--ease-out) both',
  }}
>
  {/* 패널 */}
  <div
    role="dialog" aria-modal="true"
    onClick={e => e.stopPropagation()}
    style={{
      width: '100%', maxWidth: 440,
      background: 'var(--paper-pure)',
      border: '1px solid var(--line)',
      borderRadius: 24, boxShadow: 'var(--shadow-3)',
      padding: '28px 28px 24px',
      animation: 'days-pop 300ms var(--ease-soft) both',
    }}
  />
</div>
```

---

## 4. 애니메이션

새 요소 진입 시 아래 keyframe을 쓴다. `animation-fill-mode: both` 필수.
지연(delay)로 순차 등장 연출.

| keyframe | 용도 | 권장 duration |
|----------|------|--------------|
| `days-fade-in` | 페이지·오버레이 전체 | 500–600ms |
| `days-rise` | 로고·타이틀 올라오기 | 500–600ms, delay 80ms |
| `days-pop` | 카드·모달 등장 | 300–500ms, delay 160ms |
| `days-slide-in` | 사이드패널·드로어 | 320ms |
| `days-drift` | 떠다니는 장식 요소 | 8s ease-in-out infinite |

절대 쓰지 않는 것: bounce, shimmer, 회전 스피너(로딩은 `days-dot-pulse`).

---

## 5. 반드시 지킬 규칙

- 모든 색상은 `var(--…)` — 하드코딩 hex 금지.
- 순수 검정(`#000`, `black`) 금지 — 최심 텍스트는 `var(--ink-deep)`.
- Focus ring은 `var(--shadow-ring)` — 브라우저 기본 파란 ring 금지(`outline: none` + shadow-ring 조합).
- 이모지는 감정 5개(😊 😭 😠 😐 😩)에만 허용, 다른 곳엔 금지.
- 새 버튼에는 반드시 hover/press/disabled 세 가지 상태 처리.
- 카드·모달에는 `border: '1px solid var(--line)'` 항상 포함.
- 인디고·보라(`#4f46e5`, `#e5e7eb`)·네온 등 브랜드 외 색상 금지.
- 새 아이콘이 필요하면 `frontend/src/components/days/Icon.tsx`의 `<Icon name="…" />` 컴포넌트 사용.
