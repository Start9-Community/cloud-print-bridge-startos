import { sdk } from './sdk'

export const setDependencies = sdk.setupDependencies(async ({ effects }) => ({
  nextcloud: {
    kind: 'running',
    versionRange: '>=33.0.6:1',
    healthChecks: ['nextcloud'],
  },
}))
