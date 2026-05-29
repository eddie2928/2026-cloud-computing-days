import { useMemo } from 'react';
import { getSeasonFromDate, type Season } from '../../lib/season';
import { useMockDate } from '../../hooks/useMockDate';

export type PlantState = 1 | 2 | 3;

// 계절 × 상태(1=시듦, 2=보통, 3=무럭무럭)
const SEASON_VIDEO: Record<Season, Record<PlantState, string>> = {
  spring: {
    1: '/videos/plant-spring-1.mp4',
    2: '/videos/plant-spring-2.mp4',
    3: '/videos/plant-spring-3.mp4',
  },
  summer: {
    1: '/videos/plant-summer-1.mp4',
    2: '/videos/plant-summer-2.mp4',
    3: '/videos/plant-summer-3.mp4',
  },
  autumn: {
    1: '/videos/plant-autumn.mp4',
    2: '/videos/plant-autumn.mp4',
    3: '/videos/plant-autumn.mp4',
  },
  winter: {
    1: '/videos/plant-winter.mp4',
    2: '/videos/plant-winter.mp4',
    3: '/videos/plant-winter-3.mp4',
  },
};

const SEASON_LABEL: Record<Season, string> = {
  spring: '봄', summer: '여름', autumn: '가을', winter: '겨울',
};

const SEASON_MSG: Record<Season, Record<PlantState, string>> = {
  spring: {
    1: '물이 필요한 것 같아요',
    2: '새싹이 돋아나는 계절이에요',
    3: '잘 자라고 있어요!',
  },
  summer: {
    1: '일기를 써줘야 기운을 차려요',
    2: '무럭무럭 자라고 있어요',
    3: '매일 함께해줘서 고마워요!',
  },
  autumn: {
    1: '조금 지친 것 같아요',
    2: '단풍처럼 물드는 가을이에요',
    3: '단단하게 자라고 있어요',
  },
  winter: {
    1: '따뜻한 관심이 필요해요',
    2: '포근히 쉬어가는 겨울이에요',
    3: '겨울에도 씩씩하게 자라요!',
  },
};

interface PlantVideoCardProps {
  plantState: PlantState;
}

export function PlantVideoCard({ plantState }: PlantVideoCardProps) {
  const today = useMockDate();
  const season = useMemo(() => getSeasonFromDate(today), [today]);
  const src = SEASON_VIDEO[season][plantState];

  return (
    <div
      style={{
        borderRadius: 'var(--r-5)',
        border: '1px solid var(--line)',
        background: 'var(--paper-pure)',
        boxShadow: 'var(--shadow-card)',
        animation: 'days-rise 320ms var(--ease-out) 280ms both',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        padding: 14,
      }}
    >
      <div
        style={{
          flexShrink: 0,
          width: 96,
          height: 96,
          borderRadius: 'var(--r-3)',
          overflow: 'hidden',
          border: '1px solid var(--line-faint)',
        }}
      >
        <video
          key={src}
          autoPlay muted loop playsInline
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
        >
          <source src={src} type="video/mp4" />
        </video>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <span style={{ font: '600 15px/1.2 var(--font-sans)', color: 'var(--ink-deep)', letterSpacing: '-0.01em' }}>
          내 식물
        </span>
        <span style={{
          display: 'inline-flex', alignItems: 'center', alignSelf: 'flex-start',
          font: '500 12px/1 var(--font-sans)',
          color: 'var(--sage-forest)', background: 'var(--sage-wash)',
          borderRadius: 'var(--r-pill)', padding: '3px 10px',
        }}>
          {SEASON_LABEL[season]}
        </span>
        <span style={{ font: '400 13px/1.5 var(--font-sans)', color: 'var(--ink-meta)' }}>
          {SEASON_MSG[season][plantState]}
        </span>
      </div>
    </div>
  );
}
