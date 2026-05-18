export function Profile() {
  return (
    <div style={{ padding: 24, maxWidth: 400 }}>
      <h2>프로필</h2>
      <form onSubmit={(e) => e.preventDefault()}>
        <div style={{ marginBottom: 16 }}>
          <label>표시 이름</label>
          <input
            type="text"
            defaultValue="default-user"
            style={{ display: 'block', width: '100%', marginTop: 8, padding: 8 }}
          />
        </div>
        <button type="submit" style={{ padding: '8px 24px' }}>
          저장
        </button>
      </form>
    </div>
  )
}
