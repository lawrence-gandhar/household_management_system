from fastapi import Request
from fastapi_amis_admin.amis.components import PageSchema, TableColumn
from fastapi_amis_admin.crud.schema import CrudEnum

from app.admin.mixins import LabeledModelAdmin
from app.admin.site import admin_site
from app.models.user import User

# Hidden entirely from the update form (not shown, not submitted).
_UPDATE_HIDDEN: frozenset[str] = frozenset({"hashed_password"})

# Shown as static (read-only display) in the update form; not submitted.
_UPDATE_READONLY: frozenset[str] = frozenset({"email", "is_verified"})


@admin_site.register_admin
class UserAdmin(LabeledModelAdmin):
    page_schema = PageSchema(label="Users", icon="fa fa-users")
    model = User

    # ── Table columns ─────────────────────────────────────────────────────────
    list_display = [
        # TableColumn(name="id",          label="ID"),
        TableColumn(name="email",       label="Email Address"),
        TableColumn(name="full_name",   label="Full Name"),
        TableColumn(name="role",        label="Role"),
        TableColumn(name="is_active",   label="Active"),
        TableColumn(name="is_verified", label="Verified"),
        TableColumn(name="created_at",  label="Joined"),
    ]

    # ── Form field labels (create / update / filter) ──────────────────────────
    verbose_fields = {
        # "id":              "ID",
        "email":           "Email Address",
        "hashed_password": "Password Hash",
        "full_name":       "Full Name",
        "role":            "Role",
        "is_active":       "Active",
        "is_verified":     "Email Verified",
        "created_at":      "Joined",
        "updated_at":      "Last Updated",
    }

    search_fields = [User.email, User.full_name]
    list_filter   = [User.role, User.is_active, User.is_verified]
    ordering      = [User.created_at]

    # ── Update form restrictions ───────────────────────────────────────────────

    def _create_schema_update(self):
        """Exclude password, email, and is_verified from the update payload.

        Only full_name, role, and is_active are submitted on save.
        The parent mixin adds pk and timestamp exclusions on top of these.
        """
        original = self.update_exclude
        self.update_exclude = {
            **({} if original is None else original),
            **{f: True for f in _UPDATE_HIDDEN | _UPDATE_READONLY},
        }
        try:
            return super()._create_schema_update()
        finally:
            self.update_exclude = original

    async def get_form_item(self, request: Request, modelfield, action: CrudEnum):
        if action == CrudEnum.update:
            # Password: hide completely — no value should ever be visible.
            if modelfield.name in _UPDATE_HIDDEN:
                return None
        item = await super().get_form_item(request, modelfield, action)
        if action == CrudEnum.update and item is not None:
            # Email / is_verified: display current value but prevent editing.
            if modelfield.name in _UPDATE_READONLY:
                item.static = True
        return item
