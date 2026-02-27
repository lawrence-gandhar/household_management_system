import types
from pathlib import Path

from fastapi import Request
from fastapi_amis_admin.admin.settings import Settings as AdminSettings
from fastapi_amis_admin.admin.site import AdminSite, HomeAdmin
from fastapi_amis_admin.amis.components import App, Page
from fastapi_amis_admin.utils.translation import i18n

from app.core.config import settings

# ── Force English locale for all AMIS UI strings, button labels, and error messages.
# i18n is a module-level singleton; must be called before AdminSite is created.
i18n.set_language("en_US")

# ── Point AMIS components to our clean English templates (no Chinese comments or
# hardcoded lang="zh"). Must be monkey-patched before AdminSite registers routes.
_TEMPLATES = Path(__file__).parent / "templates"
Page.__default_template_path__ = str(_TEMPLATES / "page.html")
App.__default_template_path__ = str(_TEMPLATES / "app.html")

admin_site = AdminSite(
    settings=AdminSettings(
        database_url_async=settings.DATABASE_URL_ASYNC,
        secret_key=settings.ADMIN_SECRET_KEY,
        site_title="Pantry Mate — Admin",
        language="en_US",
        # site_url intentionally omitted — defaults to "" so AMIS uses
        # relative paths from the /admin mount point, avoiding double-prefix
        # bugs like /admin/admin/UserAdmin.
    )
)

# ── Remove the built-in "Home" page — Dashboard takes its place.
# HomeAdmin is auto-registered inside AdminSite.__init__; unregister it here
# so it never appears in the sidebar or routing table.
admin_site.unregister_admin(HomeAdmin)


# ── Strip the hard-coded GitHub icon (header) and copyright footer.
# BaseAdminSite._get_page_as_app injects both unconditionally; shadow it on
# the instance so the AMIS App JSON is returned without either element.
async def _get_page_as_app(self, request: Request) -> App:
    app = App()
    app.brandName = self.site.settings.site_title
    app.logo = self.site.settings.site_icon
    children = await self.get_page_schema_children(request)
    app.pages = [{"children": children}] if children else []
    return app


admin_site._get_page_as_app = types.MethodType(_get_page_as_app, admin_site)
