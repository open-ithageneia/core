from django.utils.html import format_html


def get_admin_image_thumb_preview(image):
    return format_html('<img src="{}" style="height:50px" />', image.url) if image else ""