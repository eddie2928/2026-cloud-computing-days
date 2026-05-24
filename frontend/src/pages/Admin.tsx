import { useState, useEffect, useCallback } from 'react'
import client from '../api/client'
import { ThinkingDots } from '../components/qna/ThinkingDots'

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

type Tab = 'db' | 'bedrock'

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
  borderBottom: active ? '2px solid var(--gold)' : '2px solid transparent',
  padding: '10px 4px',
  fontFamily: 'var(--font-sans)',
  fontWeight: 500,
  fontSize: 14,
  color: active ? 'var(--gold-deep)' : 'var(--ink-stone)',
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

  // Bedrock 로그 탭
  const [bedrockLogs, setBedrockLogs] = useState<BedrockLog[]>([])
  const [bedrockLoading, setBedrockLoading] = useState(false)
  const [bedrockError, setBedrockError] = useState<string | null>(null)
  const [expandedLogId, setExpandedLogId] = useState<number | null>(null)

  useEffect(() => {
    if (tab !== 'db') return
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
  }, [selectedTable, tab])

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
    <div style={{ padding: '16px 16px 40px', background: 'var(--paper-bone)', minHeight: '100vh' }}>
      <h1 style={{ fontFamily: 'var(--font-serif)', fontWeight: 400, fontSize: 24, lineHeight: 1.2, color: 'var(--ink-coffee)', margin: '0 0 20px' }}>
        관리자
      </h1>

      {/* 탭 네비게이션 */}
      <div style={{ display: 'flex', gap: 20, borderBottom: '1px solid var(--line-faint)', marginBottom: 20 }}>
        <button style={tabStyle(tab === 'db')} onClick={() => setTab('db')}>DB 조회</button>
        <button style={tabStyle(tab === 'bedrock')} onClick={() => setTab('bedrock')}>Bedrock 로그</button>
      </div>

      {/* DB 조회 탭 */}
      {tab === 'db' && (
        <div>
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-stone)', display: 'block', marginBottom: 6 }}>
              테이블
            </label>
            <select
              value={selectedTable}
              onChange={e => setSelectedTable(e.target.value)}
              style={{
                background: 'var(--paper-mist)',
                border: '1px solid var(--line)',
                borderRadius: 12,
                padding: '8px 12px',
                fontFamily: 'var(--font-sans)',
                fontSize: 14,
                color: 'var(--ink-coffee)',
                outline: 'none',
                minWidth: 200,
              }}
            >
              {TABLES.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          {dbLoading && (
            <div style={{ padding: '16px 0' }}>
              <ThinkingDots visible />
            </div>
          )}
          {dbError && <p style={{ color: 'var(--clay)', fontFamily: 'var(--font-sans)', fontSize: 14 }}>{dbError}</p>}
          {!dbLoading && !dbError && rows.length === 0 && (
            <p style={{ color: 'var(--ink-stone)', fontFamily: 'var(--font-sans)', fontSize: 14 }}>데이터 없음</p>
          )}
          {!dbLoading && !dbError && rows.length > 0 && (
            <div style={{ overflowX: 'auto', background: 'var(--paper-cream)', border: '1px solid var(--line-faint)', borderRadius: 'var(--r-3, 12px)' }}>
              <table style={{ borderCollapse: 'collapse', width: '100%', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                <thead>
                  <tr>
                    {columns.map(col => (
                      <th key={col} style={{ background: 'var(--paper-warm)', padding: '8px 12px', textAlign: 'left', color: 'var(--ink-walnut)', fontWeight: 600, borderBottom: '1px solid var(--line-faint)', whiteSpace: 'nowrap' }}>
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--line-faint)' }}>
                      {columns.map(col => (
                        <td key={col} style={{ padding: '6px 12px', color: 'var(--ink-coffee)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
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
                color: 'var(--ink-stone)',
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
          {bedrockError && <p style={{ color: 'var(--clay)', fontFamily: 'var(--font-sans)', fontSize: 14 }}>{bedrockError}</p>}
          {!bedrockLoading && !bedrockError && bedrockLogs.length === 0 && (
            <p style={{ color: 'var(--ink-stone)', fontFamily: 'var(--font-sans)', fontSize: 14 }}>로그 없음</p>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {bedrockLogs.map(log => (
              <div
                key={log.id}
                style={{
                  background: 'var(--paper-cream)',
                  border: '1px solid var(--line)',
                  borderRadius: 'var(--r-4, 18px)',
                  padding: 16,
                  animation: 'days-rise 380ms var(--ease-out) both',
                  cursor: 'pointer',
                }}
                onClick={() => setExpandedLogId(expandedLogId === log.id ? null : log.id)}
              >
                <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 500, fontSize: 11, color: 'var(--gold-deep)', margin: '0 0 6px', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                  Q{log.sequence} · {log.asked_at ? new Date(log.asked_at).toLocaleString('ko-KR') : '—'}
                </p>
                <p style={{ fontFamily: 'var(--font-sans)', fontSize: 14, color: 'var(--ink-coffee)', margin: '0 0 4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: expandedLogId === log.id ? 'normal' : 'nowrap' }}>
                  <span style={{ color: 'var(--gold-deep)', fontWeight: 600 }}>Q</span> {log.question}
                </p>
                {log.answer && (
                  <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink-bark)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: expandedLogId === log.id ? 'normal' : 'nowrap' }}>
                    <span style={{ color: 'var(--sage)', fontWeight: 600 }}>A</span> {log.answer}
                  </p>
                )}

                {expandedLogId === log.id && (
                  <div style={{ marginTop: 16 }}>
                    <div style={{ marginBottom: 16 }}>
                      <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 12, color: 'var(--ink-walnut)', margin: '0 0 6px' }}>
                        보낸 프롬프트
                      </p>
                      <pre style={{
                        background: 'var(--paper-mist)',
                        borderRadius: 8,
                        padding: '10px 12px',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 12,
                        lineHeight: 1.5,
                        color: 'var(--ink-coffee)',
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
                      <p style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 12, color: 'var(--ink-walnut)', margin: '0 0 6px' }}>
                        Bedrock 응답
                      </p>
                      <pre style={{
                        background: 'var(--paper-mist)',
                        borderRadius: 8,
                        padding: '10px 12px',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 12,
                        lineHeight: 1.5,
                        color: 'var(--ink-coffee)',
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
                        <span key={k as string} style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--ink-stone)' }}>
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
