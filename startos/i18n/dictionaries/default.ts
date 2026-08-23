export const DEFAULT_LANG = 'en_US'

const dict = {
  // Runtime
  'Starting Cloud Print Bridge!': 0,

  // Configure action
  'Configure Cloud Print Bridge': 4,
  'Set Nextcloud and printer connection settings.': 5,
  'Nextcloud URL': 6,
  'Nextcloud Username': 8,
  'Nextcloud account used to access the Cloud Print folders.': 9,
  'Nextcloud App Password': 10,
  'App password created in Nextcloud for Cloud Print Bridge.': 11,
  'Printer IPP URL': 12,
  'Polling Interval': 14,
  'How often to check the Nextcloud Inbox for new print jobs.': 15,
  'seconds': 16,
  'Cloud Print Bridge is waiting for configuration': 17,

  // Print options
  'PDF Paper Size': 18,
  'Default paper size used when converting PDF files to printer raster.': 19,
  'Letter (8.5 x 11 in)': 20,
  'A4 (210 x 297 mm)': 21,
  'Legal (8.5 x 14 in)': 22,
  'Executive (7.25 x 10.5 in)': 23,
  'A5 (148 x 210 mm)': 24,
  'A6 (105 x 148 mm)': 25,
  'B5 (176 x 250 mm)': 26,
  'PDF Color Mode': 27,
  'Choose whether PDF files are rasterized in color or grayscale.': 28,
  'Color': 29,
  'Monochrome': 30,
  'PDF Sides': 31,
  'Choose one-sided printing or duplex printing for PDF files.': 32,
  'One-sided': 33,
  'Two-sided - Long Edge': 34,
  'Two-sided - Short Edge': 35,
  'PDF Copies': 36,
  'Number of copies to print. Copies are submitted as separate print jobs for printer compatibility.': 37,
} as const

/**
 * Plumbing. DO NOT EDIT.
 */
export type I18nKey = keyof typeof dict
export type LangDict = Record<(typeof dict)[I18nKey], string>
export default dict
