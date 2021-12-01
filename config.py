import configparser
import numpy as np

class Config():
    def __init__(self, file, logger = None):
        config = configparser.ConfigParser()
        config.read(file)

        self.sampling_frequency = config.getint("GENERAL", "sampling_frequency")
        self.encoding_bits = config.getint("GENERAL", "encoding_bits")
        self.rounds_max = config.getint("GENERAL", "rounds_max")
        self.rounds_min = config.getint("GENERAL", "rounds_min")
        self.test_mode = config["GENERAL"]["test_mode"]
        
        if self.test_mode == "staircase":
            self.staircase_mode = "top_to_bottom"

        # volume [0.0-1.0] of the beep sound anouncing a new stimuli
        self.beep_volume = config.getfloat("TEST", "beep_volume")
        # duration [s] of the beep sound anouncing a new stimuli
        self.beep_duration = config.getfloat("TEST", "beep_duration")
        # frequency [Hz] of the beep anouncing a new stimuli
        self.beep_frequency = config.getint("TEST", "beep_frequency")
        # duration [s] of the tactile stimuli
        self.stimuli_duration = config.getfloat("TEST", "stimuli_duration")
        # set of volumes [0.0-1.0] of the tactile stimuli
        self.stimuli_volumes = [float(vol) for vol in config["RANDOM"]["stimuli_volumes"].replace(' ','').split(',')]
        # set of frequencies [Hz] of the tactile stimuli
        self.stimuli_frequencies = [int(float(freq)) for freq in config["RANDOM"]["stimuli_frequencies"].replace(' ','').split(',')]
        # staircase top stimuli frequency [Hz]
        self.stimuli_staircase_top_frequency = config.getint("STAIRCASE", "stimuli_staircase_top_frequency")
        # staircase bottom stimuli frequency [Hz]
        self.stimuli_staircase_bottom_frequency = config.getint("STAIRCASE", "stimuli_staircase_bottom_frequency")
        # staircase initial (maximum) step stimuli frequency [Hz]
        self.stimuli_staircase_max_frequency_step = config.getint("STAIRCASE", "stimuli_staircase_max_frequency_step")
        self.stimuli_staircase_current_step = self.stimuli_staircase_max_frequency_step
        # staircase final (minimum) step stimuli frequency [Hz]
        self.stimuli_staircase_min_frequency_step = config.getint("STAIRCASE", "stimuli_staircase_min_frequency_step")
        # pause [s] between beep and stimuli
        self.pause_beep_stimuli = config.getfloat("TEST", "pause_beep_stimuli")
        # pause [s] at the beginning of the test
        self.pause_start = config.getfloat("TEST", "pause_start")
        # pause [s] at the end of the test
        self.pause_end = config.getfloat("TEST", "pause_end")

        self.output_folder = config["OUTPUT"]["output_folder"]

        self.logger = logger

        self.test_duration = self.pause_beep_stimuli + self.pause_end + \
                            self.stimuli_duration + self.beep_duration

        if self.test_mode == "random":
            self.volumes, self.frequencies = np.meshgrid(self.stimuli_volumes, self.stimuli_frequencies, sparse=False, indexing='xy')
            self.volumes = self.volumes.flatten()
            self.frequencies = self.frequencies.flatten()
