from fastapi_amis_admin.amis.components import PageSchema, TableColumn

from app.admin.mixins import LabeledModelAdmin
from app.admin.site import admin_site
from app.models.category import Category


@admin_site.register_admin
class CategoryAdmin(LabeledModelAdmin):
    page_schema = PageSchema(label="Categories", icon="fa fa-tags", sort=900)
    model = Category

    # ── Pagination ────────────────────────────────────────────────────────────
    # Default and available page sizes.  Max 100 per page prevents full-table
    # fetches on a 100k+ row catalog; the DB composite index keeps each page
    # load to an index-range-scan rather than a sequential scan.
    page_size      = 50
    page_size_list = [20, 50, 100]

    # ── Table columns ─────────────────────────────────────────────────────────
    list_display = [
        TableColumn(name="id",          label="ID"),
        TableColumn(name="name",        label="Name"),
        TableColumn(name="description", label="Description"),
        TableColumn(name="is_active",   label="Active"),
        TableColumn(name="created_at",  label="Created"),
    ]

    # ── Form field labels ─────────────────────────────────────────────────────
    verbose_fields = {
        "id":          "ID",
        "name":        "Category Name",
        "description": "Description",
        "is_active":   "Active",
        "created_at":  "Created",
        "updated_at":  "Last Updated",
    }

    search_fields = [Category.name]
    list_filter   = [Category.is_active]
    ordering      = [Category.name]
