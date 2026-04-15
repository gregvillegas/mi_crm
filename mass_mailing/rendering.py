from django.template import Template, Context
from django.utils.html import conditional_escape


def get_inline_asset_map(campaign, preview=False):
    asset_map = {}
    assets = campaign.inline_assets() if hasattr(campaign, 'inline_assets') else []
    for asset in assets:
        if preview and hasattr(asset.file, 'url'):
            asset_map[asset.id] = asset.file.url
        else:
            asset_map[asset.id] = f"cid:campaign-asset-{asset.id}"
    return asset_map


def build_hero_promo_html(campaign, inline_asset_map):
    hero_asset = None
    try:
        hero_asset = campaign.inline_assets().first()
    except Exception:
        hero_asset = None

    hero_src = inline_asset_map.get(hero_asset.id) if hero_asset else None
    hero_img_html = ""
    if hero_src:
        hero_img_html = f'<img src="{hero_src}" alt="Campaign Image" style="display:block;width:100%;height:auto;border:0;">'
    else:
        hero_img_html = """
        <div style="background:#f3f4f6;color:#6b7280;text-align:center;padding:60px 24px;font-size:16px;">
            Upload a hero image to complete this campaign.
        </div>
        """.strip()

    headline = conditional_escape(campaign.hero_headline or "Exclusive Offer for {{ company_name }}")
    intro = conditional_escape(campaign.hero_intro or "Hi {{ contact_name }},\nWe are excited to share this offer with you.")
    intro = intro.replace("\n", "<br>")
    bullets = [campaign.hero_bullet_1, campaign.hero_bullet_2, campaign.hero_bullet_3]
    bullets_html = "".join(
        f'<li style="margin:0 0 8px 0;">{conditional_escape(b)}</li>' for b in bullets if b
    )
    cta_label = conditional_escape(campaign.hero_cta_label or "Learn More")
    cta_url = conditional_escape(campaign.hero_cta_url or "#")

    return f"""
<!doctype html>
<html>
  <body style="margin:0;padding:0;background-color:#f4f6f8;font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f4f6f8;">
      <tr>
        <td align="center" style="padding:24px 12px;">
          <table role="presentation" width="640" cellspacing="0" cellpadding="0" style="max-width:640px;width:100%;background:#ffffff;border-radius:10px;overflow:hidden;">
            <tr>
              <td style="background:#B22222;padding:16px 24px;color:#ffffff;font-size:20px;font-weight:700;">
                MICRO IMAGE INTERNATIONAL CORP.
              </td>
            </tr>
            <tr>
              <td>{hero_img_html}</td>
            </tr>
            <tr>
              <td style="padding:28px 28px 10px 28px;">
                <div style="font-size:28px;line-height:1.2;font-weight:700;color:#111827;margin:0 0 14px 0;">{headline}</div>
                <div style="font-size:16px;line-height:1.7;color:#374151;margin:0 0 18px 0;">{intro}</div>
                <ul style="padding-left:20px;margin:0 0 24px 0;font-size:15px;line-height:1.6;color:#374151;">
                  {bullets_html}
                </ul>
                <div style="margin:0 0 24px 0;">
                  <a href="{cta_url}" style="display:inline-block;background:#B22222;color:#ffffff;text-decoration:none;padding:12px 22px;border-radius:6px;font-weight:600;">
                    {cta_label}
                  </a>
                </div>
                <div style="font-size:15px;line-height:1.7;color:#374151;">
                  Best regards,<br>
                  <strong>[Your Name]</strong><br>
                  Account Manager<br>
                  Micro Image International Corp.
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
""".strip()


