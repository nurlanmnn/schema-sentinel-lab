"""Decimal representation, binding and candidate-role constraints."""
import copy
import json
from pathlib import Path
import subprocess
import unittest
from patchgen.generator import ContractError, load_validation_profile
from patchgen.inventory_width import target, transform, propose

ROOT = Path(__file__).resolve().parents[2]


def fixture():
    case = json.loads((ROOT/'patchgen/fixtures/inventory-quantity-width/runtime-input.json').read_text())
    case['affected_files'] = [dict(path=path,language=language,source_context=subprocess.check_output(
        ['git','show',case['source_revision']+':'+path],cwd=ROOT,text=True),
        positions=[dict(start_line=n,end_line=n,reason='authored test') for n in lines])
        for path, language, lines in [('runtimes/python/inventory_runtime.py','python',[10,11,12]),
                                     ('runtimes/typescript/inventory.ts','typescript',[4,9,10,11]),
                                     ('runtimes/csharp/Inventory.cs','csharp',[13,14,15,20])]]
    return case


class InventoryWidthTests(unittest.TestCase):
    def test_exact_constructor_changes_and_preserved_observations(self):
        case = fixture();target(case)
        profile, patch = load_validation_profile(case, 'inventory-quantity-width')
        self.assertEqual(profile['inventory_case'], 'width');self.assertEqual(patch, '')
        for file in case['affected_files']:
            actual, evidence = transform(file)
            expected = file['source_context']
            if file['language'] == 'typescript':
                expected = expected.replace('Number.parseInt(request.quantity, 10)', 'request.quantity')
            if file['language'] == 'csharp':
                expected = expected.replace('int.Parse(request.Quantity', 'long.Parse(request.Quantity')
            self.assertEqual(actual, expected)
            self.assertEqual(len(evidence['edits']), 0 if file['language'] == 'python' else 1)

    def test_zigzag_proposes_the_authored_schema_only_patch(self):
        from tempfile import TemporaryDirectory
        name = 'inventory-quantity-zigzag'
        case = fixture()
        request = json.loads((ROOT/'patchgen/fixtures'/name/'runtime-input.json').read_text())
        case.update(request)
        profile, test_patch = load_validation_profile(case, name)
        self.assertEqual(profile['inventory_case'], 'zigzag')
        self.assertEqual(test_patch, '')
        with self.assertRaises(ContractError):
            load_validation_profile(case, 'inventory-quantity-width')
        with TemporaryDirectory() as tmp:
            proposal = propose(case, Path(tmp), 'zigzag')
        self.assertEqual(proposal['diff'], (ROOT/'patchgen/reference'/name/'expected.patch').read_text())

    def test_unknown_policy_type_cardinality_and_optional_rejected(self):
        case = fixture()
        for kind in ('policy', 'unsigned', 'repeated', 'optional'):
            wrong = copy.deepcopy(case)
            if kind == 'policy':wrong['intended_behavior'] = 'Use JSON numbers.'
            elif kind == 'unsigned':wrong['change']['new_schema'] = wrong['change']['new_schema'].replace('int64', 'uint64')
            else:wrong['change']['new_schema'] = wrong['change']['new_schema'].replace('int64', kind+' int64')
            with self.subTest(kind=kind),self.assertRaises(ContractError):target(wrong)

    def test_predicate_observation_and_binding_drift_rejected(self):
        case = fixture()
        for file in case['affected_files']:
            for mutation in ('predicate', 'binding', 'missing'):
                wrong = copy.deepcopy(file)
                if mutation == 'predicate':wrong['source_context'] = wrong['source_context'].replace(' > 0', ' >= 0')
                elif mutation == 'binding':wrong['source_context'] = wrong['source_context'].replace('StockItem', 'OtherStockItem')
                else:wrong['positions'] = [p for p in wrong['positions'] if p['start_line'] != {'python':10,'typescript':9,'csharp':13}[file['language']]]
                with self.subTest(language=file['language'],mutation=mutation),self.assertRaises(ContractError):transform(wrong)

    def test_number_input_or_observation_rejected(self):
        file = fixture()['affected_files'][1]
        for old,new in [('quantity: string','quantity: number'),('entity.quantity.toString()', 'Number(entity.quantity)')]:
            wrong = copy.deepcopy(file);wrong['source_context'] = wrong['source_context'].replace(old,new)
            with self.assertRaises(ContractError):transform(wrong)


if __name__ == '__main__':
    unittest.main()

class InventoryReviewTests(unittest.TestCase):
    def test_review_rejects_missing_policy_and_changed_runtime_evidence(self):
        import tempfile
        import shutil
        from patchgen.review import check_host_evidence, ARTIFACTS
        source = ROOT/'patchgen/evidence/pipeline-inventory-width-002'
        report = json.loads((source/'proposal/report.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            for name in ARTIFACTS:
                path = source/name
                if path.is_file():
                    destination = target/name;destination.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(path,destination)
            check_host_evidence(target, report)
            policy = target/'proposal/inventory-width-source.py'
            content = policy.read_bytes();policy.unlink()
            with self.assertRaises(ContractError):check_host_evidence(target, report)
            policy.write_bytes(content)
            evidence = target/'proposal/inventory/typescript.json'
            record = json.loads(evidence.read_text());values = json.loads(record['stdout'])
            values[12]['fields']['quantity'] = str(1 << 53)
            record['stdout'] = json.dumps(values);evidence.write_text(json.dumps(record))
            with self.assertRaises(ContractError):check_host_evidence(target, report)
