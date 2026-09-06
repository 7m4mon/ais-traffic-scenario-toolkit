# AIS Traffic Scenario Toolkit

Python toolkit for building and replaying AIS encounter scenarios. It compiles synthetic vessel encounters to a per-second timeline, imports AIS-Catcher AIVDM logs, calculates CPA/TCPA warning levels, and replays timelines as NMEA 0183, AIVDM, AIS payload bit strings, TCP/UDP, serial, or WebSocket output.

This project does not transmit RF. If you feed generated AIS frames into external RF lab equipment, keep that work inside a legal closed test setup with suitable attenuation and no over-the-air emission.

## Install

```bash
python -m pip install -e .
python -m pip install pytest
```

Serial output needs `pyserial`:

```bash
python -m pip install pyserial
```

## Compile A Synthetic Scenario

```bash
python tools/ais_scenario_compile.py \
  --scenario scenarios/crossing_starboard_danger.json \
  --output timeline/crossing_starboard.jsonl \
  --csv timeline/crossing_starboard.csv
```

Timeline records include own-ship state, target state, local `x_nm/y_nm`, `lat/lon`, `cpa_nm`, `tcpa_sec`, `expected_level`, and computed `safe` / `caution` / `danger`.

Targets may use `active_from_sec` and `active_until_sec` to appear and disappear during a demonstration. Target event times are relative to `active_from_sec`. Message type 21 targets also accept `aton_type`, `aton_virtual`, and `aton_off_position` for AIS Aid-to-Navigation markers.

The exhibition scenario combines staged encounters, an AIS-SART, and a virtual isolated-danger mark:

```bash
python tools/ais_scenario_compile.py \
  --scenario scenarios/exhibition_gauntlet.json \
  --output timeline/exhibition_gauntlet.jsonl \
  --csv timeline/exhibition_gauntlet.csv
```

## Import AIS-Catcher Logs

```bash
python tools/ais_import_aivdm_log.py \
  --input logs/sample_aiscatcher.log \
  --output timeline/port_phillip_replay.jsonl \
  --csv timeline/port_phillip_replay.csv \
  --origin-lat -37.8840 \
  --origin-lon 144.9500 \
  --own-source none \
  --ignore-checksum
```

AIS-Catcher metadata such as `signalpower`, `ppm`, and `timestamp` is preserved as timeline fields. Use `--ignore-checksum` for imperfect field logs.

## Replay To OpenCPN

OpenCPN can consume a single mixed TCP stream containing own-ship RMC/GGA/HDT and target AIVDM:

```bash
python tools/ais_scenario_player.py \
  --timeline timeline/crossing_starboard.jsonl \
  --nmea-tcp-server 127.0.0.1:10110
```

To see each sentence as it is sent:

```bash
python tools/ais_scenario_player.py \
  --timeline timeline/crossing_starboard.jsonl \
  --nmea-tcp-server 127.0.0.1:10110 \
  --echo-output
```

For a console preview:

```bash
python tools/ais_scenario_player.py timeline/crossing_starboard.jsonl --dry-run --replay-speed 20
```

## Replay To A DUT And Mictronics

```bash
python tools/ais_scenario_player.py \
  --timeline timeline/crossing_starboard.jsonl \
  --nmea-tcp-server 127.0.0.1:10110 \
  --own-nmea-serial /dev/ttyUSB0 \
  --own-baud 4800 \
  --bitstring-ws ws://127.0.0.1:52002
```

`--own-nmea-serial` sends only own RMC/GGA/HDT. `--target-aivdm-serial` sends target AIVDM. `--bitstring-ws` sends AIS payload bit strings for Mictronics-style simulators.

For separate GPS and AIS serial inputs, use independent baud rates:

```bash
python tools/ais_scenario_player.py \
  --timeline timeline/crossing_starboard.jsonl \
  --own-nmea-serial /dev/ttyUSB0 \
  --own-baud 4800 \
  --target-aivdm-serial /dev/ttyUSB1 \
  --target-baud 38400
```

The defaults are 4800 baud for own-ship NMEA and 38400 baud for target AIVDM. The legacy `--baud` option still sets both serial outputs unless the corresponding specific option overrides it.

## AIVDM To Bit String

```bash
python tools/aivdm_to_bits.py --ignore-checksum '!AIVDM,1,1,,A,1>pf?UQP01:Gdtsb?:V9>WHd0000,0*17'
```

## Safety Notes

- This toolkit is for simulation, display testing, training, and closed-lab analysis.
- Do not radiate generated AIS signals on public AIS frequencies.
- Follow local law and use shielding, dummy loads, and attenuation for any RF-chain work.
- Prefer TCP/UDP, serial NMEA input, and simulator WebSocket paths when testing plotters and receivers.

## Article

```bash
https://nomulabo.com/ais-traffic-scenario-toolkit/
```

<img width="867" height="714" alt="Image" src="https://github.com/user-attachments/assets/2e1525ee-128d-4bf5-b736-c22c53c27d4f" />  
<img width="867" height="714" alt="Image" src="https://github.com/user-attachments/assets/afe11d3f-f91d-4d8d-903d-9b4538de8be4" />  
<img width="867" height="714" alt="Image" src="https://github.com/user-attachments/assets/0ed44d61-2605-43f9-b69f-e10197b1f2f0" />  
<img width="867" height="714" alt="Image" src="https://github.com/user-attachments/assets/8d30fb26-ae89-49a5-aa2b-496de63906e1" />  
