import pandas as pd
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output

# =============================
# Daten laden
# =============================
FILE_PATH = "Datamap.xlsx"
carb = pd.read_excel(FILE_PATH, sheet_name="Carbohydratasen", header=0)
prot = pd.read_excel(FILE_PATH, sheet_name="Proteasen", header=0)
filme = pd.read_excel(FILE_PATH, sheet_name="Filme", header=0)

# =============================
# Dash App
# =============================
app = Dash(__name__)

app.layout = html.Div([
    html.H1("📊 Interaktive Datenkarte", style={'textAlign': 'center'}),

    # Dataset-Auswahl
    html.Div([
        html.Label("Datensatz wählen:"),
        dcc.Dropdown(
            id="dataset-choice",
            options=[
                {"label": "Carbohydratasen", "value": "carb"},
                {"label": "Proteasen", "value": "prot"}
            ],
            value="carb", clearable=False
        )
    ], style={"padding": "10px"}),

    # Material-Filter
    html.Div([
        html.Label("Material:"),
        dcc.Dropdown(id="material-choice", multi=True)
    ], style={"padding": "10px"}),

    # Enzym-Filter
    html.Div([
        html.Label("Enzyme:"),
        dcc.Dropdown(id="enzym-choice", multi=True)
    ], style={"padding": "10px"}),

    # MM-Fraktionen (nur Proteasen)
    html.Div([
        html.Label("M-Fraktionen:"),
        dcc.Dropdown(
            id="mm-fractions",
            options=[{"label": f"M{i}", "value": f"M{i}"} for i in range(1, 11)],
            value=["M1"], multi=True
        )
    ], style={"padding": "10px"}),

    # Zusatzoptionen Carbohydratasen
    html.Div([
        html.Label("Zusatzdaten (Carbohydratasen):"),
        dcc.Checklist(
            id="carb-options",
            options=[
                {"label": "Proteinlöslichkeit [%]", "value": "loes"},
                {"label": "ΔpH", "value": "deltaph"},
                {"label": "Reduzierende Zucker [µM]", "value": "glc"},
                {"label": "pH (vor/nach)", "value": "ph"}
            ],
            value=["loes", "deltaph", "glc"],
            inline=True
        )
    ], style={"padding": "10px"}),

    # Zusatzoptionen Proteasen
    html.Div([
        html.Label("Zusatzdaten (Proteasen):"),
        dcc.Checklist(
            id="prot-options",
            options=[
                {"label": "Proteinlöslichkeit [%]", "value": "loes"},
                {"label": "DH [%]", "value": "dh"},
                {"label": "Heatmap", "value": "heat"}
            ],
            value=["loes", "dh"],
            inline=True
        )
    ], style={"padding": "10px"}),

    dcc.Graph(id="main-plot", style={"height": "800px"})
])


