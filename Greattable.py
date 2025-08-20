# -*- coding: utf-8 -*-
import os
import re
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Input, Output

# --- 1) Pfad zur Datei ---
FILE_PATH = "Datamap.xlsx"
if not os.path.exists(FILE_PATH):
    raise FileNotFoundError(f"Datei nicht gefunden: {FILE_PATH}")

# ---------- Hilfsfunktionen ----------

def parse_number_de(x):
    if x is None or (isinstance(x, float) and np.isnan(x)): return np.nan
    if isinstance(x, (int, float, np.number)): return float(x)
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "none"}: return np.nan
    s = s.replace("\xa0", " ").replace("%", "").replace("‰", "").strip()
    s = s.replace(" ", "").replace(".", "").replace(",", ".")
    try: return float(s)
    except Exception: return np.nan

def as_percent_0_100(x):
    v = parse_number_de(x)
    if np.isnan(v): return np.nan
    return v * 100.0 if 0.0 <= abs(v) <= 1.0 else v

def clean_cols(df):
    df = df.rename(columns={c: re.sub(r"\s+", " ", str(c).strip()) for c in df.columns})
    aliases = {
        "TS Anteil ÜS %": "TS Anteil ÜS [%]", "TS Anteil Sedi %": "TS Anteil Sedi [%]",
        "DH": "DH [%]", "Stabiltät": "Stabilität", "AdhesieSchale": "Adhäsion Schale",
        "AdhesieOberfläche": "Adhäsion Oberfläche",
    }
    df = df.rename(columns={a: b for a, b in aliases.items() if a in df.columns and b not in df.columns})
    return df

def load_sheet(name):
    df = pd.read_excel(FILE_PATH, sheet_name=name, header=0)
    df = clean_cols(df)
    if "Material" in df.columns: df["Material"] = df["Material"].ffill()
    return df

# --- 2) Daten laden ---
carb = load_sheet("Carbohydratasen")
prot = load_sheet("Proteasen")
filme = load_sheet("Filme")

mm_columns_all = [c for c in prot.columns if str(c).strip().startswith("MM")]

# --- 3) numerische Spalten aufbereiten ---
num_cols_map = {
    "carb": (carb, ["TS Anteil ÜS [%]", "TS Anteil Sedi [%]", "Löslichkeit [%]"], ["cglc [μM]", "pH (vor)", "pH (nach)"]),
    "prot": (prot, ["TS Anteil ÜS [%]", "TS Anteil Sedi [%]", "Löslichkeit [%]", "DH [%]"] + mm_columns_all, ["pH (vor)", "pH (nach)"]),
    "filme": (filme, [], ["Homogenität", "Stabilität", "Adhäsion Schale", "Adhäsion Oberfläche", "Kohäsion", "Geruch", "Summe"])
}
for name, (df, pct_cols, num_cols) in num_cols_map.items():
    for col in pct_cols:
        if col in df.columns: df[col] = df[col].apply(as_percent_0_100)
    for col in num_cols:
        if col in df.columns: df[col] = df[col].apply(parse_number_de)

# --- 4) Dash App ---
app = Dash(__name__)
app.title = "Interaktive Datenkarte — AniMOX"

