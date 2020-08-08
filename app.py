import base64
import json
import logging
import os
import sys

import boto3
from chalice import Chalice

app_name = 'CMSFilterApp'

app = Chalice(app_name=app_name)

# Initialize the logger
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(app_name)

# Set the log level from Environment variable LOG_LEVEL
if os.environ.get('LOG_LEVEL') is None:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(os.environ['LOG_LEVEL'])

kinesis_endpoint_url = os.environ.get('KINESIS_ENDPOINT_URL')
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
aws_region = os.environ.get('AWS_REGION')
to_filter_parameters = os.environ.get('TO_FILTER_PARAMETERS')
output_stream_name = os.environ.get('OUTPUT_STREAM')
logger.debug('##Environment variables {}'.format(os.environ))


# function to create a client with aws for a specific service and region
def create_client(service):
    return boto3.client(
        service,
        endpoint_url=kinesis_endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region)


# function for sending data to Kinesis at the absolute maximum throughput
def send_kinesis(kinesis_client, kinesis_stream_name, kinesis_record):
    kinesisRecords = [kinesis_record]
    # put the records to kinesis
    kinesis_client.put_records(
        Records=kinesisRecords,
        StreamName=kinesis_stream_name
    )


def parse_kinesis_record(record):
    try:
        logger.info("Decoded event with eventId {}".format(record['eventID']))
        return base64.b64decode(record["kinesis"]["data"]).decode('utf-8')
    except KeyError as ex:
        logger.error("Error: Key not found {}".format(ex))
    except TypeError as ex:
        logger.error("Type Error: {}".format(ex))


def filter_event(record, filter_parameter):
    try:
        for element in filter_parameter:
            values = element.split('.')
            if len(values) > 1:
                expr = 'del record'
                for element_name in values:
                    expr = expr + '[\'' + element_name + '\']'
                code = compile(expr, 'delete_record', 'exec')
                eval(code)
            else:
                del record[values[0]]
        return record
    except TypeError as ex:
        logger.error("Error: {}".format(ex))


"""
This method filter the published records in CMSEvent Kinesis Queue.

:param
-event: The event stream
"""


@app.lambda_function()
def execute(event, context):
    output = []
    succeeded_record_count = 0
    failed_record_count = 0
    # create a client with kinesis
    kinesis = create_client('kinesis')

    # if records are not present exit
    if "Records" not in event:
        logger.warning("Records not found in the arc cms event stream. Terminating the function")
        sys.exit(1)

    logger.info('Total events received: {}'.format(len(event['Records'])))
    for record in event['Records']:
        cms_event_json: str = parse_kinesis_record(record)
        try:
            logger.info('Transforming the decoded event with partitionKey {} '
                        'to json'.format(record["kinesis"]['partitionKey']))
            event_data: object = json.loads(cms_event_json)
            logger.debug("got the event {}".format(event_data))
            if event_data['published']:
                filtered_event = filter_event(event_data, to_filter_parameters.split(","))
                output_record = {
                    'PartitionKey': record["kinesis"]['partitionKey'],
                    'Data': base64.b64encode(json.dumps(filtered_event).encode('utf-8'))
                }
                send_kinesis(kinesis, output_stream_name, output_record)

                succeeded_record_count += 1
                logger.info('Successfully send the decoded event with partitionKey {}'
                            .format(record["kinesis"]['partitionKey']))
        except ValueError as ex:
            logger.error("Error: Json decoding failed {}".format(ex))
        except Exception as e:
            failed_record_count += 1
            logger.warning("Failed to transform event partitionKey {}. Error: {}".format(record['partitionKey'],
                                                                                         e.message))
    logger.info('Successful processed {} out of records {}, Transformed={}, errors={}'
                .format(len(output), len(event['Records']),
                        succeeded_record_count, failed_record_count))
    return {'records': output}
