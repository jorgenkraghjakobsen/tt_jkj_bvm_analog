# reg_bank tests

`reg_bank` is generated from the register database with the IC Works
regmap tool and is never hand-edited, so it has no standalone bench.

It is exercised through `dig_top`:

- `test_reset_defaults_readback` — every reset value in the published map
- `test_bringup_duty_follows_register` — a write reaches the PWM datapath
- `test_trim_outputs_follow_registers` — `bg_trim`, `bias_trim`, `dbl_en`
- `test_status_combines_bias_ok_and_bg_valid` — the read-only STATUS path

```bash
cd ../../dig_top/tb && make
```

If the regmap tool regenerates `reg_bank.v`, re-run those four tests
before anything else: they are what catch a changed address or a changed
reset value.
