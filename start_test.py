import pygame
from pygame import color
import pygame_gui
from pygame.locals import *
import math
import numpy
from enum import Enum
import configparser
import os
from config import Config
import logging
import datetime
import random

def get_next_test(config, tests):
    if config.test_mode == "random":
        next_test = None
        while next_test is None:
            test_idx = random.randint(0, len(tests)-1)                    
            if len(tests[test_idx].sensed_history) < config.rounds_max and \
                    (sum(tests[test_idx].sensed_history) < config.rounds_min or len(tests[test_idx].sensed_history) < config.rounds_min):
                next_test = tests[test_idx]
        return next_test

    if config.test_mode == "staircase":
        if len(tests) == 0:
            tests.append(Test(volume = 1.0, frequency = config.stimuli_staircase_top_frequency))
        else:
            if abs(config.stimuli_staircase_current_step) < abs(config.stimuli_staircase_min_frequency_step)\
                and config.staircase_mode == "top_to_bottom":
                config.staircase_mode = "bottom_to_top"
                config.stimuli_staircase_current_step = config.stimuli_staircase_max_frequency_step
                tests.append(Test(volume = 1.0, frequency = config.stimuli_staircase_bottom_frequency))
            else:
                if config.staircase_mode == "bottom_to_top":
                    if tests[-1].sensed_history[-1] == 0:
                        tests.append(Test(volume = 1.0, frequency = tests[-1].frequency + config.stimuli_staircase_current_step))
                    else:
                        tests.append(Test(volume = 1.0, frequency = tests[-1].frequency - config.stimuli_staircase_current_step))
                        config.stimuli_staircase_current_step = int(config.stimuli_staircase_current_step - config.stimuli_staircase_current_step/10)
                        config.logger.debug("Staircase method, new step: {}".format(config.stimuli_staircase_current_step))

                if config.staircase_mode == "top_to_bottom":
                    if tests[-1].sensed_history[-1] == 0:
                        tests.append(Test(volume = 1.0, frequency = tests[-1].frequency - config.stimuli_staircase_current_step))
                    else:
                        tests.append(Test(volume = 1.0, frequency = tests[-1].frequency + config.stimuli_staircase_current_step))
                        config.stimuli_staircase_current_step = int(config.stimuli_staircase_current_step - config.stimuli_staircase_current_step/10)
                        config.logger.debug("Staircase method, new step: {}".format(config.stimuli_staircase_current_step))

        return tests[-1]

def is_trial_done(config, tests):
    if config.test_mode == "random":
        DONE = True
        for test in tests:
            if len(test.sensed_history) < config.rounds_max and \
                    sum(test.sensed_history) < config.rounds_min:
                    DONE = False
        return DONE

    if config.test_mode == "staircase":
        if abs(config.stimuli_staircase_current_step) < abs(config.stimuli_staircase_min_frequency_step) \
            and config.staircase_mode == "bottom_to_top":
            return True
        else:
            return False


def dump_csv(tests, config):
    filename_csv = config.logger.handlers[0].baseFilename.split('.')[0] + '.csv'
    with open(filename_csv,'wb') as file:
        for i, test in enumerate(tests):
            file.write(("{},{},{},{}\n".format(i, test.volume, test.frequency, test.sensed_history)).encode('utf-8'))

class Test():
    def __init__(self, volume, frequency):
        self.volume = volume
        self.frequency = frequency
        self.sensed_history = []

class State(Enum):
    NO_TEST = 0
    OUTPUT_BEEP = 1
    OUTPUT_STIMULI = 2

def get_sound(volume = 1.0, duration = 1.0, frequency = 500, sampling_rate = 44100, channel = 1, bits = 16):
    n_samples = int(round(duration*sampling_rate))

    #setup our numpy array to handle 16 bit ints, which is what we set our mixer to expect with "bits" up above
    buf = numpy.zeros((n_samples, 2), dtype = numpy.int16)
    max_sample = 2**(bits - 1) - 1

    for s in range(n_samples):
        t = float(s)/sampling_rate    # time in seconds

        #grab the x-coordinate of the sine wave at a given time, while constraining the sample to what our mixer is set to with "bits"
        buf[s][channel] = int(round(max_sample*volume*math.sin(2*math.pi*frequency*t)))   

    return buf


