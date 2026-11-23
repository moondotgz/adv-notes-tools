#!/usr/bin/env python3
"""Translation helper for the tools in this repository.

Every tool can have i18n/<tag>.json next to its index.html (e.g. tools/quiz/i18n/pt-BR.json), keyed by the
English text, with a "_meta" block: {"name": "...", "description": "...", "machineTranslated": true}.
The app passes it to the tool; advnotes.js translates static HTML text automatically and offers
AdvNotes.t("text {0}", value) for text built in JavaScript. Missing strings stay English.

  scripts/i18n.py           write tools/<id>/i18n/en.json (the template: every key found) for every tool
  scripts/i18n.py --check   report missing keys / placeholder mistakes per translation; fail if a template is stale
"""
import html.parser, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')
LETTERS = re.compile(r'[A-Za-z]{2}')
ATTRS = ('placeholder', 'title', 'aria-label')

class Parser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.keys = []; self.skip = 0; self.scripts = []; self.in_script = False
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.skip += 1; self.in_script = tag == 'script'
        if tag == 'textarea': self.skip += 1
        a = dict(attrs)
        if a.get('translate') == 'no': return
        for k in ATTRS:
            v = (a.get(k) or '').strip()
            if v and LETTERS.search(v): self.keys.append(v)
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'textarea'): self.skip = max(0, self.skip - 1); self.in_script = False
    def handle_data(self, data):
        if self.in_script: self.scripts.append(data); return
        if self.skip: return
        d = data.strip()
        if d and LETTERS.search(d): self.keys.append(d)

def js_keys(code):
    keys = []
    # t('...'), t("..."), t(`...`) — the first argument, when it is a plain literal
    for m in re.finditer(r'(?<![\w$.])tr\(\s*(\'(?:[^\'\\]|\\.)*\'|"(?:[^"\\]|\\.)*"|`[^`$]*`)', code):
        keys.append(json.loads('"' + m.group(1)[1:-1].replace('"', '\\"').replace("\\'", "'") + '"') if m.group(1)[0] != '`' else m.group(1)[1:-1])
    # Data marked for translation:
    #   /* i18n: cols 0,1 */ [[...], ...]   the given columns of each row
    #   /* i18n: keys */ { Key: ..., }       the top-level keys of an object
    #   /* i18n: names */ `Sym Name ...|...` the second word of each |-separated record
    #   /* i18n: 'A', "B" */                 the listed strings
    lit = r"'((?:[^'\\\n]|\\.)*)'|\"((?:[^\"\\\n]|\\.)*)\""
    for m in re.finditer(r'/\*\s*i18n:\s*([^*]*)\*/', code):
        spec, rest = m.group(1).strip(), code[m.end():]
        if spec.startswith('cols'):
            cols = [int(x) for x in re.findall(r'\d+', spec)]
            depth, i = 0, rest.index('[')
            for j in range(i, len(rest)):
                if rest[j] == '[': depth += 1
                elif rest[j] == ']':
                    depth -= 1
                    if depth == 0: break
            for row in re.finditer(r'\[([^\[\]]*)\]', rest[i + 1:j]):
                vals = [a if a is not None and a != '' or b is None else b for a, b in re.findall(lit, row.group(1))]
                vals = [x.replace("\\'", "'") for x in vals]
                for c in cols:
                    if c < len(vals) and LETTERS.search(vals[c]): keys.append(vals[c])
        elif spec.startswith('keys'):
            body = rest[rest.index('{') + 1:]
            depth = 0
            for line in body.split('\n'):
                km = re.match(r'\s*([A-Za-z][\w ]*?)\s*:', line) if depth == 0 else None
                if km: keys.append(km.group(1))
                depth += line.count('[') + line.count('{') - line.count(']') - line.count('}')
                if depth < 0: break
        elif spec.startswith('names'):
            body = rest[rest.index('`') + 1:]; body = body[:body.index('`')]
            keys += [r.split(' ')[1] for r in body.split('|') if len(r.split(' ')) > 1]
        else:
            keys += [a or b for a, b in re.findall(lit, spec)]
    # HTML written from JavaScript: >Text< and placeholder="..." inside string/template literals
    for m in re.finditer(r'>([^<>`${}\n]*?[A-Za-z]{2}[^<>`${}\n]*?)<', code):
        k = m.group(1).strip()
        if k and not re.search(r'[=;{}]|\w\(|\b(const|let|return|function)\b', k): keys.append(k)
    for m in re.finditer(r'\b(?:placeholder|title|aria-label)="([^"$`]*[A-Za-z]{2}[^"$`]*)"', code):
        keys.append(m.group(1).strip())
    return keys

def collect(tool_dir):
    p = Parser(); p.feed(open(os.path.join(tool_dir, 'index.html'), encoding='utf-8').read())
    keys = list(p.keys)
    for s in p.scripts: keys += js_keys(s)
    seen, out = set(), []
    for k in keys:
        k = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), k)   # JS \u2019 escapes
        k = re.sub(r'\s+', ' ', k).strip()
        if re.fullmatch(r'[a-z_$][\w$]*(\.[\w$]+)+', k): continue        # code like c.due, not text
        if k and k not in seen: seen.add(k); out.append(k)
    return out

def tool_dirs():
    for d in sorted(os.listdir(TOOLS)):
        full = os.path.join(TOOLS, d)
        if os.path.isfile(os.path.join(full, 'index.html')) and os.path.isfile(os.path.join(full, 'manifest.json')): yield d, full

def dump(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2); f.write('\n')

def main():
    check = '--check' in sys.argv; ok = True
    for tid, d in tool_dirs():
        m = json.load(open(os.path.join(d, 'manifest.json'), encoding='utf-8'))
        keys = collect(d)
        template = {'_meta': {'name': m.get('name', ''), 'description': m.get('description', '')}}
        template.update({k: '' for k in keys})
        en = os.path.join(d, 'i18n', 'en.json')
        if check:
            if not os.path.exists(en) or json.load(open(en, encoding='utf-8')) != template: print(f'{tid}: i18n/en.json is out of date'); ok = False
        else:
            dump(en, template)
        idir = os.path.join(d, 'i18n')
        for f in sorted(os.listdir(idir)) if os.path.isdir(idir) else []:
            if not f.endswith('.json') or f == 'en.json': continue
            t = json.load(open(os.path.join(idir, f), encoding='utf-8'))
            missing = [k for k in keys if not t.get(k)]
            bad = [k for k in keys if t.get(k) and sorted(re.findall(r'\{\d+\}', k)) != sorted(re.findall(r'\{\d+\}', t[k]))]
            print(f'{tid}/{f}: {len(keys) - len(missing)}/{len(keys)} translated')
            for k in missing[:10]: print('   missing:', json.dumps(k, ensure_ascii=False))
            for k in bad: print('   placeholders differ:', json.dumps(k, ensure_ascii=False)); ok = False
    sys.exit(0 if ok else 1)

main()
