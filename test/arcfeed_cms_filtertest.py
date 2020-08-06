import base64
import json
import unittest

from app import execute, parse_kinesis_record

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
        print(is_published)
        self.assertNotEqual(is_published, bool('true'))

    def test_emptyInput(self):
        with self.assertRaises(SystemExit) as cm:
            execute("", "")

        self.assertEqual(cm.exception.code, 1)

    def test_emptyJson(self):
        with self.assertRaises(SystemExit) as cm:
            execute({}, "")

        self.assertEqual(cm.exception.code, 1)

if __name__ == '__main__':
    unittest.main()