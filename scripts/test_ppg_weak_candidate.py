"""Kiểm HR yếu: ngoại lệ, mất dữ liệu, xác nhận và xung đột hai kênh."""
import unittest
from unittest.mock import patch

import numpy as np

from benchmark_ppg_weak import choose
from ppg_weak_candidate import ALGORITHMS, CONFIGURATIONS, Evaluator, robust_peaks, period_consensus


def wave(bpm=80):
    x = 100*np.sin(np.arange(400)*2*np.pi*bpm/3000)
    return np.column_stack((x, .7*x))


class CandidateTests(unittest.TestCase):
    def test_clean_rates_without_preferred_resting_rate(self):
        for bpm in (60, 80, 100, 150, 180):
            with self.subTest(bpm=bpm):
                evaluator = Evaluator()
                self.assertIsNone(evaluator(wave(bpm), 13000, 1, None)[0][ALGORITHMS[0]])
                value = evaluator(wave(bpm), 14000, 1, None)[0][ALGORITHMS[0]]
                self.assertIsNotNone(value)
                self.assertLess(abs(value-bpm), 2)

    def test_period_candidate_covers_rate_boundaries_and_harmonic(self):
        config = CONFIGURATIONS[1]
        for bpm in (40, 60, 80, 100, 150, 180, 200):
            for phase in (0., .6, 1.2):
                x = 100*np.sin(np.arange(400)*2*np.pi*bpm/3000+phase)
                result = period_consensus(x, config)
                self.assertTrue(result['usable'], (bpm, phase, result))
                self.assertLess(abs(result['bpm']-bpm), 2)
        phase = np.arange(400)*2*np.pi*48/3000
        result = period_consensus(100*(np.sin(phase)+1.3*np.sin(2*phase+.3)), config)
        self.assertTrue(result['usable'], result)
        self.assertLess(abs(result['bpm']-48), 2)

    def test_period_candidate_has_same_reset_and_conflict_rules(self):
        evaluator = Evaluator()
        evaluator(wave(), 13000, 1, None)
        self.assertIsNotNone(evaluator(wave(), 14000, 1, None)[0]['period_consensus'])
        self.assertIsNone(evaluator(None, 15000, 1, 80)[0]['period_consensus'])
        self.assertIsNone(evaluator(wave(), 16000, 1, None)[0]['period_consensus'])
        conflict = np.column_stack((wave(80)[:, 0], wave(130)[:, 0]))
        evaluator(conflict, 17000, 1, None)
        self.assertIsNone(evaluator(conflict, 18000, 1, None)[0]['period_consensus'])

    def test_one_extra_peak_does_not_veto_entire_window(self):
        # Sóng 80bpm; một đỉnh sai tạo hai RR ngắn. Không tạo lại đỉnh bị thiếu.
        peaks = np.array([9, 47, 84, 122, 159, 197, 234, 272, 309, 347, 384])
        contaminated = np.sort(np.append(peaks, 215))
        with patch('ppg_weak_candidate.detect', return_value=(contaminated, np.array([]))):
            result = robust_peaks(wave()[:, 0], CONFIGURATIONS[0])
        self.assertTrue(result['usable'], result)
        self.assertLess(result['intervals_used'], result['intervals_total'])
        self.assertLess(abs(result['bpm']-80), 2)

    def test_no_forward_fill_after_missing_or_invalid_window(self):
        for invalid in (None, np.zeros((399, 2)), np.full((400, 2), np.nan), np.ones((400, 2))):
            with self.subTest(invalid=str(type(invalid))):
                evaluator = Evaluator()
                evaluator(wave(), 13000, 1, None)
                self.assertIsNotNone(evaluator(wave(), 14000, 1, None)[0][ALGORITHMS[0]])
                self.assertIsNone(evaluator(invalid, 15000, 1, 80)[0][ALGORITHMS[0]])
                self.assertIsNone(evaluator(wave(), 16000, 1, None)[0][ALGORITHMS[0]])

    def test_boot_gap_and_duplicate_time_require_new_confirmation(self):
        for now, segment in ((14000, 2), (15001, 1), (13000, 1), (12000, 1)):
            evaluator = Evaluator()
            evaluator(wave(), 13000, 1, None)
            self.assertIsNone(evaluator(wave(), now, segment, None)[0][ALGORITHMS[0]])

    def test_two_good_channels_disagree(self):
        values = np.column_stack((wave(80)[:, 0], wave(130)[:, 0]))
        evaluator = Evaluator()
        evaluator(values, 13000, 1, None)
        prediction, diagnostic = evaluator(values, 14000, 1, None)
        self.assertIsNone(prediction[ALGORITHMS[0]])
        self.assertTrue(diagnostic[ALGORITHMS[0]]['conflict'])

    def test_flat_channel_does_not_invent_second_measurement(self):
        values = wave()
        values[:, 1] = 0
        evaluator = Evaluator()
        evaluator(values, 13000, 1, None)
        result = evaluator(values, 14000, 1, None)[0][ALGORITHMS[0]]
        self.assertIsNotNone(result)
        self.assertLess(abs(result-80), 2)

    def test_empty_reference_cannot_be_selected_as_accurate(self):
        result = choose([])
        self.assertIsNone(result['selected_for_new_simulation'])
        self.assertIsNone(result['candidates'][ALGORITHMS[0]]['reference']['mae'])

    def test_noise_and_new_large_errors_veto_selection(self):
        def row(base, candidate, reference=80.):
            return {'reference_bpm': reference, 'predictions': {
                'current_cpp': base, **{name: candidate for name in ALGORITHMS}}}

        records = [
            {'category': 'BIDMC_seen_regression', 'rows': [row(80, 80), row(None, 80)]},
            {'category': 'SYNTHETIC_clean', 'rows': [row(80, 80)]},
            {'category': 'SYNTHETIC_weak_pulse', 'rows': [row(None, 80)]},
            {'category': 'SYNTHETIC_noise', 'expected_no_pulse': True, 'rows': [row(None, None, None)]},
        ]
        self.assertIsNotNone(choose(records)['selected_for_new_simulation'])
        records[-1]['rows'] = [row(None, 80, None)]
        self.assertIsNone(choose(records)['selected_for_new_simulation'])
        records[-1]['rows'] = [row(None, None, None)]
        records[2]['rows'] = [row(None, 160)]
        self.assertIsNone(choose(records)['selected_for_new_simulation'])


if __name__ == '__main__':
    unittest.main()
