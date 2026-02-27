"""Admin mixin — human-readable form and table labels.

Usage
-----
Inherit from :class:`LabeledModelAdmin` instead of ``admin.ModelAdmin``,
then declare a ``verbose_fields`` class attribute that maps SQLAlchemy column
names to the human-readable string you want shown as the field label in both
**table headers** (set separately via ``TableColumn`` in ``list_display``) and
**create / update / filter forms**::

    class MyAdmin(LabeledModelAdmin):
        model = MyModel
        verbose_fields = {
            "email":     "Email Address",
            "full_name": "Full Name",
            ...
        }
"""

from typing import Union

from fastapi import Request
from fastapi_amis_admin import admin
from fastapi_amis_admin.crud.schema import CrudEnum


class LabeledModelAdmin(admin.ModelAdmin):
    """ModelAdmin that applies ``verbose_fields`` labels to every form field.

    ``verbose_fields`` maps SQLAlchemy attribute name → human-readable label.
    The override is applied to create, update, and filter form items.
    """

    verbose_fields: dict[str, str] = {}

    # Fields managed automatically by the database — never expose in any form
    # and never require in the generated Pydantic create/update schemas.
    # Both timestamps are set/updated by the DB; neither belongs in user input.
    _db_managed_fields: frozenset[str] = frozenset({"created_at", "updated_at"})

    # ── Schema exclusion ──────────────────────────────────────────────────────

    def _create_schema_create(self):
        """Exclude _db_managed_fields + pk from the create schema."""
        original = self.create_exclude
        self.create_exclude = {
            self.pk_name: True,
            **({} if original is None else original),
            **{f: True for f in self._db_managed_fields},
        }
        try:
            return super()._create_schema_create()
        finally:
            self.create_exclude = original

    def _create_schema_update(self):
        """Exclude _db_managed_fields + pk from the update schema."""
        original = self.update_exclude
        self.update_exclude = {
            self.pk_name: True,
            **({} if original is None else original),
            **{f: True for f in self._db_managed_fields},
        }
        try:
            return super()._create_schema_update()
        finally:
            self.update_exclude = original

    # ── Form UI ───────────────────────────────────────────────────────────────

    async def get_form_item(self, request: Request, modelfield, action: CrudEnum):
        # Drop server-managed fields from create / update / filter forms.
        if modelfield.name in self._db_managed_fields:
            return None
        item = await super().get_form_item(request, modelfield, action)
        # hasattr guard: FK-relation items are SchemaNode and may not carry .label
        if item is not None and hasattr(item, "label") and modelfield.name in self.verbose_fields:
            item.label = self.verbose_fields[modelfield.name]
        return item
