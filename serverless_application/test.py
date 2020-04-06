import json

def main_handler(event, context):
    return {
        "statusCode": 200,
        "body": json.dumps('Cheers from AWS Lambda!!')
    }
