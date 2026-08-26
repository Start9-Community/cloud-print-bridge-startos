import { configJson } from '../fileModels/config.json'
import { sdk } from '../sdk'

const { InputSpec, Value } = sdk

const inputSpec = InputSpec.of({
  printerDiscoveryCidr: Value.text({
    name: 'Printer Discovery Network(s)',
    description:
      'One or more IPv4 networks to scan for IPP printers. Separate multiple networks with commas, for example 192.168.1.0/24 or 192.168.1.0/24, 10.20.30.0/24.',
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

function stringField(
  value: Record<string, unknown>,
  key: string,
): string {
  const field = value[key]
  return typeof field === 'string' ? field : ''
}

export const discoverPrinters = sdk.Action.withInput(
  'discover-printers',
  {
    name: 'Discover Printers',
    description:
      'Scan the configured network(s) for IPP printers and display their persistent UUIDs and IPP addresses.',
    warning: null,
    allowedStatuses: 'any',
    group: null,
    visibility: 'enabled',
  },

  inputSpec,

  async () => {
    const current = await configJson.read().once()

    return {
      printerDiscoveryCidr:
        current?.printerDiscoveryCidr ?? '',
    }
  },

  async ({ effects, input }) => {
    const discoveryNetworks =
      input.printerDiscoveryCidr.trim()

    if (!discoveryNetworks) {
      throw new Error(
        'Printer discovery network(s) are required.',
      )
    }

    const execution =
      await sdk.SubContainer.withTemp(
        effects,
        { imageId: 'main' },
        sdk.Mounts.of(),
        'discover-printers',
        async sub =>
          sub.exec([
            'python3',
            '/app/discover_printers.py',
            discoveryNetworks,
          ]),
      )

    const stdout = execution.stdout.toString().trim()
    const stderr = execution.stderr.toString().trim()

    if (execution.exitCode !== 0) {
      throw new Error(
        stderr ||
          'Printer discovery failed.',
      )
    }

    let parsed: unknown

    try {
      parsed = JSON.parse(stdout)
    } catch {
      throw new Error(
        'Printer discovery returned invalid output.',
      )
    }

    if (!Array.isArray(parsed)) {
      throw new Error(
        'Printer discovery returned an unexpected result.',
      )
    }

    const printers: DiscoveredPrinter[] = []

    for (const item of parsed) {
      if (
        typeof item !== 'object' ||
        item === null ||
        Array.isArray(item)
      ) {
        continue
      }

      const record = item as Record<string, unknown>

      const printer: DiscoveredPrinter = {
        name: stringField(record, 'name'),
        model: stringField(record, 'model'),
        info: stringField(record, 'info'),
        uuid: stringField(record, 'uuid'),
        uri: stringField(record, 'uri'),
        host: stringField(record, 'host'),
      }

      if (printer.uri) {
        printers.push(printer)
      }
    }

    if (printers.length === 0) {
      return {
        version: '1',
        title: 'Printer Discovery',
        message:
          'No IPP printers were found on the specified network(s).',
        result: {
          type: 'single' as const,
          name: 'Result',
          description: null,
          value: 'No IPP printers found',
          masked: false,
          copyable: false,
          qr: false,
        },
      }
    }

    const values = printers.flatMap(
      (printer, index) => {
        const label =
          printer.name ||
          printer.model ||
          printer.host ||
          `Printer ${index + 1}`

        const descriptionParts = [
          printer.model,
          printer.info,
          printer.host
            ? `Host: ${printer.host}`
            : '',
        ].filter(Boolean)

        const description =
          descriptionParts.length > 0
            ? descriptionParts.join(' — ')
            : null

        return [
          {
            type: 'single' as const,
            name: `${label} — UUID`,
            description,
            value:
              printer.uuid ||
              'Printer did not advertise a UUID',
            masked: false,
            copyable: Boolean(printer.uuid),
            qr: false,
          },
          {
            type: 'single' as const,
            name: `${label} — IPP URI`,
            description: null,
            value: printer.uri,
            masked: false,
            copyable: true,
            qr: false,
          },
        ]
      },
    )

    return {
      version: '1',
      title: 'Discovered Printers',
      message:
        printers.length === 1
          ? 'Found 1 IPP printer. Copy its UUID into Configure Cloud Print Bridge and select Locate Printer by UUID.'
          : `Found ${printers.length} IPP printers. Copy the UUID of the printer you want into Configure Cloud Print Bridge and select Locate Printer by UUID.`,
      result: {
        type: 'group' as const,
        value: values,
      },
    }
  },
)
