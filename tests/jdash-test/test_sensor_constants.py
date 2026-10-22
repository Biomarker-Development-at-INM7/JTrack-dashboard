from jdash.config import constants


def test_home_beacon_is_available_in_sensor_registries():
    assert constants.homeBeacon == "homeBeacon"
    assert constants.sensor_list[constants.homeBeacon] == "hb"
    assert ("homeBeacon", "homeStation") in constants.SENSORS_LIST
    assert ("homeBeacon", "homeStation") in constants.SENSORS_LIST_DB


def test_low_recording_frequency_options_are_not_available():
    assert (1, "1 Hz") not in constants.RECORDING_FREQUENCIES
    assert (5, "5 Hz") not in constants.RECORDING_FREQUENCIES
    assert (10, "10 Hz") not in constants.RECORDING_FREQUENCIES


def test_motion_sensors_are_active_only():
    assert ("accelerometer", "accelerometer") in constants.SENSORS_LIST
    assert ("gyroscope", "gyroscope") in constants.SENSORS_LIST
    assert ("accelerometer", "accelerometer") not in constants.PASSIVE_SENSORS_LIST
    assert ("gyroscope", "gyroscope") not in constants.PASSIVE_SENSORS_LIST
