import os
from io import BytesIO

import boto3


def r2_configurado():
    required = [
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET_NAME",
    ]
    return all(os.environ.get(name) for name in required)


def r2_bucket_name():
    return os.environ["R2_BUCKET_NAME"]


def r2_client():
    account_id = os.environ["R2_ACCOUNT_ID"]
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def enviar_arquivo_r2(caminho_local, chave, content_type=None):
    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type

    r2_client().upload_file(
        caminho_local,
        r2_bucket_name(),
        chave,
        ExtraArgs=extra_args or None,
    )
    return f"r2://{r2_bucket_name()}/{chave}"


def baixar_arquivo_r2(uri):
    prefix = "r2://"
    if not uri.startswith(prefix):
        raise ValueError("URI R2 invalida")

    bucket_e_chave = uri[len(prefix):]
    bucket, chave = bucket_e_chave.split("/", 1)
    buffer = BytesIO()
    r2_client().download_fileobj(bucket, chave, buffer)
    buffer.seek(0)
    return buffer

