from fastapi_amis_admin.amis.components import PageSchema, TableColumn

from app.admin.mixins import LabeledModelAdmin
from app.admin.site import admin_site
from app.models.user import User


@admin_site.register_admin
class UserAdmin(LabeledModelAdmin):
    page_schema = PageSchema(label="Users", icon="fa fa-users")
    model = User

    # ── Table columns ─────────────────────────────────────────────────────────
    list_display = [
        TableColumn(name="id",          label="ID"),
        TableColumn(name="email",       label="Email Address"),
        TableColumn(name="full_name",   label="Full Name"),
        TableColumn(name="role",        label="Role"),
        TableColumn(name="is_active",   label="Active"),
        TableColumn(name="is_verified", label="Verified"),
        TableColumn(name="created_at",  label="Joined"),
    ]

    # ── Form field labels (create / update / filter) ──────────────────────────
    verbose_fields = {
        "id":              "ID",
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
