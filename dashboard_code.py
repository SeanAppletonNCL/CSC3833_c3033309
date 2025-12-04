import pandas as pd
import altair as alt
from vega_datasets import data as vega_data
import json

# -------------------------------------------------------------------
# 1. Load & prepare data
# -------------------------------------------------------------------

df = pd.read_csv("imputed_country_economics_data.csv")

# Normalise column names to lower case
df.columns = [c.lower() for c in df.columns]

num_cols = [
    "latitude",
    "longitude",
    "population",
    "gdp",
    "gdp_growth",
    "interest_rate",
    "inflation_rate",
    "jobless_rate",
    "gov_budget",
    "debt_gdp",
    "current_account",
    "gdp_per_capita",
]

for col in num_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# -------------------------------------------------------------------
# Split Americas into North / South for the dashboard
# -------------------------------------------------------------------


def split_region(row):
    reg = row["region"]
    sub = str(row.get("subregion", "")).lower()

    if reg == "Americas":
        if "north" in sub:
            return "North America"
        if "south" in sub or "central" in sub or "caribbean" in sub:
            return "South America"
        return "South America"
    elif reg in ["Africa", "Asia", "Europe", "Oceania"]:
        return reg
    else:
        return "Other"


df["region_dash"] = df.apply(split_region, axis=1)

# -------------------------------------------------------------------
# Rename for nicer labels in charts
# -------------------------------------------------------------------

df_viz = df.rename(
    columns={
        "name": "Country",
        "region_dash": "Region",
        "population": "Population",
        "gdp_per_capita": "GDP per Capita (USD)",
        "gdp": "GDP (USD Billions)",
        "debt_gdp": "Debt/GDP (%)",
        "gov_budget": "Gov. Budget (% of GDP)",
        "jobless_rate": "Jobless Rate (%)",
        "inflation_rate": "Inflation Rate (%)",
        "gdp_growth": "GDP Growth (%)",
    }
)

metric_columns = [
    "GDP per Capita (USD)",
    "GDP (USD Billions)",
    "Debt/GDP (%)",
    "Gov. Budget (% of GDP)",
    "Jobless Rate (%)",
    "Inflation Rate (%)",
    "GDP Growth (%)",
]

# Long-form table for indicator-driven charts (bar, heatmap)
viz_long = df_viz.melt(
    id_vars=["Country", "Region", "latitude", "longitude", "Population"],
    value_vars=metric_columns,
    var_name="Indicator",
    value_name="Metric value",
)

# -------------------------------------------------------------------
# 1b. Map-specific data with safe column names (for lookup)
# -------------------------------------------------------------------

map_metric_spec = {
    "gdp_pc": "GDP per Capita (USD)",
    "gdp_total": "GDP (USD Billions)",
    "debt_ratio": "Debt/GDP (%)",
    "gov_budget_pct": "Gov. Budget (% of GDP)",
    "jobless": "Jobless Rate (%)",
    "inflation": "Inflation Rate (%)",
    "gdp_growth": "GDP Growth (%)",
}

df_map = df_viz.rename(columns={pretty: safe for safe, pretty in map_metric_spec.items()})

map_metric_columns = list(map_metric_spec.keys())

# -------------------------------------------------------------------
# 2. Global controls (Altair parameters)
# -------------------------------------------------------------------

region_options = [
    "All",
    "Africa",
    "Asia",
    "Europe",
    "North America",
    "South America",
    "Oceania",
    "Other",
]

region_param = alt.param(
    "Region_param",
    bind=alt.binding_select(options=region_options, name="Region: "),
    value="All",
)

# Single indicator selector used everywhere (map + bar + heatmap)
metric_param = alt.param(
    "metric_param",
    bind=alt.binding_select(options=metric_columns, name="Economic indicator: "),
    value="GDP per Capita (USD)",
)

n_countries_param = alt.param(
    "n_countries",
    bind=alt.binding_range(min=3, max=25, step=1, name="Number of countries: "),
    value=10,
)

top_mode_param = alt.param(
    "top_mode",
    bind=alt.binding_radio(
        options=["Highest", "Lowest"],
        name="Ranking: ",
    ),
    value="Highest",
)

region_filter_expr = "(Region_param == 'All') || (datum.Region == Region_param)"

# -------------------------------------------------------------------
# Shared region colour scale (for scatter + bar)
# -------------------------------------------------------------------

region_domain = [
    "Africa",
    "Asia",
    "Europe",
    "North America",
    "Oceania",
    "South America",
    "Other",
]

