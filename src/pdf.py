import json
import boto3
import pdfplumber
import fitz
from markdown_strings import header, image
import io
import os
import logging

s3 = boto3.client('s3')

dest_bucket = 'gogoro-hackton-markdown-123'
img_bucket = 'gogoro-hackton-extracted-image-123'

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        # Extract bucket and key from the event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        logger.info(f"Bucket: {bucket}, Key: {key}")
        
        pdf_extractor(bucket, key)
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        raise e

def pdf_extractor(bucket, pdf_key):
    try:
        # Download PDF from S3
        pdf_obj = s3.get_object(Bucket=bucket, Key=pdf_key)
        pdf_data = pdf_obj['Body'].read()
        filename = os.path.basename(pdf_key)
        prefix = filename.split('.')[0]
        
        # Open the PDF with pdfplumber
        pdf = pdfplumber.open(io.BytesIO(pdf_data))
        pdf_4img = fitz.open(stream=pdf_data, filetype="pdf")

        tolerance = 5
        min_width, min_height = 25, 25

        md_content = io.StringIO()

        for page_num, page in enumerate(pdf.pages):
            logger.info(f"Processing page {page_num}")
            x0_now = 0
            top_now = 0

            objects = []
            words = page.extract_words()
            for word in words:
                if word["top"] - top_now > tolerance:
                    top_now = word["top"]
                x0_now = word["x0"]

                type = "word"
                size = word["bottom"] - word["top"]
                if size > 19.5:
                    type = "title"
                elif size > 15:
                    type = "subtitle"
                elif size > 14:
                    type = "subsubtitle"
                else:
                    type = "content"

                data = word["text"].replace('●', '- ')
                obj = {
                    "type": type,
                    "data": data,
                    "pos": (x0_now, top_now),
                    "size": size
                }
                objects.append(obj)

            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    data = ""
                    for col in row:
                        if col:
                            data += col + " "
                    data += "\n"
                obj = {
                    "type": "table",
                    "data": data,
                    "pos": (x0_now, top_now)
                }
                objects.append(obj)

            page_4img = pdf_4img[page_num]
            image_info = page_4img.get_image_info(xrefs=True)
            if not image_info:
                logger.info(f"Processing page {page_num} with no images found")
            for idx, info in enumerate(image_info):
                x0, y0, x1, y1 = info["bbox"]

                width = x1 - x0
                height = y1 - y0
                if width <= min_width or height <= min_height:
                    continue

                pixmap = fitz.Pixmap(pdf_4img, info["xref"])
                img_bytes = io.BytesIO()
                img_bytes.write(pixmap.tobytes("jpg"))
                img_bytes.seek(0)
                
                # Generate unique image key with prefix based on pdf_key
                img_key = f"{prefix}/page{page_num+1}_img{idx+1}.jpg"
                
                s3.put_object(Body=img_bytes.getvalue(), Bucket=img_bucket, Key=img_key)

                obj = {
                    "type": "image",
                    "data": img_key,
                    "pos": (x1, y0)
                }
                objects.append(obj)
            objects.sort(key=lambda x: (x["pos"][1], x["pos"][0]))

            type_now = "word"
            top_now = 0
            for obj in objects:
                if type_now == obj["type"] and obj["pos"][1] - top_now < 5:
                    md_content.write(obj["data"])
                else:
                    type_now = obj["type"]
                    top_now = obj["pos"][1]
                    md_content.write("\n")
                    if obj["type"] == "title":
                        md_content.write(header(obj["data"], 1))
                    elif obj["type"] == "subtitle":
                        md_content.write(header(obj["data"], 2))
                    elif obj["type"] == "subsubtitle":
                        md_content.write(header(obj["data"], 3))
                    elif obj["type"] == "content":
                        md_content.write(obj["data"])
                    elif obj["type"] == "table":
                        md_content.write(obj["data"])
                    elif obj["type"] == "image":
                        md_content.write(image("", f"https://{img_bucket}.s3.us-west-2.amazonaws.com/{obj['data']}"))

        result_data = md_content.getvalue().encode('utf-8')
        markdown_key = f"{prefix}.md"
        s3.put_object(Body=result_data, Bucket=dest_bucket, Key=markdown_key)
        
        pdf.close()
        pdf_4img.close()
        
    except s3.exceptions.NoSuchKey as e:
        logger.error(f"The specified key does not exist: {pdf_key}")
        raise e
    except Exception as e:
        logger.error(f"An error occurred in pdf_extractor: {str(e)}")
        raise e
