"""Admin analytics dashboard page.

Architecture
------------
- ``DashboardAdmin`` extends ``admin.PageAdmin`` — no model, no CRUD, display only.
- All data is fetched via ``DashboardService`` which owns all aggregation queries.
- DB session is obtained from ``AsyncSessionFactory`` (same pool as the API),
  not from the admin site's internal session maker, to stay consistent with the
  app's own connection settings (pool_size, pool_pre_ping, etc.).
- AMIS components are expressed as plain Python dicts wherever the component is
  not available as a typed class in fastapi-amis-admin 0.7.3.  This is safe
  because ``AmisNode`` (the Pydantic base) is declared with ``extra="allow"``,
  so each dict becomes a pass-through during JSON serialisation.
- The page is admin-auth-gated by default (inherited from ``PageAdmin`` —
  unauthenticated requests are redirected to the admin login page).

Registration
------------
  Import this module after ``admin_site`` is created to trigger the
  ``@admin_site.register_admin`` decorator.  See ``app/admin/views/__init__.py``.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi_amis_admin import admin
from fastapi_amis_admin.amis.components import Page, PageSchema

from app.admin.site import admin_site
from app.db.session import AsyncSessionFactory
from app.services.dashboard import BusinessMetrics, DashboardMetrics, DashboardService


@admin_site.register_admin
class DashboardAdmin(admin.PageAdmin):
    """Read-only system analytics dashboard, restricted to admin users."""

    page_schema = PageSchema(
        label="Dashboard",
        icon="fa fa-tachometer-alt",
        isDefaultPage=True,  # becomes the landing page when admin loads
        sort=1000,           # sidebar sorts descending — highest value = topmost
    )

    # ── Entry point ───────────────────────────────────────────────────────────

    async def get_page(self, request: Request) -> Page:
        async with AsyncSessionFactory() as db:
            metrics = await DashboardService.get_all_metrics(db)

        generated_at = metrics.generated_at.strftime("%Y-%m-%d %H:%M UTC")

        return Page(
            title="Pantry Mate — Analytics Dashboard",
            body=[
                self._page_header(generated_at),
                # ── User section ──────────────────────────────────────────
                self._section_heading("👤  User Metrics"),
                self._user_stat_row(metrics),
                # ── Inventory section ─────────────────────────────────────
                self._section_heading("📦  Inventory Metrics"),
                self._inventory_stat_row(metrics),
                # ── Recipe section ────────────────────────────────────────
                self._section_heading("🍽️  Recipe Metrics"),
                self._recipe_stat_row(metrics),
                # ── Business section ──────────────────────────────────────
                self._section_heading("💰  Business Metrics"),
                self._business_stat_row(metrics),
                # ── Charts ────────────────────────────────────────────────
                self._section_heading("📈  Trends & Distribution"),
                self._charts_row(metrics),
                # ── Tables ────────────────────────────────────────────────
                self._section_heading("🏆  Top 5 Rankings"),
                self._tables_row(metrics),
            ],
        )

    # =========================================================================
    # Private builders — each returns an AMIS-compatible dict or list of dicts
    # =========================================================================

    # ── Page chrome ───────────────────────────────────────────────────────────

    def _page_header(self, generated_at: str) -> dict[str, Any]:
        return {
            "type": "tpl",
            "tpl": (
                '<div style="margin-bottom:8px;color:#8c8c8c;font-size:12px;">'
                f"Data snapshot: {generated_at} &nbsp;·&nbsp; "
                "Refresh the page to recalculate."
                "</div>"
            ),
        }

    def _section_heading(self, title: str) -> dict[str, Any]:
        return {
            "type": "tpl",
            "tpl": (
                '<div style="'
                "margin:20px 0 8px;"
                "padding-left:10px;"
                "border-left:4px solid #1677ff;"
                "font-size:15px;"
                'font-weight:600;">'
                f"{title}"
                "</div>"
            ),
        }

    # ── Stat-card helpers ─────────────────────────────────────────────────────

    def _stat(
        self,
        title: str,
        value: Any,
        desc: str = "",
        color: str = "#1677ff",
    ) -> dict[str, Any]:
        """Stat card rendered as a ``tpl`` HTML block.

        The AMIS SDK bundled with fastapi-amis-admin 0.7.3 does NOT include a
        ``stat`` renderer — using it produces "找不到对应的渲染器" (unknown
        renderer) errors in Chinese.  ``tpl`` is a core primitive that is always
        available and produces identical visual output.
        """
        import html as _html

        safe_title = _html.escape(str(title))
        safe_value = _html.escape(str(value))
        safe_desc  = _html.escape(str(desc))
        return {
            "type": "tpl",
            "tpl": (
                '<div style="'
                "background:#ffffff;"
                "border-radius:8px;"
                "box-shadow:0 1px 6px rgba(0,0,0,.10);"
                "padding:18px 20px 14px;"
                "margin:4px 2px;"
                '">'
                f'<div style="font-size:12px;color:#8c8c8c;margin-bottom:8px;'
                f'letter-spacing:.3px;text-transform:uppercase;">{safe_title}</div>'
                f'<div style="font-size:30px;font-weight:700;color:{color};'
                f'line-height:1.15;margin-bottom:6px;">{safe_value}</div>'
                f'<div style="font-size:12px;color:#bfbfbf;">{safe_desc}</div>'
                "</div>"
            ),
        }

    def _stat_grid(self, cards: list[dict[str, Any]]) -> dict[str, Any]:
        """Four-column responsive grid of stat cards."""
        return {
            "type": "grid",
            "className": "mb-3",
            "columns": [{"sm": 3, "body": card} for card in cards],
        }

    # ── Section rows ──────────────────────────────────────────────────────────

    def _user_stat_row(self, m: DashboardMetrics) -> dict[str, Any]:
        u = m.users
        return self._stat_grid([
            self._stat("Total Users",   u.total,   "All registered accounts"),
            self._stat("Active Users",  u.active,  "is_active = true"),
            self._stat("Premium Users", u.premium, "Converted to premium tier",   "#52c41a"),
            self._stat("New (7 Days)",  u.new_7d,  "Registered in last 7 days",   "#faad14"),
        ])

    def _inventory_stat_row(self, m: DashboardMetrics) -> dict[str, Any]:
        inv = m.inventory
        return self._stat_grid([
            self._stat("Total Items",      inv.total,        "Across all users"),
            self._stat("Expiring (24 h)",  inv.expiring_24h, "Items due today / tomorrow", "#ff4d4f"),
            self._stat("Avg Items / User", inv.avg_per_user, "Mean inventory depth"),
            self._stat("Expiry Records",   inv.expiring_24h, "Active expiry-tracking rows"),
        ])

    def _recipe_stat_row(self, m: DashboardMetrics) -> dict[str, Any]:
        r = m.recipes
        top = r.top_cuisines[0]["cuisine"] if r.top_cuisines else "—"
        return self._stat_grid([
            self._stat("Total Recipes",   r.total,         "All stored recipes"),
            self._stat("Premium Recipes", r.premium_count, "Flagged is_premium = true",  "#722ed1"),
            self._stat("New (7 Days)",    r.new_7d,        "Recipes added this week"),
            self._stat("Top Cuisine",     top,             "Most requested cuisine type", "#13c2c2"),
        ])

    def _business_stat_row(self, m: DashboardMetrics) -> dict[str, Any]:
        b = m.business
        revenue_str = f"${b.estimated_monthly_revenue:,.2f}"
        conv_str    = f"{b.conversion_rate}%"
        return self._stat_grid([
            self._stat("Free Users",     b.free_count,    "On free tier"),
            self._stat("Premium Users",  b.premium_count, "Converted users",        "#52c41a"),
            self._stat("Conversion",     conv_str,        "Free → Premium rate",    "#faad14"),
            self._stat("Est. Revenue",   revenue_str,     "Active subs × $9.99/mo", "#1677ff"),
        ])

    # ── Charts ────────────────────────────────────────────────────────────────

    def _charts_row(self, m: DashboardMetrics) -> dict[str, Any]:
        return {
            "type": "grid",
            "className": "mb-3",
            "columns": [
                {"sm": 5, "body": self._user_growth_chart(m.users.growth_30d)},
                {"sm": 3, "body": self._tier_pie_chart(m.business)},
                {"sm": 4, "body": self._cuisine_bar_chart(m.recipes.top_cuisines)},
            ],
        }

    def _chart_panel(self, title: str, config: dict[str, Any]) -> dict[str, Any]:
        """Wraps an ECharts config in an AMIS chart + panel."""
        return {
            "type": "panel",
            "title": title,
            "style": {
                "borderRadius": "6px",
                "boxShadow": "0 1px 4px rgba(0,0,0,.12)",
            },
            "body": {
                "type": "chart",
                "style": {"height": "300px"},
                "config": config,
            },
        }

    def _user_growth_chart(self, growth: list[dict[str, Any]]) -> dict[str, Any]:
        dates  = [row["date"]  for row in growth]
        counts = [row["count"] for row in growth]
        return self._chart_panel(
            "User Growth — Last 30 Days",
            {
                "tooltip": {"trigger": "axis"},
                "grid": {"left": "5%", "right": "5%", "bottom": "15%", "top": "10%"},
                "xAxis": {
                    "type": "category",
                    "data": dates,
                    "axisLabel": {"rotate": 45, "fontSize": 10},
                },
                "yAxis": {"type": "value", "minInterval": 1},
                "series": [{
                    "name": "New Users",
                    "type": "line",
                    "smooth": True,
                    "areaStyle": {"opacity": 0.15},
                    "data": counts,
                    "itemStyle": {"color": "#1677ff"},
                    "lineStyle": {"width": 2},
                }],
            },
        )

    def _tier_pie_chart(self, b: BusinessMetrics) -> dict[str, Any]:
        return self._chart_panel(
            "Subscription Tier Distribution",
            {
                "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
                "legend": {"bottom": 5, "left": "center"},
                "series": [{
                    "type": "pie",
                    "radius": ["38%", "65%"],
                    "center": ["50%", "45%"],
                    "data": [
                        {
                            "value": b.free_count,
                            "name": "Free",
                            "itemStyle": {"color": "#bfbfbf"},
                        },
                        {
                            "value": b.premium_count,
                            "name": "Premium",
                            "itemStyle": {"color": "#52c41a"},
                        },
                    ],
                    "label": {"formatter": "{b}\n{d}%"},
                    "emphasis": {
                        "itemStyle": {"shadowBlur": 10, "shadowOffsetX": 0}
                    },
                }],
            },
        )

    def _cuisine_bar_chart(self, cuisines: list[dict[str, Any]]) -> dict[str, Any]:
        names  = [row["cuisine"] for row in cuisines]
        counts = [row["count"]   for row in cuisines]
        return self._chart_panel(
            "Top Cuisines",
            {
                "tooltip": {"trigger": "axis"},
                "grid": {"left": "5%", "right": "5%", "bottom": "15%", "top": "10%"},
                "xAxis": {
                    "type": "category",
                    "data": names,
                    "axisLabel": {"rotate": 30, "fontSize": 11},
                },
                "yAxis": {"type": "value", "minInterval": 1},
                "series": [{
                    "type": "bar",
                    "data": counts,
                    "itemStyle": {"color": "#722ed1"},
                    "label": {"show": True, "position": "top"},
                }],
            },
        )

    # ── Tables ────────────────────────────────────────────────────────────────

    def _tables_row(self, m: DashboardMetrics) -> dict[str, Any]:
        return {
            "type": "grid",
            "columns": [
                {"sm": 6, "body": self._top_items_table(m.inventory.top_items)},
                {"sm": 6, "body": self._top_cuisines_table(m.recipes.top_cuisines)},
            ],
        }

    def _data_table(
        self,
        title: str,
        columns: list[dict[str, str]],
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generic AMIS table wrapped in a panel."""
        return {
            "type": "panel",
            "title": title,
            "style": {
                "borderRadius": "6px",
                "boxShadow": "0 1px 4px rgba(0,0,0,.12)",
            },
            "body": {
                "type": "table",
                "columns": columns,
                "source": rows,
                "className": "table-sm",
            },
        }

    def _top_items_table(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        rows = [
            {"rank": i + 1, "name": item["name"], "count": item["count"]}
            for i, item in enumerate(items)
        ]
        return self._data_table(
            "Top 5 Most Common Inventory Items",
            columns=[
                {"name": "rank",  "label": "#",          "width": 40},
                {"name": "name",  "label": "Item Name"},
                {"name": "count", "label": "Total Count", "width": 100},
            ],
            rows=rows,
        )

    def _top_cuisines_table(self, cuisines: list[dict[str, Any]]) -> dict[str, Any]:
        rows = [
            {"rank": i + 1, "cuisine": row["cuisine"], "count": row["count"]}
            for i, row in enumerate(cuisines)
        ]
        return self._data_table(
            "Top 5 Most Requested Cuisines",
            columns=[
                {"name": "rank",    "label": "#",             "width": 40},
                {"name": "cuisine", "label": "Cuisine Type"},
                {"name": "count",   "label": "Recipe Count",  "width": 110},
            ],
            rows=rows,
        )
