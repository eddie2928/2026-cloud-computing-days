/* global window */
const { useState, Logo, CloudLeaf, PillButton, BoxInput, Chip, FieldLabel, ProgressBar, Icon, SoftBackdrop } = window.DaysUI;

const INTERESTS = ['커리어', '건강', '자기계발', '연애', '취미'];
const GENDERS = ['남', '여', '기타'];

function OnboardingScreen({ onComplete }) {
  const [nickname, setNickname] = useState('');
  const [gender, setGender] = useState('남');
  const [age, setAge] = useState('26');
  const [interests, setInterests] = useState(['커리어', '자기계발']);

  const toggleInterest = (i) => {
    setInterests(prev => prev.includes(i) ? prev.filter(x => x !== i) : [...prev, i]);
  };

  return (
    <div className="days-screen-fill" style={{
      position: 'relative',
      width: '100%', height: '100%',
      background: 'linear-gradient(180deg, var(--paper-bone) 0%, var(--sage-paper) 100%)',
      padding: '40px 24px 28px',
      display: 'flex',
      flexDirection: 'column',
      gap: 18,
      overflow: 'auto',
      animation: 'days-fade-in 500ms var(--ease-out) both',
    }}>
      <SoftBackdrop variant="screen" />

      <div style={{ position: 'relative', animation: 'days-rise 500ms var(--ease-out) 60ms both' }}>
        <Logo size={28} mark={true} markColor="var(--sage-forest)" />
        <h1 className="t-h1" style={{ margin: '20px 0 4px' }}>프로필을 알려주세요</h1>
        <p className="t-meta" style={{ margin: 0 }}>맞춤형 질문을 위해 사용돼요</p>
        <div style={{ marginTop: 16 }}>
          <ProgressBar value={1} max={4} />
        </div>
      </div>

      <div style={{ position: 'relative', animation: 'days-rise 500ms var(--ease-out) 140ms both' }}>
        <FieldLabel required>닉네임</FieldLabel>
        <BoxInput
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          placeholder="예) 에디"
          icon={<Icon name="user" size={18} color="var(--ink-meta)" />}
          ariaLabel="닉네임"
        />
      </div>

      <div style={{ position: 'relative', animation: 'days-rise 500ms var(--ease-out) 200ms both' }}>
        <FieldLabel required>성별</FieldLabel>
        <div style={{ display: 'flex', gap: 10 }}>
          {GENDERS.map(g => (
            <Chip key={g} variant="segment" active={gender === g} onClick={() => setGender(g)}>{g}</Chip>
          ))}
        </div>
      </div>

      <div style={{ position: 'relative', animation: 'days-rise 500ms var(--ease-out) 260ms both' }}>
        <FieldLabel required>나이</FieldLabel>
        <BoxInput
          value={age}
          onChange={(e) => setAge(e.target.value)}
          type="number"
          icon={<Icon name="cake" size={18} color="var(--ink-meta)" />}
          ariaLabel="나이"
        />
      </div>

      <div style={{ position: 'relative', animation: 'days-rise 500ms var(--ease-out) 320ms both' }}>
        <FieldLabel>관심사</FieldLabel>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {INTERESTS.map(i => (
            <Chip key={i} active={interests.includes(i)} onClick={() => toggleInterest(i)}>{i}</Chip>
          ))}
        </div>
      </div>

      <div style={{ flex: 1 }} />

      <div style={{ position: 'relative', animation: 'days-rise 500ms var(--ease-out) 420ms both', paddingTop: 8 }}>
        <PillButton variant="save" onClick={onComplete} disabled={!nickname.trim()}>
          다음
        </PillButton>
      </div>
    </div>
  );
}

window.OnboardingScreen = OnboardingScreen;
