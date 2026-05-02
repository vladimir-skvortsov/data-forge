from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser
from app.db.session import DBSession
from app.schemas.dashboard import EstimateResponse
from app.schemas.jobs import (
    JobCreateRequest,
    JobListResponse,
    JobOut,
    RunJobResponse,
)
from app.services import job_service
from app.services.billing_service import InsufficientBalanceError
from app.services.job_service import (
    FileLimitExceededError,
    FileSizeLimitError,
    JobAccessDeniedError,
    JobNotFoundError,
    JobStateError,
)

router = APIRouter(prefix='/jobs', tags=['jobs'])


def _job_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Job not found')


def _job_forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')


@router.post('', status_code=status.HTTP_201_CREATED)
async def create_job(
    body: JobCreateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> JobOut:
    job = await job_service.create_job(
        user_id=str(current_user.id),
        title=body.title,
        schema_config=body.schema_config,
        pipeline_config=[b.model_dump() for b in body.pipeline_config],
        db=db,
    )
    return JobOut.model_validate(job)


@router.get('')
async def list_jobs(
    current_user: CurrentUser,
    db: DBSession,
) -> JobListResponse:
    jobs = await job_service.list_jobs(str(current_user.id), db)
    return JobListResponse(
        items=[JobOut.model_validate(j) for j in jobs],
        total=len(jobs),
    )


@router.get('/{job_id}')
async def get_job(
    job_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> JobOut:
    try:
        job = await job_service.get_job(job_id, str(current_user.id), db)
    except JobNotFoundError:
        raise _job_not_found()
    except JobAccessDeniedError:
        raise _job_forbidden()
    return JobOut.model_validate(job)


@router.delete('/{job_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    try:
        await job_service.delete_job(job_id, str(current_user.id), db)
    except JobNotFoundError:
        raise _job_not_found()
    except JobAccessDeniedError:
        raise _job_forbidden()
    except JobStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post('/{job_id}/files', status_code=status.HTTP_201_CREATED)
async def upload_file(
    job_id: str,
    file: UploadFile,
    current_user: CurrentUser,
    db: DBSession,
) -> JobOut:
    try:
        await job_service.add_file(job_id, str(current_user.id), file, db)
        job = await job_service.get_job(job_id, str(current_user.id), db)
    except JobNotFoundError:
        raise _job_not_found()
    except JobAccessDeniedError:
        raise _job_forbidden()
    except JobStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except FileLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    except FileSizeLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        )
    return JobOut.model_validate(job)


@router.post('/{job_id}/run')
async def run_job(
    job_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> RunJobResponse:
    try:
        job, credits_held = await job_service.run_job(job_id, str(current_user.id), db)
    except JobNotFoundError:
        raise _job_not_found()
    except JobAccessDeniedError:
        raise _job_forbidden()
    except JobStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except InsufficientBalanceError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail='Insufficient balance',
        )
    return RunJobResponse(job_id=job.id, status=job.status, credits_held=credits_held)


@router.get('/{job_id}/estimate')
async def estimate_job(
    job_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> EstimateResponse:
    try:
        data = await job_service.get_estimate(job_id, str(current_user.id), db)
    except JobNotFoundError:
        raise _job_not_found()
    except JobAccessDeniedError:
        raise _job_forbidden()
    return EstimateResponse(**data)


@router.get('/{job_id}/download')
async def download_result(
    job_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> FileResponse:
    try:
        result_path, filename = await job_service.get_result_file_path(
            job_id, str(current_user.id), db
        )
    except JobNotFoundError:
        raise _job_not_found()
    except JobAccessDeniedError:
        raise _job_forbidden()
    except JobStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return FileResponse(
        path=result_path,
        filename=filename,
        media_type='application/octet-stream',
    )


@router.get('/{job_id}/result')
async def get_job_result(
    job_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> list[dict]:
    try:
        return await job_service.get_job_result(job_id, str(current_user.id), db)
    except JobNotFoundError:
        raise _job_not_found()
    except JobAccessDeniedError:
        raise _job_forbidden()
    except JobStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
