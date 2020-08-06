# Build and test stage
FROM python:3.8-buster as build

# Upgrade pip
RUN pip install -U pip

COPY . /app

WORKDIR /app

#install dependencies
RUN pip install -r requirements.txt


RUN ["cp", "test/arcfeed_cms_filtertest.py", "arcfeed_cms_filtertest.py"]

#run unit tests
RUN python arcfeed_cms_filtertest.py


#Check styling
RUN flake8 app.py

#create deployment.zip
RUN chalice package .

# Uploading stage
FROM python:3.8-buster as upload

COPY --from=build /app /app

WORKDIR /app

ENV AWS_DEFAULT_REGION="us-east-1" \
  BUCKET="pd-sophi-artifacts" \
  SUBDIRECTORY="platform/warehousing/serverless" \
  FILE_NAME="SOPHI-2386_warehousing_clickstream_events.zip" \
  PACKAGE_NAME="deployment.zip" \
  AUTO_DEPLOY="false"

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip && ./aws/install

# copy the lambda zip to S3 for terraform, need credentials to run successfullly
RUN if [ "${AUTO_DEPLOY}" = "true" ]; then \
    aws s3 cp ${PACKAGE_NAME} s3://${BUCKET}/${SUBDIRECTORY}/${FILE_NAME}; \
    fi