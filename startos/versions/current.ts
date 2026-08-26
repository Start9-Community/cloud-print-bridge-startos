import { IMPOSSIBLE, VersionInfo } from '@start9labs/start-sdk'

export const current = VersionInfo.of({
  version: '0.6.0:0',
  releaseNotes: {
    en_US:
      'Adds a Discover Printers action that scans configured IPv4 networks for IPP printers and displays their printer name, persistent UUID, and IPP URI for easier first-time setup.',
    es_ES:
      'Añade una acción Descubrir impresoras que analiza las redes IPv4 configuradas en busca de impresoras IPP y muestra el nombre de la impresora, su UUID persistente y la URI IPP para facilitar la configuración inicial.',
    de_DE:
      'Fügt eine Aktion zur Druckersuche hinzu, die konfigurierte IPv4-Netzwerke nach IPP-Druckern durchsucht und Druckername, persistente UUID und IPP-URI für eine einfachere Ersteinrichtung anzeigt.',
    pl_PL:
      'Dodaje akcję wykrywania drukarek, która skanuje skonfigurowane sieci IPv4 w poszukiwaniu drukarek IPP i wyświetla nazwę drukarki, trwały identyfikator UUID oraz URI IPP, ułatwiając pierwszą konfigurację.',
    fr_FR:
      'Ajoute une action de découverte des imprimantes qui analyse les réseaux IPv4 configurés à la recherche d’imprimantes IPP et affiche leur nom, leur UUID persistant et leur URI IPP afin de faciliter la configuration initiale.',
  },
  migrations: {
    up: async ({ effects }) => {},
    down: IMPOSSIBLE,
  },
})
