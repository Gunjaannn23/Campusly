from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape

HTML = """<table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background:#F4F1FF;padding:32px 12px;font-family:Arial,Helvetica,sans-serif;">
<tr><td align="center">
<table width="480" cellpadding="0" cellspacing="0" role="presentation" style="max-width:480px;width:100%;background:#FFFFFF;border-radius:20px;overflow:hidden;border:1px solid #DDD6F5;">
<tr><td align="center" style="background:#2A1568;padding:28px 20px;">
<span style="color:#FF5C7A;font-size:26px;">&#9670;</span>
<span style="color:#FFFFFF;font-size:26px;font-weight:bold;letter-spacing:-0.5px;padding-left:6px;">Campusly</span>
<div style="color:#C9BFF0;font-size:13px;margin-top:6px;">Your campus, pinned in one place</div>
</td></tr>
<tr><td style="padding:32px 28px 8px;">
<h1 style="margin:0 0 10px;font-size:24px;color:#1B1138;">Verify your email</h1>
<p style="margin:0;font-size:16px;line-height:1.6;color:#5E5780;">Enter this code on the Campusly sign-in page to get in.</p>
</td></tr>
<tr><td align="center" style="padding:20px 28px;">
<div style="background:#F4F1FF;border:2px dashed #6D28D9;border-radius:16px;padding:20px 10px;">
<div style="font-size:38px;font-weight:bold;letter-spacing:10px;color:#6D28D9;font-family:'Courier New',monospace;">__CODE__</div>
</div></td></tr>
<tr><td style="padding:0 28px 28px;">
<p style="margin:0 0 8px;font-size:14px;line-height:1.6;color:#5E5780;">This code expires in __MIN__ minutes and works only once. Never share it with anyone.</p>
<p style="margin:0;font-size:14px;line-height:1.6;color:#5E5780;">Didn&rsquo;t ask for this? You can safely ignore this email.</p>
</td></tr>
<tr><td align="center" style="background:#F4F1FF;padding:16px;font-size:12px;color:#8A82AD;">Sent to __EMAIL__ &middot; Campusly, the student marketplace</td></tr>
</table></td></tr></table>"""


def send_code_email(email, code):
    print(email, code)
    minutes = settings.CODE_TTL_MINUTES
    text = (
        "Your Campusly verification code is %s\n\n"
        "It expires in %d minutes and works only once. Never share it with anyone.\n"
        "If you didn't ask for it, you can ignore this email.\n" % (code, minutes)
    )
    html = HTML.replace("__CODE__", escape(code)).replace("__MIN__", str(minutes)).replace("__EMAIL__", escape(email))
    msg = EmailMultiAlternatives(
        subject="Your Campusly verification code",
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)
