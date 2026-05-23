import { useState, useEffect } from 'react'
import client from '../api/client'

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

export function Admin() {
  const [selectedTable, setSelectedTable] = useState<string>(TABLES[0])
  const [rows, setRows] = useState<Record<string, unknown>[]>([])
  const [columns, setColumns] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    client
      .get(`/admin/tables/${selectedTable}`)
      .then(res => {
        const data: Record<string, unknown>[] = res.data ?? []
        setRows(data)
        setColumns(data.length > 0 ? Object.keys(data[0]) : [])
      })
      .catch(() => setError('데이터를 불러오지 못했습니다.'))
      .finally(() => setLoading(false))
  }, [selectedTable])

  return (
    <div style={{ padding: '1rem', fontFamily: 'monospace', fontSize: '0.85rem' }}>
      <h2>[개발자] DB 조회</h2>
      <div style={{ marginBottom: '1rem' }}>
        <label htmlFor="table-select">테이블: </label>
        <select
          id="table-select"
          value={selectedTable}
          onChange={e => setSelectedTable(e.target.value)}
        >
          {TABLES.map(t => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {loading && <p>로딩 중...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {!loading && !error && rows.length === 0 && <p>데이터 없음</p>}
      {!loading && !error && rows.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table border={1} cellPadding={4} style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                {columns.map(col => (
                  <th key={col} style={{ background: '#f0f0f0' }}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {columns.map(col => (
                    <td key={col}>{String(row[col] ?? '')}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
