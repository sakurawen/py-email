from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import mailparser  # 用于解析邮件内容的第三方库
import poplib      # Python内置的POP3邮件协议库
import socks      # 用于代理支持
import socket     # 用于网络连接

# 创建邮件相关的路由器，设置路由前缀和标签
router = APIRouter(prefix="/email",tags=["Email"])


sslMap  ={
    "gmx.com":True
}
class ProxyContext:
    def __init__(self, proxy_host, proxy_port, proxy_user, proxy_pass):
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_user = proxy_user
        self.proxy_pass = proxy_pass
        self.original_socket = None

    def __enter__(self):
        if all([self.proxy_host, self.proxy_port]):
            self.original_socket = socket.socket
            socks.setdefaultproxy(
                socks.PROXY_TYPE_SOCKS5,
                self.proxy_host,
                self.proxy_port,
                username=self.proxy_user,
                password=self.proxy_pass
            )
            socket.socket = socks.socksocket
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original_socket:
            socket.socket = self.original_socket

def get_pop3_server(email:str):
    """
    根据邮箱域名获取对应的POP3服务器地址
    """
    domain = email.split('@')[-1]
    if domain == '163.com':
        return 'pop.163.com'
    elif domain == '126.com':
        return 'pop.126.com'    
    elif domain =='gmx.com':
        return 'pop.gmx.com'
    elif domain =='t-online.de':
        return 'pop.t-online.de'
    elif domain == 'qq.com':
        return 'pop.qq.com'
    elif domain == 'gmail.com':
        return 'pop.gmail.com'
    elif domain == 'yahoo.com':
        return 'pop.mail.yahoo.com'
    elif domain == 'outlook.com':
        return 'pop-mail.outlook.com'
    elif domain == 'hotmail.com':
        return 'pop3.live.com'
    elif domain == 'sina.com':
        return 'pop3.sina.com'
    elif domain == 'sohu.com':
        return 'pop.sohu.com'
    elif domain == '139.com':
        return 'pop.139.com'
    elif domain == '189.com':
        return 'pop.189.com'
    else:
        raise ValueError(f"不支持的邮箱域名: {domain}")

def parse_proxy(proxy_str: str) -> tuple:
    """
    解析代理字符串，支持两种格式：
    1. "username:password@host:port"
    2. "host:port:username:password"
    
    参数:
        proxy_str (str): 代理配置字符串
    
    返回:
        tuple: (host, port, username, password)
    """
    if not proxy_str:
        return None, None, None, None
        
    try:
        # 检查是否包含@符号，用于区分两种格式
        if '@' in proxy_str:
            # 格式1: username:password@host:port
            auth, address = proxy_str.split('@')
            username, password = auth.split(':')
            host, port = address.split(':')
        else:
            # 格式2: host:port:username:password
            parts = proxy_str.split(':')
            if len(parts) != 4:
                raise ValueError("代理格式错误：需要4个部分")
            host, port, username, password = parts
            
        return host, int(port), username, password
    except Exception as e:
        raise ValueError(f"代理格式错误: {str(e)}")

@router.get("/{password}/{email}")
def get_email(email: str, password: str, proxy: str = None):
    """
    获取指定邮箱最新一封邮件的HTML内容
    
    参数:
        email (str): 邮箱地址
        password (str): 邮箱密码或授权码
        proxy (str, optional): 代理服务器配置，格式为 "username:password@host:port"
    
    返回:
        HTMLResponse: 邮件的HTML内容，如果获取失败则返回错误信息
    """
    try:
        # 获取对应的POP3服务器地址
        pop3_server = get_pop3_server(email)
        
        # 解析代理配置
        proxy_host, proxy_port, proxy_user, proxy_pass = parse_proxy(proxy) if proxy else (None, None, None, None)
        
        # 使用上下文管理器处理代理
        with ProxyContext(proxy_host, proxy_port, proxy_user, proxy_pass):
            # 连接到POP3服务器
            domain = email.split('@')[-1]
            if(sslMap.get(domain)):
                server = poplib.POP3_SSL(pop3_server)
            else:
                server = poplib.POP3(pop3_server)
            # 登录邮箱
            server.user(email)
            server.pass_(password)
            
            # 获取邮件列表信息，返回值中list包含所有邮件的编号和大小
            _, list, _ = server.list()
            # 计算邮件总数
            total = len(list)
            
            # 获取最新一封邮件的内容（total是最后一封邮件的编号）
            _,lines,_ = server.retr(total)
            # 将邮件内容的字节列表合并成完整的字节串
            msg_content = b'\r\n'.join(lines)
            
            # 使用mailparser解析邮件内容
            parsed = mailparser.parse_from_bytes(msg_content)
            # 获取邮件的HTML内容，如果存在则取第一个HTML部分
            html_content = parsed.text_html[0] if parsed.text_html else None
            
            return HTMLResponse(content=html_content if html_content else "No HTML content found")
            
    except Exception as e:
        return HTMLResponse(content=f'获取邮件失败: {str(e)}')
