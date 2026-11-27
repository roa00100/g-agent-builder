import boto3
from botocore.client import BaseClient
from botocore.config import Config


class ObjectStorageProvider:
    """오브젝트 스토리지 접속(S3 API). boto3 클라이언트와 버킷 이름을 갖는다.

    S3 API 로만 말하므로 SeaweedFS 를 다른 S3 호환 스토리지로 바꿔도 그대로 쓴다.
    클라이언트를 만드는 것만으로는 스토리지에 붙지 않는다.
    """

    def __init__(
        self, endpoint_url: str, access_key: str, secret_key: str, bucket: str
    ) -> None:
        self.bucket = bucket
        self.client: BaseClient = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            # SeaweedFS 는 지역을 쓰지 않지만 boto3 는 서명에 지역이 필요하다.
            # 아무 값이나 된다.
            region_name="us-east-1",
            # path: 주소를 http://호스트/버킷/키 로 만든다. 기본(virtual)은
            # http://버킷.호스트/키 라서 로컬 주소에서는 이름 풀이가 안 된다.
            config=Config(s3={"addressing_style": "path"}),
        )

    def ping(self) -> bool:
        """버킷에 닿으면 True. 버킷이 없거나 키가 틀리면 False 가 아니라 예외가 난다."""
        self.client.head_bucket(Bucket=self.bucket)
        return True

    def close(self) -> None:
        self.client.close()
