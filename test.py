import pandas as pd
import altair as alt
from vega_datasets import data as vega_data

# 1. Load your data (same CSV)
df = pd.read_csv("imputed_country_economics_data.csv")

# 2. Keep columns as-is, just to test
# (We only need id and one metric to start with)
df_simple = df[["id", "gdp_per_capita"]].rename(
    columns={"gdp_per_capita": "GDP per Capita (USD)"}
)

# 3. World topojson
world = alt.topo_feature(vega_data.world_110m.url, "countries")

# 4. Minimal choropleth: no params, no folding, no dashboard
choropleth = (
    alt.Chart(world)
    .mark_geoshape(stroke="white", strokeWidth=0.5)
    .transform_lookup(
        lookup="id",
        from_=alt.LookupData(
            df_simple,
            key="id",
            fields=["GDP per Capita (USD)"],
        ),
    )
    .encode(
        color=alt.Color(
            "GDP per Capita (USD):Q",
            scale=alt.Scale(scheme="blues"),
        ),
        tooltip=[
            alt.Tooltip("id:Q"),
            alt.Tooltip("GDP per Capita (USD):Q", format=".2f"),
        ],
    )
    .properties(width=600, height=320)
    .project(type="equalEarth")
)

choropleth.save("choropleth_test.html")
print("Wrote choropleth_test.html")
