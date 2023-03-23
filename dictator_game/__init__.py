from otree.api import *
# top of the file
import sys, asyncio

if sys.platform == "win32" and (3, 8, 0) <= sys.version_info < (3, 9, 0):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Step 0: Preparations!
import tobii_research as tr
import time

doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL = 'dictator_game'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 2
    ENDOWMENT = cu(100)


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    kept = models.CurrencyField(
        doc="""Amount dictator decided to keep for himself""",
        min=0,
        max=C.ENDOWMENT,
        label="Ich behalte",
    )


class Player(BasePlayer):
    pass

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

    print("Test 0")
    try:
        os_type = platform.system()
        ETM_PATH = ''
        DEVICE_ADDRESS = ''
        if os_type == "Windows":
            print(glob.glob(os.environ["LocalAppData"] + "/Programs/TobiiProEyeTrackerManager/TobiiProEyeTrackerManager.exe")[0])
            ETM_PATH = glob.glob(os.environ["LocalAppData"] + "/Programs/TobiiProEyeTrackerManager/TobiiProEyeTrackerManager.exe")[0]
            DEVICE_ADDRESS = "tobii-ttp://IS404-100107417574"
            print("Test C")
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

        mode = "displayarea"

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
            if line.startswith("ETM Error:"):
                print(line)

    except Exception as e:
        print(e)

def calibrate(eyetracker):
    if eyetracker is None:
        return

    # <BeginExample>
    import time
    import tobii_research as tr

    calibration = tr.ScreenBasedCalibration(eyetracker)

    # Enter calibration mode.
    calibration.enter_calibration_mode()
    print("Entered calibration mode for eye tracker with serial number {0}.".format(eyetracker.serial_number))

    # Define the points on screen we should calibrate at.
    # The coordinates are normalized, i.e. (0.0, 0.0) is the upper left corner and (1.0, 1.0) is the lower right corner.
    points_to_calibrate = [(0.5, 0.5), (0.1, 0.1), (0.1, 0.9), (0.9, 0.1), (0.9, 0.9)]

    for point in points_to_calibrate:
        print("Show a point on screen at {0}.".format(point))

        # Wait a little for user to focus.
        time.sleep(0.7)

        print("Collecting data at {0}.".format(point))
        if calibration.collect_data(point[0], point[1]) != tr.CALIBRATION_STATUS_SUCCESS:
            # Try again if it didn't go well the first time.
            # Not all eye tracker models will fail at this point, but instead fail on ComputeAndApply.
            calibration.collect_data(point[0], point[1])

    print("Computing and applying calibration.")
    calibration_result = calibration.compute_and_apply()
    print("Compute and apply returned {0} and collected at {1} points.".format(calibration_result.status, len(calibration_result.calibration_points)))

    # Analyze the data and maybe remove points that weren't good.
    recalibrate_point = (0.1, 0.1)
    print("Removing calibration point at {0}.".format(recalibrate_point))
    calibration.discard_data(recalibrate_point[0], recalibrate_point[1])

    # Redo collection at the discarded point
    print("Show a point on screen at {0}.".format(recalibrate_point))
    calibration.collect_data(recalibrate_point[0], recalibrate_point[1])

    # Compute and apply again.
    print("Computing and applying calibration.")
    calibration_result = calibration.compute_and_apply()
    print("Compute and apply returned {0} and collected at {1} points.".
    format(calibration_result.status, len(calibration_result.calibration_points)))

    # See that you're happy with the result.

    # The calibration is done. Leave calibration mode.
    calibration.leave_calibration_mode()
    print("Left calibration mode.")
    # <EndExample>

def gaze_data_callback(gaze_data):
    # Print gaze points of left and right eye
    print("Left eye: ({gaze_left_eye}) \t Right eye: ({gaze_right_eye})".format(
        gaze_left_eye=gaze_data['left_gaze_point_on_display_area'],
        gaze_right_eye=gaze_data['right_gaze_point_on_display_area']))


# PAGES
class Calibration(Page):
    @staticmethod
    def vars_for_template(player):
        # Step 1: Find the eye tracker!
        found_eyetrackers = tr.find_all_eyetrackers()

        my_eyetracker = found_eyetrackers[0]
        print("Address: " + my_eyetracker.address)
        print("Model: " + my_eyetracker.model)
        print("Name (It's OK if this is empty): " + my_eyetracker.device_name)
        print("Serial number: " + my_eyetracker.serial_number)

        #Step 2: Calibrate the eye tracker
        call_eyetracker_manager_example(my_eyetracker)
        return

    @staticmethod
    def before_next_page(player, timeout_happened):
        #Step 3: Get gaze data!
        my_eyetracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, gaze_data_callback, as_dictionary=True)
        print("Eye Tracking 1 started")

class Introduction(Page):
    @staticmethod
    def before_next_page(player, timeout_happened):
        #Step 4: Wrapping up!
        my_eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, gaze_data_callback)
        print("Eye Tracking 1 finished")

        #Step 3: Get gaze data!
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
        #Step 4: Wrapping up!
        my_eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, gaze_data_callback)
        print("Eye Tracking 2 finished")

        #Step 3: Get gaze data!
        my_eyetracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, gaze_data_callback, as_dictionary=True)
        print("Eye Tracking 3 started")


class ResultsWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs

    @staticmethod
    def before_next_page(player, timeout_happened):
        #Step 4: Wrapping up!
        my_eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, gaze_data_callback)
        print("Eye Tracking 3 finished")

        #Step 3: Get gaze data!
        my_eyetracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, gaze_data_callback, as_dictionary=True)
        print("Eye Tracking 4 started")


class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group

        return dict(offer=C.ENDOWMENT - group.kept)

    @staticmethod
    def before_next_page(player, timeout_happened):
        #Step 4: Wrapping up!
        my_eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, gaze_data_callback)
        print("Eye Tracking 4 finished")


page_sequence = [
    Calibration,
    Introduction,
    Offer,
    ResultsWaitPage,
    Results
]
