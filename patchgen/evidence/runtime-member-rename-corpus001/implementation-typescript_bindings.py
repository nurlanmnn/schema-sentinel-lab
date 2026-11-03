"""Bounded ts-proto source evidence from exact emitted-module import identities.

Assumes the declared generator's standard codec API and no runtime monkeypatching.
Only immutable const dataflow is followed. No TS annotation, cast, structural
compatibility or whole-program type inference.
"""
import posixpath
from collections import Counter
import re
from tree_sitter import Language, Parser
import tree_sitter_typescript
from patchgen.source_spellings import identifier_value, quoted_value

POLICY = {
    ('proto/telemetry/vehicle.proto', 'simulation.telemetry.VehicleTelemetry'):
        ('generated/ts/telemetry/vehicle', 'VehicleTelemetry'),
    ('proto/inventory/item.proto', 'simulation.inventory.StockItem'):
        ('generated/ts/inventory/item', 'StockItem'),
    ('proto/v1/entity.proto', 'simulation.v1.Entity'): ('generated/ts/v1/entity', 'Entity'),
    ('proto/v2/entity.proto', 'simulation.v2.Entity'): ('generated/ts/v2/entity', 'Entity'),
}
FUNCTIONS = {'function_declaration', 'function_expression', 'arrow_function',
             'generator_function_declaration', 'generator_function', 'method_definition'}


def walk(node, nested=True):
    yield node
    for child in node.named_children:
        if nested or child.type not in FUNCTIONS:
            yield from walk(child, nested)


def runtime_field_name(field):
    """Bounded ts-proto 1.165.0 default keys policy, including mixed case.

    This subset excludes leading/trailing/repeated underscores and all-uppercase
    words. Unsupported spellings withdraw evidence rather than guessing.
    """
    if not isinstance(field, str) or not re.fullmatch(r'[a-z][a-zA-Z0-9]*(?:_[a-zA-Z0-9]+)*', field):
        return None
    parts = field.split('_')
    return parts[0] + ''.join(p[:1].upper()+p[1:] for p in parts[1:])


