"""
共享管理API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.controllers.share import ShareController
from app.schemas.share import ShareCreate, ShareUpdate, ShareResponse, ShareSimpleResponse, ShareQuery
from app.schemas.response import StandardResponse, PaginatedResponse
from app.middleware.auth import get_current_user
from app.schemas import TokenData
from logger import logger

# 创建路由
share_router = APIRouter()


@share_router.post("/", response_model=StandardResponse[ShareResponse])
def create_share(
    share_data: ShareCreate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """创建共享"""
    try:
        controller = ShareController(db)
        result = controller.create_share(share_data, current_user.user_id)
        
        return StandardResponse(
            code=200,
            message="创建共享成功",
            data=result
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"创建共享API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建共享失败"
        )


@share_router.get("/", response_model=StandardResponse[PaginatedResponse[ShareSimpleResponse]])
def get_shares(
    task_name: Optional[str] = Query(None, description="任务名称"),
    task_type: Optional[str] = Query(None, description="任务类型"),
    user_nickname: Optional[str] = Query(None, description="用户昵称"),
    status: Optional[str] = Query(None, description="任务状态"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """获取共享列表"""
    try:
        query = ShareQuery(
            task_name=task_name,
            task_type=task_type,
            user_nickname=user_nickname,
            status=status,
            page=page,
            size=size
        )
        
        controller = ShareController(db)
        result = controller.get_shares(query, current_user.user_id)
        
        return StandardResponse(
            code=200,
            message="获取共享列表成功",
            data=result
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"获取共享列表API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取共享列表失败"
        )


@share_router.get("/{share_id}", response_model=StandardResponse[ShareResponse])
def get_share(
    share_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """获取共享详情"""
    try:
        controller = ShareController(db)
        result = controller.get_share_by_id(share_id)
        
        return StandardResponse(
            code=200,
            message="获取共享详情成功",
            data=result
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"获取共享详情API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取共享详情失败"
        )


@share_router.put("/{share_id}", response_model=StandardResponse[ShareResponse])
def update_share(
    share_id: int,
    share_data: ShareUpdate,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """更新共享"""
    try:
        controller = ShareController(db)
        result = controller.update_share(share_id, share_data, current_user.user_id)
        
        return StandardResponse(
            code=200,
            message="更新共享成功",
            data=result
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"更新共享API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新共享失败"
        )


@share_router.delete("/{share_id}", response_model=StandardResponse[bool])
def delete_share(
    share_id: int,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """删除共享"""
    try:
        controller = ShareController(db)
        result = controller.delete_share(share_id, current_user.user_id)
        
        return StandardResponse(
            code=200,
            message="删除共享成功",
            data=result
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"删除共享API异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除共享失败"
        )