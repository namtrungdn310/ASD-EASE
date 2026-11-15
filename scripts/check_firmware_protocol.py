"""Chạy core/serializer C++ thật và kiểm tra gói bằng schema backend runtime."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from firmware_native import NativeFirmware
from app.schemas.control import Ack, Presence, StateRequest, StateResponse
from app.schemas.ingestion import InboundTelemetry


class FirmwareProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = NativeFirmware()

    @classmethod
    def tearDownClass(cls):
        cls.native.close()

    def setUp(self):
        self.call("init", device_id="SYN-FIRMWARE", data_origin="SYNTHETIC")
        self.call("connect")
        self.sync()

    def call(self, operation, now=0, **values):
        result = self.native.call(operation, now, **values)
        if result.get("will"):
            Presence.model_validate(result["will"])
        for packet in result.get("out", []):
            model = {"ack": Ack, "state/request": StateRequest, "presence": Presence}[packet["suffix"]]
            model.model_validate(packet["payload"])
            self.assertLessEqual(len(json.dumps(packet["payload"]).encode()), 4096)
            self.assertEqual(packet["qos"], 1)
            self.assertEqual(packet["retain"], packet["suffix"] == "presence")
        if "telemetry" in result:
            InboundTelemetry.model_validate(result["telemetry"])
        return result

    def sync(self, now=0, state="IDLE", accepted=None, session=None, generation=0, pending=None, error=None):
        result = self.call("tick", now)
        self.request = next(packet["payload"] for packet in result["out"] if packet["suffix"] == "state/request")
        self.response = {key: self.request[key] for key in ("control_version", "device_id", "data_origin", "boot_id", "connection_id", "request_id")}
        self.response.update(message_type="STATE_RESPONSE", session_id=session, state=state, generation=generation,
                             accepted_command_id=accepted, pending_command=pending, error_code=error)
        StateResponse.model_validate(self.response)
        return self.call("receive", now, suffix="state/response", payload=self.response)

    def command(self, now=10, generation=1, action="START", **changes):
        command = {key: self.request[key] for key in ("control_version", "device_id", "data_origin", "boot_id", "connection_id", "request_id")}
        command.update(message_type="COMMAND", command_id=f"CMD-{generation}", generation=generation, session_id="SESSION-NATIVE", action=action,
                       expires_in_ms=30000, acquisition_profile={"ppg_hz":50,"imu_hz":50,"gsr_hz":20,"window_ms":1000} if action == "START" else None)
        command.update(changes)
        self.last_command = command
        return self.call("receive", now, suffix="command", payload=command)

    def confirm_start(self, now=11):
        return self.sync(now, state="RECORDING", session="SESSION-NATIVE", accepted="CMD-1", generation=1)

    def fresh_snapshot(self, **changes):
        return {"hr":78.5,"hr_valid":True,"hr_age":100,"ppg_age":0,"gsr_adc":1800,"gsr_readable":True,
                "gsr_valid":True,"gsr_age":0,"imu_age":0,"gsr_percent":13.0,"gsr_baseline":2.0, **changes}

    def test_idle_live_requires_state_confirmation(self):
        telemetry = self.call("telemetry", 10, snapshot=self.fresh_snapshot())["telemetry"]
        self.assertIsNone(telemetry["session_id"])
        self.assertEqual(telemetry["timestamp_ms"], 10)
        self.call("disconnect")
        self.assertFalse(self.call("telemetry", 11, snapshot=self.fresh_snapshot())["accepted"])

    def test_start_requires_application_confirmation(self):
        result = self.command()
        self.assertEqual(result["state"], "RECORDING")
        self.assertFalse(result["authorized"])
        self.assertFalse(self.call("telemetry", 10, snapshot=self.fresh_snapshot())["accepted"])
        self.assertTrue(self.confirm_start()["authorized"])
        frame = self.call("telemetry", 1010, snapshot=self.fresh_snapshot())["telemetry"]
        self.assertEqual(frame["timestamp_ms"], 1000)
        self.assertEqual(frame["session_id"], "SESSION-NATIVE")

    def test_duplicate_start_does_not_reset_epoch(self):
        self.command()
        first = copy.deepcopy(self.last_command)
        result = self.call("receive", 100, suffix="command", payload=first)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["starts"], 1)
        self.assertEqual(result["epoch"], 10)

    def test_changed_profile_same_id_is_conflict(self):
        self.command()
        conflict = copy.deepcopy(self.last_command)
        conflict["acquisition_profile"]["ppg_hz"] = 100
        result = self.call("receive", 20, suffix="command", payload=conflict)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["error"], "COMMAND_CONFLICT")
        self.assertEqual(result["starts"], 1)

    def test_unsupported_profile_rejected_without_epoch(self):
        result = self.command(acquisition_profile={"ppg_hz":100,"imu_hz":50,"gsr_hz":20,"window_ms":1000})
        self.assertEqual(result["state"], "IDLE")
        self.assertEqual(result["starts"], 0)
        self.assertEqual(result["out"][0]["payload"]["reason"], "PROFILE_UNSUPPORTED")

    def test_stop_before_start_confirmation(self):
        self.command()
        first = copy.deepcopy(self.last_command)
        result = self.command(now=20, generation=2, action="STOP")
        self.assertEqual(result["state"], "STOPPED")
        ack = result["out"][0]["payload"]
        self.assertEqual(ack["result"], "STOPPED")
        self.assertFalse(ack["final_summary"]["raw_recording_enabled"])
        self.assertEqual(ack["timestamp_ms"], 0)
        late = self.call("receive", 21, suffix="command", payload=first)
        self.assertEqual(late["state"], "STOPPED")
        self.assertEqual(late["starts"], 1)

    def test_reconnect_keeps_epoch_and_rewraps_ack(self):
        self.command(); self.confirm_start()
        self.call("disconnect")
        self.call("connect", 100, connection_id="CONN-NEW")
        result = self.sync(100, "RECORDING", "CMD-1", "SESSION-NATIVE", 1)
        self.assertTrue(result["authorized"])
        self.assertEqual(result["epoch"], 10)
        self.assertEqual(self.request["last_ack"]["connection_id"], "CONN-NEW")
        self.assertEqual(self.request["last_ack"]["request_id"], self.request["request_id"])

    def test_connection_nonce_changes_lwt(self):
        before = self.call("disconnect")["will"]
        after = self.call("connect", 10, connection_id="OTHER-CONNECTION")["will"]
        self.assertNotEqual(before["connection_id"], after["connection_id"])
        self.assertEqual(before["boot_id"], after["boot_id"])

    def test_reboot_has_no_recording_or_cached_start(self):
        self.command()
        self.call("init", boot_id="REBOOT", device_id="SYN-FIRMWARE", data_origin="SYNTHETIC")
        result = self.call("connect", connection_id="CONN-REBOOT")
        self.assertEqual(result["state"], "IDLE")
        self.assertEqual(result["starts"], 0)

    def test_wrong_command_identity_and_nonces(self):
        for field, value in (("device_id","OTHER"),("boot_id","OLD"),("connection_id","OLD"),("request_id","OLD"),("data_origin","DEVICE")):
            with self.subTest(field=field):
                result = self.command(**{field:value})
                self.assertFalse(result["accepted"])
                self.assertEqual(result["starts"], 0)

    def test_retained_command_never_executes(self):
        self.command(command_id="VALID")
        self.call("init", device_id="SYN-FIRMWARE", data_origin="SYNTHETIC")
        self.call("connect"); self.sync()
        result = self.call("receive", 10, suffix="command", payload=self.last_command, retain=True)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["starts"], 0)

    def test_lease_from_request_send_time_not_command_arrival(self):
        result = self.command(now=30000)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["starts"], 0)

    def test_duplicate_does_not_extend_lease(self):
        self.command(now=1, expires_in_ms=10)
        result = self.call("receive", 10, suffix="command", payload=self.last_command)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["epoch"], 1)

    def test_strict_json_and_control_numbers(self):
        for invalid in (True, "1", 1.0, 0, 2**53):
            result = self.command(generation=invalid, command_id="BAD")
            self.assertFalse(result["accepted"], invalid)
        self.command(command_id="GOOD")
        wire = json.dumps(self.last_command)
        for bad in ('{"x":1,"x":2}', wire[:-1]+',"generation":1}', '{"x":NaN}', '{"x":Infinity}', '['*10+'0'+']'*10, ' '*4097, wire+'junk', wire+'{}'):
            result = self.call("receive", 11, suffix="command", wire=bad)
            self.assertFalse(result["accepted"])

    def test_unknown_control_field_rejected(self):
        self.assertFalse(self.command(debug=True)["accepted"])

    def test_stale_samples_and_snapshot_waiting_are_null(self):
        snapshot = self.fresh_snapshot(captured_at_ms=0)
        frame = self.call("telemetry", 1001, snapshot=snapshot)["telemetry"]
        self.assertIsNone(frame["hr_bpm"])
        self.assertIsNone(frame["gsr"]["raw"])
        self.assertIsNone(frame["gsr"]["delta"])

    def test_hr_uses_actual_beat_age(self):
        frame = self.call("telemetry", 10, snapshot=self.fresh_snapshot(hr_age=3001))["telemetry"]
        self.assertIsNone(frame["hr_bpm"])
        for value in (0, 19, 241):
            self.assertIsNone(self.call("telemetry", 10, snapshot=self.fresh_snapshot(hr=value))["telemetry"]["hr_bpm"])

    def test_gsr_ratio_baseline_and_quality_no_fabrication(self):
        frame = self.call("telemetry", 10, snapshot=self.fresh_snapshot())["telemetry"]
        self.assertAlmostEqual(frame["gsr"]["delta"], .13, places=5)
        self.assertEqual(frame["signal_quality"], {"ppg":0,"gsr":0,"imu":0})
        self.assertIsNone(frame["movement"]["score"])
        self.assertIsNone(frame["prediction"]["probability"])
        self.assertEqual(frame["prediction"]["state"], "UNCERTAIN")
        self.assertIsNone(self.call("telemetry", 10, snapshot=self.fresh_snapshot(gsr_baseline=.01))["telemetry"]["gsr"]["delta"])

    def test_only_gsr_imu_calibration_maps_calibrating(self):
        frame = self.call("telemetry", 10, snapshot=self.fresh_snapshot(gsr_calibrating=True))["telemetry"]
        self.assertEqual(frame["prediction"]["state"], "CALIBRATING")

    def test_periodic_sync_and_backend_silence_expire_authorization(self):
        self.assertTrue(self.call("tick", 15000)["out"])
        self.assertFalse(self.call("telemetry", 30001, snapshot=self.fresh_snapshot())["accepted"])

    def test_uint64_epoch_across_millis_rollover(self):
        self.call("disconnect"); self.call("connect", 2**32-10)
        self.sync(2**32-10)
        self.command(now=2**32-5)
        self.confirm_start(2**32-4)
        frame = self.call("telemetry", 2**32+10, snapshot=self.fresh_snapshot())["telemetry"]
        self.assertEqual(frame["timestamp_ms"], 15)

    def test_pending_command_and_direct_topic_execute_once(self):
        self.command()
        command = copy.deepcopy(self.last_command)
        self.response.update(pending_command=command)
        result = self.call("receive", 11, suffix="state/response", payload=self.response)
        self.assertEqual(result["starts"], 1)

    def test_aborted_backend_state_stops_unconfirmed_recording(self):
        self.command()
        result = self.sync(11, state="ABORTED", session="SESSION-NATIVE", generation=1, error="COMMAND_TIMEOUT")
        self.assertEqual(result["state"], "STOPPED")
        self.assertFalse(result["authorized"])

    def test_unknown_accepted_command_never_authorizes_recording(self):
        self.command()
        result = self.sync(11, state="RECORDING", session="SESSION-NATIVE", accepted="WRONG", generation=1)
        self.assertFalse(result["authorized"])

    def test_old_state_response_nonce_is_rejected(self):
        old = copy.deepcopy(self.response)
        self.sync(15000)
        result = self.call("receive", 15001, suffix="state/response", payload=old)
        self.assertFalse(result["accepted"])

    def test_backend_generation_cannot_move_backwards(self):
        self.command(); self.confirm_start()
        bad = copy.deepcopy(self.response)
        bad["generation"] = 0
        self.assertFalse(self.call("receive", 12, suffix="state/response", payload=bad)["accepted"])

    def test_burst_has_bounded_control_queue(self):
        self.command()
        result = self.call("burst", 11, payload=self.last_command)
        self.assertEqual(result["starts"], 1)
        self.assertEqual(len(result["out"]), 8)
        self.assertGreaterEqual(result["dropped"], 12)
        self.assertLessEqual(sum(len(json.dumps(p["payload"]).encode()) for p in result["out"]), 32768)

    def test_external_outbox_budget_is_counted(self):
        self.call("budget", count=8, bytes=32768)
        result = self.command()
        self.assertEqual(result["out"], [])
        self.assertEqual(result["starts"], 1)
        self.call("budget", count=0, bytes=0)
        result = self.call("tick", 11)
        self.assertEqual(result["out"][0]["payload"]["last_ack"]["result"], "STARTED")

    def test_recovered_aborted_device_can_send_outside_session(self):
        self.command()
        self.sync(11, state="ABORTED", session="SESSION-NATIVE", generation=1, error="COMMAND_TIMEOUT")
        self.sync(12, state="ABORTED", session="SESSION-NATIVE", generation=1)
        frame = self.call("telemetry", 13, snapshot=self.fresh_snapshot())["telemetry"]
        self.assertIsNone(frame["session_id"])

    def test_first_sync_preserves_backend_generation_floor(self):
        self.call("resync", 1)
        self.sync(1, state="STOPPED", generation=5)
        result = self.command(now=2, generation=1)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["starts"], 0)

    def motion_window(self, start=0, count=50, **axes):
        sample = {"ax": 0, "ay": 0, "az": 9.80665, "gx": 0, "gy": 0, "gz": 0, **axes}
        frames = [self.call("motion", start + index * 20, sample=sample) for index in range(count)]
        return frames

    def test_motion_stationary_warms_up_then_zero_in_any_orientation(self):
        for axes in ({}, {"ay": 9.80665, "az": 0}, {"az": -9.80665}):
            self.call("motion_reset")
            frames = self.motion_window(**axes)
            self.assertTrue(all(frame["telemetry"]["movement"]["score"] is None for frame in frames[:-1]))
            self.assertEqual(frames[-1]["telemetry"]["movement"]["score"], 0)

    def test_motion_acceleration_rotation_and_intensity_reach_runtime_schema(self):
        scores = []
        for axes in ({"az": 11.80665}, {"gx": 45}, {"gx": 90}, {"gx": -90}, {"gx": 180}):
            self.call("motion_reset")
            frame = self.motion_window(**axes)[-1]
            self.assertTrue(frame["motion"]["valid"])
            score = frame["telemetry"]["movement"]["score"]
            self.assertGreater(score, 0)
            self.assertLess(score, 1)
            scores.append(score)
        self.assertGreater(scores[2], scores[1])
        self.assertEqual(scores[2], scores[3])
        self.assertGreater(scores[4], scores[2])

    def test_motion_rotating_window_forgets_previous_activity(self):
        self.motion_window(gx=90)
        frames = self.motion_window(start=1000)
        self.assertGreater(frames[0]["motion"]["score"], 0)
        self.assertEqual(frames[-1]["motion"]["score"], 0)

    def test_motion_sensor_error_saturation_missing_axis_reset_window(self):
        for patch in ({"sensor_valid": False}, {"sample": {"ax": None}},
                      {"sample": {"ax": 0, "ay": 0, "az": 19.61, "gx": 0, "gy": 0, "gz": 0}},
                      {"sample": {"ax": 0, "ay": 0, "az": 9.80665, "gx": 250, "gy": 0, "gz": 0}}):
            self.call("motion_reset")
            self.motion_window()
            self.assertIsNone(self.call("motion", 1000, **patch)["telemetry"]["movement"]["score"])
            frames = self.motion_window(start=1020)
            self.assertTrue(all(frame["motion"]["score"] is None for frame in frames[:-1]))
            self.assertEqual(frames[-1]["motion"]["score"], 0)

    def test_motion_cached_sample_not_counted_and_clock_gap_resets(self):
        stationary = {"ax": 0, "ay": 0, "az": 9.80665, "gx": 0, "gy": 0, "gz": 0}
        self.motion_window(count=49)
        for _ in range(10):
            self.assertFalse(self.call("motion", 960, sample=stationary)["motion"]["valid"])
        self.assertTrue(self.call("motion", 980, sample=stationary)["motion"]["valid"])
        self.assertFalse(self.call("motion", 1100, sample=stationary)["motion"]["valid"])
        self.assertFalse(self.call("motion", 10, sample=stationary)["motion"]["valid"])

    def test_motion_rejects_wrong_sampling_cadence(self):
        stationary = {"ax": 0, "ay": 0, "az": 9.80665, "gx": 0, "gy": 0, "gz": 0}
        for interval in (1, 40):
            self.call("motion_reset")
            frames = [self.call("motion", index * interval, sample=stationary) for index in range(55)]
            self.assertTrue(all(frame["motion"]["score"] is None for frame in frames))

    def test_motion_serializer_preserves_zero_rejects_invalid_and_stale(self):
        for score in (0, 0.5, 1):
            frame = self.call("telemetry", 10, snapshot=self.fresh_snapshot(movement_valid=True, movement_score=score))["telemetry"]
            self.assertEqual(frame["movement"]["score"], score)
        for patch in ({"movement_valid": False}, {"imu_age": 1001}, {"captured_at_ms": 0, "imu_age": 999},
                      {"movement_score": -0.1}, {"movement_score": 1.1}):
            frame = self.call("telemetry", 10, snapshot=self.fresh_snapshot(**{"movement_valid": True, "movement_score": 0.5, **patch}))["telemetry"]
            self.assertIsNone(frame["movement"]["score"])

    def imu_snapshot(self, **patch):
        return self.fresh_snapshot(imu_valid=True,
            acceleration={"x": -0.5, "y": 0, "z": 9.806},
            angular_velocity={"x": -90, "y": 0, "z": 20.5}, **patch)

    def test_imu_axes_keep_units_sign_zero_and_schema_version(self):
        frame = self.call("telemetry", 10, snapshot=self.imu_snapshot())["telemetry"]
        self.assertEqual(frame["schema_version"], "1.1")
        self.assertEqual(frame["movement"]["acceleration"], {"x": -0.5, "y": 0, "z": 9.806})
        self.assertEqual(frame["movement"]["angular_velocity"], {"x": -90, "y": 0, "z": 20.5})
        self.assertEqual(InboundTelemetry.model_validate(frame).telemetry().movement.acceleration.z, 9.806)

    def test_imu_axes_stale_failed_or_bad_vector_not_faked_as_zero(self):
        for patch in ({"imu_valid": False}, {"imu_age": 1001}, {"captured_at_ms": 0, "imu_age": 999}):
            snapshot = self.imu_snapshot() | patch
            frame = self.call("telemetry", 10, snapshot=snapshot)["telemetry"]
            self.assertIsNone(frame["movement"]["acceleration"])
            self.assertIsNone(frame["movement"]["angular_velocity"])
        frame = self.call("telemetry", 10, snapshot=self.imu_snapshot() | {"acceleration": {"x": None, "y": 0, "z": 9.8}})["telemetry"]
        self.assertIsNone(frame["movement"]["acceleration"])
        self.assertIsNotNone(frame["movement"]["angular_velocity"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