region_palette = [
    "#1f77b4",  # Africa
    "#ff7f0e",  # Asia
    "#2ca02c",  # Europe
    "#d62728",  # North America
    "#9467bd",  # Oceania
    "#8c564b",  # South America
    "#7f7f7f",  # Other
]

region_color_scale = alt.Scale(domain=region_domain, range=region_palette)

# -------------------------------------------------------------------
# 3. Global Map – Selected Economic Indicator (choropleth)
# -------------------------------------------------------------------

world = alt.topo_feature(vega_data.world_110m.url, "countries")

map_chart = (
    alt.Chart(world)
    .transform_lookup(
        lookup="id",
        from_=alt.LookupData(
            df_map,
            key="id",
            fields=["Country", "Region"] + map_metric_columns,
        ),
    )
    .transform_fold(
        map_metric_columns,
        as_=["IndicatorSafe", "Metric value"],
    )
    .transform_calculate(
        IndicatorPretty=(
            "datum.IndicatorSafe == 'gdp_pc' ? 'GDP per Capita (USD)' : "
            "datum.IndicatorSafe == 'gdp_total' ? 'GDP (USD Billions)' : "
            "datum.IndicatorSafe == 'debt_ratio' ? 'Debt/GDP (%)' : "
            "datum.IndicatorSafe == 'gov_budget_pct' ? 'Gov. Budget (% of GDP)' : "
            "datum.IndicatorSafe == 'jobless' ? 'Jobless Rate (%)' : "
            "datum.IndicatorSafe == 'inflation' ? 'Inflation Rate (%)' : "
            "datum.IndicatorSafe == 'gdp_growth' ? 'GDP Growth (%)' : ''"
        )
    )
    # filter by selected indicator
    .transform_filter("datum.IndicatorPretty == metric_param")
    # filter by selected region so the map zooms to that region
    .transform_filter(region_filter_expr)
    .mark_geoshape(stroke="#e0e0e0", strokeWidth=0.5)
    .encode(
        shape=alt.Shape(
            "Region:N",
            title="Region (shape)",
            scale=alt.Scale(domain=region_domain),
        ),
        color=alt.Color(
            "Metric value:Q",
            scale=alt.Scale(scheme="viridis", nice=True),
            legend=alt.Legend(title="Selected map indicator value"),
        ),
        tooltip=[
            alt.Tooltip("Country:N"),
            alt.Tooltip("Region:N"),
            alt.Tooltip("IndicatorPretty:N", title="Selected indicator"),
            alt.Tooltip("Metric value:Q", title="Selected value", format=".2f"),
            alt.Tooltip("gdp_pc:Q", title="GDP per Capita (USD)", format=".2f"),
            alt.Tooltip("gdp_total:Q", title="GDP (USD Billions)", format=".2f"),
            alt.Tooltip("debt_ratio:Q", title="Debt/GDP (%)", format=".2f"),
            alt.Tooltip(
                "gov_budget_pct:Q", title="Gov. Budget (% of GDP)", format=".2f"
            ),
            alt.Tooltip("jobless:Q", title="Jobless Rate (%)", format=".2f"),
            alt.Tooltip("inflation:Q", title="Inflation Rate (%)", format=".2f"),
            alt.Tooltip("gdp_growth:Q", title="GDP Growth (%)", format=".2f"),
        ],
    )
    .properties(
        width=700,
        height=450,
        title=alt.TitleParams(
            text={
                "expr": "'World map – ' + metric_param"
            },
            subtitle="The economic indicator can be changed using the control in the bottom right."
        ),
    )
    .project(type="equalEarth")
)

# -------------------------------------------------------------------
# 4. Inflation vs Interest Rate – per-region trend lines
# -------------------------------------------------------------------

legend_title = "Region"

infl_int_outlier_expr = (
    "(datum['Inflation Rate (%)'] >= -5 && datum['Inflation Rate (%)'] <= 50) && "
    "(datum.interest_rate <= 40)"
)

infl_int_scatter = (
    alt.Chart(df_viz)
    .transform_filter(region_filter_expr)
    .transform_filter(infl_int_outlier_expr)
    .mark_point(size=65, filled=True, stroke="white", strokeWidth=0.5, opacity=0.8)
    .encode(
        tooltip=[
            "Country:N",
            "Region:N",
            alt.Tooltip("Inflation Rate (%):Q", format=".1f"),
            alt.Tooltip("interest_rate:Q", title="Interest Rate (%)", format=".1f"),
        ],
    )
)

