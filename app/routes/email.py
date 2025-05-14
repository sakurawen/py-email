from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import mailparser  # 用于解析邮件内容的第三方库
import poplib      # Python内置的POP3邮件协议库
import socks       # 用于代理支持
import socket      # 用于网络连接
import random      # 用于随机选择代理
import ssl
from email.parser import Parser
from email.header import decode_header
from email.utils import parseaddr

# 创建邮件相关的路由器，设置路由前缀和标签
router = APIRouter(prefix="/email",tags=["Email"])


class ProxiedPOP3_SSL(poplib.POP3_SSL):
    def __init__(self, host, port=995, keyfile=None, certfile=None, 
                 timeout=15, context=None, proxy_host=None, proxy_port=None, 
                 proxy_username=None, proxy_password=None):
        self.host = host
        self.port = port
        self.keyfile = keyfile
        self.certfile = certfile
        self.timeout = timeout
        self._tls_established = True
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        
        if context is None:
            context = ssl._create_stdlib_context(certfile=certfile, keyfile=keyfile)
        
        self.sock = self._create_socket(self.timeout)
        self.sock = context.wrap_socket(self.sock, server_hostname=host)
        self.file = self.sock.makefile('rb')
        self._debugging = 0
        self.welcome = self._getresp()

    def _create_socket(self, timeout):
        if self.proxy_host:
            sock = socks.socksocket()
            sock.set_proxy(
                socks.SOCKS5, 
                self.proxy_host, 
                self.proxy_port,
                username=self.proxy_username,
                password=self.proxy_password
            )
            sock.settimeout(timeout)
            return sock
        else:
            return socket.create_connection((self.host, self.port), timeout)

def create_proxy_socket(proxy_str: str) -> socket.socket:
    """
    创建一个使用代理的socket连接
    
    参数:
        proxy_str: 代理字符串，支持两种格式：
            1. username:password@host:port
            2. host:port:username:password
    
    返回:
        socket.socket: 配置了代理的socket对象
    """
    try:
        # 判断代理字符串格式
        if '@' in proxy_str:
            # 格式1: username:password@host:port
            auth, host_port = proxy_str.split('@')
            username, password = auth.split(':')
            host, port = host_port.split(':')
        else:
            # 格式2: host:port:username:password
            parts = proxy_str.split(':')
            if len(parts) != 4:
                raise ValueError("代理格式错误，应为 host:port:username:password")
            host, port, username, password = parts
        
        # 创建代理socket
        proxy_socket = socks.socksocket()
        proxy_socket.set_proxy(
            socks.SOCKS5,
            host,
            int(port),
            username=username,
            password=password
        )
        # 设置更短的超时时间
        proxy_socket.settimeout(10)  # 连接超时时间设为10秒
        
        # 测试代理连接
        test_socket = proxy_socket
        test_socket.connect(('www.baidu.com', 80))
        test_socket.close()
        
        # 重新创建socket用于实际使用
        proxy_socket = socks.socksocket()
        proxy_socket.set_proxy(
            socks.SOCKS5,
            host,
            int(port),
            username=username,
            password=password
        )
        proxy_socket.settimeout(10)
        return proxy_socket
    except Exception as e:
        print(f"创建代理socket失败: {str(e)}")
        return None

def get_pop3_server(email:str):
    """
    根据邮箱域名获取对应的POP3服务器地址
    """
    domain = email.split('@')[-1]
    if domain == '163.com':
        return 'pop.163.com'
    elif domain == '126.com':
        return 'pop.126.com'
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

@router.get("/{password}/{email}",response_class=HTMLResponse)
def get_email(email:str, password:str, proxy: str = None):
    """
    获取指定邮箱最新一封邮件的HTML内容
    
    参数:
        email (str): 邮箱地址
        password (str): 邮箱密码或授权码
        proxy (str, optional): 代理服务器配置，格式为 "username:password@host:port" 或 "host:port:username:password"
    
    返回:
        HTMLResponse: 邮件的HTML内容，如果获取失败则返回错误信息
    """
    server = None
    try:
        # 获取对应的POP3服务器地址
        pop3_server = get_pop3_server(email)
        
        # 解析代理配置
        proxy_host = None
        proxy_port = None
        proxy_username = None
        proxy_password = None
        
        if proxy:
            print(f"使用代理: {proxy}")
            if '@' in proxy:
                # 格式1: username:password@host:port
                auth, host_port = proxy.split('@')
                proxy_username, proxy_password = auth.split(':')
                proxy_host, proxy_port = host_port.split(':')
            else:
                # 格式2: host:port:username:password
                parts = proxy.split(':')
                if len(parts) != 4:
                    raise ValueError("代理格式错误，应为 host:port:username:password")
                proxy_host, proxy_port, proxy_username, proxy_password = parts
        
        # 连接到POP3服务器
        server = ProxiedPOP3_SSL(
            pop3_server,
            timeout=30,
            proxy_host=proxy_host,
            proxy_port=int(proxy_port) if proxy_port else None,
            proxy_username=proxy_username,
            proxy_password=proxy_password
        )
        
        # 登录邮箱
        server.user(email)
        server.pass_(password)
        
        # 获取邮件列表信息
        _, list, _ = server.list()
        total = len(list)
        
        if total == 0:
            return "邮箱中没有邮件"
        
        # 获取最新一封邮件的内容
        _,lines,_ = server.retr(total)
        msg_content = b'\r\n'.join(lines)
        
        # 解析邮件内容
        parsed = mailparser.parse_from_bytes(msg_content)
        html_content = parsed.text_html[0] if parsed.text_html else None
        
        if not html_content:
            return "邮件中没有HTML内容"
            
        return html_content
        
    except socket.timeout:
        return "连接超时，请检查网络或代理设置"
    except socks.SOCKS5AuthError:
        return "代理认证失败，请检查代理用户名和密码"
    except socks.GeneralProxyError:
        return "代理连接失败，请检查代理服务器是否可用"
    except poplib.error_proto as e:
        return f"POP3协议错误: {str(e)}"
    except Exception as e:
        return f'获取邮件失败: {str(e)}'
    finally:
        # 确保关闭所有连接
        if server:
            try:
                server.quit()
            except:
                pass
