import { useState, useEffect, useCallback } from 'react'
import client from '../api/client'
import { searchMusic, type MusicSearchResult } from '../api/music'
import { ThinkingDots } from '../components/qna/ThinkingDots'
import { getMockDate, setMockDate, clearMockDate, hasMockDate } from '../lib/mockDate'
import { getSeoulToday } from '../lib/today'
import { getPushState, subscribePush, type PushState } from '../lib/push'

const TABLES = [
  'users',
  'user_profiles',
  'qna_sessions',
  'qna_items',
  'diary_entries',
  'pet',
  'share_links',
  'user_schedules',
]

const TABLE_FIELD_HINTS: Record<string, Record<string, string>> = {
  users: { display_name: '예: 홍길동' },
  user_profiles: {
    user_id: '정수 (예: 1)',
    nickname: '예: 길동이',
    gender: 'male | female | other | private',
    age: '정수 (예: 25)',
    occupation: '예: 개발자',
    hobbies: 'PostgreSQL 배열 (예: {독서,등산})',
    interests: 'PostgreSQL 배열 (예: {AI,음악})',
    notification_time: 'HH:MM:SS (예: 09:00:00)',
  },
  qna_sessions: {
    user_id: '정수 (예: 1)',
    diary_date: 'YYYY-MM-DD (예: 2026-05-24)',
    status: 'in_progress | completed',
  },
  qna_items: {
    session_id: '정수 (예: 1)',
    sequence: '1~5',
    question: '자유 텍스트',
    answer: '자유 텍스트',
  },
  diary_entries: {
    session_id: '정수 (예: 1)',
    user_id: '정수 (예: 1)',
    diary_date: 'YYYY-MM-DD (예: 2026-05-24)',
    body: '자유 텍스트 (일기 본문)',
    summary: '자유 텍스트 (한줄 요약)',
    emotion: 'happy | sad | angry | neutral | bored',
  },
  pet: {
    user_id: '정수 (예: 1)',
    level: '정수 (예: 1)',
    xp: '정수 (예: 0)',
  },
  share_links: {
    user_id: '정수 (예: 1)',
    diary_date: 'YYYY-MM-DD (예: 2026-05-24)',
    token: '고유 문자열 (예: abc123xyz)',
    expires_at: 'ISO 8601 (예: 2026-05-25T00:00:00Z)',
  },
  user_schedules: {
    user_id: '정수 (예: 1)',
    period_start: 'YYYY-MM-DD (예: 2026-05-26)',
    period_end: 'YYYY-MM-DD (예: 2026-05-28)',
    situation: '구체적 활동 (예: 교토 신사 방문)',
  },
}

type Tab = 'db' | 'bedrock' | 'date' | 'push' | 'music'

interface BedrockLog {
  id: number
  session_id: number
  sequence: number
  question: string
  answer: string | null
  answered_at: string | null
  asked_at: string | null
  prompt: string | null
  raw_response: string | null
  model_id: string | null
  input_tokens: number | null
  output_tokens: number | null
  latency_ms: number | null
}

const tabStyle = (active: boolean): React.CSSProperties => ({
  background: 'none',
  border: 'none',
  borderBottom: active ? '2px solid var(--sage-leaf)' : '2px solid transparent',
  padding: '10px 4px',
  fontFamily: 'var(--font-sans)',
  fontWeight: 500,
  fontSize: 14,
  color: active ? 'var(--sage-forest)' : 'var(--ink-meta)',
  cursor: 'pointer',
  transition: 'color var(--dur-1)',
})