infl_int_trend = (
    alt.Chart(df_viz)
    .transform_filter(region_filter_expr)
    .transform_filter(infl_int_outlier_expr)
    .transform_regression(
        "interest_rate",
        "Inflation Rate (%)",
        groupby=["Region"],
        method="linear",
    )
    .mark_line(strokeDash=[4, 4])
)

inflation_interest_chart = (
    alt.layer(infl_int_scatter, infl_int_trend)
    .encode(
        x=alt.X("interest_rate:Q", title="Interest Rate (%)"),
        y=alt.Y("Inflation Rate (%):Q", title="Inflation Rate (%)"),
        color=alt.Color(
            "Region:N",
            title="Region (colour)",
            scale=region_color_scale,
            legend=alt.Legend(orient="right", columns=1),
        ),
        shape=alt.Shape(
            "Region:N",
            title="Region (shape)",
            legend=alt.Legend(orient="right", columns=1),
        ),
    )
    .properties(
        width=700,
        height=450,
        title={
            "text": "Inflation vs Interest Rate (by region, with trend lines)",
            "subtitle": "Each dashed line summarises the relationship in one region. "
            "Scroll to zoom, drag to pan, double-click to reset zoom.",
        },
    )
    .interactive()
)

# -------------------------------------------------------------------
# 5. Top Countries by Selected Economic Metric
# -------------------------------------------------------------------

top_countries = (
    alt.Chart(viz_long)
    .transform_filter("datum.Indicator == metric_param")
    .transform_filter(region_filter_expr)
    .transform_window(
        rank_high="rank()",
        sort=[alt.SortField("Metric value", order="descending")],
        groupby=["Indicator"],
    )
    .transform_window(
        rank_low="rank()",
        sort=[alt.SortField("Metric value", order="ascending")],
        groupby=["Indicator"],
    )
    .transform_filter(
        "top_mode == 'Highest' ? datum.rank_high <= n_countries : datum.rank_low <= n_countries"
    )
    .mark_bar()
    .encode(
        y=alt.Y("Country:N", sort="-x", title=None),
        x=alt.X("Metric value:Q", title="Selected Metric"),
        color=alt.Color(
            "Region:N",
            legend=None,
            scale=region_color_scale,  # <- match the key colours
        ),
        tooltip=[
            "Country:N",
            "Region:N",
            "Indicator:N",
            alt.Tooltip("Metric value:Q", format=".2f"),
        ],
    )
    .properties(
        width=600,
        height=280,
        title=alt.TitleParams(
            text={
                "expr": "top_mode == 'Highest' ? "
                        "'Top ' + metric_param + ' countries' : "
                        "'Lowest ' + metric_param + ' countries'"
            },
            subtitle="The economic indicator can be changed using the control in the bottom right."
        ),
    )
)


# -------------------------------------------------------------------
# 6. Heatmap – normalised average indicator values by region
# -------------------------------------------------------------------

heatmap_chart = (
    alt.Chart(viz_long)
    .transform_calculate(metric="datum['Metric value']")
    .transform_joinaggregate(
        min_val="min(metric)",
        max_val="max(metric)",
        groupby=["Indicator"],
    )
    .transform_calculate(
        norm="datum.max_val == datum.min_val ? 0.5 : "
        "(datum.metric - datum.min_val) / (datum.max_val - datum.min_val)"
    )
    .transform_aggregate(
        mean_norm="mean(norm)",
        mean_raw="mean(metric)",
        groupby=["Region", "Indicator"],
    )
    .mark_rect()
    .encode(
        x=alt.X(
            "Indicator:N",
            title=None,
            sort=metric_columns,
            axis=alt.Axis(labelAngle=-40),
        ),
        y=alt.Y(
            "Region:N",
            title="Region",
            sort=region_domain,
        ),
        color=alt.Color(
            "mean_norm:Q",
            title="Relative score (0–1)",
            scale=alt.Scale(scheme="viridis"),
        ),
        tooltip=[
            "Region:N",
            "Indicator:N",
            alt.Tooltip("mean_raw:Q", title="Mean value", format=".2f"),
            alt.Tooltip(
                "mean_norm:Q",
                title="Normalised score (0–1)",
                format=".2f",
            ),
        ],
    )
    .properties(
        width=700,
        height=330,
        title="How regions compare across indicators (0 = lowest, 1 = highest)",
    )
)

# -------------------------------------------------------------------
# 7. Layout, styling & export
# -------------------------------------------------------------------

