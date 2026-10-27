"""Exercise actual GUI callbacks with headless widget doubles; no printer commands."""
import ast,re,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
TREE=ast.parse((Path(__file__).parents[1]/'easycups/gui.py').read_text())
def callback(name):
 node=next(n for n in ast.walk(TREE) if isinstance(n,ast.FunctionDef) and n.name==name)
 env={'re':re,'Adw':SimpleNamespace(ActionRow=lambda **kw:kw)}
 exec(compile(ast.Module(body=[node],type_ignores=[]),'gui.py','exec'),env);return env[name]
class Results(unittest.TestCase):
 def test_discovery_failure_is_error_and_preserves_previous_results(self):
  state=SimpleNamespace(fail=Mock(),toast=Mock(),drow=['old'],dg=Mock())
  callback('found')(state,(False,'cups unavailable'))
  state.fail.assert_called_once();state.toast.assert_not_called();self.assertEqual(state.drow,['old'])
 def test_failed_queue_never_displays_empty_queue(self):
  state=SimpleNamespace(qrow=['old'],qg=Mock())
  callback('qfill')(state,(False,'connection refused'))
  self.assertEqual(len(state.qrow),1);self.assertIn('Não foi possível',state.qrow[0]['title']);self.assertIn('refused',state.qrow[0]['subtitle'])
