import { sdk } from '../sdk'
import { configure } from './configure'
import { discoverPrinters } from './discoverPrinters'

export const actions = sdk.Actions.of()
  .addAction(configure)
  .addAction(discoverPrinters)