def build_product_launch_html(campaign, inline_asset_map):
    inline_assets = list(campaign.inline_assets()[:2]) if hasattr(campaign, 'inline_assets') else []
    banner_asset = inline_assets[0] if inline_assets else None
    product_asset = inline_assets[1] if len(inline_assets) > 1 else banner_asset

    banner_src = inline_asset_map.get(banner_asset.id) if banner_asset else None
    product_src = inline_asset_map.get(product_asset.id) if product_asset else None

    banner_html = f'<img src="{banner_src}" alt="Launch banner" style="display:block;width:100%;height:auto;border:0;">' if banner_src else ''
    product_html = (
        f'<img src="{product_src}" alt="Product image" style="display:block;width:100%;height:auto;border:0;max-width:240px;margin:0 auto;">'
        if product_src else
        '<div style="background:#f3f4f6;color:#6b7280;text-align:center;padding:48px 20px;font-size:15px;">Upload 1-2 inline images for the launch layout.</div>'
    )

    headline = conditional_escape(campaign.hero_headline or "Now Launching for {{ company_name }}")
    intro = conditional_escape(campaign.hero_intro or "Hi {{ contact_name }},\nWe are excited to introduce our latest solution.").replace("\n", "<br>")
    bullets = [campaign.hero_bullet_1, campaign.hero_bullet_2, campaign.hero_bullet_3]
    bullets_html = "".join(f'<li style="margin:0 0 10px 0;">{conditional_escape(b)}</li>' for b in bullets if b)
    cta_label = conditional_escape(campaign.hero_cta_label or "Request a Demo")
    cta_url = conditional_escape(campaign.hero_cta_url or "#")

    return f"""
<!doctype html>
<html>
  <body style="margin:0;padding:0;background-color:#eef2f7;font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#eef2f7;">
      <tr>
        <td align="center" style="padding:24px 12px;">
          <table role="presentation" width="680" cellspacing="0" cellpadding="0" style="max-width:680px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;">
            <tr>
              <td style="background:#111827;color:#ffffff;padding:14px 24px;font-size:13px;font-weight:700;letter-spacing:1px;">PRODUCT LAUNCH</td>
            </tr>
            <tr>
              <td>{banner_html}</td>
            </tr>
            <tr>
              <td style="padding:32px 28px;">
                <div style="font-size:30px;line-height:1.2;font-weight:700;margin:0 0 12px 0;">{headline}</div>
                <div style="font-size:16px;line-height:1.75;color:#4b5563;margin:0 0 24px 0;">{intro}</div>
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td width="42%" valign="top" style="padding-right:16px;">
                      {product_html}
                    </td>
                    <td width="58%" valign="top">
                      <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:18px;">
                        <div style="font-size:15px;font-weight:700;margin:0 0 10px 0;color:#111827;">Why it matters</div>
                        <ul style="padding-left:20px;margin:0;font-size:15px;line-height:1.6;color:#374151;">
                          {bullets_html}
                        </ul>
                      </div>
                      <div style="margin-top:20px;">
                        <a href="{cta_url}" style="display:inline-block;background:#B22222;color:#ffffff;text-decoration:none;padding:12px 22px;border-radius:6px;font-weight:600;">{cta_label}</a>
                      </div>
                    </td>
                  </tr>
                </table>
                <div style="margin-top:24px;font-size:15px;line-height:1.7;color:#374151;">
                  We’d be happy to walk your team through the launch and discuss how it fits your current environment.
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
""".strip()


def build_product_of_week_html(campaign, inline_asset_map):
    hero_asset = None
    try:
        hero_asset = campaign.inline_assets().first()
    except Exception:
        hero_asset = None

    hero_src = inline_asset_map.get(hero_asset.id) if hero_asset else None
    hero_html = (
        f'<img src="{hero_src}" alt="Product of the Week" style="display:block;width:100%;height:auto;border:0;max-width:640px;">'
        if hero_src else
        '<div style="background:#f3f4f6;color:#6b7280;text-align:center;padding:60px 24px;font-size:16px;">Select one inline image to complete this Product of the Week email.</div>'
    )

    return f"""
<!doctype html>
<html>
  <body style="margin:0;padding:0;background-color:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f4f6f8;">
      <tr>
        <td align="center" style="padding:24px 12px;">
          <table role="presentation" width="640" cellspacing="0" cellpadding="0" style="max-width:640px;width:100%;background:#ffffff;">
            <tr>
              <td style="padding:0;margin:0;">
                {hero_html}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
""".strip()


