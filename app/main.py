from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import email  # 导入邮件相关的路由模块

# 创建FastAPI应用实例
app = FastAPI()

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，在生产环境中应该设置为具体的域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# 将邮件路由模块注册到应用中
app.include_router(email.router)
