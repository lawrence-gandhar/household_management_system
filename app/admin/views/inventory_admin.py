from fastapi import Request
from fastapi_amis_admin.amis.components import PageSchema, TableColumn
from sqlalchemy import select as sa_select
from sqlalchemy.sql import Select

from app.admin.mixins import LabeledModelAdmin
from app.admin.site import admin_site
from app.models.inventory import ExpiryTracking, InventoryItem
from app.models.user import User


@admin_site.register_admin
class InventoryAdmin(LabeledModelAdmin):
    page_schema = PageSchema(label="Inventory", icon="fa fa-box")
    model = InventoryItem

    # ── Table columns ─────────────────────────────────────────────────────────
    list_display = [
        # TableColumn(name="id",             label="ID"),
        TableColumn(name="user_email",     label="Email"),
        TableColumn(name="name",           label="Item Name"),
        TableColumn(name="category",       label="Category"),
        TableColumn(name="quantity",       label="Quantity"),
        TableColumn(name="quantity_unit",  label="Unit"),
        TableColumn(name="quantity_level", label="Stock Level"),
        TableColumn(name="is_packaged",    label="Packaged"),
        TableColumn(name="created_at",     label="Added"),
    ]

    # ── Form field labels ─────────────────────────────────────────────────────
    verbose_fields = {
        # "id":             "ID",
        "user_id":        "User",
        "name":           "Item Name",
        "category":       "Category",
        "quantity":       "Quantity",
        "quantity_unit":  "Unit",
        "quantity_level": "Stock Level",
        "barcode":        "Barcode",
        "brand":          "Brand",
        "image_url":      "Image URL",
        "is_packaged":    "Packaged",
        "notes":          "Notes",
        "created_at":     "Added",
        "updated_at":     "Last Updated",
    }

    search_fields = [InventoryItem.name, InventoryItem.barcode, InventoryItem.brand]
    list_filter   = [InventoryItem.category, InventoryItem.quantity_level, InventoryItem.is_packaged]
    ordering      = [InventoryItem.created_at]

    async def get_select(self, request: Request) -> Select:
        sel = await super().get_select(request)
        user_email = (
            sa_select(User.email)
            .where(User.id == InventoryItem.user_id)
            .scalar_subquery()
            .label("user_email")
        )
        return sel.add_columns(user_email)


@admin_site.register_admin
class ExpiryAdmin(LabeledModelAdmin):
    page_schema = PageSchema(label="Expiry Tracking", icon="fa fa-calendar-times")
    model = ExpiryTracking

    # ── Table columns ─────────────────────────────────────────────────────────
    list_display = [
        TableColumn(name="id",                   label="ID"),
        TableColumn(name="user_email",           label="Email"),
        TableColumn(name="inventory_item_id",    label="Item ID"),
        TableColumn(name="expiry_date",          label="Expiry Date"),
        TableColumn(name="notification_sent",    label="Notified"),
        TableColumn(name="notification_sent_at", label="Notified At"),
        TableColumn(name="created_at",           label="Tracked Since"),
    ]

    # ── Form field labels ─────────────────────────────────────────────────────
    verbose_fields = {
        "id":                   "ID",
        "inventory_item_id":    "Inventory Item",
        "user_id":              "User",
        "expiry_date":          "Expiry Date",
        "notification_sent":    "Notification Sent",
        "notification_sent_at": "Notified At",
        "created_at":           "Tracked Since",
    }

    list_filter = [ExpiryTracking.notification_sent]
    ordering    = [ExpiryTracking.expiry_date]

    async def get_select(self, request: Request) -> Select:
        sel = await super().get_select(request)
        user_email = (
            sa_select(User.email)
            .where(User.id == ExpiryTracking.user_id)
            .scalar_subquery()
            .label("user_email")
        )
        return sel.add_columns(user_email)
