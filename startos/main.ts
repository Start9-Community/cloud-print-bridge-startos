import { uiPort as nextcloudInternalPort } from 'nextcloud-startos/startos/utils'
import { i18n } from './i18n'
import { sdk } from './sdk'
import { WORKER_USER } from './utils'

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

  // Nextcloud rejects a request whose Host header is not one of its
  // trusted_domains, and it derives that list from this same mapper — so
  // whatever this picks, Nextcloud already trusts.
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

        return (
          [
            ...new Set(
              ui.addressInfo
                .filter({ exclude: { kind: ['link-local', 'bridge'] } })
                .format('hostname-info')
                .map((entry) =>
                  entry.metadata.kind === 'ipv6'
                    ? `[${entry.hostname}]`
                    : entry.hostname,
                ),
            ),
          ]
            .sort()
            .at(0) ?? null
        )
      },
    )
    .const()

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

  return sdk.Daemons.of(effects).addDaemon('main', {
    subcontainer,

    exec: {
      command: sdk.useEntrypoint(),
      user: WORKER_USER,
      env: {
        ...(nextcloudBridgeAddress && {
          NEXTCLOUD_BRIDGE_ADDRESS: nextcloudBridgeAddress,
        }),
        ...(nextcloudHostHeader && {
          NEXTCLOUD_HOST_HEADER: nextcloudHostHeader,
        }),
      },
    },

    ready: {
      display: i18n('Print Queue'),
      fn: () =>
        sdk.healthCheck.runHealthScript(
          ['sh', '-c', 'test -f /tmp/cloud-print-bridge.ready'],
          subcontainer,
          {
            message: () => i18n('Watching the Nextcloud print queue'),
            errorMessage: i18n('The Nextcloud print queue is not reachable'),
          },
        ),
    },

    requires: [],
  })
})
