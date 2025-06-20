import gradio as gr
import pandas as pd

# === Load Excel files ===
sf_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/DTS test/Dummy_SFs.xlsx"
wd_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/DTS test/Dummy_Working_Days.xlsx"

sf_df = pd.read_excel(sf_path)
wd_df = pd.read_excel(wd_path)
wd_df["Label"] = wd_df["Date"].astype(str) + " – " + wd_df["Unit"]

core_crew_df = sf_df[sf_df["core_daily"].str.lower() == "core crew"].copy()
dailies_df = sf_df[sf_df["core_daily"].str.lower() == "daily"].copy()

# === Global state holders ===
current_unit = {"value": wd_df["Unit"].iloc[0]}
current_table = pd.DataFrame()

# === Functions ===

def generate_timesheet(label, default_start, default_end):
    selected_row = wd_df[wd_df["Label"] == label].iloc[0]
    selected_unit = selected_row["Unit"]
    current_unit["value"] = selected_unit

    rows = []
    for _, row in core_crew_df.iterrows():
        rows.append({
            "Name – Title": f"{row['Name']} – {row['Title'].strip()}",
            "Worked": 1.0,
            "Start": default_start,
            "End": default_end,
            "MP": 0,
            "Unit": selected_unit,
            "Note": ""
        })

    df = pd.DataFrame(rows)
    current_table[:] = df
    return df, get_available_dailies(df)

def get_available_dailies(current_data):
    df = pd.DataFrame(current_data, columns=["Name – Title", "Worked", "Start", "End", "MP", "Unit", "Note"])
    used = set(df["Name – Title"])
    all_dailies = dailies_df.apply(lambda r: f"{r['Name']} – {r['Title'].strip()}", axis=1)
    available = sorted(set(all_dailies) - used)
    return gr.update(choices=available, value=None, visible=True)

def add_manual_entry(name, title, table_data):
    df = pd.DataFrame(table_data, columns=["Name – Title", "Worked", "Start", "End", "MP", "Unit", "Note"])
    if not name.strip() or not title.strip():
        return df, get_available_dailies(df)

    name_title = f"{name.strip()} – {title.strip()}"
    if name_title in df["Name – Title"].values:
        return df, get_available_dailies(df)  # Avoid duplicate

    new_row = {
        "Name – Title": name_title,
        "Worked": 1.0,
        "Start": "08:00",
        "End": "17:00",
        "MP": 0,
        "Unit": current_unit["value"],
        "Note": ""
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df, get_available_dailies(df)

def add_daily_entry(pair, table_data, selected_label_1, selected_label_2):
    if not pair or " – " not in pair:
        return table_data, gr.update()

    name, title = pair.split(" – ", 1)
    selected_row = wd_df[wd_df["Label"] == selected_label_1].iloc[0]
    selected_date = selected_row["Date"]
    selected_unit = selected_row["Unit"]

    df = pd.DataFrame(table_data, columns=["Name – Title", "Worked", "Start", "End", "MP", "Unit", "Note"])
    name_title = f"{name.strip()} – {title.strip()}"
    if name_title in df["Name – Title"].values:
        return df, get_available_dailies(df)

    new_row = {
        "Name – Title": name_title,
        "Worked": 1.0,
        "Start": "08:00",
        "End": "17:00",
        "MP": 0,
        "Unit": selected_unit,
        "Note": ""
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df, get_available_dailies(df)

def export_csv(df):
    path = "/tmp/DTS_export.csv"
    df = pd.DataFrame(df, columns=["Name – Title", "Worked", "Start", "End", "MP", "Unit", "Note"])
    df.to_csv(path, index=False)
    return path

# === Gradio UI ===
with gr.Blocks() as app:
    gr.Markdown("🎬 **Daily Time Sheet – Gradio Version**")

    unit_dropdown = gr.Dropdown(
        choices=wd_df["Label"].tolist(),
        label="🎯 Select Date and Unit",
        value=wd_df["Label"].iloc[0]
    )

    with gr.Row():
        default_start_input = gr.Textbox(label="🕗 Default Start", value="08:00")
        default_end_input = gr.Textbox(label="🕕 Default End", value="17:00")


    dts_table = gr.Dataframe(
        headers=["Name – Title", "Worked", "Start", "End", "MP", "Unit", "Note"],
        datatype=["str", "number", "str", "str", "number", "str", "str"],
        interactive=True,
        label="📝 Core Crew + Dailies"
    )

    with gr.Row():
        name_input = gr.Textbox(label="➕ New Name")
        title_input = gr.Textbox(label="🎓 New Title")
        add_button = gr.Button("Add Manual Entry")

    gr.Markdown("### 🎯 Available Dailies (Click to Add)")
    daily_picker = gr.Dropdown(choices=[], label="📋 Daily Crew", visible=False)
    add_daily_btn = gr.Button("Add Selected Daily")

    export_btn = gr.Button("💾 Export to CSV")
    download_file = gr.File(label="⬇️ Download File")

    # === Wiring ===
    unit_dropdown.change(
        fn=generate_timesheet,
        inputs=[unit_dropdown, default_start_input, default_end_input],
        outputs=[dts_table, daily_picker]
    )

    add_button.click(fn=add_manual_entry, inputs=[name_input, title_input, dts_table], outputs=[dts_table, daily_picker])
    add_daily_btn.click(fn=add_daily_entry, inputs=[daily_picker, dts_table, unit_dropdown, unit_dropdown], outputs=[dts_table, daily_picker])
    export_btn.click(fn=export_csv, inputs=dts_table, outputs=download_file)

app.launch()
