import { uiPort as nextcloudInternalPort } from 'nextcloud-startos/startos/utils'
import { i18n } from './i18n'
import { sdk } from './sdk'

const nextcloudPackageId = 'nextcloud' as const
const nextcloudHostId = 'main' as const

export const main = sdk.setupMain(async ({ effects }) => {
  console.info(i18n('Starting Cloud Print Bridge!'))

  const nextcloudBridgeAddress = await sdk.host
    .getBridgeAddress(effects, {
      packageId: nextcloudPackageId,
      hostId: nextcloudHostId,
      internalPort: nextcloudInternalPort,
    })
    .const()

  const nextcloudHostHeader = await sdk.host
    .get(
      effects,
      {
        packageId: nextcloudPackageId,
        hostId: nextcloudHostId,
      },
      (host) => {
        if (!host) return null

        const ui = Object.values(host.bindings)
          .flatMap((binding) => Object.values(binding.interfaces))
          .find((iface) => iface.id === 'ui')

        if (!ui) return null

        const hostnames = [
          ...new Set(
            ui.addressInfo
              .filter({
                exclude: {
                  kind: ['link-local', 'bridge'],
                },
              })
              .format('hostname-info')
              .map((entry) =>
                entry.metadata.kind === 'ipv6'
                  ? `[${entry.hostname}]`
                  : entry.hostname,
              ),
          ),
        ].sort()

        return hostnames[0] ?? null
      },
    )
    .const()

  if (nextcloudBridgeAddress) {
    console.info('Resolved Nextcloud StartOS bridge address.')
  } else {
    console.info(
      'Nextcloud bridge address is not currently available.',
    )
  }

  if (nextcloudHostHeader) {
    console.info('Resolved Nextcloud HTTP host identity.')
  } else {
    console.info(
      'Nextcloud HTTP host identity is not currently available.',
    )
  }

  const subcontainer = sdk.SubContainer.of(
    effects,
    { imageId: 'main' },
    sdk.Mounts.of().mountVolume({
      volumeId: 'main',
      subpath: null,
      mountpoint: '/data',
      readonly: false,
    }),
    'main',
  )

  const env: Record<string, string> = {}

  if (nextcloudBridgeAddress) {
    env.NEXTCLOUD_BRIDGE_ADDRESS =
      nextcloudBridgeAddress
  }

  if (nextcloudHostHeader) {
    env.NEXTCLOUD_HOST_HEADER =
      nextcloudHostHeader
  }

  return sdk.Daemons.of(effects).addDaemon('main', {
    subcontainer,

    exec: {
      command: sdk.useEntrypoint(),
      env,
    },

    ready: {
      display: null,
      fn: () =>
        sdk.healthCheck.runHealthScript(
          [
            'python3',
            '-c',
            'import os,sys; sys.exit(0 if os.path.exists("/tmp/cloud-print-bridge.ready") else 1)',
          ],
          subcontainer,
          {
            errorMessage: i18n(
              'Cloud Print Bridge is waiting for configuration',
            ),
          },
        ),
    },

    requires: [],
  })
})