def references(text, field, module, symbol, source_path):
    raw = text.encode()
    tree = Parser(Language(tree_sitter_typescript.language_typescript())).parse(raw)
    if tree.root_node.has_error:
        raise SyntaxError('TypeScript parse failed')
    member_field = runtime_field_name(field)
    if member_field is None:
        return [], ['field naming outside declared ts-proto camel-case policy']
    found, issues, imports = [], [], {}

    def spelling(node):
        return raw[node.start_byte:node.end_byte].decode() if node else ''

    def name(node):
        return identifier_value(spelling(node), 'typescript')

    def names(node):
        # Overapproximation used only to invalidate, never to establish a type.
        return {name(n) for n in walk(node) if n.type in ('identifier', 'type_identifier', 'shorthand_property_identifier_pattern')} if node else set()

    def property_path(node):
        if node is None:
            return ''
        if node.type == 'identifier':
            return name(node)
        if node.type in ('member_expression', 'subscript_expression'):
            base = property_path(node.child_by_field_name('object'))
            member = node.child_by_field_name('property') or node.child_by_field_name('index')
            value = quoted_value(spelling(member), 'typescript') if member and member.type == 'string' else name(member) if node.type == 'member_expression' else '*'
            return base+'.'+value if base and value else ''
        return ''

    def declaration_names(body):
        result = set()
        for item in walk(body, nested=False):
            if item.type == 'variable_declarator':
                result.update(names(item.child_by_field_name('name')))
            elif item.type in ('class_declaration', 'class', 'enum_declaration', 'internal_module'):
                result.update(names(item.child_by_field_name('name')))
            elif item.type == 'for_in_statement':
                result.update(names(item.child_by_field_name('left')))
            elif item.type == 'catch_clause':
                result.update(names(item.child_by_field_name('parameter')))
            # Nested function names are bindings in the containing body, although
            # their bodies must not contribute source evidence to that scope.
            for child in item.named_children:
                if child.type in FUNCTIONS:
                    result.update(names(child.child_by_field_name('name')))
        return result

    import_counts = Counter()
    for node in tree.root_node.named_children:
        if node.type != 'import_statement':
            continue
        for item in walk(node):
            if item.type == 'import_specifier':
                local = item.child_by_field_name('alias') or item.child_by_field_name('name')
                import_counts[name(local)] += 1
            elif item.type in ('namespace_import', 'import_clause'):
                for local in item.named_children:
                    if local.type == 'identifier': import_counts[name(local)] += 1
        source = node.child_by_field_name('source')
        value = quoted_value(spelling(source), 'typescript')
        if not value or not value.startswith('.'):
            continue
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source_path), value))
        if resolved != module:
            continue
        # Type-only imports cannot supply the runtime codec value.
        if any(child.type == 'type' for child in node.children):
            continue
        for item in walk(node):
            if item.type == 'import_specifier' and not any(c.type == 'type' for c in item.children):
                imported = item.child_by_field_name('name')
                local = item.child_by_field_name('alias') or imported
                if name(imported) == symbol:
                    imports[name(local)] = ('codec', [dict(line=item.start_point.row+1, operation='named import', module=module, symbol=symbol)])
            elif item.type == 'namespace_import':
                local = next((c for c in item.named_children if c.type == 'identifier'), None)
                if local:
                    imports[name(local)] = ('module', [dict(line=item.start_point.row+1, operation='namespace import', module=module)])

    imports = {local: value for local, value in imports.items() if import_counts[local] == 1}

    # Visible namespace writes are hazards even inside unsupported/nested scopes.
    # Alias names are conflated across scopes only for this rejection pass.
    aliases = set(imports)
    while True:
        previous = set(aliases)
        for node in walk(tree.root_node):
            if node.type in ('variable_declarator', 'assignment_expression'):
                target = node.child_by_field_name('name') or node.child_by_field_name('left')
                value = node.child_by_field_name('value') or node.child_by_field_name('right')
                if value and (value.type == 'identifier' and name(value) in aliases or
                              value.type == 'member_expression' and names(value.child_by_field_name('object')) & aliases):
                    aliases.update(names(target))
        if previous == aliases:
            break
    object_aliases = {'Object', 'globalThis.Object'}
    reflect_aliases = {'Reflect', 'globalThis.Reflect'}
    while True:
        previous = (set(object_aliases), set(reflect_aliases))
        for node in walk(tree.root_node):
            if node.type == 'variable_declarator':
                target, value = node.child_by_field_name('name'), node.child_by_field_name('value')
                if target and target.type == 'identifier':
                    if property_path(value) in object_aliases: object_aliases.add(name(target))
                    if property_path(value) in reflect_aliases: reflect_aliases.add(name(target))
        if previous == (object_aliases, reflect_aliases):
            break
    mutators = {base+'.'+method for base in object_aliases for method in
                ('assign', 'defineProperty', 'defineProperties', 'setPrototypeOf', '*')}
    mutators.update(base+'.'+method for base in reflect_aliases for method in
                    ('set', 'deleteProperty', 'defineProperty', 'setPrototypeOf', '*'))
    mutators.update({'globalThis.eval', 'globalThis.Function'})
    const_names = set(imports)
    for node in walk(tree.root_node):
        if node.type == 'lexical_declaration' and any(c.type == 'const' for c in node.children):
            for declaration in node.named_children:
                if declaration.type == 'variable_declarator':
                    const_names.update(names(declaration.child_by_field_name('name')))
    for node in walk(tree.root_node):
        reason = None
        if node.type == 'identifier' and name(node) in ('eval', 'Function') or property_path(node) in mutators:
            reason = 'dynamic namespace function or mutator reference'
        elif node.type in ('internal_module', 'ambient_declaration', 'import_alias'):
            reason = 'TypeScript namespace/ambient scope unsupported'
        elif node.type == 'with_statement':
            reason = 'dynamic with scope'
        elif node.type in ('assignment_expression', 'augmented_assignment_expression', 'update_expression'):
            target = node.child_by_field_name('left') or node.child_by_field_name('argument')
            if target and (names(target) & aliases or target.type in ('identifier', 'array_pattern', 'object_pattern') and names(target) & const_names):
                reason = 'possible codec mutation or immutable-binding reassignment'
        elif node.type == 'unary_expression' and spelling(node).lstrip().startswith('delete '):
            if names(node) & aliases:
                reason = 'possible generated codec/module deletion'
        if reason:
            return [], [dict(line=node.start_point.row+1, reason=reason+'; binding evidence disabled')]

    def evidence(token, value, kind):
        found.append(dict(line=token.start_point.row+1, column=token.start_point.column+1,
                          end_line=token.end_point.row+1, end_column=token.end_point.column+1,
                          kind=kind, binding='canonical', module=module, symbol=symbol,
                          evidence=value[1]))

    def expression(node, env):
        if node is None:
            return None
        if node.type == 'identifier':
            return env.get(name(node))
        if node.type in FUNCTIONS:
            return None  # Each function is analyzed separately from imports only.
        if node.type == 'parenthesized_expression' and len(node.named_children) == 1:
            return expression(node.named_children[0], env)
        if node.type == 'member_expression':
            value = expression(node.child_by_field_name('object'), env)
            token = node.child_by_field_name('property')
            if value and value[0] == 'module' and name(token) == symbol:
                return ('codec', value[1]+[dict(line=token.start_point.row+1, operation='generated message symbol')])
            if value and value[0] == 'instance' and name(token) == member_field:
                evidence(token, value, 'field_access')
            return None
        if node.type == 'subscript_expression':
            value = expression(node.child_by_field_name('object'), env)
            key = node.child_by_field_name('index')
            expression(key, env)
            if key and key.type == 'string' and value and value[0] == 'instance' and quoted_value(spelling(key), 'typescript') == member_field:
                evidence(key, value, 'field_key')
            return None
        if node.type == 'call_expression':
            function = node.child_by_field_name('function')
            method = function.child_by_field_name('property') if function and function.type == 'member_expression' else None
            codec = expression(function.child_by_field_name('object'), env) if method else None
            if not method:
                expression(function, env)
            args = node.child_by_field_name('arguments')
            arguments = args.named_children if args else []
            for argument in arguments:
                expression(argument, env)
            if codec and codec[0] == 'codec':
                if name(method) == 'decode':
                    return ('instance', codec[1]+[dict(line=node.start_point.row+1, operation='ts-proto decode')])
                if name(method) == 'encode' and arguments and arguments[0].type == 'object':
                    for pair in arguments[0].named_children:
                        key = pair.child_by_field_name('key') if pair.type == 'pair' else pair if pair.type == 'shorthand_property_identifier' else None
                        key_name = quoted_value(spelling(key), 'typescript') if key and key.type == 'string' else name(key)
                        if key and key_name == member_field:
                            evidence(key, codec, 'encoder_object_key')
            return None
        if node.type in ('assignment_expression', 'augmented_assignment_expression'):
            target = node.child_by_field_name('left')
            if target and target.type != 'identifier':
                expression(target, env)
            expression(node.child_by_field_name('right'), env)
            if target and target.type == 'identifier':
                env[name(target)] = None
            else:
                for local in names(target):
                    if target and target.type in ('array_pattern', 'object_pattern'): env[local] = None
            return None
        if node.type == 'update_expression':
            expression(node.child_by_field_name('argument'), env)
            for local in names(node.child_by_field_name('argument')): env[local] = None
            return None
        for child in node.named_children:
            expression(child, env)
        return None

    def statements(body, env):
        for node in body.named_children:
            if node.type in ('lexical_declaration', 'variable_declaration'):
                immutable = any(child.type == 'const' for child in node.children)
                for declaration in node.named_children:
                    if declaration.type != 'variable_declarator':
                        continue
                    value = expression(declaration.child_by_field_name('value'), env)
                    target = declaration.child_by_field_name('name')
                    if target and target.type == 'identifier':
                        env[name(target)] = (value[0], value[1]+[dict(line=target.start_point.row+1, operation='assignment', name=name(target))]) if value and immutable else None
                    else:
                        for local in names(target): env[local] = None
            elif node.type in ('expression_statement', 'return_statement', 'throw_statement'):
                expression(node, env)
            elif node.type in ('import_statement', 'interface_declaration', 'type_alias_declaration'):
                continue
            elif node.type == 'export_statement' and node.child_by_field_name('declaration') and node.child_by_field_name('declaration').type in FUNCTIONS:
                continue
            elif node.type in FUNCTIONS:
                env[name(node.child_by_field_name('name'))] = None
            else:
                # Branch/loop joins and enclosing local captures are unsupported.
                for local in declaration_names(node): env[local] = None
                for item in walk(node):
                    if item.type in ('assignment_expression', 'augmented_assignment_expression', 'update_expression'):
                        target = item.child_by_field_name('left') or item.child_by_field_name('argument')
                        if target and target.type == 'identifier': env[name(target)] = None
                issues.append(dict(line=node.start_point.row+1, reason='control flow unsupported for binding evidence'))

    global_env = dict(imports)
    for local in declaration_names(tree.root_node): global_env[local] = None
    statements(tree.root_node, dict(global_env))
    for node in walk(tree.root_node):
        if node.type not in FUNCTIONS:
            continue
        body = node.child_by_field_name('body')
        if not body:
            continue
        env = dict(global_env)
        ancestor = node.parent
        while ancestor:
            if ancestor.type in FUNCTIONS:
                outer_body = ancestor.child_by_field_name('body')
                if outer_body:
                    for local in declaration_names(outer_body): env[local] = None
                outer_parameters = ancestor.child_by_field_name('parameters') or ancestor.child_by_field_name('parameter')
                for local in names(outer_parameters): env[local] = None
                for local in names(ancestor.child_by_field_name('name')): env[local] = None
            ancestor = ancestor.parent
        for local in declaration_names(body): env[local] = None
        parameters = node.child_by_field_name('parameters') or node.child_by_field_name('parameter')
        for local in names(parameters): env[local] = None
        # Named function expressions/declarations bind their name in their body.
        for local in names(node.child_by_field_name('name')): env[local] = None
        if body.type == 'statement_block': statements(body, env)
        else: expression(body, env)
    return sorted(found, key=lambda ref: (ref['line'], ref['column'])), issues
