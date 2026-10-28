#!/usr/bin/env python3
# GNU Radio RTL-SDR receiver for Ubuntu 24.04
# GNU Radio 3.10 + gr-osmosdr + Qt GUI

import sys
import math

from PyQt5 import Qt
from gnuradio import gr, blocks, filter, analog, audio, qtgui
from gnuradio.filter import firdes
from gnuradio.fft import window
import osmosdr


class RtlSdrReceiver(gr.top_block, Qt.QWidget):
    def __init__(self):
        gr.top_block.__init__(self, "RTL-SDR FM / HF Receiver")
        Qt.QWidget.__init__(self)
        self.setWindowTitle("RTL-SDR Receiver — WFM / AM / SSB")
        self.resize(1200, 850)

        self.sample_rate = 2_400_000
        self.channel_rate = 480_000
        self.audio_rate = 48_000
        self.center_freq = 100_000_000
        self.rf_gain = 28
        self.mode = "WFM"
        self.fine_tune = 0

        root = Qt.QVBoxLayout(self)
        controls = Qt.QGridLayout()
        root.addLayout(controls)

        controls.addWidget(Qt.QLabel("Частота (МГц)"), 0, 0)
        self.freq_spin = Qt.QDoubleSpinBox()
        self.freq_spin.setRange(24.0, 1766.0)
        self.freq_spin.setDecimals(6)
        self.freq_spin.setSingleStep(0.1)
        self.freq_spin.setValue(self.center_freq / 1e6)
        controls.addWidget(self.freq_spin, 0, 1)

        controls.addWidget(Qt.QLabel("RF gain (dB)"), 0, 2)
        self.gain_spin = Qt.QDoubleSpinBox()
        self.gain_spin.setRange(0, 49.6)
        self.gain_spin.setSingleStep(1)
        self.gain_spin.setValue(self.rf_gain)
        controls.addWidget(self.gain_spin, 0, 3)

        controls.addWidget(Qt.QLabel("Режим"), 1, 0)
        self.mode_box = Qt.QComboBox()
        self.mode_box.addItems(["WFM", "AM", "USB", "LSB"])
        controls.addWidget(self.mode_box, 1, 1)

        controls.addWidget(Qt.QLabel("Подстройка (Гц)"), 1, 2)
        self.fine_spin = Qt.QSpinBox()
        self.fine_spin.setRange(-100_000, 100_000)
        self.fine_spin.setSingleStep(100)
        controls.addWidget(self.fine_spin, 1, 3)

        self.status = Qt.QLabel("Подключение к RTL-SDR…")
        root.addWidget(self.status)

        self.spectrum = qtgui.freq_sink_c(
            2048, window.WIN_BLACKMAN_hARRIS, 0, self.sample_rate,
            "RF Spectrum", 1
        )
        self.spectrum.set_update_time(0.10)
        self.spectrum.set_y_axis(-110, 0)
        self.spectrum.set_line_label(0, "RTL-SDR")
        self.spectrum_win = sip_wrap(self.spectrum.qwidget())
        root.addWidget(self.spectrum_win, 1)

        self.waterfall = qtgui.waterfall_sink_c(
            1024, window.WIN_BLACKMAN_hARRIS, 0, self.sample_rate,
            "Waterfall", 1
        )
        self.waterfall.set_update_time(0.10)
        self.waterfall.set_intensity_range(-110, 0)
        self.waterfall_win = sip_wrap(self.waterfall.qwidget())
        root.addWidget(self.waterfall_win, 2)

        self.src = osmosdr.source(args="numchan=1")
        self.src.set_sample_rate(self.sample_rate)
        self.src.set_center_freq(self.center_freq, 0)
        self.src.set_freq_corr(0, 0)
        self.src.set_gain(self.rf_gain, 0)
        self.src.set_if_gain(20, 0)
        self.src.set_bb_gain(20, 0)
        self.src.set_antenna("", 0)
        self.src.set_bandwidth(0, 0)

        # Translate the tuned channel to baseband and decimate 2.4 MS/s -> 480 kS/s.
        # A 100 kHz low-pass is suitable for WFM broadcast; narrower modes are
        # filtered again in their respective demodulation branches.
        chan_taps = firdes.low_pass(1.0, self.sample_rate, 100_000, 25_000, window.WIN_HAMMING)
        self.channel = filter.freq_xlating_fir_filter_ccc(
            5, chan_taps, 0, self.sample_rate
        )

        self.wfm_demod = analog.wfm_rcv(
            quad_rate=self.channel_rate, audio_decimation=10
        )
        self.am_mag = blocks.complex_to_mag()
        am_taps = firdes.low_pass(1.0, self.channel_rate, 5_000, 1_500, window.WIN_HAMMING)
        self.am_lpf = filter.fir_filter_fff(1, am_taps)
        self.am_resamp = filter.rational_resampler_fff(interpolation=1, decimation=10)

        # Basic product-detector SSB: shift the suppressed carrier by 1.5 kHz,
        # then take the real component and low-pass to audio bandwidth.
        self.usb_rot = blocks.rotator_cc(-2.0 * math.pi * 1500 / self.channel_rate)
        self.lsb_rot = blocks.rotator_cc( 2.0 * math.pi * 1500 / self.channel_rate)
        ssb_taps = firdes.low_pass(1.0, self.channel_rate, 3_000, 1_000, window.WIN_HAMMING)
        self.usb_lpf = filter.fir_filter_ccf(10, ssb_taps)
        self.lsb_lpf = filter.fir_filter_ccf(10, ssb_taps)
        self.usb_real = blocks.complex_to_real()
        self.lsb_real = blocks.complex_to_real()

        self.audio_select = blocks.selector(gr.sizeof_float, 4, 1, 0, 0)
        self.audio_select.set_enabled(True)
        self.volume = blocks.multiply_const_ff(0.7)
        self.audio_sink = audio.sink(self.audio_rate, "", True)

        self.connect(self.src, self.spectrum)
        self.connect(self.src, self.waterfall)
        self.connect(self.src, self.channel)

        self.connect(self.channel, self.wfm_demod)
        self.connect(self.channel, self.am_mag, self.am_lpf, self.am_resamp)
        self.connect(self.channel, self.usb_rot, self.usb_lpf, self.usb_real)
        self.connect(self.channel, self.lsb_rot, self.lsb_lpf, self.lsb_real)

        self.connect((self.wfm_demod, 0), (self.audio_select, 0))
        self.connect(self.am_resamp, (self.audio_select, 1))
        self.connect(self.usb_real, (self.audio_select, 2))
        self.connect(self.lsb_real, (self.audio_select, 3))
        self.connect(self.audio_select, self.volume, self.audio_sink)

        self.freq_spin.valueChanged.connect(self.set_frequency_mhz)
        self.gain_spin.valueChanged.connect(self.set_gain_db)
        self.mode_box.currentTextChanged.connect(self.set_mode)
        self.fine_spin.valueChanged.connect(self.set_fine_tune)

        self.set_mode("WFM")
        self.status.setText("RTL-SDR настроен. Выберите частоту и режим.")

    def set_frequency_mhz(self, mhz):
        self.center_freq = int(mhz * 1e6)
        self.src.set_center_freq(self.center_freq, 0)
        self.spectrum.set_frequency_range(0, self.sample_rate)
        self.waterfall.set_frequency_range(0, self.sample_rate)
        self.channel.set_center_freq(self.fine_tune, self.sample_rate)
        self.status.setText(f"Настройка: {mhz:.6f} MHz · {self.mode}")

    def set_gain_db(self, gain):
        self.rf_gain = gain
        self.src.set_gain(gain, 0)

    def set_fine_tune(self, hz):
        self.fine_tune = hz
        self.channel.set_center_freq(hz, self.sample_rate)

    def set_mode(self, mode):
        self.mode = mode
        self.audio_select.set_input_index({"WFM": 0, "AM": 1, "USB": 2, "LSB": 3}[mode])
        self.status.setText(f"Режим: {mode} · Частота: {self.center_freq / 1e6:.6f} MHz")


def sip_wrap(widget):
    # Qt GUI sinks expose their native QWidget via sip in GNU Radio's PyQt build.
    import sip
    return sip.wrapinstance(int(widget), Qt.QWidget)


def main():
    app = Qt.QApplication(sys.argv)
    tb = RtlSdrReceiver()
    tb.start()
    tb.show()

    def stop():
        tb.stop()
        tb.wait()

    app.aboutToQuit.connect(stop)
    app.exec_()


if __name__ == "__main__":
    main()
