import { setupManifest } from '@start9labs/start-sdk'
import { long, short } from './i18n'

export const manifest = setupManifest({
  id: 'cloud-print-bridge',
  title: 'Cloud Print Bridge',
  license: 'AGPL-3.0-only',
  packageRepo: 'https://github.com/purely-reclining/cloud-print-bridge-startos',
  upstreamRepo: 'https://github.com/purely-reclining/cloud-print-bridge-startos',
  marketingUrl: 'https://github.com/purely-reclining/cloud-print-bridge-startos',
  donationUrl: null,
  description: { short, long },
  volumes: ['main'],
  images: {
    main: {
      source: { dockerBuild: {} },
      arch: ['x86_64', 'aarch64'],
    },
  },
  dependencies: {
    nextcloud: {
      description: 'Provides the WebDAV print queue.',
      optional: false,
      metadata: {
        title: 'Nextcloud',
        icon: 'https://raw.githubusercontent.com/Start9Labs/nextcloud-startos/next/icon.svg',
      },
    },
  },
})
