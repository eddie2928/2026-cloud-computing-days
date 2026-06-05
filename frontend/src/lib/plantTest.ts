import type { Season } from './season'
import type { PlantState } from '../components/hub/PlantVideoCard'

const SEASON_KEY = 'days_plant_test_season'
const STATE_KEY = 'days_plant_test_state'
const EVENT = 'days-plant-test-changed'

export function getPlantTestSeason(): Season | null {
  return localStorage.getItem(SEASON_KEY) as Season | null
}

export function setPlantTestSeason(season: Season): void {
  localStorage.setItem(SEASON_KEY, season)
  window.dispatchEvent(new Event(EVENT))
}

export function clearPlantTestSeason(): void {
  localStorage.removeItem(SEASON_KEY)
  window.dispatchEvent(new Event(EVENT))
}

export function hasPlantTestSeason(): boolean {
  return localStorage.getItem(SEASON_KEY) !== null
}

export function getPlantTestState(): PlantState | null {
  const v = localStorage.getItem(STATE_KEY)
  return v ? (parseInt(v, 10) as PlantState) : null
}

export function setPlantTestState(state: PlantState): void {
  localStorage.setItem(STATE_KEY, String(state))
  window.dispatchEvent(new Event(EVENT))
}

export function clearPlantTestState(): void {
  localStorage.removeItem(STATE_KEY)
  window.dispatchEvent(new Event(EVENT))
}

export function hasPlantTestState(): boolean {
  return localStorage.getItem(STATE_KEY) !== null
}

export function clearPlantTest(): void {
  localStorage.removeItem(SEASON_KEY)
  localStorage.removeItem(STATE_KEY)
  window.dispatchEvent(new Event(EVENT))
}

export function hasPlantTest(): boolean {
  return hasPlantTestSeason() || hasPlantTestState()
}

export { EVENT as PLANT_TEST_EVENT }
