# Synthetic Multimodal Data Specification

## Purpose and scientific limitation

The generator enables ingestion, preprocessing, quality, baseline, feature, integration and parity software work before hardware datasets exist. It is a configurable engineering approximation—not real ASD physiological data, a medically validated PPG/EDA simulator, clinical evidence, or proof of anxiety recognition.

## Shared temporal model

Each session has shared latent activity, simulated autonomic activation, contact quality, periodic movement and time since onset. Sensor streams sample interpolated versions of these variables at configurable rates. Defaults are PPG 100 Hz, IMU 50 Hz, GSR 20 Hz and telemetry 1 Hz. These are development defaults only. Samples remain ordered; optional jitter keeps explicit per-stream timestamps; raw API batches use precise rate-based reconstruction and `null` placeholders for loss.

## Signal assumptions and units

- PPG red/IR: approximate pulse morphology (systolic peak plus smaller dicrotic component), phase integrated from the same HR reference, baseline drift, noise and motion/contact artifacts. Units are device-like sample counts (0–262143), not optical/clinical units.
- HR: participant resting baseline plus slow variability, activation/activity effects and small noise. It is derived consistently with PPG phase, not an unrelated random series.
- GSR: 12-bit ADC-like counts (0–4095), individual tonic baseline, slow drift, delayed activation response, independent occasional transients, noise and contact artifacts. Counts are not calibrated microsiemens and are not a direct anxiety measure.
- IMU: acceleration in g and gyroscope in degrees/s, including gravity under slowly changing orientation, natural/ordinary movement, periodic motion and noise. Periodic movement is not assumed to mean distress.

Motion influences PPG corruption/contact quality, while GSR transients and delay remain independently timed. `artifact_frequency` is an approximate artifact-event start rate per second; dropout is a per-sample probability. Noise and participant baseline variation are configurable. Normal activity and elevated-activation scenarios deliberately overlap.

## Scenarios

- `NORMAL_REST`: low activity with natural variability.
- `NORMAL_ACTIVITY`: ordinary motion and possible HR increase; useful for false-alert tests.
- `REPETITIVE_MOVEMENT`: a periodic wrist-motion pattern without forced GSR activation; not a validated model of stimming.
- `ELEVATED_AROUSAL_PROXY`: imperfectly correlated HR/GSR trends and optional movement; never confirmed anxiety.
- `POOR_SIGNAL`: low contact, motion corruption and increased dropout for quality gating.
- `TRANSITION`: gradual logistic change rather than simultaneous jumps.
- `DISCONNECT_RECONNECT`: stable acquisition timeline while the mock transport pauses.

## Individuals and variability

Pseudonymous `SYN-P###` profiles vary resting HR, HR variability, GSR baseline/gain, movement gain, contact, noise and response delay. Trials use distinct seed offsets; renaming an identical session is not acceptable.

## Labels and leakage

Scenario ground truth is distinct from deployment engineering state. The explicit experimental mapping lives in `synthetic/labeling.py`; low quality overrides to `UNCERTAIN`. It is not a clinical-label mapping. Scenario/participant/session IDs, simulator probabilities, selected state and seed are prohibited model inputs. Poor-quality windows should be quality-gated and may be excluded from binary experiments. Labels must not be created by the exact fixed thresholds later used as baselines.

## Dataset schema and provenance

Saved JSON contains `metadata`, `streams` and compact `telemetry`. Manifest records `data_origin=SYNTHETIC`, generator version/config, seed, schema version, participant/session, scenario, rates, duration, UTC creation time and limitation notice. Generated files remain below `AI/data/synthetic` and are gitignored; real data remains elsewhere.

## Reproducibility and validation

Identical configuration, profile and seed reproduce signal arrays. Timestamps, sample counts/rates, ranges, schema, dropout, motion-quality coupling, baseline differences, non-identical sessions, transitions, serialization and preprocessing compatibility are tested. `created_at` metadata is not expected to be byte-identical. Diagnostic plots support visual inspection only, not physiological validation.

## Usage

```bash
$env:PYTHONPATH="AI"
python -m simulator.mock_device --scenario repetitive_movement --duration 30 --save
python -m simulator.mock_device --generate-dataset --duration 30
python -m simulator.mock_device --replay AI/data/synthetic/raw/SYN-SESSION001.json --send-raw --speed 5
python -m pytest AI/tests
```

Inside Docker, prefix with `docker compose --profile ai run --rm ai`. A synthetic-only training smoke test belongs to a later ML phase and any resulting model must carry `SYNTHETIC_ONLY` provenance; it cannot be auto-selected for deployment.
