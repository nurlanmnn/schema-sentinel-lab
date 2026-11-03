"""Bounded Python import/constructor evidence under an explicit binding policy.

This is static source evidence, assuming declared generated modules have their
standard Protobuf API. It is not runtime import validation or whole-program proof.
Unrecognized expressions never acquire a message type. Branches and nested scopes
are deliberately not followed; lexical candidates remain available in the locator.
"""
import ast
import io
import tokenize
import unicodedata

# Declared standard protoc outputs for this repository (buf module root: proto).
# Unknown schema/message pairs, including authored corpus stubs, stay candidates.
POLICY = {
    ('proto/telemetry/vehicle.proto', 'simulation.telemetry.VehicleTelemetry'):
        ('telemetry.vehicle_pb2', 'VehicleTelemetry'),
    ('proto/inventory/item.proto', 'simulation.inventory.StockItem'):
        ('inventory.item_pb2', 'StockItem'),
    ('proto/v1/entity.proto', 'simulation.v1.Entity'): ('v1.entity_pb2', 'Entity'),
    ('proto/v2/entity.proto', 'simulation.v2.Entity'): ('v2.entity_pb2', 'Entity'),
}


def stored_names(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del))}


def local_names(body):
    """Python locals shadow globals throughout a function, even before assignment."""
    result = set()
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result.add(node.name)
            continue
        result.update(stored_names(node))
        for item in ast.walk(node):
            # Pattern captures use string fields rather than Name(Store).
            if isinstance(item, (ast.MatchAs, ast.MatchStar)) and item.name:
                result.add(item.name)
            if isinstance(item, ast.MatchMapping) and item.rest:
                result.add(item.rest)
            if isinstance(item, (ast.Import, ast.ImportFrom)):
                result.update(alias.asname or alias.name.split('.')[0] for alias in item.names)
            if isinstance(item, ast.ExceptHandler) and item.name:
                result.add(item.name)
    return result


