"""Conservative syntax candidates; no whole-program receiver/type certainty."""
import ast
import re
from tree_sitter import Language, Parser
import tree_sitter_python
import tree_sitter_typescript
import tree_sitter_c_sharp
from patchgen.adapter import digest
from patchgen.generator import command
from patchgen.python_bindings import POLICY
from patchgen.typescript_bindings import POLICY as TYPESCRIPT_POLICY
from patchgen.binding_analysis import analyze_bindings, reference_requires_edit
from patchgen.runtime_inventory import inventory, blocking_entries
from patchgen.source_spellings import csharp_field_spellings, identifier_value, quoted_value

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


def literal_string(node, raw, language):
    if node is None or node.type not in ('string', 'string_literal', 'concatenated_string', 'verbatim_string_literal', 'template_string'):
        return None
    value = raw[node.start_byte:node.end_byte].decode()
    if language == 'python':
        try:
            result = ast.literal_eval(value)
            return result if isinstance(result, str) else None
        except (ValueError, SyntaxError):
            return None
    if node.type == 'template_string' and any(child.type == 'template_substitution' for child in node.named_children):
        return None
    return quoted_value(value, language)


SUBSCRIPTS = {'element_access_expression', 'subscript', 'subscript_expression'}


def subscript_key(node):
    index = node.child_by_field_name('index') or node.child_by_field_name('subscript')
    if index is not None and index.type == 'bracketed_argument_list':
        children = index.named_children
        index = children[0] if len(children) == 1 else None
        if index is not None and index.type == 'argument' and len(index.named_children) == 1:
            index = index.named_children[0]
    return index


def dynamic_index(node, index, raw, language):
    # Keep the bounded receiver heuristic for otherwise unknown subscripts.
    receiver = node.named_children[0] if node.named_children else None
    if receiver is None or identifier_value(raw[receiver.start_byte:receiver.end_byte].decode(), language) not in ('entity', 'decoded'):
        return False
    if index is None:
        return True
    if literal_string(index, raw, language) is not None:
        return False
    return index.type not in ('integer','float','number','integer_literal','real_literal',
                              'true','false','boolean','none','null','null_literal','boolean_literal')


def key_initializer(node, language):
    if language == 'python' and node.type == 'assignment':
        return node.child_by_field_name('left'), node.child_by_field_name('right')
    if node.type == 'variable_declarator':
        target = node.child_by_field_name('name')
        if language == 'typescript':
            return target, node.child_by_field_name('value')
        if language == 'csharp':
            children = [child for child in node.named_children if child.type != 'comment']
            if len(children) == 2 and children[0] == target:
                return target, children[1]
    return None, None


PYTHON_REFLECTION = {'getattr', 'setattr', 'delattr', 'hasattr'}


def python_reflection_keys(tree):
    """Find possible dynamic builtin-reflection calls through visible aliases."""
    modules, callables = {'builtins'}, set(PYTHON_REFLECTION)
    assignments, calls = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.asname or alias.name for alias in node.names if alias.name == 'builtins')
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == 'builtins':
            callables.update(alias.asname or alias.name for alias in node.names if alias.name in PYTHON_REFLECTION)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            assignments.extend((target.id, node.value) for target in targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.Call):
            calls.append(node)

    def is_reflector(expr):
        if isinstance(expr, ast.Name):
            return expr.id in callables
        return (isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name)
                and expr.value.id in modules and expr.attr in PYTHON_REFLECTION)

    # File-wide overapproximation only. Rebinding can add warnings, but can
    # never establish that a call resolves to a builtin or a canonical receiver.
    while True:
        size = len(modules) + len(callables)
        for name, value in assignments:
            if isinstance(value, ast.Name) and value.id in modules:
                modules.add(name)
            if is_reflector(value):
                callables.add(name)
        if len(modules) + len(callables) == size:
            break

    for call in calls:
        if not is_reflector(call.func):
            continue
        if any(isinstance(arg, ast.Starred) for arg in call.args[:2]):
            yield call.lineno, None
        elif len(call.args) >= 2:
            key = call.args[1]
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                yield call.lineno, key


