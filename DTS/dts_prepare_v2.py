import gradio as gr
import pandas as pd
from pathlib import Path
from datetime import datetime

# === Output folder ===
output_folder = Path("/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/DTS test")


# === Cleaners ===
def format_cell(val):
    if pd.isna(val):
        return ""
    if isinstance(val, pd.Timestamp):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, (float, int)):
        if float(val).is_integer():
            return str(int(val))
        return f"{val:.2f}"
    return str(val).strip()


def load_excel(file):
    if file is None:
        return pd.DataFrame()

    df = pd.read_excel(file.name)
    df = df.applymap(format_cell)  # convert every cell to string with formatting
    return df


def save_excel(edited_df):
    now = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = output_folder / f"Corrected_Table_{now}.xlsx"
    df = pd.DataFrame(edited_df)
    df.to_excel(output_path, index=False)
    return f"✅ File saved to: {output_path}"


# === UI ===
with gr.Blocks() as app:
    gr.Markdown("## ✏️ DTS Table Editor (All as Strings)")

    with gr.Row():
        file_input = gr.File(label="Upload Excel file (.xlsx)", file_types=[".xlsx"])
        load_button = gr.Button("📂 Load File")

    df_editor = gr.Dataframe(
        label="📝 Edit freely",
        interactive=True,
        datatype=["str"] * 18,  # All columns are treated as strings
        row_count="dynamic",
        col_count=(18, "fixed")
    )

    save_button = gr.Button("💾 Save to Excel")
    save_output = gr.Textbox(label="Status")

    load_button.click(load_excel, inputs=file_input, outputs=df_editor)
    save_button.click(save_excel, inputs=df_editor, outputs=save_output)

app.launch()
