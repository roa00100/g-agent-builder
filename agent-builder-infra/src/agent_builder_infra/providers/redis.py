from redis import Redis


class RedisProvider:
    """Redis 접속. 클라이언트(안에 연결 풀이 있다)를 갖는다.

    연결은 처음 쓸 때 만들어진다. 만드는 것만으로는 Redis 에 붙지 않는다.
    """

    def __init__(self, url: str) -> None:
        # decode_responses=True: 값을 bytes 가 아니라 str 로 돌려준다.
        # 저장할 값은 문자열·JSON 이라 str 이 맞다.
        self.client: Redis = Redis.from_url(url, decode_responses=True)

    def ping(self) -> bool:
        """붙으면 True. 붙지 못하면 False 가 아니라 예외가 난다 — 까닭을 잃지 않는다."""
        return self.client.ping()

    def close(self) -> None:
        self.client.close()
