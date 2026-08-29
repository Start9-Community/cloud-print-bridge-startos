export const DEFAULT_LANG = 'en_US'

const dict = {
  // Configure action — Nextcloud
  'Nextcloud Username': 0,
  'Nextcloud account used to access the Cloud Print folders.': 1,
  'Nextcloud App Password': 2,
  'App password created in Nextcloud for Cloud Print Bridge.': 3,

  // Configure action — printer
  'Printer Mode': 4,
  'Send to a fixed IPP address, or find the printer by its permanent UUID each time. Run Discover Printers to learn that UUID.': 5,
  'Manual IPP URL': 6,
  'Locate Printer by UUID': 7,
  'Printer IPP URL': 8,
  'The printer address, for example ipp://192.168.1.50/ipp/print. In UUID mode this is tried first, before searching.': 9,
  'Printer Discovery Network(s)': 10,
  'IPv4 networks to search, separated by commas — for example 192.168.1.0/24, 10.20.30.0/24.': 11,
  'Printer UUID': 12,
  'The printer’s permanent IPP UUID, as reported by Discover Printers — for example urn:uuid:12345678-1234-1234-1234-123456789abc.': 13,

  // Configure action — print options
  'Paper Size': 14,
  'Paper size every job is rendered onto.': 15,
  'Letter (8.5 x 11 in)': 16,
  'A4 (210 x 297 mm)': 17,
  'Legal (8.5 x 14 in)': 18,
  'Executive (7.25 x 10.5 in)': 19,
  'A5 (148 x 210 mm)': 20,
  'A6 (105 x 148 mm)': 21,
  'B5 (176 x 250 mm)': 22,
  'Color Mode': 23,
  'Print in color or in grayscale.': 24,
  Color: 25,
  Monochrome: 26,
  Sides: 27,
  'One-sided or duplex printing.': 28,
  'One-sided': 29,
  'Two-sided - Long Edge': 30,
  'Two-sided - Short Edge': 31,
  Copies: 32,
  'Number of copies to print. Copies are submitted as separate print jobs for printer compatibility.': 33,
  'Polling Interval': 34,
  'How often to check the Nextcloud Inbox for new print jobs.': 35,
  seconds: 36,

  // Configure action — metadata and validation
  'Configure Cloud Print Bridge': 37,
  'Set Nextcloud and printer connection settings.': 38,
  'Printer IPP URL must begin with ipp:// or ipps://': 39,
  'Locating a printer by UUID needs at least one discovery network': 40,
  'Set your Nextcloud account and printer to start printing': 41,

  // Discover Printers action
  'Discover Printers': 42,
  'Search the network for IPP printers and show their permanent UUIDs and addresses.': 43,
  'Enter at least one network to search.': 44,
  'Printer discovery failed.': 45,
  'Printer discovery returned unreadable output.': 46,
  'Printer Discovery': 47,
  'No IPP printers answered on the network(s) you gave.': 48,
  Result: 49,
  'No printers found': 50,
  'Discovered Printers': 51,
  'Copy the UUID of the printer you want into Configure Cloud Print Bridge, then choose Locate Printer by UUID.': 52,
  Printer: 53,
  UUID: 54,
  'This printer advertises no UUID': 55,
  'IPP URL': 56,

  // Runtime
  'Starting Cloud Print Bridge!': 57,
  'Print Queue': 58,
  'Watching the Nextcloud print queue': 59,
  'The Nextcloud print queue is not reachable': 60,
} as const

/**
 * Plumbing. DO NOT EDIT.
 */
export type I18nKey = keyof typeof dict
export type LangDict = Record<(typeof dict)[I18nKey], string>
export default dict
