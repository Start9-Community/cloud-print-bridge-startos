import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '0.6.0:3',
  releaseNotes: {
    en_US:
      'Finalizes documentation and package metadata for public release preparation.',
    es_ES:
      'Finaliza la documentación y los metadatos del paquete para preparar la publicación pública.',
    de_DE:
      'Schließt Dokumentation und Paket-Metadaten zur Vorbereitung der öffentlichen Veröffentlichung ab.',
    pl_PL:
      'Finalizuje dokumentację i metadane pakietu w ramach przygotowania do publicznego wydania.',
    fr_FR:
      'Finalise la documentation et les métadonnées du paquet en vue de la publication publique.',
  },
  migrations: {
    up: async ({ effects }) => {},
    down: IMPOSSIBLE,
  },
})
