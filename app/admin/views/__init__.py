# Importing these modules causes the @admin_site.register_admin decorators to run.
# dashboard is imported first so it appears at the top of the sidebar (sort=-100).
import app.admin.dashboard  # noqa: F401

from app.admin.views import (  # noqa: F401
    user_admin,
    subscription_admin,
    inventory_admin,
    recipe_admin,
    equipment_admin,
    category_admin,
)
