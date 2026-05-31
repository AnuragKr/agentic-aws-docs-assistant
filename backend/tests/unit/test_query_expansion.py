
from agent.query_expansion import QueryExpansionService
from config.settings import Settings


def test_query_expansion_includes_original_and_aliases() -> None:
    settings = Settings(max_query_expansions=5)
    service = QueryExpansionService(settings)
    expansions = service.expand("Secure S3")
    assert expansions[0] == "Secure S3"
    assert len(expansions) <= 5
    assert any("S3" in query for query in expansions)
