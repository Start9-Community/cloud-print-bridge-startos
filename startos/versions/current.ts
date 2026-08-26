import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '0.6.0:1',
  releaseNotes: {
    en_US:
      'Refines third-party license and copyright notices based on an audit of the final runtime image.',
    es_ES:
      'Mejora los avisos de licencias y derechos de autor de terceros basándose en una auditoría de la imagen de ejecución final.',
    de_DE:
      'Präzisiert die Lizenz- und Urheberrechtshinweise für Drittanbieter auf Grundlage einer Prüfung des finalen Laufzeit-Images.',
    pl_PL:
      'Doprecyzowuje informacje o licencjach i prawach autorskich stron trzecich na podstawie audytu końcowego obrazu środowiska uruchomieniowego.',
    fr_FR:
      'Précise les mentions de licences et de droits d’auteur des composants tiers à partir d’un audit de l’image d’exécution finale.',
  },
  migrations: {
    up: async ({ effects }) => {},
    down: IMPOSSIBLE,
  },
})
