from datetime import datetime
from pathlib import Path
import logging

from . import state
from .data import ABDataPoint

logger = logging.getLogger("airbrakes_data")


class Airbrakes:

    MOTOR_BURN_TIME = 1.7  # Time from liftoff detected to control start

    # this is the pin that the servo's data wire is plugged into
    SERVO_PIN = 32

    # these angles represent open and closed for the airbrakes, they are arbitrary
    SERVO_CLOSED_DUTY = 9.2
    SERVO_OPEN_DUTY = 6.3

    def __init__(self, mock_servo=False, mock_imu=False):

        self.ready_to_shutdown = False

        if mock_servo:
            from .mock import MockServoInterface as ServoInterface
        else:
            from .hardware import ServoInterface

        self.servo = ServoInterface.Servo(self.SERVO_PIN, 3.5, 11.5)

        if mock_imu:
            from .mock import MockMSCLInterface

            self.interface = MockMSCLInterface.MockMSCLInterface(self.servo)

        else:
            from .hardware import MSCLInterface

            now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")

            log_folder = Path("./logs")
            log_folder.mkdir(parents=True, exist_ok=True)

            self.interface = MSCLInterface.MSCLInterface(
                "/dev/ttyACM0",
                open(f"./logs/{now}_rawLORDlog.csv", "w+"),
                open(f"./logs/{now}_estLORDlog.csv", "w+"),
            )

        self.interface.start_logging_loop_thread()

        self.to_state(state.StandbyState)

    def to_state(self, new_state):
        logger.info("State Change,%s", new_state.__name__)
        self.state = new_state(self)

    def process_data_point(self, data_point: ABDataPoint):
        self.state.process(data_point)

    def update(self):
        data_point = self.interface.pop_data_point()
        if data_point == "Done":
            self.ready_to_shutdown = True
            logger.info("Done")
        elif data_point is not None:
            # log as csv
            logger.info("Data point,%s,%s", data_point.altitude, data_point.accel)
            self.process_data_point(data_point)

    def shutdown(self):
        self.interface.stop_logging_loop()
