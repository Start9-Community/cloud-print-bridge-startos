import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '0.5.0:6',
  releaseNotes: {
    en_US:
      'Fixes duplex orientation for PDF page-selection jobs by first creating a normalized selected-page PDF and then using the proven full-document PWG Raster printing path.',
    es_ES:
      'Corrige la orientación dúplex de los trabajos PDF con selección de páginas creando primero un PDF normalizado con las páginas seleccionadas y utilizando después la ruta de impresión PWG Raster de documento completo ya validada.',
    de_DE:
      'Behebt die Duplex-Ausrichtung bei PDF-Druckaufträgen mit Seitenauswahl, indem zuerst eine normalisierte PDF-Datei mit den ausgewählten Seiten erstellt und anschließend der bewährte PWG-Raster-Druckpfad für vollständige Dokumente verwendet wird.',
    pl_PL:
      'Naprawia orientację druku dwustronnego dla zadań PDF z wyborem stron, najpierw tworząc znormalizowany plik PDF zawierający wybrane strony, a następnie korzystając ze sprawdzonej ścieżki drukowania całego dokumentu w formacie PWG Raster.',
    fr_FR:
      'Corrige l’orientation recto verso des tâches PDF avec sélection de pages en créant d’abord un PDF normalisé contenant les pages sélectionnées, puis en utilisant le chemin d’impression PWG Raster déjà validé pour les documents complets.',
  },
  migrations: {
    up: async ({ effects }) => {},
    down: IMPOSSIBLE,
  },
})