export function Admin() {
  const [tab, setTab] = useState<Tab>('db')

  // DB 탭
  const [selectedTable, setSelectedTable] = useState<string>(TABLES[0])
  const [rows, setRows] = useState<Record<string, unknown>[]>([])
  const [columns, setColumns] = useState<string[]>([])
  const [dbLoading, setDbLoading] = useState(false)
  const [dbError, setDbError] = useState<string | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newRow, setNewRow] = useState<Record<string, string>>({})
  const [addError, setAddError] = useState<string | null>(null)

  // Bedrock 로그 탭
  const [bedrockLogs, setBedrockLogs] = useState<BedrockLog[]>([])
  const [bedrockLoading, setBedrockLoading] = useState(false)
  const [bedrockError, setBedrockError] = useState<string | null>(null)
  const [expandedLogId, setExpandedLogId] = useState<number | null>(null)

  // 날짜 탭
  const [mockDateInput, setMockDateInput] = useState(getMockDate())
  const [isMockActive, setIsMockActive] = useState(hasMockDate())

  // 푸시 탭
  const [pushState, setPushState] = useState<PushState | null>(null)
  const [notifPerm, setNotifPerm] = useState<NotificationPermission | null>(null)
  const [swRegistered, setSwRegistered] = useState<boolean | null>(null)
  const [subJson, setSubJson] = useState<object | null>(null)
  const [subscribeMsg, setSubscribeMsg] = useState<string | null>(null)
  const [subscribeLoading, setSubscribeLoading] = useState(false)
  const [pushStateRaw, setPushStateRaw] = useState(false)
  const [subRaw, setSubRaw] = useState(false)
  const [testPushResult, setTestPushResult] = useState<unknown>(null)
  const [testPushLoading, setTestPushLoading] = useState(false)
  const [serverSubs, setServerSubs] = useState<unknown[]>([])
  const [serverSubsLoading, setServerSubsLoading] = useState(false)
  const [testPushRaw, setTestPushRaw] = useState(false)
  const [debugInfo, setDebugInfo] = useState<Record<string, unknown> | null>(null)
  const [debugLoading, setDebugLoading] = useState(false)

  // 음악 API 탭
  const [musicTerm, setMusicTerm] = useState('')
  const [musicLimit, setMusicLimit] = useState(10)
  const [musicLoading, setMusicLoading] = useState(false)
  const [musicResult, setMusicResult] = useState<MusicSearchResult | null>(null)
  const [musicRaw, setMusicRaw] = useState(false)

  const handleMusicSearch = async () => {
    if (!musicTerm.trim()) return
    setMusicLoading(true)
    try {
      const res = await searchMusic(musicTerm.trim(), musicLimit)
      setMusicResult(res)
    } catch (e) {
      setMusicResult({
        ok: false,
        status_code: null,
        latency_ms: 0,
        results: [],
        error: e instanceof Error ? e.message : String(e),
      })
    } finally {
      setMusicLoading(false)
    }
  }

  const refreshPushStatus = useCallback(async () => {
    const state = await getPushState()
    setPushState(state)
    setNotifPerm('Notification' in window ? Notification.permission : null)
    if ('serviceWorker' in navigator) {
      const reg = await navigator.serviceWorker.getRegistration()
      setSwRegistered(!!reg)
      if (reg) {
        const sub = await reg.pushManager.getSubscription()
        setSubJson(sub ? sub.toJSON() : null)
      } else {
        setSubJson(null)
      }
    } else {
      setSwRegistered(false)
      setSubJson(null)
    }
  }, [])

  const handleSubscribe = async () => {
    setSubscribeLoading(true)
    setSubscribeMsg(null)
    try {
      await subscribePush()
      setSubscribeMsg('구독 성공')
      await refreshPushStatus()
    } catch (e) {
      setSubscribeMsg(`오류: ${e instanceof Error ? e.message : String(e)}`)
      await refreshPushStatus()
    } finally {
      setSubscribeLoading(false)
    }
  }

  const handleTestPush = async () => {
    setTestPushLoading(true)
    try {
      const res = await client.post('/push/test')
      setTestPushResult(res.data)
    } catch (e) {
      setTestPushResult({ error: e instanceof Error ? e.message : String(e) })
    } finally {
      setTestPushLoading(false)
    }
  }

  const fetchServerSubs = useCallback(async () => {
    setServerSubsLoading(true)
    try {
      const res = await client.get('/push/subscriptions')
      setServerSubs(res.data ?? [])
    } catch {
      setServerSubs([])
    } finally {
      setServerSubsLoading(false)
    }
  }, [])

  const fetchDebugInfo = useCallback(async () => {
    setDebugLoading(true)
    try {
      const res = await client.get('/push/debug')
      setDebugInfo(res.data)
    } catch {
      setDebugInfo(null)
    } finally {
      setDebugLoading(false)
    }
  }, [])

  useEffect(() => {
    if (tab === 'push') {
      refreshPushStatus()
      fetchServerSubs()
      fetchDebugInfo()
    }
  }, [tab, refreshPushStatus, fetchServerSubs, fetchDebugInfo])

  const fetchTable = useCallback(() => {
    setDbLoading(true)
    setDbError(null)
    client
      .get(`/admin/tables/${selectedTable}`)
      .then(res => {
        const data: Record<string, unknown>[] = res.data ?? []
        setRows(data)
        setColumns(data.length > 0 ? Object.keys(data[0]) : [])
      })
      .catch(() => setDbError('데이터를 불러오지 못했습니다.'))
      .finally(() => setDbLoading(false))
  }, [selectedTable])

  useEffect(() => {
    if (tab !== 'db') return
    fetchTable()
  }, [selectedTable, tab, fetchTable])

  const handleDelete = async (id: unknown) => {
    if (!confirm(`ID ${id} 행을 삭제하시겠습니까?`)) return
    try {
      await client.delete(`/admin/tables/${selectedTable}/${id}`)
      fetchTable()
    } catch {
      alert('삭제 실패')
    }
  }

  const handleAdd = async () => {
    setAddError(null)
    const payload: Record<string, string> = {}
    for (const [k, v] of Object.entries(newRow)) {
      if (v.trim() !== '') payload[k] = v.trim()
    }
    if (Object.keys(payload).length === 0) {
      setAddError('최소 한 개 필드를 입력하세요.')
      return
    }
    try {
      await client.post(`/admin/tables/${selectedTable}`, payload)
      setShowAddForm(false)
      setNewRow({})
      fetchTable()
    } catch {
      setAddError('추가 실패. 입력값을 확인하세요.')
    }
  }

  const fetchBedrockLogs = useCallback(() => {
    setBedrockLoading(true)
    setBedrockError(null)
    client
      .get('/admin/bedrock-logs?limit=50')
      .then(res => setBedrockLogs(res.data ?? []))
      .catch(() => setBedrockError('로그를 불러오지 못했습니다.'))
      .finally(() => setBedrockLoading(false))
  }, [])

  useEffect(() => {
    if (tab === 'bedrock') fetchBedrockLogs()
  }, [tab, fetchBedrockLogs])

  useEffect(() => {
    if (tab !== 'bedrock') return
    const timer = setInterval(fetchBedrockLogs, 30000)
    return () => clearInterval(timer)
  }, [tab, fetchBedrockLogs])

  return (
    <div style={{ padding: '16px 16px 40px' }}>
      <h1 style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 24, lineHeight: 1.2, color: 'var(--sage-forest)', margin: '0 0 20px' }}>
        관리자
      </h1>

      {/* 탭 네비게이션 */}
      <div style={{ display: 'flex', gap: 20, borderBottom: '1px solid var(--line-faint)', marginBottom: 20 }}>
        <button style={tabStyle(tab === 'db')} onClick={() => setTab('db')}>DB 조회</button>
        <button style={tabStyle(tab === 'bedrock')} onClick={() => setTab('bedrock')}>Bedrock 로그</button>
        <button style={tabStyle(tab === 'date')} onClick={() => setTab('date')}>
          날짜{isMockActive ? ' ●' : ''}
        </button>
        <button style={tabStyle(tab === 'push')} onClick={() => setTab('push')}>푸시</button>
        <button style={tabStyle(tab === 'music')} onClick={() => setTab('music')}>음악 API</button>
      </div>

      {/* DB 조회 탭 */}
      {tab === 'db' && (
        <div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
            <div>
              <label style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-meta)', display: 'block', marginBottom: 6 }}>
                테이블
              </label>
              <select
                value={selectedTable}
                onChange={e => { setSelectedTable(e.target.value); setShowAddForm(false); setNewRow({}) }}
                style={{
                  background: 'var(--paper-mist)',
                  border: '1px solid var(--line)',
                  borderRadius: 12,
                  padding: '8px 12px',
                  fontFamily: 'var(--font-sans)',
                  fontSize: 14,
                  color: 'var(--ink-deep)',
                  outline: 'none',
                  minWidth: 200,
                }}
              >
                {TABLES.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <button
              onClick={() => { setShowAddForm(!showAddForm); setNewRow({}); setAddError(null) }}
              style={{
                background: 'transparent',
                border: 'none',
                fontFamily: 'var(--font-sans)',
                fontSize: 13,
                color: 'var(--ink-meta)',
                cursor: 'pointer',
                padding: '8px 4px',
              }}
            >
              {showAddForm ? '취소' : '행 추가'}
            </button>
            <button
              onClick={fetchTable}
              style={{
                background: 'transparent',
                border: 'none',
                fontFamily: 'var(--font-sans)',
                fontSize: 13,
                color: 'var(--ink-meta)',
                cursor: 'pointer',
                padding: '8px 4px',
              }}
            >
              새로고침
            </button>
          </div>

          {showAddForm && (
            <div style={{ background: 'var(--paper-pure)', border: '1px solid var(--line)', borderRadius: 12, padding: 16, marginBottom: 16 }}>
              <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, fontWeight: 600, color: 'var(--ink-deep)', margin: '0 0 12px' }}>
                새 행 추가 (id, created_at 등 자동 생성 필드는 비워두세요)
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {columns.filter(c => c !== 'id').map(col => {
                  const hint = TABLE_FIELD_HINTS[selectedTable]?.[col]
                  return (
                    <div key={col} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <label style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--ink-meta)', minWidth: 140 }}>{col}</label>
                      <div style={{ flex: 1 }}>
                        <input
                          value={newRow[col] ?? ''}
                          onChange={e => setNewRow(prev => ({ ...prev, [col]: e.target.value }))}
                          placeholder={hint ?? ''}
                          style={{
                            width: '100%',
                            background: 'var(--paper-mist)',
                            border: '1px solid var(--line-faint)',
                            borderRadius: 8,
                            padding: '6px 10px',
                            fontFamily: 'var(--font-mono)',
                            fontSize: 12,
                            color: 'var(--ink-deep)',
                            outline: 'none',
                            boxSizing: 'border-box',
                          }}
                        />
                        {hint && (
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-hint)', opacity: 0.7 }}>
                            {hint}
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
              {addError && <p style={{ color: 'var(--accent-clay)', fontFamily: 'var(--font-sans)', fontSize: 13, margin: '8px 0 0' }}>{addError}</p>}
              <button
                onClick={handleAdd}
                style={{
                  marginTop: 12,
                  background: 'var(--sage-leaf)',
                  color: 'var(--paper-pure)',
                  border: 'none',
                  borderRadius: 10,
                  padding: '8px 20px',
                  fontFamily: 'var(--font-sans)',
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                추가
              </button>
            </div>
          )}

          {dbLoading && (
            <div style={{ padding: '16px 0' }}>
              <ThinkingDots visible />
            </div>
          )}
          {dbError && <p style={{ color: 'var(--accent-clay)', fontFamily: 'var(--font-sans)', fontSize: 14 }}>{dbError}</p>}
          {!dbLoading && !dbError && rows.length === 0 && (
            <p style={{ color: 'var(--ink-meta)', fontFamily: 'var(--font-sans)', fontSize: 14 }}>데이터 없음</p>
          )}
          {!dbLoading && !dbError && rows.length > 0 && (
            <div style={{ overflowX: 'auto', background: 'var(--paper-pure)', border: '1px solid var(--line-faint)', borderRadius: 'var(--r-3, 12px)' }}>
              <table style={{ borderCollapse: 'collapse', width: '100%', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                <thead>
                  <tr>
                    <th style={{ background: 'var(--paper-warm)', padding: '8px 12px', textAlign: 'center', color: 'var(--ink-deep)', fontWeight: 600, borderBottom: '1px solid var(--line-faint)', whiteSpace: 'nowrap' }}>
                      삭제
                    </th>
                    {columns.map(col => (
                      <th key={col} style={{ background: 'var(--paper-warm)', padding: '8px 12px', textAlign: 'left', color: 'var(--ink-deep)', fontWeight: 600, borderBottom: '1px solid var(--line-faint)', whiteSpace: 'nowrap' }}>
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--line-faint)' }}>
                      <td style={{ padding: '6px 12px', textAlign: 'center' }}>
                        <button
                          onClick={() => handleDelete(row['id'])}
                          style={{
                            background: 'none',
                            border: '1px solid var(--accent-clay)',
                            borderRadius: 6,
                            padding: '2px 8px',
                            fontFamily: 'var(--font-sans)',
                            fontSize: 11,
                            color: 'var(--accent-clay)',
                            cursor: 'pointer',
                          }}
                        >
                          삭제
                        </button>
                      </td>
                      {columns.map(col => (
                        <td key={col} style={{ padding: '6px 12px', color: 'var(--ink-deep)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {String(row[col] ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* 날짜 설정 탭 */}
      {tab === 'date' && (
        <div style={{ maxWidth: 360 }}>
          <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-meta)', margin: '0 0 20px', lineHeight: 1.6 }}>
            "오늘"로 인식할 날짜를 지정합니다.<br />
            홈 화면, 일기 시작, 일기 조회에 반영됩니다.
          </p>

          {isMockActive && (
            <div style={{
              background: 'var(--sage-wash)',
              border: '1px solid var(--sage-mist)',
              borderRadius: 'var(--r-3)',
              padding: '10px 14px',
              marginBottom: 20,
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--sage-forest)', fontWeight: 600 }}>
                {getMockDate()}
              </span>
              <span style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--ink-meta)' }}>으로 설정됨</span>
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-body)', display: 'block', marginBottom: 8, fontWeight: 500 }}>
                날짜 선택
              </label>
              <input
                type="date"
                value={mockDateInput}
                onChange={e => setMockDateInput(e.target.value)}
                style={{
                  width: '100%',
                  background: 'var(--paper-pure)',
                  border: '1px solid var(--line)',
                  borderRadius: 'var(--r-3)',
                  padding: '10px 14px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 14,
                  color: 'var(--ink-deep)',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => {
                  if (!mockDateInput) return
                  setMockDate(mockDateInput)
                  setIsMockActive(true)
                }}
                style={{
                  flex: 1,
                  background: 'var(--sage-leaf)',
                  color: 'var(--paper-pure)',
                  border: 'none',
                  borderRadius: 'var(--r-3)',
                  padding: '10px 0',
                  fontFamily: 'var(--font-sans)',
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                적용
              </button>
              <button
                onClick={() => {
                  clearMockDate()
                  setMockDateInput(getSeoulToday())
                  setIsMockActive(false)
                }}
                style={{
                  flex: 1,
                  background: 'transparent',
                  color: 'var(--ink-meta)',
                  border: '1px solid var(--line)',
                  borderRadius: 'var(--r-3)',
                  padding: '10px 0',
                  fontFamily: 'var(--font-sans)',
                  fontSize: 14,
                  cursor: 'pointer',
                }}
              >
                오늘로 초기화
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 푸시 디버깅 탭 */}
      {tab === 'push' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 600 }}>
          {/* 브라우저 상태 섹션 */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--ink-deep)', margin: 0 }}>브라우저 상태</p>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={refreshPushStatus} style={{ background: 'none', border: 'none', fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--ink-meta)', cursor: 'pointer' }}>새로고침</button>
                <button onClick={() => setPushStateRaw(r => !r)} style={{ background: 'none', border: '1px solid var(--line)', borderRadius: 6, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-meta)', cursor: 'pointer', padding: '2px 8px' }}>{pushStateRaw ? 'Pretty' : 'Raw'}</button>
              </div>
            </div>
            {pushStateRaw ? (
              <pre style={{ background: 'var(--paper-mist)', borderRadius: 8, padding: '10px 12px', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--ink-deep)', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {JSON.stringify({ pushState, notifPermission: notifPerm, swRegistered }, null, 2)}
              </pre>
            ) : (
              <div style={{ background: 'var(--paper-pure)', border: '1px solid var(--line-faint)', borderRadius: 10, padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {([['Push 상태', pushState], ['알림 권한', notifPerm], ['SW 등록', swRegistered != null ? (swRegistered ? '등록됨' : '미등록') : null]] as [string, string | boolean | null][]).map(([label, val]) => (
                  <div key={label} style={{ display: 'flex', gap: 8 }}>
                    <span style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--ink-meta)', minWidth: 100 }}>{label}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--ink-deep)', fontWeight: 600 }}>{val != null ? String(val) : '—'}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 구독 시작 버튼 */}
          <div>
            {notifPerm === 'denied' && (
              <div style={{
                background: 'var(--accent-clay-soft)',
                border: '1px solid var(--accent-clay)',
                borderRadius: 10,
                padding: '10px 14px',
                marginBottom: 10,
                fontFamily: 'var(--font-sans)',
                fontSize: 13,
                color: 'var(--accent-clay)',
                lineHeight: 1.5,
              }}>
                알림이 차단된 상태입니다. 브라우저 주소창 왼쪽의 자물쇠 아이콘 → 사이트 설정에서 알림을 허용으로 변경해 주세요.
              </div>
            )}
            <button
              onClick={handleSubscribe}
              disabled={subscribeLoading || notifPerm === 'denied'}
              style={{ background: 'var(--sage-leaf)', color: 'var(--paper-pure)', border: 'none', borderRadius: 10, padding: '10px 20px', fontFamily: 'var(--font-sans)', fontSize: 13, fontWeight: 600, cursor: (subscribeLoading || notifPerm === 'denied') ? 'default' : 'pointer', opacity: (subscribeLoading || notifPerm === 'denied') ? 0.4 : 1 }}
            >
              {subscribeLoading ? '구독 중...' : '구독 시작'}
            </button>
            {subscribeMsg && <p style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: subscribeMsg.startsWith('오류') ? 'var(--accent-clay)' : 'var(--sage-forest)', margin: '8px 0 0' }}>{subscribeMsg}</p>}
          </div>

          {/* 현재 구독 정보 */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--ink-deep)', margin: 0 }}>현재 구독 정보</p>
              <button onClick={() => setSubRaw(r => !r)} style={{ background: 'none', border: '1px solid var(--line)', borderRadius: 6, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-meta)', cursor: 'pointer', padding: '2px 8px' }}>{subRaw ? 'Pretty' : 'Raw'}</button>
            </div>
            {subJson == null ? (
              <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-hint)' }}>구독 없음</p>
            ) : subRaw ? (
              <pre style={{ background: 'var(--paper-mist)', borderRadius: 8, padding: '10px 12px', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-deep)', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                {JSON.stringify(subJson, null, 2)}
              </pre>
            ) : (
              <div style={{ background: 'var(--paper-pure)', border: '1px solid var(--line-faint)', borderRadius: 10, padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {Object.entries(subJson).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', gap: 8 }}>
                    <span style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--ink-meta)', minWidth: 80 }}>{k}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-deep)', wordBreak: 'break-all' }}>{typeof v === 'object' ? JSON.stringify(v) : String(v ?? '')}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Test 푸시 요청 */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
              <button
                onClick={handleTestPush}
                disabled={testPushLoading}
                style={{ background: 'var(--sage-leaf)', color: 'var(--paper-pure)', border: 'none', borderRadius: 10, padding: '10px 20px', fontFamily: 'var(--font-sans)', fontSize: 13, fontWeight: 600, cursor: testPushLoading ? 'default' : 'pointer', opacity: testPushLoading ? 0.7 : 1 }}
              >
                {testPushLoading ? '전송 중...' : 'Test 푸시 요청'}
              </button>
              {testPushResult != null && (
                <button onClick={() => setTestPushRaw(r => !r)} style={{ background: 'none', border: '1px solid var(--line)', borderRadius: 6, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-meta)', cursor: 'pointer', padding: '2px 8px' }}>{testPushRaw ? 'Pretty' : 'Raw'}</button>
              )}
            </div>
            {testPushResult != null && (
              testPushRaw ? (
                <pre style={{ background: 'var(--paper-mist)', borderRadius: 8, padding: '10px 12px', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--ink-deep)', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {JSON.stringify(testPushResult, null, 2)}
                </pre>
              ) : (
                <div style={{ background: 'var(--paper-pure)', border: '1px solid var(--line-faint)', borderRadius: 10, padding: '12px 14px' }}>
                  {(testPushResult as { results?: Array<{ endpoint: string; success: boolean; expired: boolean; error: string | null; status_code: number | null; traceback: string | null }> }).results?.length === 0 ? (
                    <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-hint)', margin: 0 }}>구독 없음</p>
                  ) : (
                    (testPushResult as { results?: Array<{ endpoint: string; success: boolean; expired: boolean; error: string | null; status_code: number | null; traceback: string | null }> }).results?.map((r, i) => (
                      <div key={i} style={{ borderBottom: '1px solid var(--line-faint)', paddingBottom: 8, marginBottom: 8 }}>
                        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-meta)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.endpoint}</span>
                          <span style={{
                            fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, padding: '1px 7px', borderRadius: 4,
                            background: r.success ? 'var(--sage-wash)' : 'var(--accent-clay-soft)',
                            color: r.success ? 'var(--sage-forest)' : 'var(--accent-clay)',
                          }}>
                            {r.success ? '성공' : r.expired ? '만료' : '실패'}
                          </span>
                          {r.status_code != null && (
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-meta)' }}>HTTP {r.status_code}</span>
                          )}
                        </div>
                        {r.error && (
                          <p style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent-clay)', margin: '4px 0 0', wordBreak: 'break-word' }}>{r.error}</p>
                        )}
                        {r.traceback && (
                          <details style={{ marginTop: 4 }}>
                            <summary style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--ink-meta)', cursor: 'pointer' }}>Traceback</summary>
                            <pre style={{ background: 'var(--paper-mist)', borderRadius: 6, padding: '8px 10px', fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--ink-deep)', margin: '4px 0 0', whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 200, overflowY: 'auto' }}>
                              {r.traceback}
                            </pre>
                          </details>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )
            )}
          </div>

          {/* 서버 진단 */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--ink-deep)', margin: 0 }}>서버 진단</p>
              <button onClick={fetchDebugInfo} style={{ background: 'none', border: 'none', fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--ink-meta)', cursor: 'pointer' }}>새로고침</button>
            </div>
            {debugLoading ? (
              <ThinkingDots visible />
            ) : debugInfo == null ? (
              <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-hint)' }}>진단 정보를 불러오지 못했습니다.</p>
            ) : (
              <div style={{ background: 'var(--paper-pure)', border: '1px solid var(--line-faint)', borderRadius: 10, padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {Object.entries(debugInfo).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', gap: 8 }}>
                    <span style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--ink-meta)', minWidth: 200 }}>{k}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--ink-deep)', fontWeight: typeof v === 'boolean' ? 600 : 400, wordBreak: 'break-all' }}>
                      {v == null ? '—' : String(v)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 서버 구독 목록 */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--ink-deep)', margin: 0 }}>서버 구독 목록</p>
              <button onClick={fetchServerSubs} style={{ background: 'none', border: 'none', fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--ink-meta)', cursor: 'pointer' }}>새로고침</button>
            </div>
            {serverSubsLoading ? (
              <ThinkingDots visible />
            ) : serverSubs.length === 0 ? (
              <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-hint)' }}>서버 구독 없음</p>
            ) : (
              <div style={{ overflowX: 'auto', background: 'var(--paper-pure)', border: '1px solid var(--line-faint)', borderRadius: 10 }}>
                <table style={{ borderCollapse: 'collapse', width: '100%', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                  <thead>
                    <tr>
                      {['id', 'endpoint', 'created_at'].map(col => (
                        <th key={col} style={{ background: 'var(--paper-warm)', padding: '6px 10px', textAlign: 'left', color: 'var(--ink-deep)', fontWeight: 600, borderBottom: '1px solid var(--line-faint)', whiteSpace: 'nowrap' }}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(serverSubs as Array<{ id: number; endpoint: string; created_at: string }>).map(sub => (
                      <tr key={sub.id} style={{ borderBottom: '1px solid var(--line-faint)' }}>
                        <td style={{ padding: '6px 10px', color: 'var(--ink-deep)', whiteSpace: 'nowrap' }}>{sub.id}</td>
                        <td style={{ padding: '6px 10px', color: 'var(--ink-deep)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{sub.endpoint}</td>
                        <td style={{ padding: '6px 10px', color: 'var(--ink-deep)', whiteSpace: 'nowrap' }}>{sub.created_at ? new Date(sub.created_at).toLocaleString('ko-KR') : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 음악 API 탭 */}
      {tab === 'music' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 680 }}>
          {/* 검색 입력 */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 180 }}>
              <label style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-meta)', display: 'block', marginBottom: 6 }}>
                검색어 (term)
              </label>
              <input
                type="text"
                value={musicTerm}
                onChange={e => setMusicTerm(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleMusicSearch()}
                placeholder="예: IU, BTS, jazz..."
                style={{
                  width: '100%',
                  padding: '10px 14px',
                  borderRadius: 12,
                  border: '1.5px solid var(--line)',
                  background: 'var(--paper-bone)',
                  font: '400 14px/1.4 var(--font-sans)',
                  color: 'var(--ink-deep)',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            <div>
              <label style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-meta)', display: 'block', marginBottom: 6 }}>
                limit
              </label>
              <input
                type="number"
                value={musicLimit}
                min={1}
                max={25}
                onChange={e => setMusicLimit(Math.min(25, Math.max(1, Number(e.target.value))))}
                style={{
                  width: 72,
                  padding: '10px 12px',
                  borderRadius: 12,
                  border: '1.5px solid var(--line)',
                  background: 'var(--paper-bone)',
                  font: '400 14px/1 var(--font-sans)',
                  color: 'var(--ink-deep)',
                  outline: 'none',
                }}
              />
            </div>
            <button
              onClick={handleMusicSearch}
              disabled={musicLoading || !musicTerm.trim()}
              style={{
                padding: '10px 20px',
                borderRadius: 12,
                border: 'none',
                background: (musicLoading || !musicTerm.trim()) ? 'var(--sage-mist)' : 'var(--sage-leaf)',
                color: 'var(--paper-pure)',
                font: '600 14px/1 var(--font-sans)',
                cursor: (musicLoading || !musicTerm.trim()) ? 'not-allowed' : 'pointer',
                opacity: (musicLoading || !musicTerm.trim()) ? 0.6 : 1,
                transition: 'background var(--dur-1) var(--ease-out)',
                whiteSpace: 'nowrap',
              }}
            >
              {musicLoading ? '검색 중...' : '검색 / 통신 테스트'}
            </button>
          </div>

          {musicLoading && (
            <div style={{ padding: '8px 0' }}>
              <ThinkingDots visible />
            </div>
          )}

          {/* 통신 결과 패널 */}
          {musicResult != null && !musicLoading && (
            <>
              <div style={{
                background: 'var(--paper-pure)',
                border: '1px solid var(--line-faint)',
                borderRadius: 10,
                padding: '12px 14px',
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
              }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  <span style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                    fontWeight: 600,
                    padding: '2px 8px',
                    borderRadius: 4,
                    background: musicResult.ok ? 'var(--sage-wash)' : 'var(--accent-clay-soft)',
                    color: musicResult.ok ? 'var(--sage-forest)' : 'var(--accent-clay)',
                  }}>
                    {musicResult.ok ? '성공' : '실패'}
                  </span>
                  {musicResult.status_code != null && (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--ink-meta)' }}>
                      HTTP {musicResult.status_code}
                    </span>
                  )}
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--ink-meta)' }}>
                    {musicResult.latency_ms} ms
                  </span>
                  {musicResult.count != null && (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--ink-meta)' }}>
                      {musicResult.count}건
                    </span>
                  )}
                </div>
                {!musicResult.ok && musicResult.error && (
                  <p style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--accent-clay)', margin: '4px 0 0', wordBreak: 'break-word' }}>
                    {musicResult.error}
                  </p>
                )}
              </div>

              {/* Raw/Pretty 토글 */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8 }}>
                <button
                  onClick={() => setMusicRaw(r => !r)}
                  style={{
                    background: 'none',
                    border: '1px solid var(--line)',
                    borderRadius: 6,
                    fontFamily: 'var(--font-mono)',
                    fontSize: 11,
                    color: 'var(--ink-meta)',
                    cursor: 'pointer',
                    padding: '2px 8px',
                  }}
                >
                  {musicRaw ? 'Pretty' : 'Raw'}
                </button>
              </div>

              {musicRaw ? (
                <pre style={{
                  background: 'var(--paper-mist)',
                  borderRadius: 8,
                  padding: '10px 12px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 12,
                  color: 'var(--ink-deep)',
                  margin: 0,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  maxHeight: 400,
                  overflowY: 'auto',
                }}>
                  {JSON.stringify(musicResult, null, 2)}
                </pre>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {musicResult.results.length === 0 ? (
                    <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-hint)' }}>결과 없음</p>
                  ) : (
                    musicResult.results.map((track, i) => (
                      <div
                        key={i}
                        style={{
                          background: 'var(--paper-pure)',
                          border: '1px solid var(--line)',
                          borderRadius: 14,
                          padding: '12px 14px',
                          display: 'flex',
                          gap: 12,
                          alignItems: 'flex-start',
                        }}
                      >
                        {track.artworkUrl100 && (
                          <img
                            src={track.artworkUrl100}
                            alt={track.trackName}
                            width={56}
                            height={56}
                            style={{ borderRadius: 8, flexShrink: 0, objectFit: 'cover' }}
                          />
                        )}
                        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
                          <p style={{ font: '600 14px/1.3 var(--font-sans)', color: 'var(--ink-deep)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {track.trackName || '(제목 없음)'}
                          </p>
                          <p style={{ font: '400 12px/1.3 var(--font-sans)', color: 'var(--ink-meta)', margin: 0 }}>
                            {track.artistName}
                          </p>
                          <p style={{ font: '400 11px/1.3 var(--font-sans)', color: 'var(--ink-hint)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {track.collectionName}
                          </p>
                          {track.previewUrl && (
                            <audio
                              controls
                              src={track.previewUrl}
                              style={{ width: '100%', height: 32, marginTop: 4 }}
                            />
                          )}
                          {track.trackViewUrl && (
                            <a
                              href={track.trackViewUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ font: '400 11px/1 var(--font-sans)', color: 'var(--sage-leaf)', marginTop: 2 }}
                            >
                              iTunes에서 보기
                            </a>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Bedrock 로그 탭 */}
      {tab === 'bedrock' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
            <button
              onClick={fetchBedrockLogs}
              style={{
                background: 'transparent',
                border: 'none',
                fontFamily: 'var(--font-sans)',
                fontSize: 13,
                color: 'var(--ink-meta)',
                cursor: 'pointer',
                padding: '4px 8px',
              }}
            >
              새로고침
            </button>
          </div>

          {bedrockLoading && (
            <div style={{ padding: '16px 0' }}>
              <ThinkingDots visible />
            </div>
          )}
          {bedrockError && <p style={{ color: 'var(--accent-clay)', fontFamily: 'var(--font-sans)', fontSize: 14 }}>{bedrockError}</p>}
          {!bedrockLoading && !bedrockError && bedrockLogs.length === 0 && (
            <p style={{ color: 'var(--ink-meta)', fontFamily: 'var(--font-sans)', fontSize: 14 }}>로그 없음</p>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {bedrockLogs.map(log => (
              <div
                key={log.id}
                style={{
                  background: 'var(--paper-pure)',
                  border: '1px solid var(--line)',
                  borderRadius: 'var(--r-4, 18px)',
                  padding: 16,
                  animation: 'days-rise 380ms var(--ease-out) both',
                  cursor: 'pointer',
                }}
                onClick={() => setExpandedLogId(expandedLogId === log.id ? null : log.id)}
              >
                <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 500, fontSize: 11, color: 'var(--sage-forest)', margin: '0 0 6px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                  Q{log.sequence} · {log.asked_at ? new Date(log.asked_at).toLocaleString('ko-KR') : '—'}
                </p>
                <p style={{ fontFamily: 'var(--font-sans)', fontSize: 14, color: 'var(--ink-deep)', margin: '0 0 4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: expandedLogId === log.id ? 'normal' : 'nowrap' }}>
                  <span style={{ color: 'var(--sage-forest)', fontWeight: 600 }}>Q</span> {log.question}
                </p>
                {log.answer && (
                  <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-hint)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: expandedLogId === log.id ? 'normal' : 'nowrap' }}>
                    <span style={{ color: 'var(--sage-leaf)', fontWeight: 600 }}>A</span> {log.answer}
                  </p>
                )}

                {expandedLogId === log.id && (
                  <div style={{ marginTop: 16 }}>
                    <div style={{ marginBottom: 16 }}>
                      <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 12, color: 'var(--ink-deep)', margin: '0 0 6px' }}>
                        보낸 프롬프트
                      </p>
                      <pre style={{
                        background: 'var(--paper-mist)',
                        borderRadius: 8,
                        padding: '10px 12px',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 12,
                        lineHeight: 1.5,
                        color: 'var(--ink-deep)',
                        overflowY: 'auto',
                        maxHeight: 300,
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        margin: 0,
                      }}>
                        {log.prompt ?? '(없음)'}
                      </pre>
                    </div>
                    <div style={{ marginBottom: 16 }}>
                      <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 12, color: 'var(--ink-deep)', margin: '0 0 6px' }}>
                        Bedrock 응답
                      </p>
                      <pre style={{
                        background: 'var(--paper-mist)',
                        borderRadius: 8,
                        padding: '10px 12px',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 12,
                        lineHeight: 1.5,
                        color: 'var(--ink-deep)',
                        overflowY: 'auto',
                        maxHeight: 300,
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        margin: 0,
                      }}>
                        {log.raw_response ?? '(없음)'}
                      </pre>
                    </div>
                    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                      {[
                        ['model', log.model_id],
                        ['input', log.input_tokens != null ? `${log.input_tokens} tok` : null],
                        ['output', log.output_tokens != null ? `${log.output_tokens} tok` : null],
                        ['latency', log.latency_ms != null ? `${log.latency_ms} ms` : null],
                      ].filter(([, v]) => v != null).map(([k, v]) => (
                        <span key={k as string} style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-meta)' }}>
                          {k}: {v}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
