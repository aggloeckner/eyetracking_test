from otree.api import *
# top of the file
import sys, asyncio
import csv
import tobii_research as tr
import time

if sys.platform == "win32" and (3, 8, 0) <= sys.version_info < (3, 9, 0):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'dictator_game'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    ENDOWMENT = cu(100)


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    kept = models.CurrencyField(
        doc="""Amount dictator decided to keep for himself""",
        min=0,
        max=C.ENDOWMENT,
        label="Ich behalte",
        initial=0,
    )

class Player(BasePlayer):
    eyetrackerAddress = models.StringField(label="Eyetracker-Adresse:")

# FUNCTIONS
def set_payoffs(group: Group):
    p1 = group.get_player_by_id(1)
    p2 = group.get_player_by_id(2)
    p1.payoff = group.kept
    p2.payoff = C.ENDOWMENT - group.kept

def call_eyetracker_manager_example(eyetracker):
    import os
    import subprocess
    import platform
    import glob
    import tobii_research as tr

    try:
        os_type = platform.system()
        ETM_PATH = ''
        DEVICE_ADDRESS = ''
        if os_type == "Windows":
            print(glob.glob(os.environ["LocalAppData"] + "/Programs/TobiiProEyeTrackerManager/TobiiProEyeTrackerManager.exe")[0])
            ETM_PATH = glob.glob(os.environ["LocalAppData"] + "/Programs/TobiiProEyeTrackerManager/TobiiProEyeTrackerManager.exe")[0]
            DEVICE_ADDRESS = "tobii-ttp://IS404-100107417574"
        elif os_type == "Linux":
            ETM_PATH = "TobiiProEyeTrackerManager"
            DEVICE_ADDRESS = "tobii-ttp://TOBII-IS404-100107417574"
        elif os_type == "Darwin":
            ETM_PATH = "/Applications/TobiiProEyeTrackerManager.app/Contents/MacOS/TobiiProEyeTrackerManager"
            DEVICE_ADDRESS = "tobii-ttp://TOBII-IS404-100107417574"
        else:
            print("Unsupported...")
            exit(1)

        print(os_type)

        mode = "usercalibration"

        etm_p = subprocess.Popen([ETM_PATH,"--device-address=" + eyetracker.address, "--mode=" + mode],stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)

        stdout, stderr = etm_p.communicate()  # Returns a tuple with (stdout, stderr)

        if etm_p.returncode == 0:
            print("Eye Tracker Manager was called successfully!")
        else:
            print("Eye Tracker Manager call returned the error code: " + str(etm_p.returncode))
            errlog = None
        if os_type == "Windows":
            errlog = stdout  # On Windows ETM error messages are logged to stdout
        else:
            errlog = stderr

        for line in errlog.splitlines():
            if line.startswith('ETM Error:'):
                print(line)

    except Exception as e:
        print(e)

gaze_data_samples = []

def gaze_data_callback(gaze_data):
    global gaze_data_samples
    gaze_data_samples.append(gaze_data)

def save_gaze_data(gaze_samples_list, player, pageName):
    if not gaze_samples_list:
        print("No gaze samples were collected. Skipping saving")
        return
    # To show what kinds of data are available in each sample's dictionary,
    # we print the available keys here.
    print("Sample dictionary keys:", gaze_samples_list[0].keys())
    # This is meant to serve as a simple example of how you can save
    # some of the gaze data - check the keys to see what else is available.

    from pathlib import Path

    file_name = "gaze_data/" + player.participant.label + "_gaze_data.csv"

    if not Path(file_name).is_file():
        file_handle = open(file_name, "w")
        gaze_writer = csv.writer(file_handle)
        gaze_writer.writerow(["id", "page", "time_seconds", "left_x", "left_y", "right_x", "right_y"])
        file_handle.close()

    file_handle = open(file_name, "a")
    gaze_writer = csv.writer(file_handle)
    start_time = gaze_samples_list[0]["system_time_stamp"]
    for recording_dict in gaze_samples_list:
        sample_time_from_start = recording_dict["system_time_stamp"] - start_time
        # convert from microseconds to seconds
        sample_time_from_start = sample_time_from_start / (10**(6))
        # x is horizontal coordinate on the screen
        # y is vertical coordinate on the screen
        id = player.participant.label
        page = pageName
        left_x, left_y  = recording_dict["left_gaze_point_on_display_area"]
        right_x, right_y = recording_dict["right_gaze_point_on_display_area"]
        gaze_writer.writerow(
            [id, page, sample_time_from_start, left_x, left_y, right_x, right_y]
        )
    file_handle.close()

# PAGES
class EyetrackerAddress(Page):
    form_model = 'player'
    form_fields = ['eyetrackerAddress']

class Introduction(Page):
    None

class Calibration(Page):
    @staticmethod
    def vars_for_template(player):
        player.participant.label = str(player.participant.session.code) + "_" + str(player.participant.id_in_session)

        # Step 1: Find the eye tracker!
        global my_eyetracker
        my_eyetracker = tr.EyeTracker(player.eyetrackerAddress)

        print("Address: " + my_eyetracker.address)
        print("Model: " + my_eyetracker.model)
        print("Name (It's OK if this is empty): " + my_eyetracker.device_name)
        print("Serial number: " + my_eyetracker.serial_number)

        # Step 2: Calibrate the eye tracker
        call_eyetracker_manager_example(my_eyetracker)
        return

    @staticmethod
    def before_next_page(player, timeout_happened):
        #Step 3: Get gaze data!
        my_eyetracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, gaze_data_callback, as_dictionary=True)
        print("Eye Tracking 1 started")


class Instructions(Page):
    @staticmethod
    def before_next_page(player, timeout_happened):
        # Step 4: Wrapping up!
        my_eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, gaze_data_callback)
        print("Eye Tracking 1 finished")
        save_gaze_data(gaze_data_samples, player, "Instructions")
        gaze_data_samples.clear()

        # Step 3: Get gaze data!
        my_eyetracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, gaze_data_callback, as_dictionary=True)
        print("Eye Tracking 2 started")

class Offer(Page):
    form_model = 'group'
    form_fields = ['kept']

    @staticmethod
    def is_displayed(player: Player):
        return player.id_in_group == 1

    @staticmethod
    def before_next_page(player, timeout_happened):
        # Step 4: Wrapping up!
        my_eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, gaze_data_callback)
        print("Eye Tracking 2 finished")
        save_gaze_data(gaze_data_samples, player, "Offer")
        gaze_data_samples.clear()

        # Step 3: Get gaze data!
        my_eyetracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, gaze_data_callback, as_dictionary=True)
        print("Eye Tracking 3 started")


class ResultsWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs

    @staticmethod
    def before_next_page(player, timeout_happened):
        # Step 4: Wrapping up!
        my_eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, gaze_data_callback)
        print("Eye Tracking 3 finished")
        save_gaze_data(gaze_data_samples, player, "ResultsWaitPage")
        gaze_data_samples.clear()

        # Step 3: Get gaze data!
        my_eyetracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, gaze_data_callback, as_dictionary=True)
        print("Eye Tracking 4 started")


class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group

        return dict(offer=C.ENDOWMENT - group.kept)

    @staticmethod
    def before_next_page(player, timeout_happened):
        # Step 4: Wrapping up!
        my_eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, gaze_data_callback)
        print("Eye Tracking 4 finished")
        save_gaze_data(gaze_data_samples, player, "Results")
        gaze_data_samples.clear()


page_sequence = [
    EyetrackerAddress,
    Introduction,
    Calibration,
    Instructions,
    Offer,
    ResultsWaitPage,
    Results
]
