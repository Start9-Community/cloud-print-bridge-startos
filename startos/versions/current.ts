import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '0.6.0:1',
  releaseNotes: {
    en_US: 'Discover Printers no longer fails when searching large networks.',
    es_ES: '«Descubrir impresoras» ya no falla al buscar en redes grandes.',
    de_DE:
      '„Drucker suchen“ schlägt beim Durchsuchen großer Netzwerke nicht mehr fehl.',
    pl_PL:
      'Akcja „Wykryj drukarki” nie kończy się już błędem podczas przeszukiwania dużych sieci.',
    fr_FR:
      "« Découvrir les imprimantes » n'échoue plus lors de la recherche sur de grands réseaux.",
  },
  migrations: {
    up: async ({ effects }) => {},
    down: IMPOSSIBLE,
  },
})
