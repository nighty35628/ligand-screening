import unittest
from unittest.mock import patch
from amadeus import data_engine as d

class DataEngineTests(unittest.TestCase):
    def test_units_preserve_original(self):
        raw={'columns':['v','c'],'rows':[{'v':10,'c':100}]}
        new,log=d.normalize(raw,[{'column':'v','output':'amount','operation':'amount_nmol','concentration_column':'c'}])
        self.assertEqual(new['rows'][0]['amount'],1);self.assertNotIn('amount',raw['rows'][0]);self.assertEqual(log[0]['new'],1)
    def test_role_filter(self):
        ds={'columns':['id','role'],'rows':[{'id':'a','role':'sample'},{'id':'b','role':'blank'}]}
        new,log=d.normalize(ds,[{'operation':'keep_samples'}]);self.assertEqual([r['id'] for r in new['rows']],['a']);self.assertEqual(log[0]['excluded'],['b'])
    def test_extraction_rejects_unmatched_evidence(self):
        response={'content':'{"records":[{"values":{"id":"A","temperature":25,"yield":0.9},"evidence":{"temperature":"25 C","yield":"invented quote"}}]}'}
        with patch('amadeus.provider.chat',return_value=response):draft=d.extract('Sample A at 25 C','test')
        self.assertNotIn('yield',draft['records'][0]['values']);self.assertEqual(len(draft['issues']),1)
    def test_no_supported_records(self):
        with patch('amadeus.provider.chat',return_value={'content':'{"records":[]}'}):
            with self.assertRaises(ValueError):d.extract('No experimental values','test')
    def test_quantum_yield_reference_identity(self):
        x={'reference_yield':.8,'sample_integral':100,'reference_integral':100,'sample_absorbance':.05,'reference_absorbance':.05,'sample_refractive_index':1.4,'reference_refractive_index':1.4}
        self.assertAlmostEqual(d.plqy(x)['calculated_plqy'],.8)
        x['sample_absorbance']=0
        with self.assertRaises(ValueError):d.plqy(x)

if __name__=='__main__':unittest.main()
