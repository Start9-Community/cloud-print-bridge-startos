import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '0.6.0:3',
  releaseNotes: {
    en_US: '- Updates Pillow to 13.0.0 with security fixes.',
    es_ES: '- Actualiza Pillow a 13.0.0 con correcciones de seguridad.',
    de_DE: '- Aktualisiert Pillow auf 13.0.0 mit Sicherheitskorrekturen.',
    pl_PL: '- Aktualizuje Pillow do wersji 13.0.0 z poprawkami bezpieczeństwa.',
    fr_FR: '- Met à jour Pillow vers 13.0.0 avec des correctifs de sécurité.',
  },
  migrations: {
    up: async ({ effects }) => {},
    down: IMPOSSIBLE,
  },
})
