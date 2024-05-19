import json
import boto3
import base64
import re

# Configuration
SERVICE_NAME = "bedrock-runtime"
REGION_NAME = "us-west-2"
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

s3_client = boto3.client('s3')

def invoke_claude_3_multimodal(prompt: str, base64_image_data: str) -> str:
    client = boto3.client(service_name=SERVICE_NAME, region_name=REGION_NAME)
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": base64_image_data}
                    },
                ],
            }
        ],
    }
    try:
        response = client.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request_body),
        )
        result = json.loads(response.get("body").read())
        return result['content'][0]['text'] if result.get("content") else ""
    except Exception as e:
        print(f"Error invoking the model: {type(e).__name__}: {e}")
        raise

def process_and_describe_image(image_data: bytes, prompt: str):
    base64_image_data = base64.b64encode(image_data).decode('utf-8')
    description = invoke_claude_3_multimodal(prompt, base64_image_data)
    return description

def lambda_handler(event, context):
    # The bucket and key from the triggering event
    source_bucket = 'gogoro-hackton-markdown-123'
    destination_bucket = 'gogoro-hackton-replace-image'
    key = event['Records'][0]['s3']['object']['key']
    file_name_prefix = key.split('.')[0]  # Extract prefix like s3_3

    # Download the markdown file from S3
    response = s3_client.get_object(Bucket=source_bucket, Key=key)
    markdown_content = response['Body'].read().decode('utf-8')

    # Extract all image links from the markdown file
    image_links = re.findall(r'!\[\]\((https://[^\)]+)\)', markdown_content)

    updated_content = markdown_content

    for link in image_links:
        # Parse the S3 URL
        s3_url_pattern = r'https://([^/]+)\.s3\.([^/]+)\.amazonaws\.com/(.+)'
        match = re.match(s3_url_pattern, link)
        if match:
            image_bucket = match.group(1)
            image_key = match.group(3)

            # Download the image
            image_response = s3_client.get_object(Bucket=image_bucket, Key=image_key)
            image_data = image_response['Body'].read()

            # Generate description using AI model
            prompt = '''我會給你很多關於Gogoro的圖片，你需要盡可能的精確描述這些圖片顯示什麼東西，請用繁體中文15字以內描述這張圖, 並且取名為Description: '''
            description = process_and_describe_image(image_data, prompt)

            # Replace the placeholder in markdown with the generated description
            updated_content = updated_content.replace(f'![]({link})', f'![Image {description}]({link})')

    # Upload the updated markdown file back to S3
    new_key = f"{file_name_prefix}.md"
    s3_client.put_object(Bucket=destination_bucket, Key=new_key, Body=updated_content.encode('utf-8'))

    return {
        'statusCode': 200,
        'body': json.dumps(f'Successfully updated {key} and saved as {new_key} in bucket {destination_bucket}')
    }
