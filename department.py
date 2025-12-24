"""
部门管理API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.controllers import DepartmentController
from app.schemas import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse, 
    DepartmentSimpleResponse, TokenData, DepartmentPermissionUpdate
)
from app.schemas.response import StandardResponse, PaginatedResponse
from app.middleware.auth import get_current_user, require_permission
from logger import logger

# 创建部门路由
router = APIRouter()


@router.post("/create", response_model=StandardResponse[DepartmentSimpleResponse])
@require_permission("CREATE_DEPARTMENT")
def create_department(
    department_data: DepartmentCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建部门"""
    controller = DepartmentController(db)
    result = controller.create_department(department_data)
    return StandardResponse(
        message="创建部门成功",
        data=result
    )


@router.get("/{department_id}/detail", response_model=StandardResponse[DepartmentResponse])
@require_permission("GET_DEPARTMENT")
def get_department(
    department_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取部门详情"""
    controller = DepartmentController(db)
    result = controller.get_department_by_id(department_id)
    return StandardResponse(
        message="获取部门成功",
        data=result
    )


@router.get("/list", response_model=StandardResponse[PaginatedResponse[DepartmentSimpleResponse]])
@require_permission("GET_DEPARTMENTS")
def get_departments(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=-1, description="每页大小，-1表示获取全部数据"),
    parent_id: Optional[int] = Query(None, description="父部门ID, 为-1表示获取根部门"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取部门列表"""
    controller = DepartmentController(db)
    result = controller.get_departments(page, size, parent_id)
    return StandardResponse(
        message="获取部门列表成功",
        data=result
    )


@router.get("/tree", response_model=StandardResponse[List[DepartmentResponse]])
@require_permission("GET_DEPARTMENT_TREE")
def get_department_tree(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取部门树形结构"""
    controller = DepartmentController(db)
    result = controller.get_department_tree()
    return StandardResponse(
        message="获取部门树形结构成功",
        data=result
    )


@router.post("/{department_id}/update", response_model=StandardResponse[DepartmentSimpleResponse])
@require_permission("UPDATE_DEPARTMENT")
def update_department(
    department_id: int,
    department_data: DepartmentUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新部门"""
    controller = DepartmentController(db)
    result = controller.update_department(department_id, department_data)
    return StandardResponse(
        message="更新部门成功",
        data=result
    )


@router.post("/{department_id}/delete", response_model=StandardResponse)
@require_permission("DELETE_DEPARTMENT")
def delete_department(
    department_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除部门"""
    controller = DepartmentController(db)
    controller.delete_department(department_id)
    return StandardResponse(
        message="删除部门成功"
    )


@router.post("/{department_id}/permissions", response_model=StandardResponse[DepartmentResponse])
@require_permission("UPDATE_DEPARTMENT_PERMISSIONS")
def update_department_permissions(
    department_id: int,
    permission_data: DepartmentPermissionUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新部门权限"""
    controller = DepartmentController(db)
    result = controller.update_department_permissions(department_id, permission_data)
    return StandardResponse(
        message="更新部门权限成功",
        data=result
    ) 