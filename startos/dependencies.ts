import { sdk } from './sdk'

export const dependencies = sdk.Dependencies.of().addDependency(
  sdk.Dependency.required('nextcloud', {
    description: 'Provides the WebDAV print queue.',
    metadata: {
      title: 'Nextcloud',
      icon: 'https://raw.githubusercontent.com/Start9Labs/nextcloud-startos/next/icon.svg',
    },
    versionRange: '>=33.0.6:1',
    kind: 'running',
    healthChecks: ['nextcloud'],
  }),
)
