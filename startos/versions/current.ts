import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '0.6.0:2',
  releaseNotes: {
    en_US:
      'Updates the Cloud Print Bridge service icon and user-facing package presentation.',
    es_ES:
      'Actualiza el icono del servicio Cloud Print Bridge y la presentación del paquete para el usuario.',
    de_DE:
      'Aktualisiert das Cloud-Print-Bridge-Dienstsymbol und die benutzerseitige Paketdarstellung.',
    pl_PL:
      'Aktualizuje ikonę usługi Cloud Print Bridge oraz prezentację pakietu widoczną dla użytkownika.',
    fr_FR:
      'Met à jour l’icône du service Cloud Print Bridge et la présentation du paquet destinée à l’utilisateur.',
  },
  migrations: {
    up: async ({ effects }) => {},
    down: IMPOSSIBLE,
  },
})
