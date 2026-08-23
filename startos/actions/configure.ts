import { i18n } from '../i18n'
import { configJson, defaultPollSeconds } from '../fileModels/config.json'
import { sdk } from '../sdk'

const { InputSpec, Value } = sdk

const inputSpec = InputSpec.of({
  nextcloudUsername: Value.text({
    name: i18n('Nextcloud Username'),
    description: i18n(
      'Nextcloud account used to access the Cloud Print folders.',
    ),
    required: true,
    default: '',
    masked: false,
  }),

  nextcloudAppPassword: Value.text({
    name: i18n('Nextcloud App Password'),
    description: i18n(
      'App password created in Nextcloud for Cloud Print Bridge.',
    ),
    required: true,
    default: '',
    masked: true,
  }),

  printerMode: Value.select({
    name: 'Printer Mode',
    description:
      'Choose a manually configured IPP URL or rediscover a printer by its persistent IPP UUID.',
    default: 'manual',
    values: {
      manual: 'Manual IPP URL',
      'uuid-discovery': 'Automatic UUID Discovery',
    },
  }),

  printerUrl: Value.text({
    name: i18n('Printer IPP URL'),
    description:
      'Manual printer IPP URL. In UUID discovery mode this may also serve as a fallback or last-known address.',
    required: false,
    default: '',
    masked: false,
  }),

  printerDiscoveryCidr: Value.text({
    name: 'Printer Discovery Network(s)',
    description:
      'One or more IPv4 networks to search for the printer. Separate multiple networks with commas, for example 192.168.1.0/24 or 192.168.1.0/24, 10.20.30.0/24.',
    required: false,
    default: '',
    masked: false,
  }),

  printerUuid: Value.text({
    name: 'Printer UUID',
    description:
      'Persistent IPP printer UUID, for example urn:uuid:12345678-1234-1234-1234-123456789abc.',
    required: false,
    default: '',
    masked: false,
  }),

  media: Value.select({
    name: i18n('PDF Paper Size'),
    description: i18n(
      'Default paper size used when converting PDF files to printer raster.',
    ),
    default: 'na_letter_8.5x11in',
    values: {
      'na_letter_8.5x11in': i18n('Letter (8.5 x 11 in)'),
      'iso_a4_210x297mm': i18n('A4 (210 x 297 mm)'),
      'na_legal_8.5x14in': i18n('Legal (8.5 x 14 in)'),
      'na_executive_7.25x10.5in': i18n('Executive (7.25 x 10.5 in)'),
      'iso_a5_148x210mm': i18n('A5 (148 x 210 mm)'),
      'iso_a6_105x148mm': i18n('A6 (105 x 148 mm)'),
      'iso_b5_176x250mm': i18n('B5 (176 x 250 mm)'),
    },
  }),

  colorMode: Value.select({
    name: i18n('PDF Color Mode'),
    description: i18n(
      'Choose whether PDF files are rasterized in color or grayscale.',
    ),
    default: 'color',
    values: {
      color: i18n('Color'),
      monochrome: i18n('Monochrome'),
    },
  }),

  sides: Value.select({
    name: i18n('PDF Sides'),
    description: i18n(
      'Choose one-sided printing or duplex printing for PDF files.',
    ),
    default: 'one-sided',
    values: {
      'one-sided': i18n('One-sided'),
      'two-sided-long-edge': i18n('Two-sided - Long Edge'),
      'two-sided-short-edge': i18n('Two-sided - Short Edge'),
    },
  }),

  copies: Value.number({
    name: i18n('PDF Copies'),
    description: i18n(
      'Number of copies to print. Copies are submitted as separate print jobs for printer compatibility.',
    ),
    required: true,
    default: 1,
    min: 1,
    max: 99,
    step: 1,
    integer: true,
    units: null,
  }),

  pollSeconds: Value.number({
    name: i18n('Polling Interval'),
    description: i18n(
      'How often to check the Nextcloud Inbox for new print jobs.',
    ),
    required: true,
    default: defaultPollSeconds,
    min: 5,
    max: 3600,
    step: 5,
    integer: true,
    units: i18n('seconds'),
  }),
})

export const configure = sdk.Action.withInput(
  'configure',
  {
    name: i18n('Configure Cloud Print Bridge'),
    description: i18n('Set Nextcloud and printer connection settings.'),
    warning: null,
    allowedStatuses: 'any',
    group: null,
    visibility: 'enabled',
  },

  inputSpec,

  async () => {
    const current = await configJson.read().once()

    return (
      current ?? ({
        nextcloudUsername: '',
        nextcloudAppPassword: '',
        printerMode: 'manual',
        printerUrl: '',
        printerDiscoveryCidr: '',
        printerUuid: '',
        media: 'na_letter_8.5x11in',
        colorMode: 'color',
        sides: 'one-sided',
        copies: 1,
        pollSeconds: defaultPollSeconds,
      } as const)
    )
  },

  async ({ effects, input }) => {
    await configJson.merge(effects, {
      ...input,
      printerUrl: input.printerUrl ?? '',
      printerDiscoveryCidr:
        input.printerDiscoveryCidr ?? '',
      printerUuid: input.printerUuid ?? '',
    })
  },
)
