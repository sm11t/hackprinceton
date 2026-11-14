import unittest
from decision_context import attach_context

class ContextTests(unittest.TestCase):
    def test_gate_and_evidence_survive_model_like_assumptions(self):
        row = dict(fact='scan_address', value=None, source='costar', source_id='x', captured_at=None,
                   confidence=.1, evidence_url=None, status='conflict', needs_human=True, note='Mismatch')
        report = dict(property_id=1, requested_suite='A', scope_label='Suite A', proposed_use='fitness studio',
                      ownership='lease', identity={'records':[row]}, eligibility={'status':'blocked'}, space=None)
        result = attach_context(report, {'starting_cash':10})['decision_context']
        self.assertEqual(result['gates']['eligibility'],'blocked')
        self.assertEqual(result['conflicts'],[row])
        self.assertEqual(result['cash_budget'],10)
        self.assertIsNone(result['evidence'][0]['captured_at'])
    def test_attachment_date_not_camera_capture(self):
        row=dict(fact='ceiling_height_ft', value=18,source='matterport',source_id='s',captured_at='2026-01-01',confidence=.5,evidence_url=None,status='unknown',needs_human=True,note='Height')
        report=dict(property_id=1,requested_suite=None,scope_label='building',proposed_use='fitness studio',ownership='lease',identity={'records':[row]},eligibility={'status':'conditional'},space=None)
        c=attach_context(report,{})['decision_context']['evidence'][0]
        self.assertIsNone(c['captured_at'])
        self.assertEqual(c['attachment_date'],'2026-01-01')
