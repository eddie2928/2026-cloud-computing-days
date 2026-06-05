import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  getPlantTestSeason, setPlantTestSeason, clearPlantTestSeason, hasPlantTestSeason,
  getPlantTestState, setPlantTestState, clearPlantTestState, hasPlantTestState,
  clearPlantTest, hasPlantTest, PLANT_TEST_EVENT,
} from '../../lib/plantTest'

// Use a simple localStorage mock via vitest's jsdom environment
beforeEach(() => {
  localStorage.clear()
})

describe('plantTest season', () => {
  it('get returns null when not set', () => {
    expect(getPlantTestSeason()).toBeNull()
  })

  it('set/get round-trip', () => {
    setPlantTestSeason('winter')
    expect(getPlantTestSeason()).toBe('winter')
  })

  it('has returns false when not set', () => {
    expect(hasPlantTestSeason()).toBe(false)
  })

  it('has returns true after set', () => {
    setPlantTestSeason('summer')
    expect(hasPlantTestSeason()).toBe(true)
  })

  it('clear removes the value', () => {
    setPlantTestSeason('autumn')
    clearPlantTestSeason()
    expect(getPlantTestSeason()).toBeNull()
    expect(hasPlantTestSeason()).toBe(false)
  })
})

describe('plantTest state', () => {
  it('get returns null when not set', () => {
    expect(getPlantTestState()).toBeNull()
  })

  it('set/get round-trip', () => {
    setPlantTestState(3)
    expect(getPlantTestState()).toBe(3)
  })

  it('has returns true after set', () => {
    setPlantTestState(2)
    expect(hasPlantTestState()).toBe(true)
  })

  it('clear removes the value', () => {
    setPlantTestState(1)
    clearPlantTestState()
    expect(getPlantTestState()).toBeNull()
    expect(hasPlantTestState()).toBe(false)
  })
})

describe('clearPlantTest / hasPlantTest', () => {
  it('hasPlantTest is true when either is set', () => {
    setPlantTestSeason('spring')
    expect(hasPlantTest()).toBe(true)
  })

  it('clearPlantTest removes both', () => {
    setPlantTestSeason('spring')
    setPlantTestState(2)
    clearPlantTest()
    expect(hasPlantTest()).toBe(false)
    expect(getPlantTestSeason()).toBeNull()
    expect(getPlantTestState()).toBeNull()
  })
})

describe('PLANT_TEST_EVENT dispatch', () => {
  it('dispatches event on setPlantTestSeason', () => {
    const handler = vi.fn()
    window.addEventListener(PLANT_TEST_EVENT, handler)
    setPlantTestSeason('winter')
    window.removeEventListener(PLANT_TEST_EVENT, handler)
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('dispatches event on clearPlantTest', () => {
    const handler = vi.fn()
    window.addEventListener(PLANT_TEST_EVENT, handler)
    clearPlantTest()
    window.removeEventListener(PLANT_TEST_EVENT, handler)
    expect(handler).toHaveBeenCalledTimes(1)
  })
})
