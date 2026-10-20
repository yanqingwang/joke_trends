"""Email delivery: render the weekly Markdown report into a clean HTML email + .md attachment."""
import os
import re
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr, formatdate


def md_to_html(md_text: str) -> str:
    import markdown
    html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    # SVG 多数邮箱客户端会被拦截，邮件正文里剥掉，保留数字明细
    html = re.sub(r"<svg.*?</svg>", "", html, flags=re.S)
    return f"""<div style="font-family:-apple-system,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;
     max-width:720px;margin:0 auto;color:#222;line-height:1.6;">
<style>table{{border-collapse:collapse}}td,th{{border:1px solid #ddd;padding:4px 8px}}a{{color:#2563eb}}</style>
{html}
<hr><small>本邮件由 joke_trends 自动化流水线每周一发送 · 中文内容请放心食用</small>
</div>"""


def enabled(profile_cfg: dict) -> bool:
    """Send only when profile opts in AND credentials exist."""
    return bool(profile_cfg.get("mail")) and bool(os.environ.get("SMTP_PASS")) and bool(os.environ.get("SMTP_USER"))


def send(subject: str, md_text: str, attach_path: str | None = None) -> None:
    host = os.environ.get("SMTP_HOST", "smtp.qq.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ["SMTP_USER"]
    pwd = os.environ["SMTP_PASS"]
    from_addr = os.environ.get("MAIL_FROM", user)
    to_addrs = [x.strip() for x in os.environ.get("MAIL_TO", user).split(",") if x.strip()]

    msg = MIMEMultipart("mixed")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header("HR Trends 机器人", "utf-8")), from_addr))
    msg["To"] = ", ".join(to_addrs)
    msg["Date"] = formatdate()

    msg.attach(MIMEText(md_to_html(md_text), "html", "utf-8"))

    if attach_path and os.path.exists(attach_path):
        with open(attach_path, "rb") as f:
            att = MIMEApplication(f.read())
        att.add_header("Content-Disposition", "attachment",
                       filename=("utf-8", "", os.path.basename(attach_path)))
        msg.attach(att)

    ctx = ssl.create_default_context()
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, context=ctx, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        server.starttls(context=ctx)
    try:
        server.login(user, pwd)
        server.sendmail(from_addr, to_addrs, msg.as_string())
    finally:
        server.quit()
