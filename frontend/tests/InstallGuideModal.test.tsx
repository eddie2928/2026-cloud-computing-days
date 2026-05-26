import { render, screen, fireEvent } from '@testing-library/react'
import { vi, describe, it, expect } from 'vitest'
import { InstallGuideModal } from '../src/components/days/InstallGuideModal'

describe('InstallGuideModal', () => {
  it('open=false이면 아무것도 렌더 안 됨', () => {
    const onClose = vi.fn()
    render(<InstallGuideModal open={false} onClose={onClose} mode="all" />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('open=true mode=all: iPhone·Android·Mac·Windows 4개 라벨 존재', () => {
    const onClose = vi.fn()
    render(<InstallGuideModal open={true} onClose={onClose} mode="all" />)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('iPhone (Safari)')).toBeInTheDocument()
    expect(screen.getByText('Android')).toBeInTheDocument()
    expect(screen.getByText('Mac')).toBeInTheDocument()
    expect(screen.getByText('Windows PC')).toBeInTheDocument()
  })

  it('open=true mode=ios-safari: iPhone 안내만 존재, Android·Windows 라벨 부재', () => {
    const onClose = vi.fn()
    render(<InstallGuideModal open={true} onClose={onClose} mode="ios-safari" />)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('iPhone (Safari)')).toBeInTheDocument()
    expect(screen.queryByText('Android')).not.toBeInTheDocument()
    expect(screen.queryByText('Windows PC')).not.toBeInTheDocument()
  })

  it('X 버튼 클릭: onClose 1회 호출', () => {
    const onClose = vi.fn()
    render(<InstallGuideModal open={true} onClose={onClose} mode="all" />)
    fireEvent.click(screen.getByRole('button', { name: '닫기' }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('ESC 키: onClose 1회 호출', () => {
    const onClose = vi.fn()
    render(<InstallGuideModal open={true} onClose={onClose} mode="all" />)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('백드롭 클릭: onClose 1회 호출', () => {
    const onClose = vi.fn()
    const { container } = render(<InstallGuideModal open={true} onClose={onClose} mode="all" />)
    // 백드롭은 가장 바깥 div (fixed overlay)
    const backdrop = container.firstChild as HTMLElement
    fireEvent.click(backdrop)
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
