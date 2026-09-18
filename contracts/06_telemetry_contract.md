Revision: 1.0
Status: FROZEN PHASE 2 DESIGN; implementation and acceptance tests pending.

# 06 — Telemetry Contract

## Inputs / Outputs

Four adapter contracts: Direct DCGM/Hostengine (timestamp-preserving low-latency candidate, recorded control trace); DCGM Exporter (monitoring/Prometheus/replay/integration); Synthetic (through same measurement pipeline); Recorded Replay (causal source-time playback). All expose read_available(t)->immutable records and capabilities. PHASE 7 implements adapters/disturbance pipeline; no live implementation now. No hardware latency guarantee from adapter name.

TelemetryRecord required:
schema_version, source_type (DIRECT_DCGM / DCGM_EXPORTER / SYNTHETIC / RECORDED_REPLAY), source_version;
entity_type, entity_uuid, rack_id, tray_id, branch_id;
metric_name, value, unit;
sample_time, receive_time, available_time;
sequence_id, quality, averaging_window;
power_domain, thermal_domain, included_in.
Add timebase, clock_offset/uncertainty_ns, raw_source_timestamp, source_sample_id, raw_value, capability_version, value_origin. entity_uuid is canonical; legacy device_uuid may be an alias only if equal, never separate inventory. Nullable mapping references (e.g. board spans several thermal nodes) resolve via allocation map, never invent a die mapping.

## Time / quality invariants

Times normalized to integer ns simulation epoch, preserving raw clock. Source sample_time denotes measurement window end; averaging_window>=0 defines [sample_time−window,sample_time]. receive_time is adapter receipt, available_time is post-processing controller release. Semantically distinct even when zero delays make them numerically equal. For trusted clocks sample<=receive<=available<=t for any controller-visible sample. Samples timestamped in future beyond declared clock uncertainty are rejected/quarantined, not relabeled.

Freshness worst-case age=t−sample_time+clock_uncertainty. Default Generic watchdog max_age=1.0s, recovery as15; a real deployment needs verified sampling/window and qualified settings, not reuse as an OEM value. Averages also checked: window<=configured max_average_window (Generic1.0s). Unknown sample time -> TIMESTAMP_UNKNOWN, no qualified FF in this contract version; monitoring may retain receipt time separately. No conservative unknown-age exception is enabled by default.

Repeated scrape retains source sample ID/time. New receive_time is not a new sample. GPU hardware sampling interval != Prometheus scrape interval != exporter refresh. Cannot identify repeat/freshness -> timestamp quality unknown. Source IDs/sequences are per source/entity/metric and restart epoch; restart requires reset event, not silent wrap.

Quality enum includes VALID, STALE, MISSING, NONFINITE, SENTINEL, TIMESTAMP_UNKNOWN, CLOCK_INVALID, OUT_OF_ORDER, DUPLICATE, LOW_CONFIDENCE. Keep raw invalid values for audit; numeric value=null for invalid payload. Never replace missing temp/power with0. Out-of-order record archived; cannot replace newer controller-held record. Exact repeated sample ignored for recovery counts. Distinct samples may have same values and still be fresh.

Noise/bias/sampling/delay/drop are measurement transforms, not plant modifications. Synthetic source noise uses independent keyed stream(sensor_id,sample_index,seed), stable regardless of controller calls. Hardware averaging is modeled once; do not repeat it in adapter. A control record must have complete required coverage and valid constituent timestamps.

## Failure / fallback

Bad/stale/low-confidence required IT channel -> FF_DISABLED; local sensors independent. Local sensor failure invokes15. Exporter data remains monitoring-only unless capability and timestamp qualification explicitly pass the same policy. No API field IDs hardcoded at architecture stage; target DCGM/driver/firmware/Grace support verified before live integration.

## Acceptance specifications

TEL-01: scrape stale sample10 times with new receipt times; age still grows and FF disables.
TEL-02: sample at0, network.2, processing.1: unavailable before.3, age .3 at release.
TEL-03: duplicates do not advance recovery count; sentinel/null/out-of-order/restart tested.
TEL-04: replay records with future available_time invisible; sources with same sampling/noise produce identical records for same truth.

