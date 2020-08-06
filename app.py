import boto3
import base64
import json
import logging
import sys
from chalice import Chalice
from os import environ

app_name = 'CMSFilterApp'

app = Chalice(app_name=app_name)

# Initialize the logger
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(app_name)

# Set the log level from Environment variable LOG_LEVEL
if environ.get('LOG_LEVEL') is not None:
    logger.setLevel(environ.get('LOG_LEVEL'))
else:
    logger.setLevel(logging.DEBUG)


# function to create a client with aws for a specific service and region
def create_client(service, region):
    return boto3.client(
        service,
        endpoint_url='http://172.22.0.2:4568',
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy',
        region_name=region)


# function for sending data to Kinesis at the absolute maximum throughput
def send_kinesis(kinesis_client, kinesis_stream_name, kinesis_shard_count, kinesisRecord):
    kinesisRecords = []  # empty list to store data
    currentBytes = 0  # counter for bytes
    rowCount = 0  # as we start with the first
    sendKinesis = False  # flag to update when it's time to send data
    shardCount = 1  # shard counter
    kinesisRecords.append(kinesisRecord)  # add the object to the list
    # put the records to kinesis
    response = kinesis_client.put_records(
        Records=kinesisRecords,
        StreamName=kinesis_stream_name
    )


def parse_kinesis_record(record):
    try:
        logger.debug('Processing record {}'.format(record["kinesis"]["data"]))
        cms_event_json: str = base64.b64decode(record["kinesis"]["data"]).decode('utf-8')
        logger.info("Decoded event with eventId {}".format(record['eventID']))
        return cms_event_json
    except KeyError as ex:
        logger.error("Error: Key not found {}".format(ex))
    except TypeError as ex:
        logger.error("Type Error: {}".format(ex))


"""
This method filter the published records in CMSEvent Kinesis Queue.

:param
-event: The event stream
"""


@app.route('/')
def execute(event, context):
    global cms_event_json
    logger.debug('##Environment variables {}'.format(environ))
    output = []
    succeeded_record_count = 0
    failed_record_count = 0
    # create a client with kinesis
    kinesis = create_client('kinesis', 'us-east-1')
    # Output data stream
    output_stream_name = "filtered_cmsfeed"
    stream_shard_count = 1

    # if records are not present exit
    if "Records" not in event:
        logger.warning("Records not found in the arc cms event stream. Terminating the function")
        sys.exit(1)

    logger.info('Total events received: {}'.format(len(event['Records'])))
    for record in event['Records']:
        print(record)
        cms_event_json = parse_kinesis_record(record)
        try:
            logger.debug('Transforming the decoded event with partitionKey {} '
                         'to json'.format(record["kinesis"]['partitionKey']))
            event_data = json.loads(cms_event_json)
            if event_data['published']:
                output_record = {
                    'PartitionKey': record["kinesis"]['partitionKey'],
                    'Data': base64.b64encode(json.dumps(event_data).encode('utf-8'))
                }
                send_kinesis(kinesis, output_stream_name, stream_shard_count, output_record)

                succeeded_record_count += 1
                logger.info('Successfully send the decoded event with partitionKey {}'
                            .format(record["kinesis"]['partitionKey']))
        except ValueError as ex:
            logger.error("Error: Json decoding failed {}".format(ex))
        except Exception as e:
            for error_message in e.error_messages:
                output_record = {
                    'partitionKey': record['partitionKey'],
                    'result': 'ProcessingFailed',
                    'data': record["data"]
                }
                failed_record_count += 1
                logger.warning("Failed to transform event partitionKey {}. Error: {}".format(record['partitionKey'],
                                                                                             error_message))
    logger.info('Successful processed {} out of records {}, Transformed={}, errors={}'
                .format(len(output), len(event['Records']),
                        succeeded_record_count, failed_record_count))
    return {'records': output}
