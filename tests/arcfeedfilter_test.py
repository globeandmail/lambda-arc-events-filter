import json

import pytest

from app import decode_record, filter_event

# the test data file contains AWS Kinesis stream event
validDataFile = "tests/resources/arcfeed_kinesis_message.json"
invalidDataFile = "tests/resources/arcfeed_kinesis_invalid_message.json"
app_name = "lambda-arcfeed-events-filter"


def test_valid_record():
    with open(validDataFile) as json_file:
        validRecord = json.load(json_file)
    output = decode_record(validRecord)
    event_data = json.loads(output)
    assert event_data["published"]


def test_invalid_record():
    with open(invalidDataFile) as json_file:
        invalidRecord = json.load(json_file)
    output = decode_record(invalidRecord)
    event_data: object = json.loads(output)
    assert not event_data["published"]


def test_filter_function():
    with open(validDataFile) as json_file:
        validRecord = json.load(json_file)
    output = decode_record(validRecord)
    record = json.loads(output)
    to_filter_parameter = ["operation", "type"]
    filtered_event = filter_event(record, to_filter_parameter)
    with pytest.raises(KeyError):
        assert filtered_event["operation"]


def test_filter_function_with_nested_object():
    with open(validDataFile) as json_file:
        validRecord = json.load(json_file)
    output = decode_record(validRecord)
    record = json.loads(output)
    to_filter_parameter = ["body.credits.by"]
    filtered_event = filter_event(record, to_filter_parameter)
    with pytest.raises(KeyError):
        assert filtered_event["body.credits.by"]


def test_filter_function_no_parameter_passed():
    with open(validDataFile) as json_file:
        validRecord = json.load(json_file)
    output = decode_record(validRecord)
    record = json.loads(output)
    to_filter_parameter = []
    filtered_event = filter_event(record, to_filter_parameter)
    assert record == filtered_event
