"""Kiểm lưu bằng chứng khi rút USB; không mở cổng thật hoặc cấp nguồn ESP."""
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import serial

from capture_ppg_trace import capture_trace


class Clock:
    value = 0

    def __call__(self):
        return self.value


class Port:
    def __init__(self, clock, lines=(), *, read_error=None, stop_error=False, open_error=False):
        self.clock = clock
        self.lines = iter(lines)
        self.read_error = read_error
        self.stop_error = stop_error
        self.open_error = open_error
        self.commands = []
        self.is_open = False
        self.closed = False

    def open(self):
        if self.open_error:
            raise serial.SerialException("Cannot configure port")
        self.is_open = True

    def reset_input_buffer(self):
        pass

    def write(self, value):
        self.commands.append(value)
        if value == b"q" and self.stop_error:
            raise serial.SerialException("WriteFile failed")
        return len(value)

    def readline(self):
        self.clock.value += 1
        try:
            return next(self.lines)
        except StopIteration:
            if self.read_error is not None:
                raise self.read_error
            return b""

    def close(self):
        self.is_open = False
        self.closed = True


class CaptureTests(unittest.TestCase):
    def run_capture(self, lines=(), **options):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        clock = Clock()
        port = Port(clock, lines, **options)
        details = capture_trace(Path(self.temporary.name), "FAKE", 10,
                                port_factory=lambda **_: port, clock=clock)
        meta = json.loads(Path(details["file"]).with_suffix(".json").read_text(encoding="utf-8"))
        return details, meta, port

    def test_complete_capture_preserves_values_and_ignores_config_secrets(self):
        details, meta, port = self.run_capture([
            b"[CONFIG] PASSWORD=do-not-store\n", b"[NET] wifi=1 mqtt=1\n",
            b"[PPG-RAW] t=100 red=90000 ir=100000\n",
            b"[PPG-RAW] t=120 red=90001 ir=100002\n", b"[PPG-TRACE] dropped=2\n",
        ])
        self.assertEqual(details["capture_status"], "complete")
        self.assertEqual(details["samples"], 2)
        self.assertEqual(details["max_interval_ms"], 20)
        self.assertEqual(details["trace_dropped"], 2)
        self.assertEqual(meta["diagnostics"], ["[NET] wifi=1 mqtt=1"])
        self.assertNotIn("do-not-store", json.dumps(meta))
        with Path(details["file"]).open(newline="", encoding="utf-8") as file:
            self.assertEqual(list(csv.reader(file))[1:], [["100", "90000", "100000"], ["120", "90001", "100002"]])
        self.assertEqual(port.commands, [b"p", b"q"])
        self.assertTrue(port.closed)

    def test_v2_preserves_aligned_motion_and_exposure_without_changing_raw_csv(self):
        details, meta, _ = self.run_capture([
            b"[PPG-RAW] t=100 red=90000 ir=100000 imu=98,1,0.1,0.2,1.0,0.0,0.1,-0.1 led=50,60,2\n",
            b"[PPG-OPT] redLed=50 irLed=60\n",
        ])
        self.assertEqual(details["motion_rows"], 1)
        with Path(details["motion_file"]).open(newline="", encoding="utf-8") as file:
            row = list(csv.DictReader(file))[0]
        self.assertEqual(row["imu_t_ms"], "98")
        self.assertEqual(row["valid"], "1")
        self.assertEqual(row["ir_led"], "60")
        self.assertEqual(row["exposure_generation"], "2")
        self.assertEqual(meta["diagnostics"], ["[PPG-OPT] redLed=50 irLed=60"])

    def test_unplug_saves_partial_raw_and_diagnostics(self):
        details, meta, port = self.run_capture([
            b"[PPG-DAQ] io=0\n", b"[PPG-RAW] t=40 red=1 ir=2\n",
        ], read_error=serial.SerialException("ClearCommError failed"))
        self.assertEqual(details["capture_status"], "interrupted")
        self.assertEqual(details["samples"], 1)
        self.assertEqual(meta["diagnostics"], ["[PPG-DAQ] io=0"])
        self.assertIn("ClearCommError", details["capture_error"]["message"])
        self.assertTrue(Path(details["file"]).exists())
        self.assertTrue(port.closed)

    def test_stop_failure_does_not_mask_original_disconnect(self):
        details, meta, port = self.run_capture([b"[PPG-RAW] t=40 red=1 ir=2\n"],
            read_error=serial.SerialException("ClearCommError failed"), stop_error=True)
        self.assertEqual(meta["samples"], 1)
        self.assertIn("ClearCommError", details["capture_error"]["message"])
        self.assertEqual(details["cleanup_errors"][0]["operation"], "stop_trace")
        self.assertTrue(port.closed)

    def test_open_failure_creates_interrupted_metadata_without_reset_retry(self):
        details, meta, port = self.run_capture(open_error=True)
        self.assertEqual(meta["capture_status"], "interrupted")
        self.assertEqual(details["samples"], 0)
        self.assertEqual(port.commands, [])
        self.assertTrue(port.closed)

    def test_user_interrupt_retains_partial_capture(self):
        details, meta, port = self.run_capture([b"[PPG-RAW] t=40 red=1 ir=2\n"], read_error=KeyboardInterrupt())
        self.assertEqual(details["capture_status"], "interrupted")
        self.assertEqual(meta["capture_error"]["type"], "KeyboardInterrupt")
        self.assertEqual(meta["samples"], 1)
        self.assertTrue(port.closed)

    def test_no_samples_is_not_reported_complete(self):
        details, meta, _ = self.run_capture()
        self.assertEqual(meta["capture_status"], "no_samples")
        self.assertIsNone(details["capture_error"])


if __name__ == "__main__":
    unittest.main()
