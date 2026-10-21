#!usr/bin/env python3
import os
import logging
import sys
import boto3
import requests
import time
import json
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

s3 = boto3.client("s3", region_name="us-east-1")

def parse_args():
    '''
    parses arguments from command line and stores them as variables. logs an error if less than three arguments are passed
    '''
    if len(sys.argv) < 4:
        log.error('Not enough arguments')
    else:
        list_file = sys.argv[1]
        index_path = sys.argv[2]
        bucket = sys.argv[3]
    return list_file, index_path, bucket

def download_books(list_file, dest_dir):
    '''
    reads the urls from the list file, skipping empty lines, then iterates over a list of them to retrieve the file paths for books. 
    downloads a each book using the requests package before saving it in destination directory and returning a list of the local paths of books.
    does not re-download if downloads are already completed.
    '''
    os.makedirs(dest_dir, exist_ok=True)
    with open(list_file) as f:
        urls = []
        for line in f:
            line = line.strip() #skipping empty lines
            if line:
                urls.append(line)
    paths = []
    for url in urls:
        filename = url.rstrip("/").split("/")[-1] #removing trailing dashes and getting last part of url
        path = os.path.join(dest_dir, filename) #path name
        if os.path.exists(path):
            log.info('Already downloaded')
            paths.append(path)
        else:
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()  # raise an error for 404 
                with open(path, "wb") as out: #saving contents to file
                    out.write(response.content)
                    log.info(f"Downloaded {url} --> {path}")
                    paths.append(path)
            except requests.RequestException as e:
                log.error(f"Error downloading {url}: e")
            time.sleep(1) 
    return paths

def create_bucket(bucket):
    '''
    creates bucket with argument from parse_args as name. 
    returns true if bucket already exists or if bucket was successfully created,
    returns false otherwise.
    '''
    try:
        s3.head_bucket(Bucket=bucket)
        log.info('Bucket already exists.')
        return True
    except ClientError:
        try:
            s3.create_bucket(Bucket=bucket)
            log.info('Created bucket.')
            return True
        except ClientError as e:
            log.error('Error creating bucket: ', e)
            return False

def make_public(bucket):
    '''
    turns off block public access before attaching a legible bucket policy
    '''
    try:
        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": False,                
                "IgnorePublicAcls": False,
                "BlockPublicPolicy": False,
                "RestrictPublicBuckets": False,
            },
        )        
        policy = {
            "Version": "2012-10-17",            
            "Statement": [
                {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket}/*",
                }
            ],
        }
        s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
        return True
    except ClientError as e:
        return False

def upload_files(bucket, file_paths):
    '''
    uploading each file to bucket as plain text. logs and continues if upload fails
    returns number of files uploaded successfully
    '''
    count = 0
    for path in file_paths:
        key=path.split("/")[-1]
        try:
            with open(path, 'rb') as f:
                s3.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=f,
                    ContentType="text/plain; charset=utf-8"
                )
            log.info(f"Uploaded to s3://{bucket}/{key}")
            count+=1
        except ClientError as e:
            log.error(f"Error uploading object: {e}")
    return count

def upload_index(bucket, index_path):
    '''
    takes in index_path and bucket to upload onto a webpage
    returns true on success and false otherwise, raising file not found error if file is not found
    '''
    try:
        with open(index_path, "rb") as f:
            s3.put_object(
                Bucket=bucket,
                Key="index.html",
                Body=f,
                ContentType="text/html",  # display as a web page
            )
        return True
    except FileNotFoundError:
        log.error("Local file not found: ", index_path)
        return False
    except (ClientError, BotoCoreError) as e:
        log.error(f"Error uploading {index_path}: {e}")
        return False

def main():
    '''
    parses arguments list_files, bucket, and index_path from command line
    downloads books and returns a list of paths (books directory)
    creates a bucket and makes it public
    uploads files to top level of bucket then uploads it to a webpage using index.html as key
    stops with sys.exit(1) if all downloads fail or bucket is not created/made public
    returns none
    '''
    list_file, index_path, bucket = parse_args()
    paths = download_books(list_file, "books")
    if not paths:
        log.error("No books were downloaded; nothing to upload.")
        sys.exit(1)
    if not create_bucket(bucket):
        log.error('Could not create bucket')
        sys.exit(1)
    if not make_public(bucket):
        sys.exit(1)
        log.error('Could not make bucket public')
    else:
        uploaded = upload_files(bucket, paths)
        index_ok = upload_index(bucket, index_path)
        log.info(f"Successfully uploaded {uploaded} books")
    log.info(f"Public URL: https://{bucket}.s3.amazonaws.com/index.html")


if __name__ == "__main__":
    main()







