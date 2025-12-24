"""
系统配置管理API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.controllers.system import SystemConfigController
from app.schemas.system import (
    ConfigCreate, ConfigUpdate, ConfigResponse,
    ConfigGroupCreate, ConfigGroupUpdate, ConfigGroupResponse,
    ConfigGroupDetailResponse, PublicConfigResponse
)
from app.schemas.response import StandardResponse, PaginatedResponse
from app.middleware.auth import get_current_user, require_permission
from app.schemas import TokenData
from app.services.system import get_config_value
from logger import logger

# 创建系统配置路由
config_router = APIRouter()
config_group_router = APIRouter()


# ==================== 配置组管理路由 ====================

@config_group_router.post("/create", response_model=StandardResponse[ConfigGroupResponse])
@require_permission("CREATE_CONFIG_GROUP")
def create_config_group(
    group_data: ConfigGroupCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建配置组"""
    controller = SystemConfigController(db)
    result = controller.create_config_group(group_data)
    return StandardResponse(
        message="创建配置组成功",
        data=result
    )


@config_group_router.get("/{group_id}/detail", response_model=StandardResponse[ConfigGroupDetailResponse])
@require_permission("GET_CONFIG_GROUP")
def get_config_group(
    group_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取配置组详情"""
    controller = SystemConfigController(db)
    result = controller.get_config_group_by_id(group_id)
    return StandardResponse(
        message="获取配置组成功",
        data=result
    )


@config_group_router.get("/list", response_model=StandardResponse[PaginatedResponse[ConfigGroupResponse]])
@require_permission("GET_CONFIG_GROUPS")
def get_config_groups(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(-1, ge=-1, description="每页大小，-1表示获取全部数据"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取配置组列表"""
    controller = SystemConfigController(db)
    result = controller.get_config_groups(page, size)
    return StandardResponse(
        message="获取配置组列表成功",
        data=result
    )


@config_group_router.post("/{group_id}/update", response_model=StandardResponse[ConfigGroupResponse])
@require_permission("UPDATE_CONFIG_GROUP")
def update_config_group(
    group_id: int,
    group_data: ConfigGroupUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新配置组"""
    controller = SystemConfigController(db)
    result = controller.update_config_group(group_id, group_data)
    return StandardResponse(
        message="更新配置组成功",
        data=result
    )


@config_group_router.post("/{group_id}/delete", response_model=StandardResponse)
@require_permission("DELETE_CONFIG_GROUP")
def delete_config_group(
    group_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除配置组"""
    controller = SystemConfigController(db)
    controller.delete_config_group(group_id)
    return StandardResponse(
        message="删除配置组成功"
    )


# ==================== 配置管理路由 ====================

@config_router.post("/create", response_model=StandardResponse[ConfigResponse])
@require_permission("CREATE_CONFIG")
def create_config(
    config_data: ConfigCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建配置"""
    controller = SystemConfigController(db)
    result = controller.create_config(config_data)
    return StandardResponse(
        message="创建配置成功",
        data=result
    )


@config_router.get("/{config_id}/detail", response_model=StandardResponse[ConfigResponse])
@require_permission("GET_CONFIG")
def get_config(
    config_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取配置详情"""
    controller = SystemConfigController(db)
    result = controller.get_config_by_id(config_id)
    return StandardResponse(
        message="获取配置成功",
        data=result
    )


@config_router.get("/list", response_model=StandardResponse[PaginatedResponse[ConfigResponse]])
@require_permission("GET_CONFIGS")
def get_configs(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(-1, ge=-1, description="每页大小，-1表示获取全部数据"),
    group_id: Optional[int] = Query(None, description="配置组ID过滤"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取配置列表"""
    controller = SystemConfigController(db)
    result = controller.get_configs(page, size, group_id)
    return StandardResponse(
        message="获取配置列表成功",
        data=result
    )


@config_router.post("/{config_id}/update", response_model=StandardResponse[ConfigResponse])
@require_permission("UPDATE_CONFIG")
def update_config(
    config_id: int,
    config_data: ConfigUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新配置"""
    controller = SystemConfigController(db)
    result = controller.update_config(config_id, config_data)
    return StandardResponse(
        message="更新配置成功",
        data=result
    )


@config_router.post("/{config_id}/delete", response_model=StandardResponse)
@require_permission("DELETE_CONFIG")
def delete_config(
    config_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除配置"""
    controller = SystemConfigController(db)
    controller.delete_config(config_id)
    return StandardResponse(
        message="删除配置成功"
    )


@config_router.post("/refresh-cache", response_model=StandardResponse)
@require_permission("REFRESH_CONFIG_CACHE")
def refresh_config_cache(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """刷新配置缓存"""
    controller = SystemConfigController(db)
    controller.refresh_config_cache()
    return StandardResponse(
        message="刷新配置缓存成功"
    )


@config_router.get("/public", response_model=StandardResponse[List[PublicConfigResponse]])
def get_public_configs(db: Session = Depends(get_db)):
    """获取公开配置（无需鉴权）"""
    controller = SystemConfigController(db)
    result = controller.get_public_configs()
    return StandardResponse(
        message="获取公开配置成功",
        data=result
    )