row_top = alt.hconcat(map_chart, inflation_interest_chart)
row_bottom = alt.hconcat(top_countries, heatmap_chart)

dashboard = (
    alt.vconcat(row_top, row_bottom)
    .configure_view(stroke=None)
    .configure_axis(
        labelFont="Arial",
        titleFont="Arial",
        labelFontSize=11,
        titleFontSize=12,
        gridColor="#f0f0f0",
        domainColor="#b3b3b3",
    )
    .configure_legend(
        labelFont="Arial",
        titleFont="Arial",
        labelFontSize=11,
        titleFontSize=12,
    )
    .configure_title(
        font="Arial",
        fontSize=14,
        anchor="start",
        color="#333333",
    )
    .configure(background="white")
)

dashboard = dashboard.add_params(
    region_param,
    metric_param,
    n_countries_param,
    top_mode_param,
)

alt.theme.enable("default")

# Basic export (Altair default)
dashboard.save("dashboard.html")
print("Dashboard written to dashboard.html")

# -------------------------------------------------------------------
# 8. Pretty HTML wrapper with nicer controls + export menu
# -------------------------------------------------------------------

spec_dict = dashboard.to_dict()
spec_json = json.dumps(spec_dict, separators=(",", ":"))

html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Global Economic Indicators Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body {{
      margin: 0;
      padding: 24px 32px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background-color: #f5f5f5;
    }}
    .page {{
      max-width: 1920px;
      margin: 0 auto;
      background: #ffffff;
      padding: 24px 28px 32px;
      box-shadow: 0 12px 30px rgba(0,0,0,0.08);
      border-radius: 10px;
    }}
    h1 {{
      margin: 0 0 4px 0;
      font-size: 24px;
      letter-spacing: 0.03em;
    }}
    .subtitle {{
      margin: 0 0 20px 0;
      color: #555;
      font-size: 14px;
      line-height: 1.4;
    }}
    #vis {{
      width: 100%;
    }}

    /* -------- Make Vega-Lite controls look nicer -------- */
    #vis .vega-bindings {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 24px;
      margin-top: 16px;
      padding-top: 8px;
      border-top: 1px solid #eee;
      font-size: 13px;
      position: relative;
    }}
    #vis .vega-bind {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    #vis .vega-bind-name {{
      font-weight: 500;
      color: #444;
    }}
    #vis select,
    #vis input[type="range"],
    #vis input[type="radio"] {{
      font-size: 13px;
    }}
    #vis input[type="range"] {{
      width: 140px;
    }}

    /* Param order:
       1 = Region (global)
       2 = Economic indicator (global)
       3 = Number of countries (bar chart)
       4 = Ranking (bar chart)
    */

    /* Bar chart controls (3 & 4) on the left */
    #vis .vega-bind:nth-child(3),
    #vis .vega-bind:nth-child(4) {{
      order: 1;
    }}

    /* Move indicator control first on the right */
    #vis .vega-bind:nth-child(2) {{
      order: 2;
      margin-left: auto;
    }}
    
    /* Move Region control AFTER indicator */
    #vis .vega-bind:nth-child(1) {{
      order: 3;
    }}


    /* Section labels */
    #vis .vega-bindings::before {{
      content: "BAR CHART CONTROLS";
      flex-basis: 100%;
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #999;
      margin-bottom: -4px;
    }}
    #vis .vega-bindings::after {{
      content: "GLOBAL CONTROLS";
      position: absolute;
      right: 0;
      bottom: 32px;
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #999;
    }}

    /* Nudge the map slightly left */
    #vis svg g.marks > g:nth-child(1) {{
      transform: translateX(-25px);
    }}

    /* Move the Region (shape) legend underneath the Region (colour) legend.
       Tweak these numbers if you want it slightly higher/lower or more left/right. */
    #vis svg g[aria-label^="Region (shape)"] {{
      transform: translate(850px, 80px);
      transform-origin: top left;
    }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
</head>
<body>
  <div class="page">
    <h1>Global Economic Indicators Dashboard</h1>
    <p class="subtitle">
      Explore how different economic indicators vary across countries and regions.
      Use the controls below to filter the view.
    </p>
    <div id="vis"></div>
  </div>

  <script>
    const spec = {spec_json};
    vegaEmbed("#vis", spec, {{
      renderer: "canvas",
      actions: {{
        export: true,
        source: false,
        compiled: false,
        editor: false
      }}
    }}).catch(console.error);
  </script>
</body>
</html>
"""

with open("dashboard_pretty.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("Pretty dashboard written to dashboard_pretty.html")