def build_newsletter_digest_html(campaign, inline_asset_map):
    inline_assets = list(campaign.inline_assets()[:2]) if hasattr(campaign, 'inline_assets') else []
    hero_asset = inline_assets[0] if inline_assets else None
    side_asset = inline_assets[1] if len(inline_assets) > 1 else None

    hero_src = inline_asset_map.get(hero_asset.id) if hero_asset else None
    side_src = inline_asset_map.get(side_asset.id) if side_asset else None

    hero_html = (
        f'<img src="{hero_src}" alt="Newsletter hero" style="display:block;width:100%;height:auto;border:0;">'
        if hero_src else
        '<div style="background:#e5eef9;color:#4b5563;text-align:center;padding:52px 22px;font-size:15px;">Upload a hero image for your newsletter digest.</div>'
    )
    side_html = (
        f'<img src="{side_src}" alt="Digest image" style="display:block;width:100%;height:auto;border:0;border-radius:10px;">'
        if side_src else
        '<div style="background:#f3f4f6;color:#6b7280;text-align:center;padding:40px 16px;font-size:14px;border-radius:10px;">Optional secondary image</div>'
    )

    headline = conditional_escape(campaign.hero_headline or "What’s New for {{ company_name }}")
    intro = conditional_escape(campaign.hero_intro or "Hi {{ contact_name }},\nHere’s a quick roundup of updates, promos, and insights from our team.").replace("\n", "<br>")
    bullets = [campaign.hero_bullet_1, campaign.hero_bullet_2, campaign.hero_bullet_3]
    bullets_html = "".join(
        f'<div style="padding:12px 0;border-bottom:1px solid #e5e7eb;"><strong style="color:#111827;">Update {idx}</strong><br>{conditional_escape(b)}</div>'
        for idx, b in enumerate([b for b in bullets if b], start=1)
    )
    cta_label = conditional_escape(campaign.hero_cta_label or "Read More")
    cta_url = conditional_escape(campaign.hero_cta_url or "#")

    return f"""
<!doctype html>
<html>
  <body style="margin:0;padding:0;background-color:#f5f7fb;font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f5f7fb;">
      <tr>
        <td align="center" style="padding:24px 12px;">
          <table role="presentation" width="680" cellspacing="0" cellpadding="0" style="max-width:680px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;">
            <tr>
              <td style="background:#0f172a;color:#ffffff;padding:16px 24px;">
                <div style="font-size:12px;letter-spacing:1.2px;text-transform:uppercase;opacity:.8;">Newsletter Digest</div>
                <div style="font-size:24px;font-weight:700;margin-top:4px;">Micro Image Update</div>
              </td>
            </tr>
            <tr>
              <td>{hero_html}</td>
            </tr>
            <tr>
              <td style="padding:28px;">
                <div style="font-size:28px;line-height:1.2;font-weight:700;margin:0 0 12px 0;color:#111827;">{headline}</div>
                <div style="font-size:16px;line-height:1.75;color:#4b5563;margin:0 0 24px 0;">{intro}</div>
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td width="62%" valign="top" style="padding-right:18px;">
                      <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:18px;">
                        <div style="font-size:16px;font-weight:700;color:#111827;margin-bottom:8px;">Highlights</div>
                        {bullets_html}
                      </div>
                    </td>
                    <td width="38%" valign="top">
                      {side_html}
                    </td>
                  </tr>
                </table>
                <div style="margin-top:24px;">
                  <a href="{cta_url}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 22px;border-radius:6px;font-weight:600;">{cta_label}</a>
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
""".strip()


def render_campaign_html(campaign, context_dict, preview=False):
    inline_asset_map = get_inline_asset_map(campaign, preview=preview)

    if getattr(campaign, 'template_type', 'html') == 'hero_promo':
        body_content = build_hero_promo_html(campaign, inline_asset_map)
    elif getattr(campaign, 'template_type', 'html') == 'product_launch':
        body_content = build_product_launch_html(campaign, inline_asset_map)
    elif getattr(campaign, 'template_type', 'html') == 'product_of_week':
        body_content = build_product_of_week_html(campaign, inline_asset_map)
    elif getattr(campaign, 'template_type', 'html') == 'newsletter_digest':
        body_content = build_newsletter_digest_html(campaign, inline_asset_map)
    else:
        body_content = campaign.body_html
        import re
        if not re.search(r'<[a-z][\s\S]*>', body_content or '', re.IGNORECASE):
            body_content = (body_content or '').replace('\n', '<br>')

    template = Template(body_content or '')
    context = Context(context_dict)
    rendered_body = template.render(context)

    # Replace generic placeholders with inline asset paths when present
    for asset_id, src in inline_asset_map.items():
        rendered_body = rendered_body.replace(f"cid:campaign-asset-{asset_id}", src)

    return rendered_body
