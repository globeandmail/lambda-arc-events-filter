# Build and test stage
FROM python:3.8-buster as build

# Upgrade pip
RUN pip install -U pip

WORKDIR /app

COPY . /app

#install dependencies
RUN pip install -r requirements.txt

#run unit tests
RUN python3 -m unittest tests.arcfeed_cms_filtertest

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
  FILE_NAME="SOPHI4-616-ArcCms_kinesis_feed_filter_.zip" \
  PACKAGE_NAME="deployment.zip" \
  AUTO_DEPLOY="false"

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip -qq awscliv2.zip && ./aws/install

# copy the lambda zip to S3 for terraform, need credentials to run successfullly
RUN if [ "${AUTO_DEPLOY}" = "true" ]; then \
    aws s3 cp ${PACKAGE_NAME} s3://${BUCKET}/${SUBDIRECTORY}/${FILE_NAME}; \
    fi