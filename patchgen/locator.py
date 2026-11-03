"""Conservative syntax candidates; no whole-program receiver/type certainty."""
import re
from pathlib import Path
from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_typescript
import tree_sitter_c_sharp
from patchgen.adapter import digest
from patchgen.generator import command
from patchgen.python_bindings import POLICY, references

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
                 resolution='candidate') for line,kinds in sorted(lines.items())], warnings, tree.root_node.has_error


def attach_bindings(text, language, event, policy, positions, parse_error=False):
    """Attach positive evidence without upgrading all matches or excluding candidates."""
    limitations = []
    if language == 'python' and policy and not parse_error:
        try:
            bound, limitations = references(text, event['old_name'], *policy)
        except SyntaxError:
            return positions, ['Python AST parse failed; no binding evidence']
        for position in positions:
            evidence = [item for item in bound if item['line'] == position['start_line']]
            if evidence:
                position['binding_evidence'] = evidence
                position['required_reference'] = event['category'] in ('field_renamed', 'field_removed')
    return positions, limitations


def enum_symbols(detector):
    """Descriptor-derived names only; no receiver resolution or exhaustiveness proof."""
    from patchgen.detector import descriptor, qualified
    file, _ = descriptor(detector['change']['old_schema'], detector['change']['schema_path'])
    target = detector['events'][0]['enum']
    declarations = {qualified(file.package, e.name): e for e in file.enum_type}
    fields = []
    def visit(messages, prefix):
        for message in messages:
            full = qualified(prefix, message.name)
            declarations.update({full + '.' + e.name: e for e in message.enum_type})
            fields.extend(dict(message=full, name=f.name, number=f.number)
                          for f in message.field if f.type == 14 and f.type_name == '.' + target)
            visit(message.nested_type, full)
    visit(file.message_type, file.package)
    if target not in declarations:
        raise ValueError('old enum descriptor identity missing')
    enum = declarations[target]
    # Include common generated spellings and unqualified value names. These
    # remain conservative string identities, not imported-symbol resolution.
    symbols = {enum.name, *(f['name'] for f in fields)}
    for value in enum.value:
        symbols.add(value.name)
        lower = value.name.lower()
        symbols.update(names(lower))
        # Some generators strip a matching enum-name prefix from value names.
        prefix = re.sub(r'(?<!^)(?=[A-Z])', '_', enum.name).lower() + '_'
        if lower.startswith(prefix):
            symbols.update(names(lower[len(prefix):]))
    return dict(enum=target, fields=fields, symbols=sorted(symbols), status='candidate_only',
                limitations=['No alias, receiver, numeric dispatch, exhaustiveness or default-case proof.',
                             'All enum additions remain partial and blocked from generation.'])


def scan_enum(text, language, symbols):
    lines, warnings, error = {}, [], False
    for symbol in symbols:
        found, issues, failed = scan(text, language, symbol)
        error |= failed
        for issue in issues:
            if issue not in warnings:
                warnings.append(issue)
        for position in found:
            lines.setdefault(position['start_line'], set()).add(symbol)
    return [dict(start_line=line, end_line=line,
                 reason='Enum syntax candidate; matched symbols: ' + ', '.join(sorted(found)),
                 resolution='candidate') for line, found in sorted(lines.items())], warnings, error


def locate(repo, detector):
    revision = detector['source_revision']
    paths = command(['git','ls-tree','-r','--name-only',revision,'--','runtimes/'],repo).splitlines()
    record = dict(adapter_version='1.0', producer='independent-tree-sitter-locator/1.2',
                  source_revision=revision, change_id=detector['change']['id'],
                  old_schema_sha256=detector['old_schema_sha256'], status='partial', files=[], scanned=[], issues=[],
                  resolution_scope='syntax candidates; binding evidence is separate and bounded; conservative cross-version matches')
    if detector['status'] != 'complete':
        record['issues'].append('detector incomplete'); return record
    event = detector['events'][0]
    enum = None
    if 'old_name' not in event:
        enum = enum_symbols(detector)
        record['enum_analysis'] = enum
        record['issues'].append('enum candidates only; consumer behavior/exhaustiveness analysis unsupported')
    policy = POLICY.get((detector['change']['schema_path'], event.get('message')))
    record['binding_policy'] = dict(scope='declared standard protoc Python modules; lexical import identity only',
        python_module=policy[0] if policy else None, python_symbol=policy[1] if policy else None,
        assumptions=['Generated module imports follow the declared policy; no runtime monkeypatching.',
                     'No cross-function, branch merge, annotation or whole-program type proof.'])
    for path in paths:
        suffix = Path(path).suffix
        if suffix not in LANGUAGES:
            if suffix in ('.tsx','.jsx','.js','.mjs','.java','.cpp','.cc','.h','.rs','.go'):
                record['issues'].append(dict(path=path,reason='unsupported runtime source language'))
            continue
        language = LANGUAGES[suffix]
        text = command(['git','show',revision+':'+path],repo)
        positions, warnings, error = (scan_enum(text,language,enum['symbols']) if enum else
                                      scan(text,language,event['old_name']))
        if not enum:
            positions, limitations = attach_bindings(text, language, event, policy, positions, error)
            record.setdefault('binding_limitations', []).extend(dict(path=path, detail=item) for item in limitations)
        record['scanned'].append(dict(path=path, source_sha256=digest(text), language=language))
        if error or warnings:
            record['issues'].append(dict(path=path,parse_error=error,warnings=warnings))
        if positions:
            record['files'].append(dict(path=path,language=language,source_sha256=digest(text),positions=positions))
    record['status'] = 'complete' if not record['issues'] and record['scanned'] else 'partial'
    return record
