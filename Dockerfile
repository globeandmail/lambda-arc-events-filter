# Build and test stage
FROM python:3.8-buster as build

#env variable with default value
ARG aws_default_region="us-east-1"
ENV AWS_DEFAULT_REGION=$aws_default_region

# Upgrade pip
RUN pip install -U pip

WORKDIR /app

COPY . /app

#install dependencies
RUN pip install -r requirements-dev.txt

#check styling
RUN flake8 app.py

#check formatting
RUN black .

#run unit tests
RUN py.test -v

#create deployment.zip
RUN chalice package .

# uploading stage
FROM python:3.8-buster as upload

COPY --from=build /app /app

WORKDIR /app

ARG bucket="arc-cms"
ARG file_name="ArcEvent_Kinesis_Filter.zip"
ARG package_path="deployment.zip"
ARG auto_deploy="false"

ENV BUCKET=$bucket \
  FILE_NAME=$file_name \
  PACKAGE_NAME=$package_path \
  AUTO_DEPLOY=$auto_deploy

# for getting the AWS CLI to upload the zip file
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip -qq awscliv2.zip && ./aws/install

# copy the lambda zip to S3 for terraform, need credentials to run successfullly
RUN if [ "${AUTO_DEPLOY}" = "true" ]; then \
    aws s3 cp ${PACKAGE_NAME} s3://${BUCKET}/${FILE_NAME}; \
    fi