#the number of channels specified here is NOT 
#the channels talked about here http://www.pygame.org/docs/ref/mixer.html#pygame.mixer.get_num_channels

def main(config):

    tests = []
    if config.test_mode == "random":
        config.logger.info("Tests: {}".format(numpy.size(config.volumes)))
        config.logger.info("Stimuli frequency / volumes pairs: ")
        for i in range(numpy.size(config.volumes)):
            config.logger.info("Test {}: {} volume, {} Hz".format(i, config.volumes[i], config.frequencies[i]))
            tests.append(Test(volume = config.volumes[i], frequency = config.frequencies[i]))

    # PyGame init
    size = (800, 600) # pixels

    pygame.mixer.pre_init(config.sampling_frequency, -config.encoding_bits, 2)
    pygame.init()

    pygame.display.set_caption('Sabina Rautu - Tactile Stimuli Test')
    window_surface = pygame.display.set_mode(size)

    background = pygame.Surface(size)
    background.fill(pygame.Color('#000000'))

    manager = pygame_gui.UIManager(size)

    hello_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((350, 275), (300, 200)),
                                                text='Stimuli sensed',
                                                manager=manager)

    clock = pygame.time.Clock()
    is_running = True
    last_test_start = -8
    beep = []
    stimuli = []
    stimuli_sensed = False
    test_count = 0
    state = State.NO_TEST
    next_test = get_next_test(config, tests)
    while is_running:
        time_delta = clock.tick(60)/1000.0
        now = pygame.time.get_ticks() / 1000.0
        # play beep once
        if now - last_test_start > config.test_duration and state == State.NO_TEST:
            last_test_start = now

            # Create sounds
            beep = get_sound(volume = config.beep_volume, 
                            duration = config.beep_duration, 
                            frequency = config.beep_frequency, 
                            sampling_rate = config.sampling_frequency, 
                            channel = 0, 
                            bits = config.encoding_bits)
            stimuli = get_sound(volume = next_test.volume, 
                                duration = config.stimuli_duration, 
                                frequency = next_test.frequency, 
                                sampling_rate = config.sampling_frequency, 
                                channel = 1,
                                bits = config.encoding_bits)

            # Output beep sound
            sound = pygame.sndarray.make_sound(beep)
            sound.play(loops = 0)
            stimuli_sensed = False
            state = State.OUTPUT_BEEP

        if  now - last_test_start > config.beep_duration + config.pause_beep_stimuli and state == State.OUTPUT_BEEP:
            # Output stimuli
            sound = pygame.sndarray.make_sound(stimuli)
            sound.play(loops=0)
            state = State.OUTPUT_STIMULI

        if now - last_test_start >= config.test_duration and state == State.OUTPUT_STIMULI:
            if stimuli_sensed:
                next_test.sensed_history.append(1)
            else:
                next_test.sensed_history.append(0)
            config.logger.info("Test {} -> Stimuli volume [0.0-1.0]: {}; stimuli frequency [Hz]: {}; response: {}".format(test_count, next_test.volume, next_test.frequency, stimuli_sensed))
            state = State.NO_TEST
            next_test = None
            test_idx = -1
            
            if is_trial_done(config, tests):
                config.logger.info("Done!")
                dump_csv(tests, config)
                exit()

            next_test = get_next_test(config, tests)
                    
            test_count += 1
                

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                is_running = False

            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == hello_button:
                        stimuli_sensed = True
                        config.logger.debug('Stimuli sensed!')

            manager.process_events(event)

        manager.update(time_delta)

        window_surface.blit(background, (0, 0))
        manager.draw_ui(window_surface)

        pygame.display.update()

if __name__ == "__main__":
    logFormatter = logging.Formatter("[%(asctime)s] %(message)s")
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)

    config = Config(file=os.path.join(os.path.dirname(__file__), "config.ini"), logger=rootLogger)

    log_file = "{}_stimuli_test_{}.txt".format(datetime.datetime.today().strftime('%Y-%m-%d_%H-%M-%S'), config.test_mode)
    fileHandler = logging.FileHandler(os.path.join(os.path.join(os.path.dirname(__file__), config.output_folder), log_file))
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

    print(config.__dict__)
    main(config)
