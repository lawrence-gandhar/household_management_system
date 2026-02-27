from fastapi_amis_admin.amis.components import PageSchema, TableColumn

from app.admin.mixins import LabeledModelAdmin
from app.admin.site import admin_site
from app.models.recipe import Recipe, RecipeIngredient


@admin_site.register_admin
class RecipeAdmin(LabeledModelAdmin):
    page_schema = PageSchema(label="Recipes", icon="fa fa-utensils")
    model = Recipe

    # ── Table columns ─────────────────────────────────────────────────────────
    list_display = [
        TableColumn(name="id",           label="ID"),
        TableColumn(name="user_id",      label="User ID"),
        TableColumn(name="title",        label="Title"),
        TableColumn(name="cuisine_type", label="Cuisine"),
        TableColumn(name="difficulty",   label="Difficulty"),
        TableColumn(name="source",       label="Source"),
        TableColumn(name="is_premium",   label="Premium"),
        TableColumn(name="created_at",   label="Created"),
    ]

    # ── Form field labels ─────────────────────────────────────────────────────
    verbose_fields = {
        "id":                 "ID",
        "user_id":            "User",
        "title":              "Title",
        "description":        "Description",
        "cuisine_type":       "Cuisine Type",
        "prep_time_minutes":  "Prep Time (mins)",
        "cook_time_minutes":  "Cook Time (mins)",
        "servings":           "Servings",
        "difficulty":         "Difficulty",
        "source":             "Source",
        "source_url":         "Source URL",
        "instructions":       "Instructions",
        "tags":               "Tags",
        "is_premium":         "Premium Only",
        "created_at":         "Created",
        "updated_at":         "Last Updated",
    }

    search_fields = [Recipe.title, Recipe.cuisine_type]
    list_filter   = [Recipe.source, Recipe.difficulty, Recipe.is_premium, Recipe.cuisine_type]
    ordering      = [Recipe.created_at]


@admin_site.register_admin
class RecipeIngredientAdmin(LabeledModelAdmin):
    page_schema = PageSchema(label="Recipe Ingredients", icon="fa fa-list")
    model = RecipeIngredient

    # ── Table columns ─────────────────────────────────────────────────────────
    list_display = [
        TableColumn(name="id",          label="ID"),
        TableColumn(name="recipe_id",   label="Recipe ID"),
        TableColumn(name="name",        label="Ingredient"),
        TableColumn(name="quantity",    label="Quantity"),
        TableColumn(name="unit",        label="Unit"),
        TableColumn(name="is_optional", label="Optional"),
    ]

    # ── Form field labels ─────────────────────────────────────────────────────
    verbose_fields = {
        "id":          "ID",
        "recipe_id":   "Recipe",
        "name":        "Ingredient",
        "quantity":    "Quantity",
        "unit":        "Unit",
        "is_optional": "Optional",
        "notes":       "Notes",
    }

    search_fields = [RecipeIngredient.name]
    list_filter   = [RecipeIngredient.is_optional]
