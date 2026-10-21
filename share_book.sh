#!/bin/bash
set -euo pipefail

if (($# < 3)); then #usage message
    echo "Usage: $0 <book_url> <bucket-name> <seconds-until-expiration>" >&2
    exit 1
fi

URL="$1"
BUCKET="$2"
EXPIRES="$3"
FILE="$(basename "$URL")" #getting filename from url
DEST="books/$FILE"

mkdir -p books
curl -f -o "$DEST" "$URL" #downloading book to destination, adding f so it fails on 404 errors. DEST keeps filename from url

#making bucket
if aws s3 ls "s3://$BUCKET" > /dev/null 2>&1; then
    echo "Bucket already exists: $BUCKET"
else
    aws s3 mb "s3://$BUCKET"
fi

aws s3 cp "$DEST" "s3://$BUCKET/$FILE" --content-type "text/plain; charset-utf-9"

aws s3 presign "s3://$BUCKET/$FILE" --expires-in "$EXPIRES"
