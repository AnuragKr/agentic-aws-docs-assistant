from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

from app.core.config import Settings


def create_opensearch_client(settings: Settings) -> OpenSearch:
    hosts = [{"host": settings.opensearch_host, "port": settings.opensearch_port}]
    use_ssl = settings.opensearch_use_ssl

    if settings.opensearch_auth_mode == "aws_sigv4":
        import boto3

        credentials = boto3.Session().get_credentials()
        auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            settings.aws_region,
            "es",
            session_token=credentials.token,
        )
        return OpenSearch(
            hosts=hosts,
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )

    http_auth = (settings.opensearch_user, settings.opensearch_password)
    return OpenSearch(
        hosts=hosts,
        http_auth=http_auth,
        use_ssl=use_ssl,
        verify_certs=use_ssl,
        connection_class=RequestsHttpConnection,
    )
