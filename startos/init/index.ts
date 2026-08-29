import { sdk } from '../sdk'
import { setDependencies } from '../dependencies'
import { setInterfaces } from '../interfaces'
import { versionGraph } from '../versions'
import { actions } from '../actions'
import { restoreInit } from '../backups'
import { seedConfig } from './seedConfig'
import { watchSetup } from './watchSetup'

export const init = sdk.setupInit(
  restoreInit,
  versionGraph,
  setInterfaces,
  setDependencies,
  actions,
  seedConfig,
  watchSetup,
)

export const uninit = sdk.setupUninit(versionGraph)
