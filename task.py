"""
任务管理API视图
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.controllers.task import TaskController
from app.schemas import (
    TaskCreate, TaskResponse, TaskTypeResponse, StandardResponse, PaginatedResponse, TaskListResponse, TokenData,
    TaskTypeCreate, TaskTypeUpdate, TaskTypeDetailResponse
)
from app.middleware.auth import get_current_user, require_permission
from logger import logger

task_type_router = APIRouter()
task_router = APIRouter()


@task_type_router.post("/create", response_model=StandardResponse[TaskTypeDetailResponse], summary="创建任务类型")
@require_permission("CREATE_TASK_TYPE_DETAIL")
def create_task_type(
    task_type_data: TaskTypeCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建任务类型"""
    controller = TaskController(db)
    result = controller.create_task_type(task_type_data)
    return StandardResponse(message="创建任务类型成功", data=result)


@task_type_router.get("/list", response_model=StandardResponse[PaginatedResponse[TaskTypeDetailResponse]], summary="获取任务类型列表")
@require_permission("GET_TASK_TYPES_LIST")
def list_task_types(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, description="每页大小"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务类型列表"""
    controller = TaskController(db)
    result = controller.list_task_types(page, size)
    return StandardResponse(message="获取任务类型列表成功", data=result)


@task_type_router.get("/{task_type_id}", response_model=StandardResponse[TaskTypeDetailResponse], summary="获取任务类型详情")
@require_permission("GET_TASK_TYPE_DETAIL")
def get_task_type(
    task_type_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务类型详情"""
    controller = TaskController(db)
    result = controller.get_task_type_detail(task_type_id)
    return StandardResponse(message="获取任务类型详情成功", data=result)


@task_type_router.post("/{task_type_id}/update", response_model=StandardResponse[TaskTypeDetailResponse], summary="更新任务类型")
@require_permission("UPDATE_TASK_TYPE_DETAIL")
def update_task_type(
    task_type_id: int,
    task_type_data: TaskTypeUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新任务类型"""
    controller = TaskController(db)
    result = controller.update_task_type(task_type_id, task_type_data)
    return StandardResponse(message="更新任务类型成功", data=result)


@task_type_router.post("/{task_type_id}/delete", response_model=StandardResponse, summary="删除任务类型")
@require_permission("DELETE_TASK_TYPE_DETAIL")
def delete_task_type(
    task_type_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除任务类型"""
    controller = TaskController(db)
    controller.delete_task_type(task_type_id)
    return StandardResponse(message="删除任务类型成功")


@task_router.get("/types", response_model=StandardResponse[List[TaskTypeResponse]], summary="获取任务类型列表")
@require_permission("GET_TASK_TYPES")
def get_task_types(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有可用的任务类型列表(不包含API密钥，用于前端选择任务类型)"""
    controller = TaskController(db)
    result = controller.get_task_types()
    return StandardResponse(message="获取任务类型列表成功", data=result)


@task_router.post("/create", response_model=StandardResponse[TaskResponse], summary="创建分析任务")
@require_permission("CREATE_TASK")
def create_task(
    task_data: TaskCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新的分析任务"""
    controller = TaskController(db)
    result = controller.create_task(task_data, current_user.user_id)
    return StandardResponse(message="创建分析任务成功", data=result)


@task_router.get("/list", response_model=StandardResponse[PaginatedResponse[TaskListResponse]], summary="获取任务列表")
@require_permission("GET_TASKS")
def list_tasks(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页大小"),
    status: Optional[str] = Query(None, description="任务状态过滤"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务列表"""
    controller = TaskController(db)
    result = controller.list_tasks(page, size, status, current_user.user_id)
    return StandardResponse(message="获取任务列表成功", data=result)


@task_router.get("/{task_id}", response_model=StandardResponse[TaskResponse], summary="获取任务详情")
@require_permission("GET_TASK")
def get_task(
    task_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """根据ID获取任务详情"""
    controller = TaskController(db)
    result = controller.get_task(task_id, current_user.user_id)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    return StandardResponse(message="获取任务详情成功", data=result)


@task_router.get("/{task_id}/status", response_model=StandardResponse[dict], summary="获取任务状态")
@require_permission("GET_TASK_STATUS")
def get_task_status(
    task_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务状态"""
    controller = TaskController(db)
    status = controller.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")
    return StandardResponse(message="获取任务状态成功", data={"task_id": task_id, "status": status})


@task_router.get("/{task_id}/shared", response_model=StandardResponse[TaskResponse], summary="获取共享任务详情")
@require_permission("GET_TASK")
def get_shared_task(
    task_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """根据ID获取共享任务详情（包含共享权限检查）"""
    controller = TaskController(db)
    result = controller.get_task(task_id, current_user.user_id, check_share_access=True)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在或无权限访问")
    return StandardResponse(message="获取任务详情成功", data=result)


@task_router.post("/{task_id}/cancel", response_model=StandardResponse[dict], summary="取消任务")
@require_permission("CANCEL_TASK")
def cancel_task(
    task_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消任务"""
    controller = TaskController(db)
    controller.cancel_task(task_id, current_user.user_id)
    return StandardResponse(message="任务已取消", data={"task_id": task_id})


@task_router.post("/{task_id}/delete", response_model=StandardResponse[dict], summary="删除任务")
@require_permission("DELETE_TASK")
def delete_task(
    task_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除任务"""
    controller = TaskController(db)
    controller.delete_task(task_id, current_user.user_id)
    return StandardResponse(message="任务已删除", data={"task_id": task_id})