# =============================
# Callback
# =============================
@app.callback(
    Output("main-plot", "figure"),
    Input("dataset-choice", "value"),
    Input("material-choice", "value"),
    Input("enzym-choice", "value"),
    Input("mm-fractions", "value"),
    Input("carb-options", "value"),
    Input("prot-options", "value")
)
def update_plot(dataset, mats, enz, mm_selected, carb_opts, prot_opts):
    # --------------------
    # Carbohydratasen
    # --------------------
    if dataset == "carb":
        dff = carb.copy()
        if mats:
            dff = dff[dff["Material"].isin(mats)]
        if enz:
            dff = dff[dff["Enzym"].isin(enz)]

        # Prozentwerte korrekt formatieren
        for col in ["TS Anteil ÜS %", "TS Anteil Sedi %", "Löslichkeit [%]"]:
            dff[col] = pd.to_numeric(dff[col], errors="coerce")

        fig = go.Figure()

        # Bars: TS Supernatant & Sediment
        fig.add_trace(go.Bar(
            x=dff["Enzym"], y=dff["TS Anteil ÜS %"],
            name="TS Überstand [%]", marker_color="royalblue"
        ))
        fig.add_trace(go.Bar(
            x=dff["Enzym"], y=dff["TS Anteil Sedi %"],
            name="TS Sediment [%]", marker_color="orange"
        ))

        # Zusatzdaten
        if "loes" in carb_opts:
            fig.add_trace(go.Scatter(
                x=dff["Enzym"], y=dff["Löslichkeit [%]"].round(2),
                name="Proteinlöslichkeit [%]", mode="markers+lines",
                marker=dict(size=8, color="green"), yaxis="y2"
            ))
        if "glc" in carb_opts:
            fig.add_trace(go.Scatter(
                x=dff["Enzym"], y=pd.to_numeric(dff["cglc [μM]"], errors="coerce").round(2),
                name="Reduzierende Zucker [µM]", mode="markers+lines",
                marker=dict(size=8, color="brown"), yaxis="y2"
            ))
        if "deltaph" in carb_opts:
            dff["ΔpH"] = pd.to_numeric(dff["pH (nach)"], errors="coerce") - pd.to_numeric(dff["pH (vor)"], errors="coerce")
            fig.add_trace(go.Scatter(
                x=dff["Enzym"], y=dff["ΔpH"].round(2),
                name="ΔpH", mode="lines+markers",
                marker=dict(size=6, color="red"), yaxis="y2"
            ))
        if "ph" in carb_opts:
            fig.add_trace(go.Scatter(
                x=dff["Enzym"], y=pd.to_numeric(dff["pH (vor)"], errors="coerce").round(2),
                name="pH (vor)", mode="markers+lines",
                marker=dict(size=6, color="purple"), yaxis="y2"
            ))
            fig.add_trace(go.Scatter(
                x=dff["Enzym"], y=pd.to_numeric(dff["pH (nach)"], errors="coerce").round(2),
                name="pH (nach)", mode="markers+lines",
                marker=dict(size=6, color="violet"), yaxis="y2"
            ))

        fig.update_layout(
            barmode="group",
            title="Carbohydratasen — TS-Verteilung und Zusatzdaten",
            xaxis_title="Enzym",
            yaxis=dict(title="TS [%]"),
            yaxis2=dict(title="Zusatzdaten", overlaying="y", side="right"),
            legend=dict(orientation="h", y=-0.25),
            template="plotly_white"
        )
        return fig

    # --------------------
    # Proteasen
    # --------------------
    if dataset == "prot":
        dff = prot.copy()
        if mats:
            dff = dff[dff["Material"].isin(mats)]
        if enz:
            dff = dff[dff["Enzym"].isin(enz)]

        fig = go.Figure()

        # Heatmap über M-Fraktionen
        if "heat" in prot_opts and mm_selected:
            mm_cols = [c for c in dff.columns if any(m in c for m in mm_selected)]
            heat_data = dff[mm_cols].apply(pd.to_numeric, errors="coerce")
            fig.add_trace(go.Heatmap(
                z=heat_data.values,
                x=mm_cols,
                y=dff["Enzym"],
                colorbar=dict(title="Intensität"),
                colorscale="Viridis"
            ))

        # Löslichkeit
        if "loes" in prot_opts:
            fig.add_trace(go.Scatter(
                x=dff["Enzym"], y=pd.to_numeric(dff["Löslichkeit [%]"], errors="coerce").round(2),
                name="Proteinlöslichkeit [%]", mode="markers+lines",
                marker=dict(size=8, color="green")
            ))

        # DH
        if "dh" in prot_opts and "DH [%]" in dff.columns:
            fig.add_trace(go.Scatter(
                x=dff["Enzym"], y=pd.to_numeric(dff["DH [%]"], errors="coerce").round(2),
                name="DH [%]", mode="markers+lines",
                marker=dict(size=8, color="red"), yaxis="y2"
            ))

        fig.update_layout(
            title="Proteasen — Zusatzdaten",
            xaxis_title="Enzym",
            yaxis=dict(title="Löslichkeit [%]"),
            yaxis2=dict(title="DH [%]", overlaying="y", side="right"),
            legend=dict(orientation="h", y=-0.25),
            template="plotly_white"
        )
        return fig


# =============================
# Run
# =============================
if __name__ == "__main__":
    app.run_server(debug=True)



