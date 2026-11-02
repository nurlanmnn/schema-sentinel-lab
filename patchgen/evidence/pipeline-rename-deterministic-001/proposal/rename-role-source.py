"""Prompt 2.7: syntax-role names and all-or-none token coverage per edited line.

This constrains a model proposal; it is not receiver/type or semantic resolution.
"""
import json
import re
from patchgen.detector import detect
from tree_sitter import Language, Parser
from patchgen.locator import FACTORIES, walk
from patchgen.rename_tokens import inventory as base_inventory, make_prompt as base_prompt, resolve as base_resolve
from patchgen.generator import ContractError, require


def inventory(case, file):
    tokens = base_inventory(case, file)
    if file['language'] != 'typescript':
        return tokens
    raw = file['source_context'].encode()
    tree = Parser(Language(FACTORIES['typescript']())).parse(raw)
    nodes = {(n.start_byte, n.end_byte): n for n in walk(tree.root_node)
             if n.type in ('identifier', 'property_identifier', 'string', 'string_literal')}
    def text(node):
        return raw[node.start_byte:node.end_byte].decode() if node else ''
    change = case['change']
    event = detect(change['old_schema'], change['new_schema'], change['schema_path'],
                   case['source_revision'], change['id'], case['intended_behavior'])['events'][0]
    canonical = event['new_name']
    if not re.fullmatch(r'[a-z][a-z0-9]*(?:_[a-z][a-z0-9]*)*', canonical):
        raise ContractError('unsupported descriptor naming convention')
    for token in tokens:
        node = nodes[(token['start_byte'], token['end_byte'])]
        parent = node.parent
        role = None
        if parent.type == 'member_expression' and parent.child_by_field_name('property') == node:
            role = 'generated_property'
        elif parent.type == 'pair' and parent.child_by_field_name('key') == node:
            obj = parent.parent
            args = obj.parent
            if args.type == 'arguments' and args.parent.type == 'call_expression':
                function = args.parent.child_by_field_name('function')
                if function and function.type == 'member_expression' and text(function.child_by_field_name('property')) == 'encode':
                    role = 'generated_construction_key'
            else:
                value = parent.child_by_field_name('value')
                ancestor = obj
                while ancestor and ancestor.type not in ('variable_declarator', 'program'):
                    ancestor = ancestor.parent
                if (ancestor and ancestor.type == 'variable_declarator'
                        and text(ancestor.child_by_field_name('name')) == 'fields'
                        and value.type == 'member_expression'
                        and text(value.child_by_field_name('property')) == token['text']):
                    # Explicit testbed policy: fields observation keys use canonical names.
                    if 'Runtime observation key becomes' in case['intended_behavior']:
                        role = 'canonical_observation_key'
        if role is None:
            raise ContractError(f'unsupported TypeScript rename syntax role on line {token["line"]}')
        # snake_case is the descriptor name; camelCase is the generated TS spelling.
        parts = canonical.split('_')
        camel = parts[0] + ''.join(p[:1].upper() + p[1:] for p in parts[1:])
        token['allowed'] = [canonical if role == 'canonical_observation_key' else camel]
        token['role'] = role
    return tokens


def make_prompt(case, file):
    messages, _ = base_prompt(case, file)
    tokens = inventory(case, file)
    payload = json.loads(messages[1]['content'])
    payload['prompt_version'] = '2.7'
    payload['syntax_tokens'] = [{k:v for k,v in t.items() if k not in ('start_byte','end_byte')} for t in tokens]
    messages[0]['content'] += '\nEach token now has one role-constrained allowed replacement. On each line marked edit, select ALL inventory tokens on that line. Mixed affected/unaffected tokens on one line are unsupported; request clarification instead. A line marked unaffected must select NO tokens. Never omit a canonical observation-key token.'
    messages[1]['content'] = json.dumps(payload, indent=2)
    return messages, tokens


def resolve(source, value, tokens, positions):
    # Validate ids/reviews and dispositions before enforcing stricter completeness.
    updated = base_resolve(source, value, tokens, positions)
    selected = {e['token_id'] for e in require(value, 'token_edits', list, 'file_response')}
    for review in require(value, 'candidate_reviews', list, 'file_response'):
        on_line = {t['token_id'] for t in tokens if t['line'] == review['line']}
        if review['decision'] == 'edit' and (not on_line or not on_line <= selected):
            raise ContractError('edited candidate line requires all rename tokens; mixed roles unsupported')
    return updated


def propose(case, output):
    """Explicit deterministic proposal, separate from model attempts and answers.

    Every located candidate token is proposed for rename. Receiver identity remains
    an assumption for validation/review; no model inference or success is claimed.
    """
    from patchgen.generator import save, unified_diff, validate_output
    diff = unified_diff(case['change']['schema_path'], case['change']['old_schema'], case['change']['new_schema'])
    for index, file in enumerate(case['affected_files'], 1):
        tokens = inventory(case, file)
        value = dict(outcome='patch', token_edits=[dict(token_id=t['token_id'], replacement=t['allowed'][0]) for t in tokens],
                     candidate_reviews=[dict(line=line, decision='edit', reason='Explicit deterministic all-candidate rename policy; receiver identity unproved')
                                        for line in sorted({line for p in file['positions'] for line in range(p['start_line'],p['end_line']+1)})],
                     rationale='Descriptor-derived syntax-token rename proposal', confidence=0,
                     assumptions=['All located candidates refer to the renamed field; validate and review this assumption.'])
        directory = output/'deterministic'/f'{index:02d}'
        save(directory/'token-inventory.json', tokens)
        save(directory/'proposal.json', value)
        updated = resolve(file['source_context'], value, tokens, file['positions'])
        diff += unified_diff(file['path'], file['source_context'], updated)
    save(output/'assembly.json', dict(strategy='deterministic_rename_roles', model_requests=0, automatic_repairs=0,
                                    schema_origin='supplied new_schema, copied by host',
                                    policy='propose every located token; receiver identity unproved'))
    return validate_output(dict(contract_version='1.0', outcome='patch', diff=diff,
                               rationale='Deterministic descriptor/syntax-role proposal; independent validation and human review required.',
                               confidence=0, assumptions=['Confidence is not estimated; zero is a placeholder, not a calibrated probability.',
                                                         'All candidate tokens refer to the target field; receiver identity is unproved.']))