app.layout = html.Div([
    html.H1("📊 Interaktive Datenkarte — AniMOX", style={"textAlign": "center"}),
    html.Div([
        html.Div([
            html.Label("Datensatz"),
            dcc.Dropdown(id="dataset-choice", options=[
                {"label": "Carbohydratasen", "value": "carb"}, {"label": "Proteasen", "value": "prot"},
                {"label": "Filme", "value": "filme"}], value="carb", clearable=False)
        ], style={"width": "22%", "display": "inline-block", "padding": "8px"}),
        html.Div([
            html.Label("Material"),
            dcc.Dropdown(id="material-choice", multi=True, placeholder="Alle")
        ], style={"width": "28%", "display": "inline-block", "padding": "8px"}),
        html.Div([
            html.Label("Enzym"),
            dcc.Dropdown(id="enzym-choice", multi=True, placeholder="Alle")
        ], style={"width": "28%", "display": "inline-block", "padding": "8px"}),
    ]),
    html.Div([
        html.Div(id="carb-options-container", children=[
            html.Label("Zusatzdaten (Carbohydratasen)"),
            dcc.Checklist(id="carb-options", options=[
                {"label": "Proteinlöslichkeit [%]", "value": "loes"}, {"label": "abs(ΔpH)", "value": "deltaph"},
                {"label": "Reduzierende Zucker [µM]", "value": "glc"}, {"label": "pH (vor/nach)", "value": "ph"}
            ], value=["loes", "glc", "deltaph"], inline=True)
        ], style={"padding": "6px"}),
        html.Div(id="prot-options-container", children=[
            html.Label("Ansicht (Proteasen)"),
            dcc.RadioItems(id='prot-view-choice', options=[
                {'label': 'Verteilung TS', 'value': 'distribution'}, {'label': 'Heatmap MM-Fraktionen', 'value': 'heatmap'}
            ], value='distribution', inline=True, style={"marginBottom": "10px"}),
            html.Div(id="prot-ts-options-container", children=[
                html.Label("Zusatzdaten für TS-Verteilung"),
                dcc.Checklist(id="prot-options", options=[
                    {"label": "Proteinlöslichkeit [%]", "value": "loes"}, {"label": "Hydrolysegrad [%]", "value": "dh"},
                    {"label": "abs(ΔpH)", "value": "deltaph"}, {"label": "pH (vor/nach)", "value": "ph"}
                ], value=["loes", "dh", "deltaph"], inline=True),
            ]),
            html.Div(id="prot-heatmap-options-container", children=[
                html.Label("MM-Fraktionen für Heatmap"),
                dcc.Checklist(id="mm-fractions", options=[{"label": m, "value": m} for m in mm_columns_all],
                              value=mm_columns_all, inline=True)
            ]),
        ], style={"padding": "6px"}),
    ]),
    dcc.Graph(id="main-plot", config={"displayModeBar": True}, style={'height': '60vh'}),
], style={"padding": "10px"})

# --- 5) Dynamische Callbacks ---
@app.callback(
    [Output("material-choice", "options"), Output("enzym-choice", "options")],
    [Input("dataset-choice", "value")]
)
def update_dropdowns(dataset):
    df_map = {"carb": carb, "prot": prot, "filme": filme}
    df = df_map.get(dataset, carb)
    mats = sorted(df["Material"].dropna().unique())
    enz = sorted(df["Enzym"].dropna().unique()) if "Enzym" in df.columns else []
    return ([{"label": m, "value": m} for m in mats], [{"label": e, "value": e} for e in enz])

@app.callback(
    [Output("carb-options-container", "style"), Output("prot-options-container", "style")],
    [Input("dataset-choice", "value")]
)
def toggle_option_visibility(dataset):
    return ({'display': 'block' if dataset == 'carb' else 'none'},
            {'display': 'block' if dataset == 'prot' else 'none'})

@app.callback(
    [Output("prot-ts-options-container", "style"), Output("prot-heatmap-options-container", "style")],
    [Input("dataset-choice", "value"), Input("prot-view-choice", "value")]
)
def toggle_prot_sub_options(dataset, view):
    if dataset != 'prot': return {'display': 'none'}, {'display': 'none'}
    return ({'display': 'block' if view == 'distribution' else 'none'},
            {'display': 'block' if view == 'heatmap' else 'none'})

