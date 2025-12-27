# src/core/s3_handler.py
import boto3
from src.core.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME
from src.core.logger import logger

def get_s3_client():
    try:
        client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
            endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com"
        )
        return client
    except Exception as e:
        logger.error(f"Error creating S3 client: {e}")
        return None

def get_pdf_url(pdf_filename: str) -> str | None:
    client = get_s3_client()
    if not client:
        return None
    try:
        url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET_NAME,
                'Key': pdf_filename,
                'ResponseContentType': 'application/pdf',
                'ResponseContentDisposition': f'attachment; filename="{pdf_filename.split("/")[-1]}"'
            },
            ExpiresIn=3600  # 1 hour
        )
        logger.info(f"Generated S3 presigned URL for {pdf_filename}")
        return url
    except Exception as e:
        logger.error(f"Error generating presigned URL: {e}")
        return None