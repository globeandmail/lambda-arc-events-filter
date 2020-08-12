import base64
import json
import logging
import os
import sys
import boto3

from chalice import Chalice

app_name = 'FilterArcEventsApp'

app = Chalice(app_name=app_name)

# Initialize the logger
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(app_name)

# Set the log level from Environment variable LOG_LEVEL, by default INFO
logger.setLevel(os.environ.get('LOG_LEVEL', logging.INFO))

kinesis_endpoint_url = os.environ.get('KINESIS_ENDPOINT_URL', 'https://kinesis.us-east-1.amazonaws.com')
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID', 'iam')
aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY', 'iam')
aws_region = os.environ.get('AWS_REGION', 'us-east-1')
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


def decode_record(record):
    try:
        logger.info("Decoded event with eventId {}".format(record['eventID']))
        return base64.b64decode(record["kinesis"]["data"]).decode('utf-8')
    except TypeError as ex:
        logger.error("Type Error: {}".format(ex))


def filter_event(record, filters):
    """
    A Generic method that removes the provided parameter from the given json record.
    :param record: Kinesis record in json representation
    :param filters: parameter in events that are required to be removed
    :return: filtered json record
    """
    try:
        for filter in filters:
            # splitting with '.' as we can have nested parameters that needs to be filtered, like body.type
            values = filter.split('.')
            if len(values) > 1:
                expr = 'del record'
                for element_name in values:
                    expr = expr + '[\'' + element_name + '\']'
                code = compile(expr, 'delete_record', 'exec')
                eval(code)
            else:
                # if only one filter parameter present then just fetch that and delete it
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
    # parameters to filter the stream, by default empty
    to_filter_parameters = os.environ.get('TO_FILTER_PARAMETERS', '')
    succeeded_record_count = 0
    failed_record_count = 0
    skipped_record_count = 0
    # create a client with kinesis
    kinesis = create_client('kinesis')

    # if records are not present exit
    if "Records" not in event:
        logger.error("Not able to get records from arc cms event stream. Terminating the function")
        sys.exit(1)

    logger.info('Total events received: {}'.format(len(event['Records'])))
    for record in event['Records']:
        cms_event_json = decode_record(record)
        try:
            logger.info('Transforming the decoded event with partitionKey {} '
                        'to json'.format(record["kinesis"]['partitionKey']))
            event_data = json.loads(cms_event_json)
            event_published_status = event_data['published']
            logger.debug("event received with status PUBLISHED = {}. Event will be filtered is published=false"
                         .format(event_published_status))
            if event_published_status == bool('true'):
                logger.debug("filtering the event by omitting parameter/'s' - {}".format(to_filter_parameters))
                filtered_event = filter_event(event_data, to_filter_parameters.split(","))
                output_record = {
                    'PartitionKey': record["kinesis"]['partitionKey'],
                    'Data': base64.b64encode(json.dumps(filtered_event).encode('utf-8'))
                }
                send_kinesis(kinesis, output_stream_name, output_record)

                succeeded_record_count += 1
                logger.info('Successfully send the decoded event with partitionKey {}'
                            .format(record["kinesis"]['partitionKey']))
            else:
                skipped_record_count += 1
        except ValueError as ex:
            logger.error("Error: Json decoding failed {}".format(ex))
        except Exception as e:
            failed_record_count += 1
            logger.error(
                "Failed to transform event partitionKey {}. Error: {}".format(record["kinesis"]['partitionKey'],
                                                                              e))
    logger.info('Successful processed {} records , Transformed={}, errors={}, skipped={}'
                .format(len(event['Records']),
                        succeeded_record_count, failed_record_count, skipped_record_count))
