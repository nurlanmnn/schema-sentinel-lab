"""Conservative syntax candidates; no whole-program receiver/type certainty."""
import re
from pathlib import Path
from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_typescript
import tree_sitter_c_sharp
from patchgen.adapter import digest
from patchgen.generator import command

LANGUAGES = {'.py':'python', '.ts':'typescript', '.cs':'csharp'}
FACTORIES = {'python':tree_sitter_python.language, 'typescript':tree_sitter_typescript.language_typescript,
             'csharp':tree_sitter_c_sharp.language}


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def names(field):
    parts = field.split('_')
    return {field, parts[0] + ''.join(p[:1].upper()+p[1:] for p in parts[1:]),
            ''.join(p[:1].upper()+p[1:] for p in parts)}


def scan(text, language, field):
    raw = text.encode()
    tree = Parser(Language(FACTORIES[language]())).parse(raw)
    lines, warnings = {}, []
    variants = names(field)
    for node in walk(tree.root_node):
        value = raw[node.start_byte:node.end_byte].decode()
        parent = node.parent
        if node.type in ('identifier','property_identifier') and value.lstrip('@') in variants:
            if parent and parent.type not in ('comment','string','string_literal'):
                lines.setdefault(node.start_point.row+1, set()).add(parent.type)
        if node.type in ('string','string_literal') and value.strip('"\'') in variants:
            if parent and parent.type in ('argument_list','arguments','subscript','subscript_expression','element_access_expression','pair','dictionary_splat_pattern','argument'):
                lines.setdefault(node.start_point.row+1,set()).add('literal-key/reflection candidate')
        if node.type == 'call' and value.startswith(('getattr(', 'setattr(', 'delattr(')):
            args = node.child_by_field_name('arguments')
            if args and len(args.named_children)>1 and args.named_children[1].type != 'string':
                warnings.append(dict(line=node.start_point.row+1, reason='dynamic reflection field name'))
        if node.type in ('element_access_expression','subscript','subscript_expression') and re.match(r'(?:entity|decoded)\s*\[\s*[^\"\']',value):
            warnings.append(dict(line=node.start_point.row+1,reason='dynamic entity subscript requires review'))
        if node.type in ('invocation_expression','call_expression') and re.search(r'\.(?:GetProperty|GetField|GetMember)\s*\(',value):
            warnings.append(dict(line=node.start_point.row+1,reason='reflection requires review'))
    return [dict(start_line=line,end_line=line,reason='Conservative syntax candidate: '+', '.join(sorted(kinds)),
                 resolution='resolved') for line,kinds in sorted(lines.items())], warnings, tree.root_node.has_error


def locate(repo, detector):
    revision = detector['source_revision']
    paths = command(['git','ls-tree','-r','--name-only',revision,'--','runtimes/'],repo).splitlines()
    record = dict(adapter_version='1.0', producer='independent-tree-sitter-locator/1.0',
                  source_revision=revision, change_id=detector['change']['id'],
                  old_schema_sha256=detector['old_schema_sha256'], status='partial', files=[], scanned=[], issues=[],
                  resolution_scope='resolved syntax candidates, receiver types unproved; conservative cross-version matches')
    if detector['status'] != 'complete':
        record['issues'].append('detector incomplete'); return record
    event = detector['events'][0]
    if 'old_name' not in event:
        record['issues'].append('enum consumer analysis unsupported'); return record
    for path in paths:
        suffix = Path(path).suffix
        if suffix not in LANGUAGES:
            continue
        language = LANGUAGES[suffix]
        text = command(['git','show',revision+':'+path],repo)
        positions, warnings, error = scan(text,language,event['old_name'])
        record['scanned'].append(dict(path=path, source_sha256=digest(text), language=language))
        if error or warnings:
            record['issues'].append(dict(path=path,parse_error=error,warnings=warnings))
        if positions:
            record['files'].append(dict(path=path,language=language,source_sha256=digest(text),positions=positions))
    record['status'] = 'complete' if not record['issues'] and record['scanned'] else 'partial'
    return record
