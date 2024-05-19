import boto3
import os
import re
import logging

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

s3 = boto3.client('s3')

source_bucket = 'gogoro-hackton-replace-image'
dest_bucket = "gogoro-hackton-txt-123"

def lambda_handler(event, context):
    logger.info("Event: %s", event)
    for record in event['Records']:
        file_key = record['s3']['object']['key']
        logger.info("Processing file: %s", file_key)
        if file_key.endswith('.md'):
            download_path = f'/tmp/{file_key}'
            split_folder = '/tmp/split'
            
            # 下載文件
            logger.info("Downloading file from S3: %s", file_key)
            s3.download_file(source_bucket, file_key, download_path)
            
            # 確保 split 文件夾存在
            if not os.path.exists(split_folder):
                os.makedirs(split_folder)
                logger.info("Created split folder: %s", split_folder)
            
            # 處理文件
            with open(download_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            split_file_num = 1
            split_title = f"{split_file_num}_0_{file_key[:-3]}"
            split_content = ""
            have_content = False
            
            for line_num, line in enumerate(lines):
                if line.startswith("# "):
                    if have_content:
                        save_split_file(split_folder, file_key, split_file_num, split_title, split_content)
                        split_file_num += 1
                        split_content = ""
                        split_title = re.sub(r"\n|\s+|\\|/", "", line[2:])
                    split_content += line
                    have_content = False

                elif line.startswith("## "):
                    if have_content:
                        save_split_file(split_folder, file_key, split_file_num, split_title, split_content)
                        split_file_num += 1
                        split_content = ""
                        split_title = re.sub(r"\n|\s+|\\|/", "", line[3:])
                    split_content += line
                    have_content = False

                elif line.startswith("### "):
                    if have_content:
                        save_split_file(split_folder, file_key, split_file_num, split_title, split_content)
                        split_file_num += 1
                        split_content = ""
                        split_title = re.sub(r"\n|\s+|\\|/", "", line[4:])
                    split_content += line
                    have_content = False

                else:
                    if len(line) > 5:
                        have_content = True
                    split_content += line
            
            # 處理最後一個文件
            if have_content:
                save_split_file(split_folder, file_key, split_file_num, split_title, split_content)
            
            # 上傳拆分後的文件到目標 S3 存儲桶
            logger.info("Uploading split files to S3")
            upload_split_files(split_folder, dest_bucket, file_key)

def save_split_file(folder, file_key, file_num, title, content):
    # 去掉文件的擴展名
    split_file_path = f'{folder}/{file_num}_{title}.txt'
    with open(split_file_path, 'w', encoding='utf-8') as output:
        output.write(content)
    logger.info("Saved split file: %s", split_file_path)

def upload_split_files(folder, bucket, original_key):
    # 以文件名作為目錄
    file_basename = os.path.basename(original_key).rsplit('.', 1)[0]
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        s3.upload_file(file_path, bucket, f'{file_basename}/{filename}')
        logger.info("Uploaded file to S3: %s", f'{file_basename}/{filename}')
