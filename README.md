## lambda-arc-events-filter
Filters ARC kinesis feed events

## run test cases
`python3 -m unittest tests.arcfeed_cms_filtertest`

## deployment
`docker build -t arc-cms-filter:0.1 .`

## testing locally
1) Start the local-stack
```
docker-compose up
```

2) Setup the dev env
```
sudo python3 -m venv dev_env
source dev_env/bin/activate
```

3) Install Chalice on local (if not present) 
``sudo pip install chalice``

4) Create a deployment package
```edit .chalice/config.json with required env variables```

``chalice package .``

5)Create the lambda function
```
awslocal lambda create-function --function-name cmsFilterFunction --runtime python3.7 --role admin --handler app.execute --zip-file fileb://deployment.zip

awslocal lambda create-event-source-mapping --function-name cmsFilterFunction \
--event-source  arn:aws:kinesis:us-east-1:000000000000:stream/develop_cmsfeed \
--batch-size 1 --starting-position EARLIEST

awslocal lambda update-function-code --function-name cmsFilterFunction --zip-file fileb://deployment.zip
```

6) To list 
```
awslocal lambda list-functions
awslocal kinesis list-streams
```

7) Insert one sample message in the input stream i.e develop_cmsfeed
`
awslocal kinesis put-record --stream-name develop_cmsfeed --data 'file://resources/sample_arc_message.json'  --partition-key 'uuidgen'
`

Output - 
Filtered message should be inserted in the output stream i.e filtered_cmsfeed

## Env Variables

### KINESIS_ENDPOINT_URL
kinesis endpoint when testing locally it will be local-stack docker ip which can be find from running command
- `docker container inspect localstack_main`
else aws kinesis account ip address, e.g https://kinesis.us-east-1.amazonaws.com

### AWS_ACCESS_KEY_ID
kinesis aws access key or value as "iam" when using iam user 

### AWS_SECRET_ACCESS_KEY
kinesis aws secret access key or value as "iam" when using iam user

### AWS_REGION
aws kinesis account region, e.g "us-east-1"

### TO_FILTER_PARAMETERS
comma(',') separated list of parameters that needs to be omitted from input stream, e.g "operation, body.credits.by"
or by default its empty "" 

### OUTPUT_STREAM
output stream name where filtered events will be stored 

### LOG_LEVEL
logging level for the application by default DEBUG