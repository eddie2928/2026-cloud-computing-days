/* global React, Sidebar, LoginScreen, TodayScreen, QnAChatScreen, DiaryDoneScreen, CalendarScreen, DiaryViewScreen, ProfileScreen */
const { useState: useStateApp } = React;

const TODAY_ISO = '2026-05-22';

const INITIAL_DIARIES = {
  '2026-05-08': '오늘은 늦은 봄 햇살이 책상 위까지 닿았다.\n\n오랜만에 산책길에서 마주친 이웃이 반갑게 인사를 건넸고, 그 짧은 순간이 종일 머릿속에 남았다. 별다른 일은 없었지만, 그 정도면 충분한 하루였다.\n\n내일의 나에게 — 너무 일찍 일어나지 마.',
  '2026-05-13': '회의가 길었던 날이다.\n\n점심을 거의 거르고 카페로 도망쳤다. 따뜻한 라떼 한 잔이 전부였는데, 그게 가장 맛있었다. 동료가 건넨 짧은 농담 하나에 웃었다는 게 오늘의 작은 위안.\n\n충분히 잘 살았다.',
  '2026-05-19': '비가 왔다 그쳤다 했다.\n\n저녁 즈음 창을 열어두니 흙냄새가 올라왔다. 어머니께 짧은 문자를 보냈고, 답장은 더 짧았다. 그래도 좋았다.\n\n내일은 우산을 챙기자.',
  '2026-05-20': '평범한 화요일.\n\n읽다 만 책을 다시 폈는데 두 페이지만 읽고 잠들었다. 그런 날이 있어도 괜찮다. 오히려 그런 날이 더 필요하다.',
  '2026-05-21': '오늘은 오랜만에 친구와 통화했다.\n\n별다른 용건은 없었지만 한 시간이 훌쩍 지나가 있었다. 우리는 같은 농담을 여전히 좋아한다는 걸 확인한 게 좋았다. 다음 주에 만나기로 했다.\n\n오늘의 나에게 — 잘 잤어, 잘 자.',
};

function App() {
  const [auth, setAuth] = useStateApp(false);
  const [diaries, setDiaries] = useStateApp(INITIAL_DIARIES);
  const [route, setRoute] = useStateApp({ name: 'today' });

  const savedDates = Object.keys(diaries).sort();

  const onLogin = () => { setAuth(true); setRoute({ name: 'today' }); };
  const onLogout = () => { setAuth(false); };

  const onBegin = (date) => setRoute({ name: 'qna', date });
  const onResume = (date) => setRoute({ name: 'diary', date });
  const onComplete = (date, diary) => {
    setDiaries((m) => ({ ...m, [date]: diary }));
    setRoute({ name: 'done', date, diary });
  };

  if (!auth) return <LoginScreen onLogin={onLogin}/>;

  // QnA chat is full-bleed without sidebar visible behind it? — actually app keeps sidebar visible
  const inner = (() => {
    switch (route.name) {
      case 'today':
        return <TodayScreen todayISO={TODAY_ISO} savedDates={savedDates} onBegin={onBegin} onResume={onResume}/>;
      case 'qna':
        return <QnAChatScreen date={route.date} onComplete={onComplete} onCancel={() => setRoute({ name: 'today' })}/>;
      case 'done':
        return <DiaryDoneScreen date={route.date} diary={route.diary} onToCalendar={() => setRoute({ name: 'calendar' })} onBackToToday={() => setRoute({ name: 'today' })}/>;
      case 'calendar':
        return <CalendarScreen todayISO={TODAY_ISO} savedDates={savedDates} onPickDate={(d) => setRoute({ name: 'diary', date: d })}/>;
      case 'diary':
        return <DiaryViewScreen date={route.date} diary={diaries[route.date]} onBack={() => setRoute({ name: 'calendar' })}/>;
      case 'profile':
        return <ProfileScreen todayISO={TODAY_ISO} savedDates={savedDates}/>;
      default:
        return null;
    }
  })();

  // Sidebar's active item maps from route
  const sideActive = route.name === 'qna' || route.name === 'done' || route.name === 'today' ? 'today'
                   : route.name === 'calendar' || route.name === 'diary' ? 'calendar'
                   : route.name;

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--paper-bone)' }}>
      <Sidebar active={sideActive} onNavigate={(id) => setRoute({ name: id })} onLogout={onLogout}/>
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh', overflow: 'auto', position: 'relative' }}>
        {inner}
      </main>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App/>);
