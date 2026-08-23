import { configJson } from '../fileModels/config.json'
import { sdk } from '../sdk'

export const seedConfig = sdk.setupOnInit(async (effects) => {
  await configJson.merge(effects, {})
})
