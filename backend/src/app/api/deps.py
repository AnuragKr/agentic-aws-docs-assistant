from typing import Annotated

from fastapi import Depends

from app.core.container import AppContainer, get_container
from app.ingestion.jobs.manager import JobManager


def get_job_manager(container: Annotated[AppContainer, Depends(get_container)]) -> JobManager:
    return JobManager(container)


ContainerDep = Annotated[AppContainer, Depends(get_container)]
JobManagerDep = Annotated[JobManager, Depends(get_job_manager)]
