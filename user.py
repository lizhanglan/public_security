"""
用户管理API路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.controllers import UserController
from app.schemas import (
    UserCreate, UserUpdate, UserResponse, UserSimpleResponse, PasswordChange, LoginResponse, UserLogin,
    TokenData, UserRoleUpdate, UserDepartmentUpdate
)
from app.schemas.response import StandardResponse, PaginatedResponse
from app.middleware.auth import get_current_user, require_permission
from app.services.auth import auth_service
from logger import logger

# 创建路由
user_router = APIRouter()
auth_router = APIRouter()


# 认证相关路由
@auth_router.post("/login", response_model=StandardResponse[LoginResponse])
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """用户登录"""
    try:
        # 验证用户
        user = auth_service.authenticate_user(db, login_data.username, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        # 生成令牌
        access_token = auth_service.create_user_token(db, user)
        
        # 获取用户详细信息
        controller = UserController(db)
        user_info = controller.get_user_by_id(user.id)
        
        result = LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_info
        )
        
        return StandardResponse(
            message="登录成功",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败"
        )


@auth_router.get("/me", response_model=StandardResponse[UserResponse])
@require_permission("GET_CURRENT_USER")
def get_current_user_info(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户信息"""
    controller = UserController(db)
    result = controller.get_user_by_id(current_user.user_id)
    return StandardResponse(
        message="获取用户信息成功",
        data=result
    )


@auth_router.put("/change-password", response_model=StandardResponse)
@require_permission("CHANGE_PASSWORD")
def change_password(
    password_data: PasswordChange,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    controller = UserController(db)
    controller.change_password(current_user.user_id, password_data)
    return StandardResponse(
        message="密码修改成功"
    )


# 用户管理路由
@user_router.post("/create", response_model=StandardResponse[UserResponse])
@require_permission("CREATE_USER")
def create_user(
    user_data: UserCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建用户"""
    controller = UserController(db)
    result = controller.create_user(user_data)
    return StandardResponse(
        message="创建用户成功",
        data=result
    )


@user_router.get("/{user_id}/detail", response_model=StandardResponse[UserResponse])
@require_permission("GET_USER")
def get_user(
    user_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户详情"""
    controller = UserController(db)
    result = controller.get_user_by_id(user_id)
    return StandardResponse(
        message="获取用户成功",
        data=result
    )


@user_router.get("/list", response_model=StandardResponse[PaginatedResponse[UserSimpleResponse]])
@require_permission("GET_USERS")
def get_users(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, description="每页大小，-1表示获取全部数据"),
    user_id: Optional[int] = Query(None, description="用户ID"),
    username: Optional[str] = Query(None, description="用户名"),
    nickname: Optional[str] = Query(None, description="昵称"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    role_id: Optional[int] = Query(None, description="角色ID"),
    department_id: Optional[int] = Query(None, description="部门ID"),
    show_all: bool = Query(False, description="当为true且department_id存在时，获取该部门及其所有子部门的用户"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户列表"""
    controller = UserController(db)
    result = controller.get_users(page, size, user_id, username, nickname, is_active, role_id, department_id, show_all)
    return StandardResponse(
        message="获取用户列表成功",
        data=result
    )


@user_router.post("/{user_id}/update", response_model=StandardResponse[UserResponse])
@require_permission("UPDATE_USER")
def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户"""
    controller = UserController(db)
    result = controller.update_user(user_id, user_data)
    return StandardResponse(
        message="更新用户成功",
        data=result
    )


@user_router.post("/{user_id}/delete", response_model=StandardResponse)
@require_permission("DELETE_USER")
def delete_user(
    user_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除用户"""
    controller = UserController(db)
    controller.delete_user(user_id)
    return StandardResponse(
        message="删除用户成功"
    )


@user_router.post("/{user_id}/roles", response_model=StandardResponse[UserResponse])
@require_permission("UPDATE_USER_ROLES")
def update_user_roles(
    user_id: int,
    role_data: UserRoleUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户角色"""
    controller = UserController(db)
    result = controller.update_user_roles(user_id, role_data)
    return StandardResponse(
        message="更新用户角色成功",
        data=result
    )


@user_router.post("/{user_id}/departments", response_model=StandardResponse[UserResponse])
@require_permission("UPDATE_USER_DEPARTMENTS")
def update_user_departments(
    user_id: int,
    department_data: UserDepartmentUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户部门"""
    controller = UserController(db)
    result = controller.update_user_departments(user_id, department_data)
    return StandardResponse(
        message="更新用户部门成功",
        data=result
    )
