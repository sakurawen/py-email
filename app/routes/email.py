from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import mailparser  # 用于解析邮件内容的第三方库
import poplib      # Python内置的POP3邮件协议库

# 创建邮件相关的路由器，设置路由前缀和标签
router = APIRouter(prefix="/email",tags=["Email"])

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

@router.get("/{email}/{password}",response_class=HTMLResponse)
def get_email(email:str,password:str):
    """
    获取指定邮箱最新一封邮件的HTML内容
    
    参数:
        email (str): 邮箱地址
        password (str): 邮箱密码或授权码
    
    返回:
        HTMLResponse: 邮件的HTML内容，如果获取失败则返回错误信息
    """
    try:
        # 获取对应的POP3服务器地址
        pop3_server = get_pop3_server(email)
        # 连接到POP3服务器
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
        return html_content
        
    except Exception as e:
        # 如果出现任何错误，返回错误信息
        return f'获取邮件失败:{str(e)}'
