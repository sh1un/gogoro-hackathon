import boto3
from langchain_community.chat_message_histories import DynamoDBChatMessageHistory


def create_dynamodb_table(table_name="session_table", partition_key="session_id"):
    # Get the service resource.
    dynamodb = boto3.resource("dynamodb")

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": partition_key, "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": partition_key, "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    # Wait until the table exists.
    table.meta.client.get_waiter("table_exists").wait(TableName=table_name)

    # Print out some data about the table.
    print(table.item_count)


if __name__ == "__main__":
    create_dynamodb_table()
    print("DynamoDB table created successfully!")
