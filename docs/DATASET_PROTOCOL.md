# Dataset Protocol

## Separation and identifiers

Real raw/interim/processed data lives under the corresponding `AI/data` directories; generated data lives only in `AI/data/synthetic/{raw,processed,manifests}`. Never merge them into an unlabeled pool. Real IDs use approved pseudonyms such as `P001`/`SESSION-001`; synthetic IDs use an unmistakable `SYN-P001`/`SYN-SESSION001` namespace. No names or direct identifiers are allowed.

## Provenance

Every dataset/model record must retain origin, schema/generator or firmware version, configuration, random seed where applicable, participant/session/trial IDs, sampling rates and creation/collection context. Models trained only on generated data are `SYNTHETIC_ONLY`; mixed models must declare both sources.

## Splitting and ordering

Preserve time order through preprocessing/windowing. Split by participant where possible, or by whole sessions/trials. Never randomly split adjacent windows from one session across train/test. When real data exists, hold out a separate real evaluation set that is not used for fitting or tuning.

## Leakage controls

Exclude scenario, participant/session/trial IDs, seed, simulator state/probability and other outcome-revealing metadata from features. Quality-gate poor periods. Fit normalization/baselines only from the training side of a split. Synthetic and real signals must enter the same production preprocessing/feature interfaces.

## Reporting

Synthetic evaluation verifies software execution and sensitivity to stated assumptions only. It is not real-world ASD/anxiety accuracy. Real-world performance claims require independently collected real signals, appropriate labels/ethics, a preserved evaluation set and measured metrics. No accuracy, F1, latency, memory, false-alert or battery claim may be invented.

