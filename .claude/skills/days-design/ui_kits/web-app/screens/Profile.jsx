/* global window */
const { useState, Logo, PillButton, BoxInput, Chip, FieldLabel, Icon, SoftBackdrop } = window.DaysUI;

function ProfileScreen({ onBack, onSave, onLogout }) {
  const [nickname, setNickname] = useState('에디');
  const [gender, setGender] = useState('남');
  const [age, setAge] = useState('26');
  const [job, setJob] = useState('대학생');
  const [interests, setInterests] = useState(['커리어', '자기계발']);
  const [notifyTime, setNotifyTime] = useState('오후 9:00');

  return (
    <div className="days-screen-fill" style={{
      position: 'relative',
      width: '100%', height: '100%',
      background: 'linear-gradient(180deg, var(--paper-bone) 0%, var(--sage-paper) 100%)',
      padding: '24px 24px 24px',
      display: 'flex',
      flexDirection: 'column',
      gap: 16,
      overflow: 'auto',
      animation: 'days-fade-in 400ms var(--ease-out) both',
    }}>
      <SoftBackdrop variant="screen" />

      {/* Header */}
      <header style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        marginBottom: 8,
        animation: 'days-rise 400ms var(--ease-out) 40ms both',
      }}>
        <button onClick={onBack} aria-label="뒤로" style={{
          background: 'transparent', border: 0, cursor: 'pointer', padding: 4,
        }}>
          <Icon name="chevron-left" size={24} color="var(--ink-deep)" />
        </button>
        <div className="t-h1" style={{ fontSize: 'var(--t-xl)' }}>내 정보 수정</div>
      </header>

      {/* Avatar */}
      <div style={{
        position: 'relative',
        display: 'flex',
        justifyContent: 'center',
        margin: '8px 0 4px',
        animation: 'days-pop 480ms var(--ease-soft) 80ms both',
      }}>
        <div style={{ position: 'relative' }}>
          <div style={{
            width: 96, height: 96,
            borderRadius: '50%',
            background: 'var(--sage-mist)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Icon name="user" size={42} color="var(--sage-forest)" />
          </div>
          <button aria-label="사진 변경" style={{
            position: 'absolute',
            right: -2, bottom: -2,
            width: 32, height: 32,
            borderRadius: '50%',
            background: 'var(--sage-forest)',
            border: '2px solid var(--paper-bone)',
            cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: 'var(--shadow-card)',
          }}>
            <Icon name="camera" size={16} color="var(--paper-pure)" />
          </button>
        </div>
      </div>

      <div style={{ position: 'relative', animation: 'days-rise 400ms var(--ease-out) 120ms both' }}>
        <FieldLabel>닉네임</FieldLabel>
        <BoxInput
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          suffix={<Icon name="pencil" size={16} color="var(--ink-hint)" />}
        />
      </div>

      <div style={{
        position: 'relative',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 12,
        animation: 'days-rise 400ms var(--ease-out) 180ms both',
      }}>
        <div>
          <FieldLabel>성별</FieldLabel>
          <BoxInput value={gender} onChange={(e) => setGender(e.target.value)} />
        </div>
        <div>
          <FieldLabel>나이</FieldLabel>
          <BoxInput value={age} onChange={(e) => setAge(e.target.value)} type="number" />
        </div>
      </div>

      <div style={{ position: 'relative', animation: 'days-rise 400ms var(--ease-out) 240ms both' }}>
        <FieldLabel>직업</FieldLabel>
        <BoxInput
          value={job}
          onChange={(e) => setJob(e.target.value)}
          suffix={<Icon name="pencil" size={16} color="var(--ink-hint)" />}
        />
      </div>

      <div style={{ position: 'relative', animation: 'days-rise 400ms var(--ease-out) 300ms both' }}>
        <FieldLabel>관심사</FieldLabel>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {interests.map(i => (
            <Chip key={i} active onClick={() => setInterests(prev => prev.filter(x => x !== i))}>{i}</Chip>
          ))}
          <Chip onClick={() => {}} icon={<Icon name="plus" size={14} color="var(--ink-body)" />}>추가</Chip>
        </div>
      </div>

      <hr style={{ border: 0, height: 1, background: 'var(--line-faint)', margin: '4px 0' }} />

      <div style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        animation: 'days-rise 400ms var(--ease-out) 360ms both',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Icon name="bell" size={20} color="var(--ink-body)" />
          <span className="t-label">푸시 알림 시간</span>
        </div>
        <span className="t-h3" style={{ fontWeight: 600 }}>{notifyTime}</span>
      </div>

      <div style={{ flex: 1 }} />

      <div style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        animation: 'days-rise 400ms var(--ease-out) 420ms both',
      }}>
        <PillButton variant="save" onClick={onSave}>저장</PillButton>
        <PillButton variant="danger" onClick={onLogout}>로그아웃</PillButton>
      </div>
    </div>
  );
}

window.ProfileScreen = ProfileScreen;
