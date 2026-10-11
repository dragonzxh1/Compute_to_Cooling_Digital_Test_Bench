import unittest
from .state_copy import native_copy, clone_qualifier
from .observer import observe
from .common import read
from .engine import SplitEngine


class StateCopyTests(unittest.TestCase):
    def test_aliases_and_no_sharing(self):
        shared={'x':[1]}; source=[shared,shared]; copied=native_copy(source)
        self.assertIs(copied[0],copied[1]);self.assertIsNot(copied[0],shared)
        copied[0]['x'].append(2);self.assertEqual(shared['x'],[1])

    def test_qualified_state_exact(self):
        e=SplitEngine(read('phase5_r5_2_2_fixture_tracking_profile.json'),
                      read('phase5_r5_2_silent_tracking_fault_registration.json')['classifier'])
        cloned=clone_qualifier(e.q)
        self.assertEqual(observe(cloned),observe(e.q))
        cloned.response_history.append({'test':1});self.assertFalse(e.q.response_history)

    def test_unknown_type_rejected(self):
        with self.assertRaises(TypeError):native_copy(object())


if __name__=='__main__':unittest.main()

