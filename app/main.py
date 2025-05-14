from fastapi import FastAPI
from app.routes import email  # 导入邮件相关的路由模块

# 创建FastAPI应用实例
app = FastAPI()

# 将邮件路由模块注册到应用中
app.include_router(email.router)
