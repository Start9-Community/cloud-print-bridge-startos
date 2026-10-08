import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '0.6.0:2',
  releaseNotes: {
    en_US:
      "- Configure Cloud Print Bridge's Printer Mode, Paper Size, Color Mode and Sides settings explain what each choice does.",
    es_ES:
      '- Los ajustes Modo de impresora, Tamaño de papel, Modo de color y Caras de «Configurar Cloud Print Bridge» explican qué hace cada opción.',
    de_DE:
      '- Die Einstellungen Druckermodus, Papierformat, Farbmodus und Seiten in „Cloud Print Bridge konfigurieren“ erklären, was jede Auswahl bewirkt.',
    pl_PL:
      '- Ustawienia Tryb drukarki, Rozmiar papieru, Tryb koloru i Strony w akcji „Skonfiguruj Cloud Print Bridge” wyjaśniają, co oznacza każdy wybór.',
    fr_FR:
      '- Les réglages Mode d’imprimante, Format de papier, Mode couleur et Faces de « Configurer Cloud Print Bridge » expliquent l’effet de chaque choix.',
  },
  migrations: {
    up: async ({ effects }) => {},
    down: IMPOSSIBLE,
  },
})
