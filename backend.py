import base64
import io
import pandas as pd
import plotly.graph_objects as go
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash_daq as daq
import fitz  # PyMuPDF for PDF parsing
from sqlalchemy import create_engine

# Initialize Dash app
app = dash.Dash(__name__)

# Function to extract text from PDF
def extract_text_from_pdf(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

# Function to read a database table into a DataFrame
def read_database_table():
    try:
        # Replace with your database connection string
        db_engine = create_engine("mysql+pymysql://username:password@localhost:3306/your_database")
        df = pd.read_sql("SELECT * FROM your_table_name", db_engine)
        return df
    except Exception as e:
        print(f"Database Error: {e}")
        return pd.DataFrame()

# Function to calculate dynamic metrics
def calculate_metrics(df):
    total_records = len(df)
    if total_records == 0:
        return {"completeness": 0, "consistency": 0, "overall_integrity": 0, "valid_records": 0, "invalid_records": 0}

    # Completeness: Percentage of non-null values
    completeness = (df.notnull().mean().mean()) * 100

    # Consistency: Placeholder (e.g., no duplicates)
    consistency = 100 - (df.duplicated().sum() / total_records * 100)

    # Overall Integrity: Weighted average of metrics
    overall_integrity = (0.6 * completeness + 0.4 * consistency)

    # Valid/Invalid Records (example: assume a column 'valid' exists)
    valid_records = df["valid"].sum() if "valid" in df.columns else int(0.9 * total_records)
    invalid_records = total_records - valid_records

    return {
        "completeness": round(completeness, 2),
        "consistency": round(consistency, 2),
        "overall_integrity": round(overall_integrity, 2),
        "valid_records": valid_records,
        "invalid_records": invalid_records,
    }

# Layout of the Dash App
app.layout = html.Div(
    style={'font-family': 'Arial, sans-serif', 'padding': '30px', 'backgroundColor': '#f7f7f7'},
    children=[
        html.H1('Data Integrity Dashboard', style={'text-align': 'center', 'color': '#2C3E50'}),

        # File Upload Section
        html.Div(
            children=[
                html.Label("Upload your CSV, Excel, or PDF files here:", style={'font-size': '18px', 'font-weight': 'bold', 'color': '#34495E'}),
                dcc.Upload(
                    id='file-upload',
                    children=html.Button('Upload File', style={'font-size': '16px', 'padding': '10px 20px', 'backgroundColor': '#3498db', 'color': 'white', 'border-radius': '5px'}),
                    multiple=True
                ),
                html.Button("Load Database Records", id="load-db", style={'font-size': '16px', 'margin-left': '20px', 'backgroundColor': '#2ecc71', 'color': 'white', 'border-radius': '5px'}),
            ],
            style={'margin-bottom': '20px'}
        ),

        # Loading Spinner
        dcc.Loading(
            id="loading",
            type="circle",
            children=[
                html.Div(id='loading-output', style={'text-align': 'center', 'font-size': '20px', 'color': '#3498db'})
            ]
        ),

        # Display Metrics and Graphs
        html.Div(
            children=[
                html.Div(id='overall-integrity-gauge', style={'width': '100%', 'display': 'inline-block'}),
                html.Div(id='validity-pie-chart', style={'width': '45%', 'display': 'inline-block', 'padding': '20px'}),
                html.Div(id='metrics-bar-chart', style={'width': '45%', 'display': 'inline-block', 'padding': '20px'}),
            ],
            style={'display': 'flex', 'justify-content': 'space-between'}
        ),
    ]
)

# Callback to process uploaded files and database records
@app.callback(
    [
        Output("overall-integrity-gauge", "children"),
        Output("validity-pie-chart", "children"),
        Output("metrics-bar-chart", "children"),
        Output('loading-output', 'children')
    ],
    [Input("file-upload", "contents"), Input("load-db", "n_clicks")],
    [State("file-upload", "filename")]
)
def update_visualizations(contents, db_click, filenames):
    all_data = []

    # Load database records if button clicked
    if db_click:
        db_df = read_database_table()
        if not db_df.empty:
            all_data.append(db_df)

    # Process uploaded files
    if contents:
        for content, filename in zip(contents, filenames):
            _, content_string = content.split(",")
            decoded = base64.b64decode(content_string)

            if filename.endswith(".csv"):
                df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
            elif filename.endswith(".xlsx"):
                df = pd.read_excel(io.BytesIO(decoded), engine='openpyxl')
            elif filename.endswith(".pdf"):
                text = extract_text_from_pdf(decoded)
                df = pd.DataFrame({"Extracted Text": [text]})  # Converts text to a DataFrame
            else:
                continue

            all_data.append(df)

    combined_df = pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()
    metrics = calculate_metrics(combined_df)

    # Create Gauge for Overall Integrity
    gauge_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=metrics["overall_integrity"],
        title={"text": "Overall Integrity (%)"},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "green"}},
    ))

    # Create Pie Chart for Valid/Invalid Records
    pie_fig = go.Figure(go.Pie(
        labels=["Valid Records", "Invalid Records"],
        values=[metrics["valid_records"], metrics["invalid_records"]],
        hole=0.4,
        marker=dict(colors=['#2ecc71', '#e74c3c'])
    ))

    # Create Bar Chart for Completeness and Consistency
    bar_fig = go.Figure(go.Bar(
        x=["Completeness", "Consistency"],
        y=[metrics["completeness"], metrics["consistency"]],
        marker_color=["#3498db", "#f39c12"]
    ))
    bar_fig.update_layout(title="Integrity Metrics", yaxis_title="Percentage", template="plotly_dark")

    return (
        dcc.Graph(figure=gauge_fig),
        dcc.Graph(figure=pie_fig),
        dcc.Graph(figure=bar_fig),
        "Metrics successfully calculated."
    )

if __name__ == '__main__':
    app.run_server(debug=True)
