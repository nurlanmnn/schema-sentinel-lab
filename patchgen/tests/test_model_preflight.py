"""Model support cannot silently download weights or route to a remote provider."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from patchgen.generator import ContractError, LOCAL_MODELS, generate


class ModelPreflightTests(unittest.TestCase):
    def test_supported_but_missing_14b_stops_before_inference(self):
        self.assertIn('ministral-3:14b',LOCAL_MODELS)
        with tempfile.TemporaryDirectory() as tmp,patch('patchgen.generator.api',return_value={'models':[]}) as api:
            with self.assertRaisesRegex(ContractError,'model missing'):
                generate({},'ministral-3:14b','http://127.0.0.1:11434',Path(tmp))
            api.assert_called_once_with('http://127.0.0.1:11434','/api/tags')
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_cloud_remote_and_excluded_models_stop_without_api_calls(self):
        for model,endpoint in [('ministral-3:14b-cloud','http://127.0.0.1:11434'),
                               ('qwen3.5:9b','http://127.0.0.1:11434'),
                               ('ministral-3:14b','https://remote.example')]:
            with self.subTest(model=model,endpoint=endpoint),patch('patchgen.generator.api') as api:
                with self.assertRaises(ContractError):generate({},model,endpoint,Path('/unused'))
                api.assert_not_called()
