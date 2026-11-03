"""Bounded Python import/constructor evidence under an explicit binding policy.

This is static source evidence, assuming declared generated modules have their
standard Protobuf API. It is not runtime import validation or whole-program proof.
Unrecognized expressions never acquire a message type. Branches and nested scopes
are deliberately not followed; lexical candidates remain available in the locator.
"""
import ast

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
            if isinstance(item, (ast.Import, ast.ImportFrom)):
                result.update(alias.asname or alias.name.split('.')[0] for alias in item.names)
            if isinstance(item, ast.ExceptHandler) and item.name:
                result.add(item.name)
    return result


def references(text, field, module, symbol):
    """Return bound field tokens and limitations; retain no negative type claims."""
    tree = ast.parse(text)
    found, issues = [], []
    namespace_mutations = []
    # A wildcard, namespace mutation or declaration outside our lexical model
    # disables evidence for the file. It does not suppress lexical candidates.
    hazards = (ast.Global, ast.Nonlocal)
    if any(isinstance(n, hazards) or
           isinstance(n, ast.ImportFrom) and any(a.name == '*' for a in n.names) or
           isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ('exec', 'eval', 'globals', 'locals', 'setattr', 'delattr')
           for n in ast.walk(tree)):
        return [], ['dynamic namespace mutation or global/nonlocal declaration; binding evidence disabled']

    def evidence(node, value, kind):
        found.append(dict(line=node.lineno, column=node.col_offset + 1,
                          end_line=node.end_lineno, end_column=node.end_col_offset + 1,
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
        # Comprehensions, lambdas and assignment expressions introduce scopes or
        # dataflow not modeled here. Do not inspect them using the outer env.
        if isinstance(node, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.NamedExpr)):
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
                        if any(isinstance(n, ast.Attribute) and n.attr in ('__class__', '__dict__') for n in ast.walk(target)) or any(isinstance(n, ast.Name) and env.get(n.id) and env[n.id][0] in ('module', 'class') for n in ast.walk(target)):
                            namespace_mutations.append(target.lineno)
                        expression(target, env)
                        for name in stored_names(target): env[name] = None
            elif isinstance(node, (ast.Expr, ast.Return, ast.Raise, ast.Assert)):
                expression(node, env)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                env[node.name] = None
            else:
                # Branch/loop/exception/with/delete/augassign control flow cannot
                # create evidence here. Invalidate every possibly assigned name.
                for child in ast.walk(node):
                    if isinstance(child, ast.Attribute) and isinstance(child.ctx, (ast.Store, ast.Del)) and any(
                            isinstance(n, ast.Name) and env.get(n.id) and env[n.id][0] in ('module', 'class') for n in ast.walk(child)):
                        namespace_mutations.append(child.lineno)
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
    if namespace_mutations:
        return [], issues + [dict(line=line, reason='generated class/module mutation; binding evidence disabled') for line in sorted(set(namespace_mutations))]
    return sorted(found, key=lambda r: (r['line'], r['column'])), issues
