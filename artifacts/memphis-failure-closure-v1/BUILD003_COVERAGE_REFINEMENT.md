# Build003 — immutable development evidence, not final engineering approval

Source be60a99aacdb63c364a4533c540cc14a39be24ef; manifest RAW
ffc9cadc89d27eca00dc6d99667abbb063badeac9db08e26fb916d2c417a28ff.
Run https://github.com/dragonzxh1/Compute_to_Cooling_Digital_Test_Bench/actions/runs/39178454385

Pre-delivery review found required coverage gaps/new-project defects:

- Proposed W2 preconditioning began at40.5C, establishing hold capability but
  not warm-start cooldown. Build004 starts proposed standby pipes at48.29C.
- Preconditioning-off paths returned before adding environmental heat gain;
  Build004 retains UA heat gain when pumps stop and measures7200s retention.
- Recharging A with4 source pumps lacked return to3+1 after reserve proof.
  Build004 returns to3 only after measured17TT proof and4 observed working
  pumps; a failed pump replaced by the spare is not falsely removed.
- Original pump-exit trials were during W1 failover. Build004 adds isolated
  single-pump exits and explicitly classifies their actual40s fault window.

Original source/run/results retained; no corrected-source results rebound to
Build003. Build004 reruns the complete bounded development campaign. Frozen
M1, old physical reference code, customer requirements and evidence unchanged.
