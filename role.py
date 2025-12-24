"""
角色管理API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.controllers import RoleController
from app.schemas import (
    RoleCreate, RoleUpdate, RoleResponse, RoleSimpleResponse, TokenData,
    RolePermissionUpdate
)
from app.schemas.response import StandardResponse, PaginatedResponse
from app.middleware.auth import get_current_user, require_permission
from logger import logger

# 创建角色路由
router = APIRouter()


@router.post("/create", response_model=StandardResponse[RoleResponse])
@require_permission("CREATE_ROLE")
def create_role(
    role_data: RoleCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建角色"""
    controller = RoleController(db)
    result = controller.create_role(role_data)
    return StandardResponse(
        message="创建角色成功",
        data=result
    )


@router.get("/{role_id}/detail", response_model=StandardResponse[RoleResponse])
@require_permission("GET_ROLE")
def get_role(
    role_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取角色详情"""
    controller = RoleController(db)
    result = controller.get_role_by_id(role_id)
    return StandardResponse(
        message="获取角色成功",
        data=result
    )


@router.get("/list", response_model=StandardResponse[PaginatedResponse[RoleSimpleResponse]])
@require_permission("GET_ROLES")
def get_roles(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=-1, description="每页大小，-1表示获取全部数据"),
    name: Optional[str] = Query(None, description="角色名称"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    order: int = Query(0, ge=0, le=1, description="排序方式，0为正序，1为逆序"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取角色列表"""
    controller = RoleController(db)
    result = controller.get_roles(page, size, name, is_active, order)
    return StandardResponse(
        message="获取角色列表成功",
        data=result
    )


@router.post("/{role_id}/update", response_model=StandardResponse[RoleResponse])
@require_permission("UPDATE_ROLE")
def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新角色"""
    controller = RoleController(db)
    result = controller.update_role(role_id, role_data)
    return StandardResponse(
        message="更新角色成功",
        data=result
    )


@router.post("/{role_id}/delete", response_model=StandardResponse)
@require_permission("DELETE_ROLE")
def delete_role(
    role_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除角色"""
    controller = RoleController(db)
    controller.delete_role(role_id)
    return StandardResponse(
        message="删除角色成功"
    )


@router.post("/{role_id}/permissions", response_model=StandardResponse[RoleResponse])
@require_permission("UPDATE_ROLE_PERMISSIONS")
def update_role_permissions(
    role_id: int,
    permission_data: RolePermissionUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新角色权限"""
    controller = RoleController(db)
    result = controller.update_role_permissions(role_id, permission_data)
    return StandardResponse(
        message="更新角色权限成功",
        data=result
    ) 