def scan(text, language, field, *, event=None):
    raw = text.encode()
    tree = Parser(Language(FACTORIES[language]())).parse(raw)
    lines, warnings = {}, []
    variants = names(field)
    old_field = (event or {}).get('old_field') or {}
    if language == 'csharp' and event and event.get('message'):
        variants.update(csharp_field_spellings(field, event['message'], old_field.get('proto3_optional')))
    keys = variants | {key for key in (old_field.get('json_name'), (event or {}).get('old_presence_group')) if key}
    key_sources, key_uses = {}, {}

    def identifier(node):
        return identifier_value(raw[node.start_byte:node.end_byte].decode(), language)

    for node in walk(tree.root_node):
        value = raw[node.start_byte:node.end_byte].decode()
        parent = node.parent
        if node.type in ('identifier','property_identifier') and identifier_value(value, language) in variants:
            if parent and parent.type not in ('comment','string','string_literal'):
                lines.setdefault(node.start_point.row+1, set()).add(parent.type)
        if literal_string(node, raw, language) in keys:
            if parent and parent.type in ('argument_list','arguments','subscript','subscript_expression','element_access_expression','pair','dictionary_splat_pattern','argument','computed_property_name'):
                lines.setdefault(node.start_point.row+1,set()).add('literal-key/reflection candidate')
        target, initializer = key_initializer(node, language)
        if target and target.type == 'identifier' and literal_string(initializer, raw, language) in keys:
            key_sources.setdefault(identifier(target), set()).add(initializer.start_point.row+1)
        if node.type in SUBSCRIPTS:
            index = subscript_key(node)
            if index and index.type == 'identifier':
                key_uses.setdefault(identifier(index), set()).add(index.start_point.row+1)
            if dynamic_index(node, index, raw, language):
                warnings.append(dict(line=node.start_point.row+1,reason='dynamic subscript; receiver/key identity requires review'))
                lines.setdefault(node.start_point.row+1,set()).add('dynamic subscript candidate; field identity unknown')
        function = node.child_by_field_name('function') if node.type in ('invocation_expression','call_expression') else None
        member = (function.child_by_field_name('name') or function.child_by_field_name('property')) if function else None
        member_name = raw[member.start_byte:member.end_byte].decode() if member else ''
        if member and identifier_value(member_name, language) in ('GetProperty', 'GetField', 'GetMember'):
            warnings.append(dict(line=node.start_point.row+1,reason='reflection requires review'))
            lines.setdefault(node.start_point.row+1,set()).add('reflection candidate; field identity unknown')
    parse_error = tree.root_node.has_error
    if language == 'python':
        try:
            python_tree = ast.parse(text)
        except SyntaxError:
            parse_error = True
        else:
            for line, key in python_reflection_keys(python_tree):
                warnings.append(dict(line=line, reason='dynamic reflection field name'))
                lines.setdefault(line, set()).add('dynamic reflection candidate; field identity unknown')
                if isinstance(key, ast.Name) and key.id in key_sources:
                    lines.setdefault(key.lineno, set()).add('reflection with possible named field key')
                    for source_line in key_sources[key.id]:
                        lines.setdefault(source_line, set()).add('named field-key literal source')
    warnings.sort(key=lambda warning: (warning['line'], warning['reason']))
    # Match names only within this file. Shadowing, rebinding and execution order
    # may create extras; these candidates never assert that the key reaches a use.
    for key in key_sources.keys() & key_uses.keys():
        for line in key_sources[key]:
            lines.setdefault(line, set()).add('named field-key literal source')
        for line in key_uses[key]:
            lines.setdefault(line, set()).add('subscript with possible named field key')
    return [dict(start_line=line,end_line=line,reason='Conservative syntax candidate: '+', '.join(sorted(kinds)),
                 resolution='candidate') for line,kinds in sorted(lines.items())], warnings, parse_error


def attach_bindings(text, language, event, policy, positions, parse_error=False, *, schema_path=None, source_path=None, typescript_policy=None):
    """Attach positive evidence without upgrading all matches or excluding candidates."""
    limitations = []
    if not parse_error:
        try:
            bound, limitations = analyze_bindings(text, language, event, schema_path, source_path, python_policy=policy, typescript_policy=typescript_policy)
        except SyntaxError:
            return positions, [language+' binding parse failed; no binding evidence']
        for position in positions:
            evidence = [item for item in bound if item['line'] == position['start_line']]
            if evidence:
                position['binding_evidence'] = evidence
                position['required_reference'] = reference_requires_edit(language, event)
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
    entries = inventory(repo, revision)
    record = dict(adapter_version='1.0', producer='independent-tree-sitter-locator/1.11',
                  scan_manifest_version='1.1', runtime_inventory=entries, source_revision=revision, change_id=detector['change']['id'],
                  old_schema_sha256=detector['old_schema_sha256'], status='partial', files=[], scanned=[], issues=[],
                  resolution_scope='syntax candidates; binding evidence is separate and bounded; conservative cross-version matches')
    record['issues'].extend(dict(path=e['path'], reason=e['disposition']) for e in blocking_entries(entries))
    if detector['status'] != 'complete':
        record['issues'].append('detector incomplete'); return record
    event = detector['events'][0]
    enum = None
    if 'old_name' not in event:
        enum = enum_symbols(detector)
        record['enum_analysis'] = enum
        record['issues'].append('enum candidates only; consumer behavior/exhaustiveness analysis unsupported')
    policy = POLICY.get((detector['change']['schema_path'], event.get('message')))
    ts_policy = TYPESCRIPT_POLICY.get((detector['change']['schema_path'], event.get('message')))
    record['binding_policy'] = dict(scope='declared generated Python/ts-proto modules; bounded import and immutable TS dataflow evidence',
        python_module=policy[0] if policy else None, python_symbol=policy[1] if policy else None,
        typescript_module=ts_policy[0] if ts_policy else None, typescript_symbol=ts_policy[1] if ts_policy else None,
        assumptions=['Generated module imports follow the declared policy; no runtime monkeypatching.',
                     'No cross-function value capture, branch merge, annotation/cast or whole-program type proof; TS follows const only.'],
        dynamic_subscript_scope='possible same-file named literal keys or entity/decoded receiver spelling; unknown arbitrary receivers/compound keys unsupported')
    for entry in entries:
        if entry['disposition'] != 'source':
            continue
        path, language = entry['path'], entry['language']
        text = command(['git','show',revision+':'+path],repo)
        positions, warnings, error = (scan_enum(text,language,enum['symbols']) if enum else
                                      scan(text,language,event['old_name'],event=event))
        if not enum:
            positions, limitations = attach_bindings(text, language, event, policy, positions, error,
                                                    schema_path=detector['change']['schema_path'], source_path=path)
            record.setdefault('binding_limitations', []).extend(dict(path=path, detail=item) for item in limitations)
        record['scanned'].append(dict(path=path, source_sha256=digest(text), language=language))
        if error or warnings:
            record['issues'].append(dict(path=path,parse_error=error,warnings=warnings))
        if positions:
            record['files'].append(dict(path=path,language=language,source_sha256=digest(text),positions=positions))
    record['status'] = 'complete' if not record['issues'] and record['scanned'] else 'partial'
    return record
