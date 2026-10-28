# RTL-SDR FM / HF Receiver (GNU Radio)

A Python GNU Radio 3.10 starter application for Ubuntu 24.04 and an RTL-SDR dongle. It provides a live RF spectrum and waterfall, frequency tuning, gain control, and selectable WFM, AM, and basic SSB demodulation.

## Features

- RTL-SDR source via GNU Radio's `osmosdr` source block.
- Qt GUI spectrum and waterfall display.
- Tunable center frequency (Hz) and RF gain.
- Demodulation selector: WFM, AM, USB, LSB.
- Audio output through GNU Radio's audio sink.

## Important notes

- FM broadcast reception uses WFM.
- AM is envelope detection.
- USB/LSB are basic synchronous-tuning SSB modes: tune close to the suppressed carrier. A fine-tuning control and selectable sideband are included, but this is a starter receiver, not a full communications-grade DSP chain.
- Use an appropriate antenna for the frequency range. RTL-SDR hardware usually cannot tune below roughly 24 MHz without direct sampling or an upconverter, depending on the dongle and driver.
- FM broadcast, HF, and other services have different bandwidths. This starter flowgraph is optimized for a 2.4 MS/s RF sample rate; adjust the settings if your dongle or USB host needs a lower rate.
- Only monitor frequencies and services you're legally permitted to receive.

## Install dependencies (Ubuntu 24.04)

You said GNU Radio and RTL-SDR drivers are already installed. Ensure the Python bindings and Qt GUI are available:

```bash
sudo apt update
sudo apt install gnuradio gr-osmosdr rtl-sdr python3-pyqt5
```

Check the dongle is detected:

```bash
rtl_test -t
```

Close other applications using the dongle before launching the receiver.

## Run

```bash
chmod +x run.sh
./run.sh
```

Or run directly:

```bash
python3 rtl_sdr_receiver.py
```

## Controls

- **Frequency (MHz):** tune the RTL-SDR center frequency.
- **RF gain (dB):** manual tuner gain.
- **Mode:** WFM, AM, USB, or LSB.
- **Fine tune (Hz):** small frequency correction for AM/SSB.

## Troubleshooting

- **No device / busy:** check `rtl_test -t`, unplug/replug the dongle, and close SDR apps.
- **No sound:** check Ubuntu's output device and system volume; verify GNU Radio audio support is installed.
- **Qt GUI import error:** install the Ubuntu GNU Radio package and run with the system Python that matches its GNU Radio bindings.
- **Poor HF reception:** many RTL-SDR tuners do not cover HF directly; use a supported direct-sampling mode or an HF upconverter.

## Project structure

- `rtl_sdr_receiver.py` — GNU Radio flowgraph and GUI.
- `run.sh` — launch helper.
- `requirements-ubuntu.txt` — package checklist.
