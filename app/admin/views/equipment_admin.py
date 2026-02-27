from fastapi_amis_admin.amis.components import PageSchema, TableColumn

from app.admin.mixins import LabeledModelAdmin
from app.admin.site import admin_site
from app.models.equipment import CuisineCategory, Equipment


@admin_site.register_admin
class EquipmentAdmin(LabeledModelAdmin):
    page_schema = PageSchema(label="Equipment Catalog", icon="fa fa-blender")
    model = Equipment

    # ── Table columns ─────────────────────────────────────────────────────────
    list_display = [
        TableColumn(name="id",        label="ID"),
        TableColumn(name="name",      label="Equipment Name"),
        TableColumn(name="category",  label="Category"),
        TableColumn(name="is_active", label="Active"),
    ]

    # ── Form field labels ─────────────────────────────────────────────────────
    verbose_fields = {
        "id":          "ID",
        "name":        "Equipment Name",
        "description": "Description",
        "category":    "Category",
        "is_active":   "Active",
    }

    search_fields = [Equipment.name, Equipment.description]
    list_filter   = [Equipment.category, Equipment.is_active]
    ordering      = [Equipment.name]


@admin_site.register_admin
class CuisineCategoryAdmin(LabeledModelAdmin):
    page_schema = PageSchema(label="Cuisine Categories", icon="fa fa-globe")
    model = CuisineCategory

    # ── Table columns ─────────────────────────────────────────────────────────
    list_display = [
        TableColumn(name="id",          label="ID"),
        TableColumn(name="name",        label="Category Name"),
        TableColumn(name="description", label="Description"),
        TableColumn(name="is_active",   label="Active"),
    ]

    # ── Form field labels ─────────────────────────────────────────────────────
    verbose_fields = {
        "id":          "ID",
        "name":        "Category Name",
        "description": "Description",
        "is_active":   "Active",
    }

    search_fields = [CuisineCategory.name]
    list_filter   = [CuisineCategory.is_active]
