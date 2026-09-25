import { configJson } from '../fileModels/config.json'
import { i18n } from '../i18n'
import { sdk } from '../sdk'
import { WORKER_USER } from '../utils'

const { InputSpec, Value } = sdk

const inputSpec = InputSpec.of({
  printerDiscoveryCidr: Value.text({
    name: i18n('Printer Discovery Network(s)'),
    description: i18n(
      'IPv4 networks to search, separated by commas — for example 192.168.1.0/24, 10.20.30.0/24.',
    ),
    required: true,
    default: '',
    masked: false,
  }),
})

type DiscoveredPrinter = {
  name: string
  model: string
  info: string
  uuid: string
  uri: string
  host: string
}

const stringField = (record: Record<string, unknown>, key: string) =>
  typeof record[key] === 'string' ? record[key] : ''

export const discoverPrinters = sdk.Action.withInput(
  'discover-printers',
  {
    name: i18n('Discover Printers'),
    description: i18n(
      'Search the network for IPP printers and show their permanent UUIDs and addresses.',
    ),
    warning: null,
    allowedStatuses: 'any',
    group: null,
    visibility: 'enabled',
  },

  inputSpec,

  async () => ({
    printerDiscoveryCidr:
      (await configJson.read().once())?.printerDiscoveryCidr ?? '',
  }),

  async ({ effects, input }) => {
    const networks = input.printerDiscoveryCidr.trim()

    if (!networks)
      throw new Error(i18n('Enter at least one network to search.'))

    const execution = await sdk.SubContainer.withTemp(
      effects,
      { imageId: 'main' },
      sdk.Mounts.of(),
      'discover-printers',
      async (sub) =>
        sub.exec(
          ['python3', '/app/discover_printers.py', networks],
          { user: WORKER_USER },
          null,
        ),
    )

    if (execution.exitCode !== 0)
      throw new Error(
        execution.stderr.toString().trim() || i18n('Printer discovery failed.'),
      )

    let parsed: unknown

    try {
      parsed = JSON.parse(execution.stdout.toString().trim())
    } catch {
      throw new Error(i18n('Printer discovery returned unreadable output.'))
    }

    if (!Array.isArray(parsed))
      throw new Error(i18n('Printer discovery returned unreadable output.'))

    const printers = parsed.flatMap<DiscoveredPrinter>((item) => {
      if (typeof item !== 'object' || item === null || Array.isArray(item))
        return []

      const record = item as Record<string, unknown>
      const uri = stringField(record, 'uri')

      return uri
        ? [
            {
              name: stringField(record, 'name'),
              model: stringField(record, 'model'),
              info: stringField(record, 'info'),
              uuid: stringField(record, 'uuid'),
              uri,
              host: stringField(record, 'host'),
            },
          ]
        : []
    })

    if (!printers.length)
      return {
        version: '1' as const,
        title: i18n('Printer Discovery'),
        message: i18n('No IPP printers answered on the network(s) you gave.'),
        result: {
          type: 'single' as const,
          name: i18n('Result'),
          description: null,
          value: i18n('No printers found'),
          masked: false,
          copyable: false,
          qr: false,
        },
      }

    return {
      version: '1' as const,
      title: i18n('Discovered Printers'),
      message: i18n(
        'Copy the UUID of the printer you want into Configure Cloud Print Bridge, then choose Locate Printer by UUID.',
      ),
      result: {
        type: 'group' as const,
        value: printers.flatMap((printer, index) => {
          const label =
            printer.name ||
            printer.model ||
            printer.host ||
            `${i18n('Printer')} ${index + 1}`

          const description =
            [printer.model, printer.info, printer.host]
              .filter(Boolean)
              .join(' — ') || null

          return [
            {
              type: 'single' as const,
              name: `${label} — ${i18n('UUID')}`,
              description,
              value: printer.uuid || i18n('This printer advertises no UUID'),
              masked: false,
              copyable: !!printer.uuid,
              qr: false,
            },
            {
              type: 'single' as const,
              name: `${label} — ${i18n('IPP URL')}`,
              description: null,
              value: printer.uri,
              masked: false,
              copyable: true,
              qr: false,
            },
          ]
        }),
      },
    }
  },
)
