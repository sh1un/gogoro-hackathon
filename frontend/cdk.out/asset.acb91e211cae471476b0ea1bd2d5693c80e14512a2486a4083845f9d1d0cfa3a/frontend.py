import uuid

import gradio as gr
import requests

session_uuid = str(uuid.uuid4())


def test(textbox3, dropdown_value):
    dropdown_value = dropdown_value.replace("/", "_").lower()
    url = "https://8sk70wxq58.execute-api.us-west-2.amazonaws.com/default/gogoro-hackathon-IsQuestionRelevantFunction-aTpSWLcaodLz"

    data = requests.post(
        url=url,
        json={
            "input": {
                "question": textbox3,
                "index": dropdown_value,
                "session_id": session_uuid,
            }
        },
    )

    data = data.json()
    source = format_relevent_sources(data["sources"])
    return [data["answer"], source]


def reload_session_id():
    session_uuid = str(uuid.uuid4())
    return [f"Session ID reloaded {session_uuid}", ""]


def format_relevent_sources(sources: dict) -> str:
    result = ""
    for source in sources:
        result += f"**<h1> Document{source['order']} - {source['chapter']}</h1>**\n"
        result += f"{source['document']}\n\n"
    return result


with gr.Blocks(title="Gogoro smart scooter 萬事通") as demo:
    gr.Markdown("# Gogoro smart scooter 萬事通")
    with gr.Row():
        with gr.Column():
            dropdown = gr.Dropdown(
                choices=[
                    "crossover",
                    "delight",
                    "jego",
                    "s1/1",
                    "s2/2",
                    "s3/3",
                    "superSport",
                    "viva",
                    "vivaXL",
                    "vivMIX",
                ],
                label="choose your gogoro",
            )
            user_input = gr.Textbox(lines=7, label="User Input", show_label=True)
            with gr.Row():
                submit_btn = gr.Button(value="Submit", variant="primary")
                reload_btn = gr.Button(value="Reload", variant="secondary")
            # textbox3 = gr.Textbox(lines=11, label="Change", show_label=True)
        with gr.Column():
            # output = gr.Textbox(lines=13, label="Output", show_label=True, show_copy_button=True)
            # reference = gr.Textbox(lines=7, label="Reference", show_label=True, show_copy_button=True)

            gr.Markdown("## Output")
            with gr.Group():
                output = gr.Markdown(value="", label="Output", show_label=True)
            gr.Markdown("## Reference")
            with gr.Group():
                reference = gr.Markdown(value="", label="Reference", show_label=True)

    submit_btn.click(test, inputs=[user_input, dropdown], outputs=[output, reference])
    reload_btn.click(reload_session_id, outputs=[output, reference])

demo.launch(server_port=8080)
