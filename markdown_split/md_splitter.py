import boto3
import os
import re

s3 = boto3.client('s3')

source_bucket = 'gogoro-hackton-markdown'
dest_bucket = 'gogoro-hackton-data-source-123'
file_key = 'gogoro_s1.md'

def lambda_handler(event, context):
    # 获取上传的文件信息
    for record in event['Records']:
        file_key = record['s3']['object']['key']
        download_path = f'/tmp/{file_key}'
        split_folder = '/tmp/split'
        
        # 下载文件
        s3.download_file(source_bucket, file_key, download_path)
        
        # 确保split文件夹存在
        if not os.path.exists(split_folder):
            os.makedirs(split_folder)
        
        # 处理文件
        with open(download_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        split_file_num = 1
        split_title = f"{split_file_num}_0. {file_key[:-3]}"
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
        
        # 处理最后一个文件
        if have_content:
            save_split_file(split_folder, file_key, split_file_num, split_title, split_content)
        
        # 上传拆分后的文件到目标S3桶
        upload_split_files(split_folder, dest_bucket)

def save_split_file(folder, file_key, file_num, title, content):
    split_file_path = f'{folder}/{file_key[:-3]}_{file_num}_{title}.txt'
    with open(split_file_path, 'w', encoding='utf-8') as output:
        output.write(content)

def upload_split_files(folder, bucket):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        s3.upload_file(file_path, bucket, f'split/{filename}')

