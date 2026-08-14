"""Renders a generated campaign as a sendable email.

Mirrors the look of ``frontend/src/components/generate/EmailPreview.tsx`` --
brand header bar, headline, sub-heading, CTA button, product image -- but as a
table-based HTML document with inline styles, since mail clients do not
support flexbox/grid or external stylesheets. Colours are the same hex values
as ``frontend/src/theme/theme.ts``; there is no way to share that file with an
email template, so if the theme changes this needs updating by hand.

Pure functions, no I/O -- this only builds an ``EmailMessage`` for
``EmailSender.send`` to deliver.
"""

from __future__ import annotations

from html import escape

from app.core.config import settings
from app.schemas.copy_output import GenerationOutput
from app.services.email.sender import EmailMessage

_SIDEBAR = "#10183B"
_PRIMARY = "#6548E8"
_SECONDARY = "#8C5CF6"
_TEXT_PRIMARY = "#11182F"
_TEXT_SECONDARY = "#667085"


def _image_block(image_url: str | None) -> str:
    if not image_url:
        return ""
    absolute_url = f"{settings.public_base_url.rstrip('/')}{image_url}"
    return f"""
      <td width="160" valign="top" style="padding-left:24px;">
        <img src="{escape(absolute_url)}" width="160" height="120" alt=""
             style="border-radius:12px;display:block;object-fit:cover;" />
      </td>"""


def build_campaign_email(
    output: GenerationOutput, *, to: str, brand_name: str | None
) -> EmailMessage:
    """Build the campaign email as it would actually be sent.

    Only the Email-channel copy has a header/CTA/image layout to render;
    callers are responsible for confirming ``output.channel`` is ``email``
    before calling this.
    """
    copy = output.email
    brand_label = (brand_name or "Your Brand").upper()

    html_body = f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:24px;background:#F7F8FC;
               font-family:Arial,Helvetica,sans-serif;">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0"
           style="margin:0 auto;background:#FFFFFF;border-radius:12px;overflow:hidden;">
      <tr>
        <td style="background:{_SIDEBAR};padding:16px 24px;">
          <span style="color:#FFFFFF;font-weight:700;letter-spacing:1px;font-size:13px;">
            {escape(brand_label)}
          </span>
        </td>
      </tr>
      <tr>
        <td style="padding:24px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td valign="top">
                <h1 style="margin:0 0 12px;font-size:24px;line-height:1.3;color:{_TEXT_PRIMARY};">
                  {escape(copy.headline)}
                </h1>
                <p style="margin:0 0 20px;font-size:14px;line-height:1.6;color:{_TEXT_SECONDARY};">
                  {escape(copy.sub_heading)}
                </p>
                <a href="#" style="display:inline-block;padding:12px 20px;border-radius:8px;
                     background:linear-gradient(135deg,{_PRIMARY} 0%,{_SECONDARY} 100%);
                     color:#FFFFFF;font-weight:700;font-size:12px;letter-spacing:0.5px;
                     text-decoration:none;">
                  {escape(copy.cta)}
                </a>
              </td>{_image_block(output.image_url)}
            </tr>
          </table>
        </td>
      </tr>
    </table>
    <p style="max-width:600px;margin:12px auto 0;font-size:11px;color:{_TEXT_SECONDARY};
              text-align:center;">
      This is a test send of AI-generated content. Review before publishing.
    </p>
  </body>
</html>
"""

    text_body = (
        f"{copy.headline}\n\n{copy.sub_heading}\n\n{copy.cta}\n\n"
        "This is a test send of AI-generated content. Review before publishing."
    )

    return EmailMessage(
        to=to,
        subject=copy.headline,
        text_body=text_body,
        html_body=html_body,
    )
