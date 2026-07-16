# Seguiment d’ofertes docents

El projecte manté dos canals independents que comparteixen el mateix motor
d’anàlisi:

1. un informe diari en català enviat per correu des d’un Mac;
2. un dashboard públic en català publicat amb GitHub Pages.

Es vigilen les ofertes de difícil cobertura de Tarragona, Penedès, Baix
Llobregat, Barcelonès i Terres de l’Ebre. Les coincidències prioritàries són
únicament els codis exactes `GE` i `CLA`.

## Estructura

- `escola_karen/core.py`: consulta de fonts, extracció PDF i parseig compartit;
- `job_watch.py`: informe local per correu;
- `build_dashboard.py`: dades públiques, historial i construcció del web;
- `dashboard/`: HTML, CSS, JavaScript, estat i historial públics;
- `.github/workflows/dashboard-pages.yml`: actualització i publicació diàries.

## Proves

Cal tenir Python 3.10 o posterior:

```sh
python3 -m unittest discover -s tests -v
```

Per analitzar un informe existent i generar el dashboard sense accedir a la
xarxa:

```sh
python3 build_dashboard.py \
  --from-report reports/informe-2026-07-16.json \
  --output _site
python3 -m http.server 8000 --directory _site
```

El web estarà disponible a `http://localhost:8000`.

## Informe per correu

Les adreces no formen part de la configuració pública.

1. Copieu l’exemple:

   ```sh
   cp email_config.example.json email_config.local.json
   ```

2. Completeu `sender` i `recipient`.
3. Creeu una contrasenya d’aplicació de Gmail.
4. Instal·leu Poppler: `brew install poppler`.
5. Executeu `./setup_macos.sh`.

Prova manual sense enviar cap missatge:

```sh
/usr/bin/python3 job_watch.py --dry-run
```

L’estat local, els informes, els registres i `email_config.local.json` estan
ignorats per Git.

## Dashboard GitHub Pages

El workflow:

- s’executa cada dia a les 15.05 h amb el fus `Europe/Paris`;
- també es pot iniciar manualment;
- executa les proves i instal·la Poppler;
- conserva l’historial públic dels últims 90 dies;
- manté el darrer informe vàlid si totes les fonts fallen;
- publica `_site` amb les accions oficials de GitHub Pages.

Per publicar-lo:

1. Creeu un repositori GitHub públic i pugeu el projecte a la branca `main`.
2. Aneu a **Settings → Pages**.
3. A **Build and deployment**, trieu **GitHub Actions**.
4. Executeu manualment el workflow **Actualitza i publica el dashboard**.

El workflow només utilitza el `GITHUB_TOKEN` automàtic. No necessita cap
contrasenya ni adreça de correu.

## Dades públiques

`dashboard/public/data/latest.json` conté el darrer informe explotable.
`status.json` descriu la darrera temptativa i `history/index.json` exposa un
resum dels últims 90 dies. Els informes diaris complets romanen a
`history/AAAA-MM-DD.json`.

Les dates visibles segueixen el format català `DD/MM/AAAA`. Els camps que no es
poden extreure de manera fiable es publiquen com a valor absent, sense
inventar-ne el contingut.