def references(text, field, module, symbol):
    """Return bound field tokens and limitations; retain no negative type claims."""
    tree = ast.parse(text)
    found, issues = [], []
    # AST identifiers are NFKC-normalized; offsets still describe the original
    # UTF-8 source. Index real NAME tokens instead of subtracting normalized-name
    # length from an attribute endpoint (which can point inside a Unicode token).
    normalized_text = text.replace('\r\n', '\n').replace('\r', '\n')
    source_lines = normalized_text.split('\n')
    starts, ends = {}, {}
    for token in tokenize.generate_tokens(io.StringIO(normalized_text).readline):
        if token.type != tokenize.NAME or unicodedata.normalize('NFKC', token.string) != field:
            continue
        start = (token.start[0], len(source_lines[token.start[0]-1][:token.start[1]].encode()))
        end = (token.end[0], len(source_lines[token.end[0]-1][:token.end[1]].encode()))
        starts[start] = (start, end)
        ends[end] = (start, end)
    # Audit hazards across the entire AST, including unsupported class/nested
    # bodies. This deliberately overapproximates aliases across lexical scopes:
    # uncertainty may remove positive evidence, never establish receiver identity.
    mutation_calls = {'exec', 'eval', 'globals', 'locals', 'vars', 'setattr', 'delattr'}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == 'builtins':
                mutation_calls.update(a.asname or a.name for a in node.names if a.name in mutation_calls)
            if node.level == 0 and node.module == module:
                imported.update(a.asname or a.name for a in node.names if a.name == symbol)
        elif isinstance(node, ast.Import):
            imported.update(a.asname for a in node.names if a.name == module and a.asname)
    # Follow only class/module alias syntax, without constructors or instance
    # values. Scope conflation here is safe because this set only rejects claims.
    while True:
        previous = set(imported)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value
                if isinstance(value, ast.Name) and value.id in imported or (
                        isinstance(value, ast.Attribute) and value.attr == symbol and
                        isinstance(value.value, ast.Name) and value.value.id in imported):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    imported.update(t.id for t in targets if isinstance(t, ast.Name))
        if imported == previous:
            break
    for node in ast.walk(tree):
        reason = None
        if isinstance(node, (ast.Global, ast.Nonlocal)) or (
                isinstance(node, ast.ImportFrom) and any(a.name == '*' for a in node.names)):
            reason = 'dynamic namespace or global/nonlocal declaration'
        elif (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in mutation_calls or
              isinstance(node, ast.Attribute) and node.attr in mutation_calls):
            # Reject the source reference before it can escape through aliases,
            # containers or default arguments. Scope/name conflation can suppress
            # harmless shadowed names; this pass only withdraws positive claims.
            reason = 'dynamic namespace mutation/introspection reference'
        elif isinstance(node, ast.Attribute) and node.attr == '__dict__':
            reason = 'explicit namespace dictionary access'
        elif isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.ctx, (ast.Store, ast.Del)):
            if (isinstance(node, ast.Attribute) and node.attr == '__class__' or
                    any(isinstance(n, ast.Name) and n.id in imported for n in ast.walk(node))):
                reason = 'possible generated class/module mutation'
        elif isinstance(node, ast.NamedExpr):
            # Includes annotations/defaults/decorators not visited by straight-line
            # expression evaluation. Runtime annotation evaluation varies by Python
            # version; no binding claim depends on that execution distinction.
            reason = 'assignment expression outside declared straight-line policy'
        if reason:
            return [], [dict(line=node.lineno, reason=reason + '; binding evidence disabled')]

    def evidence(node, value, kind):
        token = (ends.get((node.end_lineno, node.end_col_offset)) if isinstance(node, ast.Attribute)
                 else starts.get((node.lineno, node.col_offset)))
        if token is None:
            issues.append(dict(line=node.lineno, reason='exact source field token unavailable; no binding evidence'))
            return
        (line, column), (end_line, end_column) = token
        found.append(dict(line=line, column=column+1,
                          end_line=end_line, end_column=end_column+1,
                          kind=kind, binding='canonical', module=module, symbol=symbol,
                          evidence=value[1]))

    def expression(node, env):
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.Attribute):
            base = expression(node.value, env)
            if base:
                kind, chain = base
                if kind == 'module' and node.attr == symbol:
                    return ('class', chain + [dict(line=node.lineno, operation='generated message symbol')])
                if kind == 'instance' and node.attr == field:
                    evidence(node, base, 'field_access')
            return None
        if isinstance(node, ast.Call):
            # Recognize the parser only on the declared message class.
            parser = isinstance(node.func, ast.Attribute) and node.func.attr == 'FromString'
            value = expression(node.func.value if parser else node.func, env)
            for arg in node.args:
                expression(arg, env)
            for keyword in node.keywords:
                expression(keyword.value, env)
                if not parser and value and value[0] == 'class' and keyword.arg == field:
                    evidence(keyword, value, 'constructor_keyword')
            if value and value[0] == 'class':
                return ('instance', value[1] + [dict(line=node.lineno, operation='FromString' if parser else 'constructor')])
            return None
        # Comprehensions and lambdas introduce scopes or
        # dataflow not modeled here. Do not inspect them using the outer env.
        if isinstance(node, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for name in stored_names(node): env[name] = None
            issues.append(dict(line=node.lineno, reason='expression scope/dataflow unsupported'))
            return None
        for child in ast.iter_child_nodes(node):
            expression(child, env)
        return None

    def statements(body, env):
        for node in body:
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    name = alias.asname or alias.name
                    env[name] = ('class', [dict(line=node.lineno, operation='from import', module=module, symbol=symbol)]) if node.level == 0 and node.module == module and alias.name == symbol else None
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split('.')[0]
                    # Dotted imports without an alias require a module namespace
                    # chain; leave those candidates until it is modeled.
                    env[name] = ('module', [dict(line=node.lineno, operation='module import', module=module)]) if alias.name == module and alias.asname else None
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = expression(node.value, env)
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        env[target.id] = (value[0], value[1] + [dict(line=node.lineno, operation='assignment', name=target.id)]) if value else None
                    else:
                        expression(target, env)
                        for name in stored_names(target): env[name] = None
            elif isinstance(node, (ast.Expr, ast.Return, ast.Raise, ast.Assert)):
                expression(node, env)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                env[node.name] = None
            else:
                # Branch/loop/exception/with/delete/augassign control flow cannot
                # create evidence here. Invalidate every possibly assigned name.
                for name in local_names([node]): env[name] = None
                issues.append(dict(line=node.lineno, reason='control flow unsupported for binding evidence'))
        return env

    # Only immutable top-level import names may enter function scopes. Imports
    # rebound elsewhere in module code are excluded regardless of source order.
    module_env = statements(tree.body, {})
    mutable = set()
    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            mutable.update(local_names([node]))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            mutable.add(node.name)
    globals_env = {name: value for name, value in module_env.items() if name not in mutable}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # Decorators/defaults can alter execution and mutate imported classes.
        if node.decorator_list:
            issues.append(dict(line=node.lineno, reason='decorated function unsupported'))
            continue
        env = dict(globals_env)
        for name in local_names(node.body): env[name] = None
        args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        args += [a for a in (node.args.vararg, node.args.kwarg) if a]
        for arg in args: env[arg.arg] = None
        statements(node.body, env)
    return sorted(found, key=lambda r: (r['line'], r['column'])), issues
