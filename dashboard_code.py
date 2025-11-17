# dashboard.py

import pandas as pd
import altair as alt
from vega_datasets import data

# ------------------------------------------------------------
# 1. Setup
# ------------------------------------------------------------

alt.data_transformers.disable_max_rows()

df = pd.read_csv("imputed_country_economics_data.csv")
print("Columns:", df.columns.tolist())

# ------------------------------------------------------------
# 2. Region remapping – split Americas into North / South
# ------------------------------------------------------------

def map_region(row):
    r = row["region"]
    s = row["subregion"]

    # Non-Americas: keep as is
    if r != "Americas":
        return r

    # Americas → decide based on subregion
    if isinstance(s, str) and "South America" in s:
        return "South America"
    else:
        # Northern America, Central America, Caribbean etc. → treat as North America
        return "North America"

df["region_display"] = df.apply(map_region, axis=1)

# ------------------------------------------------------------
# 3. Interactive controls (params + bindings)
# ------------------------------------------------------------

# ----- Indicator dropdown for MAP -----
indicator_options = [
    "GDP per Capita (USD)",
    "GDP Growth (%)",
    "Jobless Rate (%)",
    "Inflation Rate (%)",
    "Debt/GDP (%)",
]

indicator_param = alt.param(
    "indicator",
    bind=alt.binding_select(options=indicator_options, name="Indicator: "),
    value="GDP per Capita (USD)",
)

indicator_expr = (
    "indicator == 'GDP per Capita (USD)' ? datum.gdp_per_capita : "
    "indicator == 'GDP Growth (%)' ? datum.gdp_growth : "
    "indicator == 'Jobless Rate (%)' ? datum.jobless_rate : "
    "indicator == 'Inflation Rate (%)' ? datum.inflation_rate : "
    "datum.debt_gdp"
)

# ----- Region dropdown (applies to all charts) -----
region_options = ["All"] + sorted(df["region_display"].dropna().unique().tolist())

region_param = alt.param(
    "region",
    bind=alt.binding_select(options=region_options, name="Region: "),
    value="All",
)

# Filter expression: keep all rows if region == "All"
region_filter = (
    (alt.datum.region_display == region_param) | (region_param == "All")
)

# ----- Metric dropdown for BAR chart -----
metric_options = [
    "GDP Growth (%)",
    "GDP per Capita (USD)",
    "Debt/GDP (%)",
    "Inflation Rate (%)",
]

metric_param = alt.param(
    "metric",
    bind=alt.binding_select(options=metric_options, name="Metric: "),
    value="GDP Growth (%)",
)

metric_expr = (
    "metric == 'GDP Growth (%)' ? datum.gdp_growth : "
    "metric == 'GDP per Capita (USD)' ? datum.gdp_per_capita : "
    "metric == 'Debt/GDP (%)' ? datum.debt_gdp : "
    "datum.inflation_rate"
)

# ----- Top N slider for BAR chart -----
top_n_param = alt.param(
    "top_n",
    value=10,
    bind=alt.binding_range(
        min=3,
        max=20,
        step=1,
        name="Number of countries: ",
    ),
)

# ----- Checkbox to hide outliers in line chart -----
remove_outliers = alt.param(
    "remove_outliers",
    value=False,
    bind=alt.binding_checkbox(name="Hide extreme outliers"),
)

# ------------------------------------------------------------
# 4. Map – world geoshape + bubbles using lat / lon
# ------------------------------------------------------------

countries = alt.topo_feature(data.world_110m.url, "countries")

base_map = (
    alt.Chart(countries)
      .mark_geoshape(fill="#e5e5e5", stroke="white", strokeWidth=0.5)
      .project("equalEarth")
      .properties(width=700, height=380)
)

points = (
    alt.Chart(df)
      .transform_filter(region_filter)
      .transform_calculate(indicator_value=indicator_expr)
      .transform_filter("isValid(datum.longitude) && isValid(datum.latitude)")
      .mark_circle(stroke="white", strokeWidth=0.3)
      .encode(
          longitude="longitude:Q",
          latitude="latitude:Q",
          color=alt.Color(
              "indicator_value:Q",
              title="Selected Indicator",
              scale=alt.Scale(scheme="viridis"),
          ),
          size=alt.Size(
              "population:Q",
              title="Population",
              scale=alt.Scale(range=[10, 800]),
              legend=None,
          ),
          tooltip=[
              alt.Tooltip("name:N", title="Country"),
              alt.Tooltip("region_display:N", title="Region"),
              alt.Tooltip("gdp:Q", title="GDP (USD billions)", format=".1f"),
              alt.Tooltip("gdp_per_capita:Q", title="GDP per Capita (USD)", format=".0f"),
              alt.Tooltip("gdp_growth:Q", title="GDP Growth (%)", format=".1f"),
              alt.Tooltip("jobless_rate:Q", title="Jobless Rate (%)", format=".1f"),
              alt.Tooltip("inflation_rate:Q", title="Inflation Rate (%)", format=".1f"),
              alt.Tooltip("debt_gdp:Q", title="Debt/GDP (%)", format=".1f"),
          ],
      )
)

