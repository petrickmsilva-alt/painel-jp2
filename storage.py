import os
import mimetypes
from io import BytesIO
from urllib.parse import quote

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

    kwargs = {}
    if extra_args:
        kwargs["ExtraArgs"] = extra_args

    r2_client().upload_file(caminho_local, r2_bucket_name(), chave, **kwargs)
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


def gerar_url_temporaria_r2(uri, nome_arquivo=None, force_download=False, expires_in=300):
    prefix = "r2://"
    if not uri.startswith(prefix):
        raise ValueError("URI R2 invalida")

    bucket_e_chave = uri[len(prefix):]
    bucket, chave = bucket_e_chave.split("/", 1)
    params = {
        "Bucket": bucket,
        "Key": chave,
    }

    if nome_arquivo:
        modo = "attachment" if force_download else "inline"
        nome_codificado = quote(nome_arquivo)
        params["ResponseContentDisposition"] = f"{modo}; filename*=UTF-8''{nome_codificado}"
        content_type = mimetypes.guess_type(nome_arquivo)[0]
        if content_type:
            params["ResponseContentType"] = content_type

    return r2_client().generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=expires_in,
    )
