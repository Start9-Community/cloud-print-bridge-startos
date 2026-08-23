import { sdk } from './sdk'

export const setDependencies = sdk.setupDependencies(
  async ({ effects }) => ({
    nextcloud: {
      kind: 'running',
      versionRange: '>=0.0.0:0',
      healthChecks: ['nextcloud'],
    },
  }),
)
