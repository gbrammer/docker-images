"""
Handle event processing with generalized grizli.aws.lambda_handler
"""

def handler(event, context):
    from grizli.aws import lambda_handler
    lambda_handler.handler(event, context)
