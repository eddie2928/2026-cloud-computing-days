import { useNavigate, useLocation } from 'react-router-dom';
import { Icon } from '../days/Icon';
import { useDayModal } from '../../hooks/dayModalContext';
import { useMockDate } from '../../hooks/useMockDate';

type NavAction = { kind: 'navigate'; path: string } | { kind: 'modal' };

interface NavItem {
  label: string;
  icon: string;
  match: string;
  action: NavAction;
}

const NAV_ITEMS: NavItem[] = [
  { label: '오늘의 일기', icon: 'sunrise', match: '/qna', action: { kind: 'modal' } },
  { label: '홈', icon: 'home', match: '/hub', action: { kind: 'navigate', path: '/hub' } },
  { label: '캘린더', icon: 'calendar', match: '/calendar', action: { kind: 'navigate', path: '/calendar' } },
  { label: '개발자', icon: 'settings', match: '/admin', action: { kind: 'navigate', path: '/admin' } },
];

export function BottomNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const { openDayModal } = useDayModal();
  const TODAY = useMockDate();

  return (
    <nav
      aria-label="하단 내비게이션"
      style={{
        position: 'fixed',
        bottom: 0,
        left: '50%',
        transform: 'translateX(-50%)',
        width: '100%',
        maxWidth: 480,
        background: 'var(--paper-pure)',
        borderTop: '1px solid var(--line-faint)',
        display: 'flex',
        justifyContent: 'space-around',
        alignItems: 'center',
        paddingBottom: 'env(safe-area-inset-bottom, 8px)',
        zIndex: 100,
        boxShadow: '0 -2px 12px -4px rgba(54, 70, 38, 0.08)',
      }}
    >
      {NAV_ITEMS.map(item => {
        const isActive = location.pathname.startsWith(item.match);
        const handleClick = () => {
          if (item.action.kind === 'modal') openDayModal(TODAY);
          else navigate(item.action.path);
        };
        return (
          <button
            key={item.label}
            aria-current={isActive ? 'page' : undefined}
            onClick={handleClick}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 4,
              padding: '10px 0',
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              color: isActive ? 'var(--sage-leaf)' : 'var(--ink-hint)',
              fontFamily: 'var(--font-sans)',
              fontSize: 'var(--t-xs)',
              fontWeight: isActive ? 600 : 400,
              transition: 'color var(--dur-1)',
            }}
          >
            <Icon name={item.icon} size={22} color={isActive ? 'var(--sage-leaf)' : 'var(--ink-hint)'} />
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
