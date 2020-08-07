import json
import unittest
from typing import Dict, List

from app import execute, parse_kinesis_record, filter_event

# the test data file contains AWS Kinesis stream event as json.
validDataFile = '../resources/test/arcfeed_kinesis_message.json'
invalidDataFile = '../resources/test/arcfeed_kinesis_invalid_message.json'
app_name = 'lambda-arcfeed-cms-filter'


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
        output: str = parse_kinesis_record(self.validRecord)
        event_data: object = json.loads(output)
        is_published: object = event_data['published']
        self.assertTrue(is_published)

    def test_invalidRecord(self):
        output: str = parse_kinesis_record(self.invalidRecord)
        event_data: object = json.loads(output)
        is_published = event_data['published']
        self.assertNotEqual(is_published, bool('true'))

    def test_emptyInput(self):
        with self.assertRaises(SystemExit) as cm:
            execute("", "")

        self.assertEqual(cm.exception.code, 1)

    def test_emptyJson(self):
        with self.assertRaises(SystemExit) as cm:
            execute({}, "")

        self.assertEqual(cm.exception.code, 1)

    def test_filterFunction(self):
        output = parse_kinesis_record(self.validRecord)
        record = json.loads(output)
        to_filter_parameter = ["operation","type"]
        filtered_event = filter_event(record, to_filter_parameter)
        with self.assertRaises(KeyError) as raises:
            return filtered_event["operation"]
        self.assertEqual(raises.exception.__doc__, "Mapping key not found.")

    def test_filterFunction_withNestedJsonObject(self):
        global finalParamterList
        data: str = """{"business_id": "fNG","full_address": "PA 15106",
        "hours": {"Monday": {"close": "23:00","open": "11:00"}}, "credits": {"by": [
        {"type": "author","name": "Ben Fox","org": "The Associated Press"}
        ]
        }}"""
        rec = json.loads(data)
        print("before: " + str(rec))
        to_filter_parameter = ["hours.Monday.close","full_address"]
        for element in to_filter_parameter:
            values = element.split('.')
            if len(values) > 1:
                del rec[values[0]][values[1]][values[2]]
            else:
                del rec[values[0]]
        print("after: " + str(rec))

if __name__ == '__main__':
    unittest.main()