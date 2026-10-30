"""Language is a presentation/conversation setting, not a model input."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from amadeus import workflow

class Preferences(unittest.TestCase):
 def test_english_agent_keeps_scientific_context(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(workflow,'HOME',Path(tmp)),patch.object(workflow,'DB',Path(tmp)/'test.sqlite3'):
   workflow.init(None,recover=False)
   project=workflow.create({'title':'My original title','goal':'CsPbBr3 at 40 nmol'})
   project['ui_language']='en'
   original=project['task'].copy()
   with patch('amadeus.provider.chat',return_value={'content':'Here is the analysis.'}) as chat:
    workflow.converse(project,'Explain the available data.')
   prompt=chat.call_args.args[0][0]['content']
   self.assertIn('Reply in English',prompt)
   self.assertIn('40 nmol',prompt)
   self.assertEqual(project['task'],original)
   self.assertEqual(project['messages'][-1]['content'],'Here is the analysis.')
   report=workflow.export_report(project).decode()
   self.assertIn('/preferences.js',report)
   self.assertIn('/locale-en.js',report)

if __name__=='__main__':unittest.main()
