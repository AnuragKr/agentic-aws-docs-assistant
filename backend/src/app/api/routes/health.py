from fastapi import APIRouter

from app.api.deps import ContainerDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health(container: ContainerDep) -> dict[str, str]:
    settings = container.settings
    return {
        "status": "ok",
        "app": settings.app_name,
        "embedding_provider": settings.embedding_provider,
        "opensearch_index": settings.opensearch_index,
    }