# --- 6) Hauptplot ---
@app.callback(
    Output("main-plot", "figure"),
    [Input("dataset-choice", "value"), Input("material-choice", "value"),
     Input("enzym-choice", "value"), Input("carb-options", "value"),
     Input("prot-options", "value"), Input("prot-view-choice", "value"),
     Input("mm-fractions", "value")]
)
def update_plot(dataset, mats, enz, carb_opts, prot_opts, prot_view, mm_selected):
    fig = go.Figure(layout={"template": "plotly_white", "title": "Bitte Daten auswählen"})
    df_map = {"carb": carb, "prot": prot, "filme": filme}
    dff = df_map.get(dataset, carb).copy()

    if "Material" in dff.columns and mats: dff = dff[dff["Material"].isin(mats)]
    if "Enzym" in dff.columns and enz: dff = dff[dff["Enzym"].isin(enz)]
    if dff.empty: return fig

    if dataset == "carb":
        dff["abs(ΔpH)"] = (dff["pH (nach)"] - dff["pH (vor)"]).abs()
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=dff["Enzym"], y=dff["TS Anteil ÜS [%]"], name="TS Überstand [%]"), secondary_y=False)
        fig.add_trace(go.Bar(x=dff["Enzym"], y=dff["TS Anteil Sedi [%]"], name="TS Sediment [%]"), secondary_y=False)
        
        traces_to_add = {
            "loes": ("Löslichkeit [%]", "Proteinlöslichkeit [%]"), "glc": ("cglc [μM]", "Reduzierende Zucker [µM]"),
            "deltaph": ("abs(ΔpH)", "abs(ΔpH)"), "ph": [("pH (vor)", "pH (vor)"), ("pH (nach)", "pH (nach)")]
        }
        for opt in carb_opts or []:
            if opt == 'ph':
                for col, name in traces_to_add[opt]: fig.add_trace(go.Scatter(x=dff["Enzym"], y=dff[col], name=name, mode="markers+lines"), secondary_y=True)
            else:
                col, name = traces_to_add[opt]; fig.add_trace(go.Scatter(x=dff["Enzym"], y=dff[col], name=name, mode="markers+lines"), secondary_y=True)

        fig.update_layout(barmode="stack", title="Carbohydratasen — TS-Verteilung & Zusatzdaten", xaxis_title="Enzym",
                          yaxis=dict(title="TS [%]", range=[0, 105]), yaxis2=dict(title="Zusatzdaten", overlaying="y", side="right"),
                          legend=dict(orientation="h", y=-0.25, yanchor="bottom"), template="plotly_white")
        return fig

    elif dataset == "prot":
        if prot_view == 'distribution':
            dff["abs(ΔpH)"] = (dff["pH (nach)"] - dff["pH (vor)"]).abs()
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=dff["Enzym"], y=dff["TS Anteil ÜS [%]"], name="TS Überstand [%]"), secondary_y=False)
            fig.add_trace(go.Bar(x=dff["Enzym"], y=dff["TS Anteil Sedi [%]"], name="TS Sediment [%]"), secondary_y=False)

            traces_to_add = {
                "loes": ("Löslichkeit [%]", "Proteinlöslichkeit [%]"), "dh": ("DH [%]", "Hydrolysegrad [%]"),
                "deltaph": ("abs(ΔpH)", "abs(ΔpH)"), "ph": [("pH (vor)", "pH (vor)"), ("pH (nach)", "pH (nach)")]
            }
            for opt in prot_opts or []:
                if opt == 'ph':
                    for col, name in traces_to_add[opt]: fig.add_trace(go.Scatter(x=dff["Enzym"], y=dff[col], name=name, mode="markers+lines"), secondary_y=True)
                else:
                    col, name = traces_to_add[opt]; fig.add_trace(go.Scatter(x=dff["Enzym"], y=dff[col], name=name, mode="markers+lines"), secondary_y=True)
            
            fig.update_layout(barmode="stack", title="Proteasen — TS-Verteilung & Zusatzdaten", xaxis_title="Enzym",
                              yaxis=dict(title="TS [%]", range=[0, 105]), yaxis2=dict(title="Zusatzdaten", overlaying="y", side="right"),
                              legend=dict(orientation="h", y=-0.25, yanchor="bottom"), template="plotly_white")
            return fig

        elif prot_view == 'heatmap':
            num_mats = len(mats) if mats else 0
            
            if num_mats > 2:
                fig.update_layout(title="Слишком много материалов для сравнения", annotations=[dict(
                        text="Пожалуйста, выберите не более двух материалов для тепловой карты.",
                        showarrow=False, xref="paper", yref="paper", font=dict(size=14))])
                return fig

            elif num_mats == 2:
                mat1, mat2 = mats[0], mats[1]
                fig = make_subplots(rows=2, cols=1, subplot_titles=(f"Материал: {mat1}", f"Материал: {mat2}"), vertical_spacing=0.15)
                mm_present = [m for m in (mm_selected or []) if m in dff.columns]
                if not mm_present:
                    fig.update_layout(title="Proteasen — Пожалуйста, выберите MM-фракции"); return fig

                dff1 = dff[dff["Material"] == mat1]
                pivot1 = dff1.melt(id_vars="Enzym", value_vars=mm_present, var_name="MM-Fraktion", value_name="Anteil [%]")\
                             .pivot_table(index="MM-Fraktion", columns="Enzym", values="Anteil [%]", aggfunc='mean')
                dff2 = dff[dff["Material"] == mat2]
                pivot2 = dff2.melt(id_vars="Enzym", value_vars=mm_present, var_name="MM-Fraktion", value_name="Anteil [%]")\
                             .pivot_table(index="MM-Fraktion", columns="Enzym", values="Anteil [%]", aggfunc='mean')
                
                z_min = min(pivot1.min().min(), pivot2.min().min()) if not pivot1.empty and not pivot2.empty else 0
                z_max = max(pivot1.max().max(), pivot2.max().max()) if not pivot1.empty and not pivot2.empty else 100

                fig.add_trace(go.Heatmap(z=pivot1.values, x=pivot1.columns, y=pivot1.index,
                                         coloraxis="coloraxis1", text=pivot1.values, texttemplate="%{text:.1f}"), row=1, col=1)
                fig.add_trace(go.Heatmap(z=pivot2.values, x=pivot2.columns, y=pivot2.index,
                                         coloraxis="coloraxis1", text=pivot2.values, texttemplate="%{text:.1f}"), row=2, col=1)
                
                fig.update_layout(title_text="Proteasen — Сравнение MM-фракций",
                                  coloraxis1=dict(colorscale='Greens', cmin=z_min, cmax=z_max, colorbar_title="Anteil [%]"),
                                  height=700, template="plotly_white")
                return fig
            
            else: # 0 или 1 материал
                mm_present = [m for m in (mm_selected or []) if m in dff.columns]
                if not mm_present:
                    fig.update_layout(title="Proteasen — Пожалуйста, выберите MM-фракции"); return fig
                
                title_text = f"Proteasen — Heatmap MM-фракций ({mats[0]})" if num_mats == 1 else "Proteasen — Heatmap MM-фракций (среднее по всем)"
                pivot = dff.melt(id_vars="Enzym", value_vars=mm_present, var_name="MM-Fraktion", value_name="Anteil [%]")\
                           .pivot_table(index="MM-Fraktion", columns="Enzym", values="Anteil [%]", aggfunc='mean')
                
                fig = px.imshow(pivot, text_auto=".1f", aspect="auto", color_continuous_scale="Greens",
                                labels=dict(x="Enzym", y="MM-Fraktion", color="Anteil [%]"), title=title_text)
                fig.update_xaxes(side="top"); fig.update_layout(template="plotly_white")
                return fig

    elif dataset == "filme":
        fig = px.bar(dff, x="Versuchsnr.", y="Summe", color="Material",
                     hover_data=["Homogenität", "Stabilität", "Adhäsion Schale",
                                 "Adhäsion Oberfläche", "Kohäsion", "Geruch"],
                     title="Filme — Gesamtbewertung")
        fig.update_layout(template="plotly_white", legend=dict(orientation="h", y=-0.2, yanchor="bottom"))
        return fig
    
    return fig

    app.title = "Interaktive Datenkarte — AniMOX"
    server = app.server
    app = Dash(__name__)
    app.layout = html.Div([
