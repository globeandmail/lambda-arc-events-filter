import json
import unittest

from app import decode_record, filter_event

# the test data file contains AWS Kinesis stream event
validDataFile = 'tests/resources/arcfeed_kinesis_message.json'
invalidDataFile = 'tests/resources/arcfeed_kinesis_invalid_message.json'
app_name = 'lambda-arcfeed-events-filter'


class UnitTests(unittest.TestCase):
    validRecord: object

    # loads the data from json file
    def setUp(self):
        super(UnitTests, self).setUp()

        with open(validDataFile) as json_file:
            self.validRecord = json.load(json_file)

        with open(invalidDataFile) as json_file:
            self.invalidRecord = json.load(json_file)

    def test_validRecord(self):
        output: str = decode_record(self.validRecord)
        event_data: object = json.loads(output)
        is_published: object = event_data['published']
        self.assertTrue(is_published)

    def test_invalidRecord(self):
        output: str = decode_record(self.invalidRecord)
        event_data: object = json.loads(output)
        is_published = event_data['published']
        self.assertNotEqual(is_published, bool('true'))

    def test_filterFunction(self):
        output = decode_record(self.validRecord)
        record = json.loads(output)
        to_filter_parameter = ["operation","type"]
        filtered_event = filter_event(record, to_filter_parameter)
        with self.assertRaises(KeyError) as raises:
            return filtered_event["operation"]
        self.assertEqual(raises.exception.__doc__, "Mapping key not found.")

    def test_filterFunction_withNestedJsonObject(self):
        output = decode_record(self.validRecord)
        record = json.loads(output)
        to_filter_parameter = ["body.credits.by"]
        filtered_event = filter_event(record, to_filter_parameter)
        with self.assertRaises(KeyError) as raises:
            return filtered_event["body.credits.by"]
        self.assertEqual(raises.exception.__doc__, "Mapping key not found.")

    def test_filterFunction_whenNoParameterPassed(self):
        output = decode_record(self.validRecord)
        record = json.loads(output)
        to_filter_parameter = []
        filtered_event = filter_event(record, to_filter_parameter)
        self.assertEqual(record, filtered_event)


if __name__ == '__main__':
    unittest.main()