import base64
import json
import logging
import os

import boto3
from chalice import Chalice

app_name = "FilterArcEventsApp"

app = Chalice(app_name=app_name)
app.log.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))

# fetching the kinesis endpoints and region from env, by default region = us-east-1
kinesis_endpoint_url = os.environ.get(
    "KINESIS_ENDPOINT_URL", "https://kinesis.us-east-1.amazonaws.com"
)
aws_region = os.environ.get("AWS_REGION", "us-east-1")

# using access keys for testing with local stack
aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID", "")
aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

# output stream where filtered events are streamed
output_stream_name = os.environ.get("OUTPUT_STREAM")

# Error stream where faulty events are streamed
error_stream_name = os.environ.get("ERROR_STREAM")
app.log.debug("### Environment variables {}".format(os.environ))


# function to create a client with aws for a specific service and region
def create_client(service):
    return boto3.client(
        service,
        endpoint_url=kinesis_endpoint_url,
        # un comment this code if testing on local with local stack
        # aws_access_key_id=aws_access_key_id,
        # aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region,
    )


# function for sending data to Kinesis at the absolute maximum throughput
def send_kinesis(kinesis_client, kinesis_stream_name, kinesis_record):
    kinesisRecords = [kinesis_record]
    # put the records to kinesis
    kinesis_client.put_records(Records=kinesisRecords, StreamName=kinesis_stream_name)


def decode_record(record):
    try:
        app.log.info("Decoded event with eventId {}".format(record["eventID"]))
        return base64.b64decode(record["kinesis"]["data"]).decode("utf-8")
    except TypeError as ex:
        app.log.error("Type Error: {}".format(ex))


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
            values = filter.split(".")
            expr = "del record"
            for element_name in values:
                expr = expr + "['" + element_name + "']"
            code = compile(expr, "delete_record", "exec")
            eval(code)
        return record
    except Exception as ex:
        app.log.warn(
            "Not able to remove the parameter: {}. Specified parameter not found in event.".format(
                ex
            )
        )
        return record


"""
This method filter the published records in CMSEvent Kinesis Queue.

:param
-event: The event stream
"""


@app.lambda_function()
def execute(event, context):
    # parameters to filter the stream, by default empty
    to_filter_parameters = os.environ.get("TO_FILTER_PARAMETERS", "")
    succeeded_record_count = 0
    failed_record_count = 0
    skipped_record_count = 0
    # create a client with kinesis
    kinesis = create_client("kinesis")

    app.log.info("Total events received: {}".format(len(event["Records"])))
    for record in event["Records"]:
        cms_event_json = decode_record(record)
        try:
            app.log.info(
                "Transforming the decoded event with partitionKey {} "
                "to json".format(record["kinesis"]["partitionKey"])
            )
            event_data = json.loads(cms_event_json)
            app.log.debug("event in json format {}".format(event_data))
            event_published_status = event_data["published"]
            app.log.info(
                "event received with status PUBLISHED = {}. Event will be filtered if PUBLISHED = False".format(
                    event_published_status
                )
            )
            if event_published_status == bool("true"):
                app.log.info(
                    "filtering the event by omitting parameter/'s' - {}".format(
                        to_filter_parameters
                    )
                )
                filtered_event = filter_event(
                    event_data, to_filter_parameters.split(",")
                )
                output_record = {
                    "PartitionKey": record["kinesis"]["partitionKey"],
                    "Data": json.dumps(filtered_event).encode("utf-8"),
                }
                app.log.debug(
                    "event after removing the specified parameters- {}".format(
                        filtered_event
                    )
                )
                app.log.debug(
                    "sending event to output stream {} having partition key as - {}".format(
                        output_stream_name, record["kinesis"]["partitionKey"]
                    )
                )
                send_kinesis(kinesis, output_stream_name, output_record)

                succeeded_record_count += 1
                app.log.info(
                    "Successfully send the decoded event with partitionKey {} to stream {}".format(
                        record["kinesis"]["partitionKey"], output_stream_name
                    )
                )
            else:
                skipped_record_count += 1
        except ValueError as ex:
            app.log.error("Error: Json decoding failed {}. Sending event to error stream named {}".
                          format(ex, error_stream_name))
            # send to Kinesis error stream
            error_record = {
                "PartitionKey": record["kinesis"]["partitionKey"],
                "Data":  record["kinesis"]["data"],
            }
            send_kinesis(kinesis, error_stream_name, error_record)
        except Exception as e:
            failed_record_count += 1
            app.log.error(
                "Failed to transform event having partitionKey {}. Error: {} Sending event to error stream - {}".format(
                    record["kinesis"]["partitionKey"], e, error_stream_name
                )
            )
            error_record = {
                "PartitionKey": record["kinesis"]["partitionKey"],
                "Data": record["kinesis"]["data"],
            }
            # send to Kinesis error stream
            send_kinesis(kinesis, error_stream_name, error_record)
    app.log.info(
        "received {} records , transformed={}, errors={}, skipped={}".format(
            len(event["Records"]),
            succeeded_record_count,
            failed_record_count,
            skipped_record_count,
        )
    )
