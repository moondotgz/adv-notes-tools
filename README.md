# Adv Notes tools

The tool marketplace for [Adv Notes](https://github.com/moondotgz/adv-notes). Everything here shows up in the app under **Tools → Get more tools** (or **Settings → Tools → Browse marketplace**), where people can install, update and remove tools with one tap.

## How it works

- Each tool is a folder in `tools/<id>/` with a `manifest.json` and an HTML entry page.
- `index.json` lists every tool and every file in it, with its size and SHA-256 hash.
- The app reads `index.json` from this repository's `main` branch, downloads the files of a tool and checks each hash before installing. A tool shows an **Update** button when its `version` here is higher than the installed one.

## Publishing or updating a tool

1. Add or change a folder under `tools/`. The folder name must equal the manifest `id`.
2. Bump `version` in its `manifest.json` (dotted numbers, e.g. `1.0.0` → `1.1.0`) so installed copies get the update.
3. Regenerate the index and commit it with the change:

   ```bash
   python3 scripts/build_index.py
   ```

CI fails if `index.json` doesn't match the tool folders.

`manifest.json`:

```json
{
  "id": "unit-converter",
  "name": "Unit converter",
  "description": "Shown in the marketplace and the tool picker",
  "entry": "index.html",
  "icon": "functions",
  "version": "1.0.0",
  "author": "you",
  "category": "Study"
}
```

`icon` is one of: calculate, book, chat, science, functions, translate, timer, map, extension. `category` groups tools into filter chips.

[`template/`](template) is a complete example tool to copy. The JavaScript API tools get (`AdvNotes.insertText`, `AdvNotes.ask`, storage, file picker…) is documented in [docs/TOOLS.md](https://github.com/moondotgz/adv-notes/blob/main/docs/TOOLS.md) in the app repository. Load it with `<script src="../lib/advnotes.js"></script>`; the app serves that path.

## Licences

Each tool keeps its own licence. The PDF reader bundles [pdf.js](https://github.com/mozilla/pdf.js) (Apache-2.0; see `tools/pdfreader/pdfjs/LICENSE`).

## Translating tools

Each tool can ship `i18n/<language>.json` next to its `index.html` (e.g. `tools/quiz/i18n/pt-BR.json`). Keys are the
English text; values are the translation. `_meta` holds the translated `name`/`description` (shown in the app's tool
list and store) and `"machineTranslated": true` for unreviewed machine translations. Missing strings stay English.

- Static text in the HTML (text, `placeholder`, `title`, `aria-label`) is translated automatically by the app.
- Text built in JavaScript goes through `tr("Delete {0}?", name)` (a wrapper around `AdvNotes.t`), and
  data tables can be marked for the extractor with `/* i18n: cols 0,1 */`, `/* i18n: keys */` or `/* i18n: 'A', 'B' */`.
- `python3 scripts/i18n.py` writes `i18n/en.json` (the template) for every tool; `--check` lists missing strings.
  To start a language, copy a tool's `en.json` to `<tag>.json` and fill it in.
