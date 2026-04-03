import time


def lambda_handler(event, context):
    params = event.get("queryStringParameters", {}) or {}

    if params.get("except") == "true":
        raise Exception("Intentional exception from Lambda")

    if params.get("status") == "500":
        return {"statusCode": 500, "body": "Intentional 500 from Lambda"}

    if params.get("timeout") == "true":
        time.sleep(35)
        return {"statusCode": 200, "body": "Should never reach here"}

    return {"statusCode": 200, "body": "Hello from Python 3.14 Lambda!"}
