from fastapi import Request
from fastapi_amis_admin.amis.components import PageSchema, TableColumn
from sqlalchemy import select as sa_select
from sqlalchemy.sql import Select

from app.admin.mixins import LabeledModelAdmin
from app.admin.site import admin_site
from app.models.subscription import Subscription
from app.models.user import User


@admin_site.register_admin
class SubscriptionAdmin(LabeledModelAdmin):
    page_schema = PageSchema(label="Subscriptions", icon="fa fa-credit-card")
    model = Subscription

    # ── Table columns ─────────────────────────────────────────────────────────
    list_display = [
        # TableColumn(name="id",                label="ID"),
        TableColumn(name="user_email",        label="Email"),
        TableColumn(name="tier",              label="Tier"),
        TableColumn(name="starts_at",         label="Started"),
        TableColumn(name="expires_at",        label="Expires"),
        TableColumn(name="is_active",         label="Active"),
        TableColumn(name="payment_reference", label="Payment Reference"),
        TableColumn(name="created_at",        label="Created"),
    ]

    # ── Form field labels ─────────────────────────────────────────────────────
    verbose_fields = {
        # "id":                "ID",
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

    async def get_select(self, request: Request) -> Select:
        sel = await super().get_select(request)
        user_email = (
            sa_select(User.email)
            .where(User.id == Subscription.user_id)
            .scalar_subquery()
            .label("user_email")
        )
        return sel.add_columns(user_email)
