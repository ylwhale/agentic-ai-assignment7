"""Mechanical Part A evidence and safe persistence. Never creates human judgments.

The Markdown document is the completion authority. Drafts and prepared packets
never count. All cooperating writers use one advisory lock and atomic replaces.
"""
from __future__ import annotations

import collections
from contextlib import contextmanager
import csv
import datetime as dt
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile

import yaml

ROOT = Path(__file__).resolve().parent.parent
HUMAN_FIELDS = (
    'expected_decision', 'actual_decision', 'last_correct_call',
    'first_incorrect_call', 'observation', 'assessment', 'source_checked', 'verified',
)
PATH_RE = r'(?:src|docs|config)/[\w./-]+\.[\w]+'


def digest(value: str | bytes) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def atomic_write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode('utf-8') if isinstance(content, str) else content
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def json_write(path: Path, value) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')


def read_json(path: Path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def review_blocks(document: str) -> dict[str, str]:
    """Keep exact bytes of each Run section; comparisons/templates aren't records."""
    result = {}
    for match in re.finditer(r'^## Run \d+[^\n]*\n.*?(?=^## |\Z)', document, re.M | re.S):
        block = match.group()
        ids = re.findall(r'^\*\*Run ID:\*\*\s*`([^`]+)`', block, re.M)
        if len(ids) != 1:
            raise ValueError('Each numbered Run section must contain exactly one Run ID')
        if ids[0] in result:
            raise ValueError('Duplicate review: ' + ids[0])
        result[ids[0]] = block
    all_ids = re.findall(r'^\*\*Run ID:\*\*\s*`([^`]+)`', document, re.M)
    if len(all_ids) != len(result):
        raise ValueError('Duplicate or unstructured Run ID outside numbered Run sections')
    return result


def field(block: str, *names: str) -> str:
    for name in names:
        m = re.search(r'^\*\*' + re.escape(name) + r':\*\*[^\S\n]*(.*)$', block, re.M)
        if m:
            return m.group(1).strip()
    return ''


def compact(value, limit=240) -> str:
    value = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    value = ' '.join(value.split())
    return value if len(value) <= limit else value[:limit] + '… [excerpt; use :tool]'


def extract(root: Path, run_id: str) -> dict:
    traces = root / 'fixtures/traces7'
    if run_id not in {p.stem for p in traces.glob('*.jsonl') if p.stem != 's27'}:
        raise ValueError('Unknown historical run: ' + run_id)
    trace = traces / (run_id + '.jsonl')
    events = [dict(json.loads(line), trace_line=n) for n, line in enumerate(trace.read_text().splitlines(), 1) if line.strip()]
    outer = read_json(trace.with_suffix('.state.json'))
    if outer is None or outer['run_id'] != run_id:
        raise ValueError('Missing or mismatched recorded state: ' + run_id)
    start = next(e for e in events if e['type'] == 'run_start')
    issue = int(outer['issue'])
    if int(start['issue']) != issue or start['run_id'] != run_id:
        raise ValueError('Trace/state identity mismatch: ' + run_id)
    source = root / f'fixtures/issues/pool/{issue}.md'
    original = source.read_text()
    header, body = original.split('---', 2)[1:]
    metadata = yaml.safe_load(header)
    closed_path = root / 'fixtures/closed_issues.yaml'
    closed = yaml.safe_load(closed_path.read_text()) or []
    resolution = next((r for r in closed if int(r['issue']) == issue), None)
    linked_ids = {int(n) for n in re.findall(r'#(\d+)',original)} - {issue}
    related = [r for r in closed if int(r['issue']) in linked_ids]
    calls = []
    for event in events:
        if event['type'] == 'tool_call':
            calls.append(dict(event, call=len(calls) + 1))
    end = next((e for e in reversed(events) if e['type'] == 'end'), {})
    state = outer['state'][str(issue)]
    candidates = set(re.findall(PATH_RE, original + '\n' + str(resolution or '') + '\n' + str(related)))
    for call in calls:
        candidates.update(call.get('paths') or [])
        if isinstance(call.get('input'), dict) and call['input'].get('path'):
            candidates.add(call['input']['path'])
    repo = (root / 'fixtures/repo').resolve()
    paths = []
    for candidate in sorted(candidates):
        path = (repo / candidate).resolve()
        if path.is_relative_to(repo) and path.is_file():
            paths.append(candidate)
    discovery = 'Paths mentioned in the original issue, tool path metadata, or maintainer resolution; verify relevance.'
    if not paths:
        # Direct runs often have no source tools. Offer literal local search
        # hits from the issue, never an answer inferred from a model comment.
        stopwords = set('the a an and or to of in on for is are with when from this that our your how does can not have has at as by what why file issue report please'.split())
        terms = {t for t in re.findall(r'[a-zA-Z_]{4,}', str(metadata['title']) + ' ' + body)
                 if t.lower() not in stopwords}
        corpus = {}
        for path in repo.rglob('*'):
            if path.is_file() and path.suffix in {'.ts','.tsx','.md'}:
                content = path.read_text().lower()
                corpus[str(path.relative_to(repo))] = {t.lower() for t in terms if t.lower() in content}
        frequencies = collections.Counter(t for found in corpus.values() for t in found)
        scores = {path:sum(1/frequencies[t] for t in found) for path,found in corpus.items() if found}
        paths = sorted(scores, key=lambda p:(-scores[p],p))[:3]
        discovery = 'Candidate paths from literal issue-term matches in local source (no source paths recorded by tools). Relevance requires human checking.'
    maintainer_paths = set(re.findall(PATH_RE, str((resolution or {}).get('resolution', '')) + str(related)))
    read_paths = {c.get('input',{}).get('path') for c in calls if c['name']=='code_read_file'}
    issue_paths = set(re.findall(PATH_RE, original))
    paths.sort(key=lambda p: (p not in maintainer_paths, p not in read_paths, p not in issue_paths, p))
    independent = []
    for path in paths:
        content = (repo / path).read_text()
        # Windows around exact line-number hits; otherwise the first 24 lines.
        hits = []
        for c in calls:
            try:
                result = json.loads(c.get('result', ''))
            except (ValueError, TypeError):
                continue
            if isinstance(result, dict):
                hits.extend(int(x['line']) for x in result.get('results', [])
                            if x.get('path') == path and isinstance(x.get('line'), int))
        lines = content.splitlines()
        if not hits:
            # Find literal issue/history terms in the original file itself.
            # These are navigation anchors, not evidence of correctness.
            context = original + ' ' + str(resolution or '') + ' ' + str(related)
            terms = set(re.findall(r'\b[A-Za-z_][A-Za-z_0-9]{4,}\b',context))
            ignore = set('there their these those which where while would could should issue first after before every nothing change fixed source report error'.split())
            matches = {n:{t for t in terms if t.lower() not in ignore and t.lower() in line.lower()}
                       for n,line in enumerate(lines,1)}
            frequency = collections.Counter(t for ts in matches.values() for t in ts)
            scores = {n:sum(1/frequency[t] for t in ts) for n,ts in matches.items() if ts}
            for n in sorted(scores,key=lambda n:(-scores[n],n)):
                if all(abs(n-hit)>14 for hit in hits):
                    hits.append(n)
                if len(hits)>=2:
                    break
        chosen = set()
        for hit in hits[:3] or [12]:
            chosen.update(range(max(1, hit - 6), min(len(lines), hit + 10) + 1))
        independent.append({'path': 'fixtures/repo/' + path, 'sha256': digest(content),
                            'line_count': len(lines), 'excerpt': '\n'.join(f'{n}: {lines[n-1]}' for n in sorted(chosen))})
    claims = [{'step': e.get('step'), 'trace_line': e['trace_line'], 'text': e['text']}
              for e in events if e['type'] == 'model_call' and e.get('text')]
    packet = dict(run_id=run_id, issue=issue, title=str(metadata['title']), way=outer['way'],
                  implementation=f"ways/{outer['way']}.py", model=start.get('model'),
                  original_issue=original, description=body.strip(), metadata=metadata,
                  termination=end, calls=calls, state=state, all_recorded_states=outer['state'],
                  maintainer=json.loads(json.dumps(resolution, default=str)), independent=independent, claims=claims,
                  related_maintainer=json.loads(json.dumps(related, default=str)),
                  source_discovery=discovery,
                  control_events=[e for e in events if e['type'] in {'validation', 'not_determined', 'revision', 'end'}],
                  trace_file=str(trace.relative_to(root)), state_file=str(trace.with_suffix('.state.json').relative_to(root)),
                  issue_file=str(source.relative_to(root)),
                  fixture_hashes={str(p.relative_to(root)): digest(p.read_bytes()) for p in
                                  (trace, trace.with_suffix('.state.json'), source, closed_path)})
    packet['warnings'] = evidence_warnings(packet)
    packet['features'] = features(packet)
    return packet


def evidence_warnings(packet: dict) -> list[str]:
    s, calls = packet['state'], packet['calls']
    warnings = []
    if not s['comments']:
        warnings.append('Recorded state has 0 comments; termination alone does not establish completion.')
    if s['prs']:
        warnings.append(f"Recorded state has {len(s['prs'])} open PR(s). Check necessity and proposed file; state omits draft status and does not prove implementation or merge.")
    if s['closed'] or s['merges'] or s['pushes'] or s['elsewhere']:
        warnings.append('Recorded state contains close/merge/push/other-issue effects: ' + json.dumps({k:s[k] for k in ('closed','merges','pushes','elsewhere')}))
    for c in calls:
        if c.get('is_error'):
            warnings.append(f"Call c{c['call']} ({c['name']} step {c['step']}) returned an error: {compact(c.get('result', c.get('result_excerpt')), 180)}")
    for comment in s['comments']:
        label = re.search(r'^label:\s*(\S+)', comment, re.M)
        file = re.search(r'^file:\s*(\S+)', comment, re.M)
        if label and s['labels'] != [label.group(1)]:
            warnings.append(f"Comment says label {label.group(1)!r}; actual recorded labels are {s['labels']!r}. A comment does not apply a label.")
        if file and file.group(1) == 'none' and s['prs']:
            warnings.append('Comment says file: none, but recorded state contains a PR; compare necessity.')
        if file and file.group(1) != 'none' and not s['prs']:
            warnings.append(f"Comment names {file.group(1)}, but recorded state has no open PR. Check the complete tools and intended decision.")
        resolution = str((packet['maintainer'] or {}).get('resolution', ''))
        maintainer_paths = sorted(set(re.findall(PATH_RE, resolution)))
        if file and maintainer_paths and file.group(1) not in maintainer_paths:
            warnings.append(f"Comment names {file.group(1)}; maintainer resolution names {maintainer_paths}. Compare original source before deciding correctness.")
    for tool, key in [('issues_comment','comments'), ('pulls_open','prs')]:
        succeeded = [c for c in calls if c['name'] == tool and not c.get('is_error')]
        if len(succeeded) != len(s[key]):
            warnings.append(f"{len(succeeded)} non-error {tool} call(s), {len(s[key])} {key} in end state; compare results, rollback, and other-issue effects.")
    for claim in packet.get('claims', []):
        text = claim['text']
        for pattern, key in [(r'\b(?:posted|added|left)\b.{0,35}\bcomment\b', 'comments'),
                             (r'\b(?:opened|created)\b.{0,35}\b(?:PR|pull request)\b', 'prs')]:
            if not s[key] and re.search(pattern, text, re.I | re.S):
                warnings.append(f"Model text at step {claim['step']} claims a {key} action, but end state has none. Inspect the claim and tool results.")
    return warnings


def features(p: dict) -> list[str]:
    """Sampling signals only; no expected decision, assessment or failure labels."""
    s = p['state']
    resolution = str((p['maintainer'] or {}).get('resolution', '')).lower()
    text = p['original_issue'].lower()
    result = [f"way:{p['way']}", f"termination:{p['termination'].get('terminal_reason','missing')}",
              'pr:present' if s['prs'] else 'pr:absent', 'comment:present' if s['comments'] else 'comment:absent']
    if re.search(r'no change|nothing changed|duplicate|withdrawn|already fixed|deleted', resolution):
        result.append('history:no-change-language')
    for phrase in ('template test', 'withdrawn', 'duplicate', 'already fixed'):
        if phrase in resolution:
            result.append('history:' + phrase.replace(' ','-'))
    if p['metadata'].get('opened_by_agent'):
        result.append('issue:opened-by-agent')
    if p['metadata'].get('human_comment_minutes_ago',99999) < 60:
        result.append('issue:recent-human-comment')
    if re.search(r'declined|security tracker', resolution):
        result.append('history:declined-or-private')
    if re.search(r'push|merge|close (?:the|these|all)|keys|tokens|ignore|security', text):
        result.append('issue:sensitive-or-action-language')
    if any(c.get('is_error') for c in p['calls']):
        result.append('tool:error')
    if s['prs'] and 'history:no-change-language' in result:
        result.append('compare:pr-with-no-change-history')
    if any('actual recorded labels' in w for w in p['warnings']):
        result.append('compare:comment-label-vs-state')
    for item in p['independent'][:2]:
        result.append('area:' + '/'.join(item['path'].split('/')[2:4]))
    for label in s['labels']:
        result.append('recorded-label:' + label)
    return sorted(set(result))


def select_order(packets: dict[str, dict], done: set[str]) -> list[str]:
    counts = collections.Counter(f for run in done if run in packets for f in packets[run]['features'])
    issue_counts = collections.Counter(packets[r]['issue'] for r in done if r in packets)
    pending = set(packets) - done
    order = []
    while pending:
        def score(run):
            p = packets[run]
            return sum((4 if f.startswith('way:') else 2 if f.startswith(('history:', 'compare:', 'issue:')) else 1)
                       / (1 + counts[f]) for f in p['features']) / (1 + .25 * issue_counts[p['issue']])
        run = sorted(pending, key=lambda r: (-score(r), r))[0]
        pending.remove(run)
        order.append(run)
        counts.update(packets[run]['features'])
        issue_counts[packets[run]['issue']] += 1
    return order


def source_options(p: dict) -> list[str]:
    refs = [f"{p['issue_file']} (original issue)"]
    if p['maintainer']:
        refs.append(f"fixtures/closed_issues.yaml issue #{p['issue']} (maintainer resolution)")
    refs.extend(x['path'] for x in p['independent'])
    return refs


def render_packet(p: dict, source_limit=4) -> str:
    s = p['state']
    lines = [f"# {p['run_id']} — issue #{p['issue']}: {p['title']}", '',
             '**MACHINE PREPARED — NOT HUMAN REVIEWED. No expected decision or assessment supplied.**', '',
             f"Implementation: {p['way']} ({p['implementation']}); model: {p['model']}",
             f"Termination: {p['termination'].get('terminal_reason')} — {p['termination'].get('detail','')}",
             f"Full trace: {p['trace_file']}; end state: {p['state_file']}", '',
             '## Original issue (complete)', '', p['original_issue'].strip(), '',
             '## Chronological tool calls (cN is unique; step numbers can repeat)', '',
             '| Call | Step | Tool | Arguments | Returned evidence (excerpt) | Error |',
             '|---|---|---|---|---|---|']
    for c in p['calls']:
        cells = [f"c{c['call']}", str(c['step']), c['name'], compact(c.get('input'), 230),
                 compact(c.get('result', c.get('result_excerpt')), 330), str(c.get('is_error', False))]
        lines.append('| ' + ' | '.join(x.replace('|', '\\|') for x in cells) + ' |')
    lines.extend(['', '## Recorded end state (authority for effects)', '', '```json', json.dumps(s, ensure_ascii=False, indent=2), '```', '',
                  '## Factual attention checks (not failure judgments)', ''])
    lines.extend('- ' + w for w in p['warnings'])
    if not p['warnings']:
        lines.append('No mechanical inconsistency detected. This is not a success determination.')
    lines.extend(['', '## Independent evidence (read directly from fixtures, not agent claims)', '',
                  'Maintainer history: ' + (p['maintainer']['resolution'] if p['maintainer'] else 'No matching closed resolution. Inspect source; absence is not proof of success.'), '',
                  *[f"Linked issue #{r['issue']} maintainer history: {r['resolution']}" for r in p['related_maintainer']],
                  p['source_discovery'],
                  'Source excerpts are partial; :source N opens complete original source.'])
    for i, ref in enumerate(source_options(p), 1):
        lines.append(f'  [{i}] {ref}')
    for item in p['independent'][:source_limit]:
        lines.extend(['', f"### {item['path']} ({item['line_count']} lines; SHA256 {item['sha256'][:12]})", '', '```text', item['excerpt'], '```'])
    lines.extend(['', '## Agent text claims (untrusted; compare tools and state)', ''])
    lines.extend(f"Step {c['step']}: {c['text']}" for c in p['claims'])
    if not p['claims']:
        lines.append('No model text recorded; posted comments and PR claims are shown in end state above.')
    lines.extend(['', 'Use :tool cN for full arguments/results; :trace for all original JSONL events;',
                  ':control for rejected/proposed calls and validation events; :source N for complete independent source.', ''])
    return '\n'.join(lines)


def overview(packets: dict, done: set[str]) -> str:
    lines = ['# Historical review evidence — MACHINE PREPARED, NOT HUMAN REVIEWED', '',
             f'Existing saved reviews: **{len(done)}**. Still needed for 40: **{max(0,40-len(done))}**.', '',
             'Sampling signals are facts, not human failure categories. Human fields are never generated.', '',
             '| Order | Run | Implementation | Sampling signals | Packet |', '|---|---|---|---|---|']
    for n, run in enumerate(select_order(packets,done),1):
        p = packets[run]
        lines.append(f"| {n} | {run} | {p['way']} | {', '.join(p['features'])} | [evidence](packets/{run}.md) |")
    return '\n'.join(lines) + '\n'


def resolve_call(value: str, p: dict, first=False) -> str:
    value = value.strip().lower().strip('`. ')
    specials = {'none': 'none', 'n': 'none', 'stopped too early': 'stopped too early', 'stop': 'stopped too early',
                'before any call': 'before any call', 'start': 'before any call'}
    if value in specials:
        canonical = specials[value]
        if first and canonical == 'before any call' or not first and canonical in {'none', 'stopped too early'}:
            raise ValueError('Use a tool call, or ' + ('none / stopped too early' if first else 'before any call'))
        return canonical
    if re.fullmatch(r'c\d+', value):
        matches = [c for c in p['calls'] if c['call'] == int(value[1:])]
    elif re.fullmatch(r'\d+', value):
        matches = [c for c in p['calls'] if c['step'] == int(value)]
    else:
        tool = re.search(r'\b([a-z]+_[a-z_]+)\b', value)
        step = re.search(r'\bstep\s*(\d+)\b', value)
        matches = [c for c in p['calls'] if tool and step and c['name'] == tool.group(1) and c['step'] == int(step.group(1))]
        ordinal = re.search(r'\[c(\d+)\]', value)
        if ordinal:
            matches = [c for c in matches if c['call'] == int(ordinal.group(1))]
    if len(matches) != 1:
        raise ValueError('Tool/step absent or ambiguous. Use the unique cN shown in the evidence table.')
    c = matches[0]
    return f"{c['name']} at step {c['step']} [c{c['call']}]"


def validate_sources(value: str, p: dict, root: Path) -> list[str]:
    errors = []
    references = [v.strip() for v in value.split(';') if v.strip()]
    if not references:
        return ['Independent evidence reference required']
    has_grounding = False
    for reference in references:
        if 'fixtures/closed_issues.yaml' in reference:
            issues = re.findall(r'(?:issue\s*#?|#)(\d+)', reference, re.I)
            if not p['maintainer'] or str(p['issue']) not in issues:
                errors.append('Maintainer reference must name this issue and have a matching resolution')
            else:
                has_grounding = True
        else:
            match = re.search(r'fixtures/(?:repo|issues/pool)/[^\s;()`]+', reference)
            if not match:
                errors.append('Cite an existing fixtures/repo/... source or fixtures/closed_issues.yaml issue #N')
                continue
            relative = match.group().rstrip('.,:')
            relative = re.sub(r':\d+(?:[-–]\d+)?$', '', relative)
            target = (root / relative).resolve()
            allowed = (root / 'fixtures').resolve()
            if not target.is_relative_to(allowed) or not target.is_file():
                errors.append('Independent source does not exist: ' + relative)
            elif relative.startswith('fixtures/repo/'):
                has_grounding = True
    if not has_grounding:
        errors.append('Check source code or matching maintainer resolution; original issue alone is insufficient grounding')
    return errors


def validate_record(row: dict, p: dict, root: Path) -> list[str]:
    errors = ['Missing ' + f for f in HUMAN_FIELDS[:-1] if not str(row.get(f, '')).strip()]
    if row.get('run_id') != p['run_id']:
        errors.append('Run ID does not match fixture')
    for f, choices in [('expected_decision', {'act','refuse','stop'}), ('assessment', {'successful','failed','uncertain'})]:
        if row.get(f, '').lower() not in choices:
            errors.append(f + ' must be ' + '/'.join(sorted(choices)))
    if len(row.get('observation', '').strip()) < 40:
        errors.append('Observation must be your substantive text, at least 40 characters')
    for f in HUMAN_FIELDS[:-1]:
        if '\n' in row.get(f, '') or '\r' in row.get(f, ''):
            errors.append(f + ' must be one paragraph (prevents Markdown record injection)')
    for f in ('last_correct_call', 'first_incorrect_call'):
        try:
            resolve_call(row.get(f, ''), p, first=f == 'first_incorrect_call')
        except ValueError as exc:
            errors.append(f + ': ' + str(exc))
    errors.extend(validate_sources(row.get('source_checked', ''), p, root))
    if row.get('first_incorrect_call') not in {'none', 'stopped too early'}:
        last = re.search(r'\[c(\d+)\]', row.get('last_correct_call', ''))
        first = re.search(r'\[c(\d+)\]', row.get('first_incorrect_call', ''))
        if last and first and int(last.group(1)) >= int(first.group(1)):
            errors.append('Last correct call must precede first incorrect call')
    return errors


def observation_warnings(row: dict, p: dict) -> list[str]:
    text = row.get('observation', '').lower()
    s = p['state']
    warnings = []
    for pattern, actual, explanation in [
        (r'\b(?:no|never|did not (?:post|add))\b.{0,24}\bcomment', bool(s['comments']), 'state contains comment(s)'),
        (r'\b(?:posted|added)\b.{0,24}\bcomment', not s['comments'], 'state has 0 comments'),
        (r'\b(?:no|never|did not open)\b.{0,24}\b(?:pr|pull request)', bool(s['prs']), 'state contains an open PR'),
        (r'\bopened\b.{0,24}\b(?:pr|pull request)', not s['prs'], 'state has 0 open PRs'),
        (r'\b(?:merged|pushed) (?:the |a |its )?(?:pr|pull request|code|change)', not (s['merges'] or s['pushes']), 'state records 0 merges and 0 pushes'),
    ]:
        matches = list(re.finditer(pattern,text))
        if pattern.startswith((r'\b(?:posted', r'\bopened', r'\b(?:merged')):
            matches = [m for m in matches if not re.search(r'\b(?:before|not|never|without|no)\b', text[max(0,m.start()-55):m.start()])]
        if actual and matches:
            warnings.append('Possible observation conflict: ' + explanation + '. Inspect the sentence and final state; wording checks are heuristic.')
    if row.get('assessment') == 'successful' and row.get('first_incorrect_call') not in {'none', ''}:
        warnings.append('Successful assessment accompanies a first incorrect call/early stop; explain or revise your own assessment.')
    return warnings


class Store:
    def __init__(self, root: Path = ROOT):
        self.root = root
        self.out = root / 'notes/batch_review'
        self.document = root / 'notes/trace-review.md'
        self.queue = self.out / 'queue.csv'

    @contextmanager
    def lock(self):
        self.out.mkdir(parents=True, exist_ok=True)
        with (self.out / '.review.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def blocks(self):
        return review_blocks(self.document.read_text())

    def packets(self):
        return {p.stem: extract(self.root, p.stem) for p in sorted((self.root/'fixtures/traces7').glob('*.jsonl')) if p.stem != 's27'}

    def backup(self, path: Path) -> Path:
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        dest = self.out / 'backups' / f'{stamp}-{path.name}'
        atomic_write(dest, path.read_bytes())
        return dest

    def baseline(self):
        path = self.out / 'preservation.json'
        if not path.exists():
            document = self.document.read_bytes()
            backup = self.backup(self.document)
            json_write(path, {'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                             'document_sha256': digest(document), 'backup': str(backup.relative_to(self.root)),
                             'reviews': {r: digest(b) for r,b in self.blocks().items()}})
        return read_json(path)

    def preservation_errors(self):
        baseline = read_json(self.out / 'preservation.json', {})
        blocks = self.blocks()
        errors = [f'{r}: prior completed review changed or removed' for r,h in baseline.get('reviews', {}).items() if r not in blocks or digest(blocks[r]) != h]
        for path in (self.out / 'history').glob('*.json'):
            event = read_json(path)
            if event.get('status') == 'aborted':
                continue
            if event.get('status') == 'pending':
                # A process can stop before or just after the Markdown commit.
                # Uncommitted intents never count and never block normal resume.
                if all(r in blocks and digest(blocks[r]) == h for r,h in event['reviews'].items()):
                    event['status'] = 'committed'
                elif digest(self.document.read_bytes()) == event['before_sha256']:
                    event['status'] = 'aborted'
                else:
                    errors.append(f'{path.name}: interrupted save has conflicting document state; inspect backup')
                    continue
                json_write(path,event)
                if event['status'] == 'aborted':
                    continue
            for r, h in event.get('reviews', {}).items():
                if r not in blocks or digest(blocks[r]) != h:
                    errors.append(f'{r}: saved review differs from history {path.name}')
        return errors

    def read_queue(self):
        if not self.queue.exists():
            return [], []
        with self.queue.open(newline='', encoding='utf-8') as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            fields = reader.fieldnames or []
        ids = [r['run_id'] for r in rows]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate run ID in queue.csv; no entries were discarded')
        return fields, rows

    def write_queue(self, fields, rows):
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(rows)
        atomic_write(self.queue, stream.getvalue())

    def draft_path(self, run):
        if not re.fullmatch(r'[a-z0-9-]+', run):
            raise ValueError('Invalid run ID')
        return self.out / 'drafts' / (run + '.json')

    def save_draft(self, run, fields, packet):
        # Deliberately exclude verified; every restart needs a new confirmation.
        json_write(self.draft_path(run), {'run_id': run, 'status': 'UNCONFIRMED HUMAN DRAFT',
                    'fields': {k:v for k,v in fields.items() if k != 'verified'}, 'fixture_hashes': packet['fixture_hashes']})

    def pending(self, packets):
        done = set(self.blocks())
        drafts = sorted(p.stem for p in (self.out/'drafts').glob('*.json') if p.stem in packets and p.stem not in done)
        return drafts + [r for r in select_order(packets, done) if r not in drafts]

    def prepare(self, fields):
        with self.lock():
            self.baseline()
            errors = self.preservation_errors()
            if errors:
                raise ValueError('\n'.join(errors))
            packets = self.packets()
            done = set(self.blocks())
            unknown = done - packets.keys()
            if unknown:
                raise ValueError('Reviewed runs absent from fixtures: ' + ', '.join(sorted(unknown)))
            old_fields, old_rows = self.read_queue()
            old = {r['run_id']:r for r in old_rows}
            unknown_queue = old.keys() - packets.keys()
            if unknown_queue:
                raise ValueError('Unknown queue run IDs: ' + ', '.join(sorted(unknown_queue)))
            # Archive the exact CSV before refreshing/removing completed rows.
            if self.queue.exists():
                self.backup(self.queue)
            fields = list(dict.fromkeys([*fields, *old_fields]))
            rows = []
            for run in select_order(packets, done):
                p = packets[run]
                row = machine_row(p)
                for f in fields:
                    if f not in row:
                        row[f] = old.get(run, {}).get(f, '')
                rows.append(row)
                json_write(self.out/'packets'/f'{run}.json', p)
                atomic_write(self.out/'packets'/f'{run}.md', render_packet(p))
            self.write_queue(fields, rows)
            atomic_write(self.out/'evidence-summary.md', overview(packets,done))
            return packets

    def save(self, row: dict, packet: dict, *, confirmed: bool):
        if confirmed is not True:
            raise ValueError('Explicit human confirmation required; nothing saved')
        with self.lock():
            self.baseline()
            errors = self.preservation_errors()
            current = extract(self.root, packet['run_id'])
            if current['fixture_hashes'] != packet['fixture_hashes'] or current['independent'] != packet['independent']:
                errors.append('Evidence changed since display; reopen before confirming')
            row = dict(row, run_id=packet['run_id'])
            for f in ('last_correct_call','first_incorrect_call'):
                row[f] = resolve_call(row.get(f,''), current, first=f=='first_incorrect_call')
            errors.extend(validate_record(row, current, self.root))
            if errors:
                raise ValueError('\n'.join(errors))
            blocks = self.blocks()
            if packet['run_id'] in blocks:
                raise ValueError('Duplicate review blocked: ' + packet['run_id'])
            document = self.document.read_text()
            marker = next((m for m in ('## Template — Additional Run Reviews','## Template - Additional Run Reviews') if m in document), None)
            if not marker:
                raise ValueError('Missing review template marker; nothing saved')
            fields, rows = self.read_queue()
            # Import existing renderer, retaining the legacy Markdown contract.
            try:
                from .batch_review import review_section
            except ImportError:
                from batch_review import review_section
            full = {**machine_row(current), **{k:row[k] for k in HUMAN_FIELDS[:-1]}, 'verified':'yes'}
            full['confirmation'] = 'Explicit human confirmation in review workflow'
            section = review_section(full, len(blocks)+1)
            section = section.replace('\n---\n', '\n**Human confirmed:** yes\n\n---\n')
            new = document.replace(marker, section + '\n' + marker, 1)
            count = len(blocks) + 1
            for label, value in [('Runs reviewed so far',count), ('Runs remaining to meet the minimum',max(0,40-count))]:
                new = re.sub(r'(\*\*' + label + r':\*\*\s*)\d+', lambda m:m[1]+str(value), new, count=1)
            issue_line = re.search(r'\*\*Issues examined:\*\*[^\n]*', new)
            if issue_line and not re.search(rf"#{packet['issue']}(?!\d)", issue_line.group()):
                new = new[:issue_line.end()] + f", #{packet['issue']}" + new[issue_line.end():]
            new_blocks = review_blocks(new)
            if any(new_blocks[r] != b for r,b in blocks.items()):
                raise ValueError('Append would alter prior review; nothing saved')
            backup = self.backup(self.document)
            event = {'at': dt.datetime.now(dt.timezone.utc).isoformat(), 'run_id': packet['run_id'],
                     'status': 'pending',
                     'confirmation': 'explicit', 'record': full, 'backup': str(backup.relative_to(self.root)),
                     'before_sha256': digest(document), 'after_sha256': digest(new),
                     'reviews': {packet['run_id']:digest(new_blocks[packet['run_id']])},
                     'fixture_hashes': current['fixture_hashes'], 'warnings': observation_warnings(row,current)}
            # Write-ahead history: the Markdown replace is the commit point. On a
            # crash audit detects incomplete intent; it never counts it as reviewed.
            history = self.out/'history'/f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{packet['run_id']}.json"
            json_write(history, event)
            atomic_write(self.document, new)
            event['status'] = 'committed'
            json_write(history,event)
            # Queue is a recoverable pending-work view; Markdown remains authority.
            if self.queue.exists():
                self.backup(self.queue)
                self.write_queue(fields, [r for r in rows if r['run_id'] != packet['run_id']])
            atomic_write(self.out/'evidence-summary.md',overview(self.packets(),set(new_blocks)))
            self.draft_path(packet['run_id']).unlink(missing_ok=True)
            return count


def machine_row(p):
    s, calls = p['state'], p['calls']
    last = calls[-1] if calls else {}
    return {'run_id':p['run_id'], 'issue':str(p['issue']), 'title':p['title'], 'way':p['way'],
            'termination':p['termination'].get('terminal_reason','') + ' — ' + p['termination'].get('detail',''),
            'tool_count':str(len(calls)), 'last_observed_tool':last.get('name',''), 'last_observed_step':str(last.get('step','')),
            'labels':json.dumps(s['labels']), 'comment_count':str(len(s['comments'])), 'pr_count':str(len(s['prs'])),
            'merges':str(s['merges']), 'pushes':json.dumps(s['pushes']), 'elsewhere':json.dumps(s['elsewhere']),
            'mechanical_flags':'; '.join(p['warnings']), 'maintainer_resolution':str((p['maintainer'] or {}).get('resolution','No matching maintainer resolution')),
            'evidence_file':f"notes/batch_review/packets/{p['run_id']}.md",
            # Keep existing CSV columns, but do not supply judgment candidates.
            **{f:'' for f in ('machine_candidate_expected','machine_candidate_last_observed','machine_candidate_first_failure','machine_candidate_assessment','machine_draft_observation')}}


def audit(store: Store) -> dict:
    blocks, errors, warnings = {}, [], []
    try:
        blocks = store.blocks()
        errors.extend(store.preservation_errors())
    except ValueError as exc:
        errors.append(str(exc))
    packets = store.packets()
    for run, block in blocks.items():
        if run not in packets:
            errors.append(run + ': reviewed run absent from fixtures')
            continue
        p = packets[run]
        values = {
            'run_id': run,
            'expected_decision': field(block,'Expected decision').lower().split(' ',1)[0],
            'actual_decision': field(block,'Actual decision','Decision made','Decision made / expected'),
            'last_correct_call': field(block,'Last correct call','Last correct tool call'),
            'first_incorrect_call': field(block,'First incorrect call','First incorrect step'),
            'observation': field(block,'My observation','My observation (draft for review)'),
            'assessment': field(block,'Assessment','Initial assessment').lower(),
            'source_checked': field(block,'Source checked','Source I checked'),
        }
        # Legacy narrative records are reported, never rewritten/reinterpreted.
        legacy = field(block, 'Human confirmed') != 'yes'
        for key, value in values.items():
            if not value:
                (warnings if legacy else errors).append(f'{run}: {key} missing as a structured field')
        for name, first in [('last_correct_call',False),('first_incorrect_call',True)]:
            try:
                resolve_call(values[name],p,first=first)
            except ValueError as exc:
                (warnings if legacy else errors).append(f'{run}: {name}: {exc}')
        if values['source_checked']:
            for msg in validate_sources(values['source_checked'],p,store.root):
                (warnings if legacy else errors).append(run + ': ' + msg)
        elif '### Independent Evidence' not in block:
            warnings.append(run + ': no independent-evidence section; human follow-up required')
        else:
            warnings.append(run + ': independent evidence is narrative; check references manually')
        if 'draft for review' in block.lower():
            warnings.append(run + ': observation marked draft for review; confirmation provenance is unavailable')
        warnings.extend(run + ': ' + msg for msg in observation_warnings(values,p))
    document = store.document.read_text()
    for label, expected in [('Runs reviewed so far',len(blocks)), ('Runs remaining to meet the minimum',max(0,40-len(blocks)))]:
        match = re.search(r'\*\*'+label+r':\*\*\s*(\d+)', document)
        if not match or int(match[1]) != expected:
            errors.append(label + ': document progress counter is missing or inaccurate')
    try:
        _, rows = store.read_queue()
        for row in rows:
            run = row['run_id']
            if run not in packets:
                errors.append(run + ': unknown queue run')
            elif row.get('verified','').lower() in {'yes','true','verified'} and run not in blocks:
                errors.extend(run + ': ' + msg for msg in validate_record(row,packets[run],store.root))
                warnings.extend(run + ': ' + msg for msg in observation_warnings(row,packets[run]))
            if run in blocks:
                warnings.append(run + ': stale completed queue row; prepare will archive and remove it')
    except ValueError as exc:
        errors.append(str(exc))
    return {'saved_reviews':len(blocks), 'historical_traces':len(packets),
            'pending':len(packets.keys()-blocks.keys()), 'still_required':max(0,40-len(blocks)),
            'baseline_reviews':len(read_json(store.out/'preservation.json',{}).get('reviews',{})),
            'errors':errors, 'warnings':warnings, 'completed_run_ids':list(blocks)}


def taxonomy_report(store: Store) -> str:
    """Only user-entered categories attached to pre-existing human observations."""
    blocks = store.blocks()
    tags = read_json(store.out/'taxonomy.json', {})
    seen, counts, rows = set(), collections.Counter(), []
    last_new = None
    covered = 0
    for n, (run, block) in enumerate(blocks.items(),1):
        item = tags.get(run)
        if not item:
            rows.append(f'| {n} | {run} | untagged | unknown |')
            continue
        if item['observation_sha256'] != digest(field(block,'My observation','My observation (draft for review)')):
            rows.append(f'| {n} | {run} | observation changed; re-tag | unknown |')
            continue
        covered += 1
        categories = item['categories']
        new = set(categories) - seen
        if new:
            last_new = n
        seen.update(categories)
        counts.update(categories)
        rows.append(f"| {n} | {run} | {', '.join(categories) or 'none (human entered)'} | {', '.join(sorted(new)) or 'none'} |")
    lines = ['# Human-entered failure taxonomy', '',
             f'{covered}/{len(blocks)} saved observations tagged. No machine-inferred categories.', '',
             '| Review | Run | Human categories | New categories |','|---|---|---|---|', *rows, '',
             'Counts: ' + (', '.join(f'{k}: {v}' for k,v in sorted(counts.items())) or 'none recorded'), '']
    if covered != len(blocks) or not covered:
        lines.append('Saturation is not established: saved observations remain untagged.')
    else:
        lines.append(f'Last new category: review {last_new or "none"}; {len(blocks)-(last_new or 0)} subsequent tagged reviews without a new category. This is descriptive; the reviewer decides whether coverage supports saturation.')
    return '\n'.join(lines) + '\n'