map_chart = (
    (base_map + points)
      .properties(title="Global Map – Selected Economic Indicator")
      .add_params(indicator_param, region_param)
)

# ------------------------------------------------------------
# 5. Scatter – GDP vs Jobless Rate (by Region)
# ------------------------------------------------------------

scatter = (
    alt.Chart(df)
      .transform_filter(region_filter)
      .mark_circle(opacity=0.75, stroke="white", strokeWidth=0.5)
      .encode(
          x=alt.X(
              "gdp:Q",
              title="GDP (USD billions)",
              scale=alt.Scale(type="log"),
          ),
          y=alt.Y(
              "jobless_rate:Q",
              title="Jobless Rate (%)",
              scale=alt.Scale(domain=[0, 35]),
          ),
          color=alt.Color("region_display:N", title="Region"),
          size=alt.Size(
              "population:Q",
              legend=alt.Legend(title="Population"),
          ),
          tooltip=[
              alt.Tooltip("name:N", title="Country"),
              alt.Tooltip("region_display:N", title="Region"),
              alt.Tooltip("gdp:Q", title="GDP (USD billions)", format=".1f"),
              alt.Tooltip("jobless_rate:Q", title="Jobless Rate (%)", format=".1f"),
          ],
      )
      .properties(
          width=600,
          height=260,
          title="GDP vs Jobless Rate (by Region)",
      )
      .add_params(region_param)
)

# ------------------------------------------------------------
# 6. Bar – Top N countries by selected metric (region aware)
# ------------------------------------------------------------

bar = (
    alt.Chart(df)
      .transform_filter(region_filter)
      .transform_calculate(
          metric_value=metric_expr,
      )
      .transform_window(
          row_number="row_number()",
          sort=[alt.SortField("metric_value", order="descending")],
      )
      .transform_filter("datum.row_number <= top_n")
      .mark_bar()
      .encode(
          y=alt.Y("name:N", sort="-x", title="Country"),
          x=alt.X("metric_value:Q", title="Selected Metric"),
          color=alt.Color("region_display:N", legend=None),
          tooltip=[
              alt.Tooltip("name:N", title="Country"),
              alt.Tooltip("region_display:N", title="Region"),
              alt.Tooltip("metric_value:Q", title="Value", format=".2f"),
          ],
      )
      .properties(
          width=700,
          height=260,
          title="Top Countries by Selected Economic Metric",
      )
      .add_params(metric_param, region_param, top_n_param)
)

# ------------------------------------------------------------
# 7. Line – Inflation vs GDP Growth (by Region) with outlier toggle
# ------------------------------------------------------------

line = (
    alt.Chart(df)
      .transform_filter(region_filter)
      .transform_filter(
          # If remove_outliers is False → keep everything
          # If True → only keep rows within reasonable bounds
          "(!remove_outliers) || "
          "(abs(datum.gdp_growth) <= 15 && datum.inflation_rate <= 80)"
      )
      .mark_line(point=True)
      .encode(
          x=alt.X("gdp_growth:Q", title="GDP Growth (%)"),
          y=alt.Y("inflation_rate:Q", title="Inflation Rate (%)"),
          color=alt.Color("region_display:N", title="Region"),
          tooltip=[
              alt.Tooltip("region_display:N", title="Region"),
              alt.Tooltip("name:N", title="Country"),
              alt.Tooltip("gdp_growth:Q", title="GDP Growth (%)", format=".1f"),
              alt.Tooltip("inflation_rate:Q", title="Inflation Rate (%)", format=".1f"),
          ],
          order="gdp_growth:Q",
      )
      .properties(
          width=600,
          height=260,
          title="Inflation vs GDP Growth (by Region)",
      )
      .add_params(region_param, remove_outliers)
)

# ------------------------------------------------------------
# 8. Layout & export
# ------------------------------------------------------------

top_row = alt.hconcat(
    map_chart,
    scatter,
).resolve_scale(color="independent")

bottom_row = alt.hconcat(
    bar,
    line,
).resolve_scale(color="independent")

dashboard = (
    alt.vconcat(top_row, bottom_row)
      .configure_view(stroke=None)
      .properties(title="Country Economic Overview Dashboard")
)

dashboard.save("dashboard.html")
print("Saved dashboard.html")
