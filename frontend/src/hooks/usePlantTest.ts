import { useState, useEffect } from 'react'
import { getPlantTestSeason, getPlantTestState, PLANT_TEST_EVENT } from '../lib/plantTest'
import type { Season } from '../lib/season'
import type { PlantState } from '../components/hub/PlantVideoCard'

interface PlantTestOverride {
  season: Season | null
  state: PlantState | null
}

function read(): PlantTestOverride {
  return { season: getPlantTestSeason(), state: getPlantTestState() }
}

export function usePlantTest(): PlantTestOverride {
  const [override, setOverride] = useState<PlantTestOverride>(read)

  useEffect(() => {
    const handler = () => setOverride(read())
    window.addEventListener(PLANT_TEST_EVENT, handler)
    return () => window.removeEventListener(PLANT_TEST_EVENT, handler)
  }, [])

  return override
}
