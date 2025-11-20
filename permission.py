"""
权限管理API路由
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.controllers import PermissionController
from app.schemas import (
    PermissionCreate, PermissionUpdate, PermissionResponse, TokenData
)
from app.schemas.response import StandardResponse, PaginatedResponse
from app.middleware.auth import get_current_user, require_permission, extract_permissions_from_routes
from logger import logger

# 创建权限路由
router = APIRouter()


@router.post("/create", response_model=StandardResponse[PermissionResponse])
@require_permission("CREATE_PERMISSION")
def create_permission(
    permission_data: PermissionCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建权限"""
    controller = PermissionController(db)
    result = controller.create_permission(permission_data)
    return StandardResponse(
        message="创建权限成功",
        data=result
    )


@router.get("/{permission_id}/detail", response_model=StandardResponse[PermissionResponse])
@require_permission("GET_PERMISSION")
def get_permission(
    permission_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取权限详情"""
    controller = PermissionController(db)
    result = controller.get_permission_by_id(permission_id)
    return StandardResponse(
        message="获取权限成功",
        data=result
    )


@router.get("/list", response_model=StandardResponse[PaginatedResponse[PermissionResponse]])
@require_permission("GET_PERMISSIONS")
def get_permissions(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=-1, description="每页大小，-1表示获取全部数据"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取权限列表"""
    controller = PermissionController(db)
    result = controller.get_permissions(page, size)
    return StandardResponse(
        message="获取权限列表成功",
        data=result
    )


@router.post("/{permission_id}/update", response_model=StandardResponse[PermissionResponse])
@require_permission("UPDATE_PERMISSION")
def update_permission(
    permission_id: int,
    permission_data: PermissionUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新权限"""
    controller = PermissionController(db)
    result = controller.update_permission(permission_id, permission_data)
    return StandardResponse(
        message="更新权限成功",
        data=result
    )


@router.post("/{permission_id}/delete", response_model=StandardResponse)
@require_permission("DELETE_PERMISSION")
def delete_permission(
    permission_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除权限"""
    controller = PermissionController(db)
    controller.delete_permission(permission_id)
    return StandardResponse(
        message="删除权限成功"
    )


@router.post("/sync", response_model=StandardResponse[List[PermissionResponse]])
@require_permission("SYNC_PERMISSIONS")
def sync_permissions(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """同步权限"""
    from app import app
    
    # 从FastAPI应用中提取权限信息
    permissions_data = extract_permissions_from_routes(app)
    
    controller = PermissionController(db)
    result = controller.sync_permissions(permissions_data)
    
    return StandardResponse(
        message="同步权限成功",
        data=result
    ) 