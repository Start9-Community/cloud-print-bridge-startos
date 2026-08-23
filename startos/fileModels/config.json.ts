import { FileHelper, z } from '@start9labs/start-sdk'
import { sdk } from '../sdk'

export const defaultPollSeconds = 30

export const supportedMedia = [
  'na_letter_8.5x11in',
  'iso_a4_210x297mm',
  'na_legal_8.5x14in',
  'na_executive_7.25x10.5in',
  'iso_a5_148x210mm',
  'iso_a6_105x148mm',
  'iso_b5_176x250mm',
] as const

export const supportedColorModes = [
  'color',
  'monochrome',
] as const

export const supportedSides = [
  'one-sided',
  'two-sided-long-edge',
  'two-sided-short-edge',
] as const

export const supportedPrinterModes = [
  'manual',
  'uuid-discovery',
] as const

const shape = z.object({
  nextcloudUsername: z.string().catch(''),
  nextcloudAppPassword: z.string().catch(''),

  printerMode: z
    .enum(supportedPrinterModes)
    .catch('manual'),

  printerUrl: z.string().catch(''),
  printerDiscoveryCidr: z.string().catch(''),
  printerUuid: z.string().catch(''),

  pollSeconds: z
    .number()
    .int()
    .min(5)
    .max(3600)
    .catch(defaultPollSeconds),

  media: z
    .enum(supportedMedia)
    .catch('na_letter_8.5x11in'),

  colorMode: z
    .enum(supportedColorModes)
    .catch('color'),

  sides: z
    .enum(supportedSides)
    .catch('one-sided'),

  copies: z
    .number()
    .int()
    .min(1)
    .max(99)
    .catch(1),
})

export const configJson = FileHelper.json(
  {
    base: sdk.volumes.main,
    subpath: './config.json',
  },
  shape,
)
