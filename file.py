"""
文件管理API视图
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from urllib.parse import quote
from app.database import get_db
from app.controllers.file import FileController
from app.schemas import FileResponse, StandardResponse, PaginatedResponse, TokenData, FileDownloadTokenResponse
from app.middleware.auth import get_current_user, require_permission
from celery_app import celery_app
from app.parsers import is_supported_file

router = APIRouter()


@router.post("/upload", response_model=StandardResponse[FileResponse], summary="上传文件")
@require_permission("UPLOAD_FILE")
def upload_file(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传文件到系统"""
    # 判断文件类型
    if not is_supported_file(file.filename):
        raise HTTPException(status_code=400, detail="文件类型不支持")
    controller = FileController(db)
    result = controller.upload_file(file, current_user.user_id)
    return StandardResponse(message="文件上传成功", data=result)


@router.get("/download", summary="下载文件")
def download_file(
    token: str = Query(..., description="下载token"),
    db: Session = Depends(get_db)
):
    """获取文件下载链接"""
    controller = FileController(db)
    data = controller.decode_file_download_token(token)
    if not data:
        raise HTTPException(status_code=404, detail="下载token不存在")
    file_id = data["file_id"]
    file = controller.get_file(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    response = controller.get_file_response(file_id)
    if not response:
        raise HTTPException(status_code=404, detail="文件不存在")
    file_name = file.filename
    # 流式返回
    def stream_response():
        try:
            for chunk in response.stream(1024):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    return StreamingResponse(
        stream_response(),
        media_type=response.headers['Content-Type'],
        headers={'Content-Disposition': f"attachment; filename*=utf-8''{quote(file_name)}"}
    )


@router.get("/{file_id}", response_model=StandardResponse[FileResponse], summary="获取文件信息")
@require_permission("GET_FILE")
def get_file(
    file_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """根据ID获取文件信息"""
    controller = FileController(db)
    result = controller.get_file(file_id, current_user.user_id)
    if not result:
        raise HTTPException(status_code=404, detail="文件不存在")
    return StandardResponse(message="获取文件信息成功", data=result)


@router.get("/", response_model=StandardResponse[PaginatedResponse[FileResponse]], summary="获取文件列表")
@require_permission("GET_FILES")
def list_files(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页大小"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文件列表"""
    controller = FileController(db)
    result = controller.list_files(page, size, current_user.user_id)
    return StandardResponse(message="获取文件列表成功", data=result)


@router.post("/{file_id}/delete", response_model=StandardResponse[dict], summary="删除文件")
@require_permission("DELETE_FILE")
def delete_file(
    file_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除文件"""
    controller = FileController(db)
    success = controller.delete_file(file_id, current_user.user_id)
    if not success:
        raise HTTPException(status_code=404, detail="文件不存在")
    return StandardResponse(message="文件删除成功", data={"file_id": file_id})


@router.get("/{file_id}/download", response_model=StandardResponse[FileDownloadTokenResponse], summary="获取下载链接")
@require_permission("DOWNLOAD_FILE")
def download_file(
    file_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文件下载链接"""
    controller = FileController(db)
    token = controller.get_file_download_token(file_id, current_user.user_id)
    return StandardResponse(message="获取文件下载链接成功", data=FileDownloadTokenResponse(token=token))


@router.post("/{file_id}/parse", response_model=StandardResponse[dict], summary="解析文件内容")
@require_permission("PARSE_FILE")
def parse_file_content(
    file_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """手动触发文件内容解析"""
    controller = FileController(db)
    result = controller.parse_file_content(file_id, current_user.user_id)
    if not result:
        raise HTTPException(status_code=404, detail="文件不存在")
    return StandardResponse(message="文件解析任务已启动", data=result)


@router.get("/{file_id}/parse/status", response_model=StandardResponse[dict], summary="查询文件解析进度")
@require_permission("GET_PARSE_STATUS")
def get_parse_status(
    file_id: int,
    task_id: str = Query(..., description="解析任务ID"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查询文件解析任务的进度"""
    # 获取Celery任务结果
    task_result = celery_app.AsyncResult(task_id)
    
    if task_result.state == 'PENDING':
        # 任务还未开始或不存在
        response = {
            'task_id': task_id,
            'file_id': file_id,
            'state': 'PENDING',
            'status': '任务等待中...',
            'current': 0,
            'total': 100
        }
    elif task_result.state == 'PROGRESS':
        # 任务正在进行中
        response = {
            'task_id': task_id,
            'file_id': file_id,
            'state': 'PROGRESS',
            'current': task_result.info.get('current', 0),
            'total': task_result.info.get('total', 100),
            'status': task_result.info.get('status', '处理中...')
        }
    elif task_result.state == 'SUCCESS':
        # 任务成功完成
        response = {
            'task_id': task_id,
            'file_id': file_id,
            'state': 'SUCCESS',
            'current': 100,
            'total': 100,
            'status': '解析完成',
            'result': task_result.result,
            'content_length': task_result.info.get('content_length', 0) if task_result.info else 0
        }
    elif task_result.state == 'FAILURE':
        # 任务失败
        response = {
            'task_id': task_id,
            'file_id': file_id,
            'state': 'FAILURE',
            'current': 0,
            'total': 100,
            'status': task_result.info.get('status', '处理失败') if task_result.info else '处理失败',
            'error': task_result.info.get('error', str(task_result.info)) if task_result.info else '未知错误'
        }
    else:
        # 其他状态
        response = {
            'task_id': task_id,
            'file_id': file_id,
            'state': task_result.state,
            'current': 0,
            'total': 100,
            'status': f'任务状态: {task_result.state}'
        }
    
    return StandardResponse(message="获取解析进度成功", data=response)


@router.post("/batch-parse", response_model=StandardResponse[dict], summary="批量解析文件内容")
@require_permission("BATCH_PARSE_FILES")
def batch_parse_files(
    file_ids: List[int],
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量解析文件内容"""
    if not file_ids:
        raise HTTPException(status_code=400, detail="文件ID列表不能为空")
    
    controller = FileController(db)
    result = controller.batch_parse_files(file_ids, current_user.user_id)
    return StandardResponse(message="批量解析任务已启动", data=result)


@router.get("/batch-parse/{task_id}/status", response_model=StandardResponse[dict], summary="查询批量解析进度")
@require_permission("GET_BATCH_PARSE_STATUS")
def get_batch_parse_status(
    task_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """查询批量解析任务的进度"""
    # 获取Celery任务结果
    task_result = celery_app.AsyncResult(task_id)
    
    if task_result.state == 'PENDING':
        response = {
            'task_id': task_id,
            'state': 'PENDING',
            'status': '任务等待中...',
            'current': 0,
            'total': 0
        }
    elif task_result.state == 'PROGRESS':
        response = {
            'task_id': task_id,
            'state': 'PROGRESS',
            'current': task_result.info.get('current', 0),
            'total': task_result.info.get('total', 0),
            'status': task_result.info.get('status', '处理中...'),
            'current_file_id': task_result.info.get('current_file_id')
        }
    elif task_result.state == 'SUCCESS':
        response = {
            'task_id': task_id,
            'state': 'SUCCESS',
            'current': task_result.info.get('total', 0),
            'total': task_result.info.get('total', 0),
            'status': '批量解析完成',
            'result': task_result.result
        }
    elif task_result.state == 'FAILURE':
        response = {
            'task_id': task_id,
            'state': 'FAILURE',
            'current': 0,
            'total': 0,
            'status': task_result.info.get('status', '批量解析失败') if task_result.info else '批量解析失败',
            'error': task_result.info.get('error', str(task_result.info)) if task_result.info else '未知错误'
        }
    else:
        response = {
            'task_id': task_id,
            'state': task_result.state,
            'current': 0,
            'total': 0,
            'status': f'任务状态: {task_result.state}'
        }
    
    return StandardResponse(message="获取批量解析进度成功", data=response) 