from fastapi_amis_admin.amis.components import PageSchema, TableColumn

from app.admin.mixins import LabeledModelAdmin
from app.admin.site import admin_site
from app.models.subscription import Subscription


@admin_site.register_admin
class SubscriptionAdmin(LabeledModelAdmin):
    page_schema = PageSchema(label="Subscriptions", icon="fa fa-credit-card")
    model = Subscription

    # ── Table columns ─────────────────────────────────────────────────────────
    list_display = [
        TableColumn(name="id",                label="ID"),
        TableColumn(name="user_id",           label="User ID"),
        TableColumn(name="tier",              label="Tier"),
        TableColumn(name="starts_at",         label="Started"),
        TableColumn(name="expires_at",        label="Expires"),
        TableColumn(name="is_active",         label="Active"),
        TableColumn(name="payment_reference", label="Payment Reference"),
        TableColumn(name="created_at",        label="Created"),
    ]

    # ── Form field labels ─────────────────────────────────────────────────────
    verbose_fields = {
        "id":                "ID",
        "user_id":           "User",
        "tier":              "Tier",
        "starts_at":         "Started",
        "expires_at":        "Expires",
        "is_active":         "Active",
        "payment_reference": "Payment Reference",
        "created_at":        "Created",
        "updated_at":        "Last Updated",
    }

    search_fields = [Subscription.payment_reference]
    list_filter   = [Subscription.tier, Subscription.is_active]
    ordering      = [Subscription.created_at]
