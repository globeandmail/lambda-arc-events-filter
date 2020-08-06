# lambda-arc-events-filter
Filters ARC kinesis feed events

# deployment

# testing locally
1) Start the local-stack
```
sudo docker-compose up
```
2) Setup the dev env
```
sudo python3 -m venv dev_env
source dev_env/bin/activate
```
3) Install Chalice on local (if not present) 
``sudo pip install chalice``

4) Create a deployment package
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
awslocal kinesis put-record --stream-name develop_cmsfeed --data 'file://resources/test/sample_arc_message.json'  --partition-key 'uuidgen'
`

Output - 
Filtered message should be inserted in the output stream i.e filtered_cmsfeed