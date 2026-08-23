import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '0.5.0:7',
  releaseNotes: {
    en_US:
      'Hardens the StartOS package for release with updated documentation, package metadata, licensing information, repository integration, and multi-architecture build support.',
    es_ES:
      'Refuerza el paquete de StartOS para su publicación con documentación, metadatos del paquete, información de licencias, integración del repositorio y compatibilidad de compilación para múltiples arquitecturas actualizadas.',
    de_DE:
      'Härtet das StartOS-Paket für die Veröffentlichung mit aktualisierter Dokumentation, Paket-Metadaten, Lizenzinformationen, Repository-Integration und Unterstützung für Builds auf mehreren Architekturen.',
    pl_PL:
      'Przygotowuje pakiet StartOS do wydania poprzez aktualizację dokumentacji, metadanych pakietu, informacji licencyjnych, integracji repozytorium i obsługi kompilacji dla wielu architektur.',
    fr_FR:
      'Renforce le paquet StartOS en vue de sa publication avec une documentation, des métadonnées, des informations de licence, une intégration du dépôt et une prise en charge multi-architecture mises à jour.',
  },
  migrations: {
    up: async ({ effects }) => {},
    down: IMPOSSIBLE,
  },
})
