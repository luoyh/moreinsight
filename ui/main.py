from tarfile import data_filter
import streamlit as st
import time
import requests
import json


if "messages" not in st.session_state:
    st.title("MoreInsight")
    resp = requests.post("http://localhost:8000/apps/adkmcp/users/u2/sessions/s2")
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def agent_process(input: str, ai_response: list):
    print(f"input: {input}")
    with requests.post("http://localhost:8000/run_sse", json={  
            "appName": "adkmcp",
            "userId": "u2",
            "sessionId": "s2",
            "newMessage": {
                "role": "user",
                "parts": [
                    {
                        "text": input
                    }
                ]
            },
            "streaming": True
        }, stream=True) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                try:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data:"):
                        data = decoded_line[len("data:"):].strip()
                        root = json.loads(data)
                        if root['partial']:
                            for text in root["content"]["parts"]:
                                ai_response.append(text["text"])
                                yield text["text"]
                except Exception as e:
                    continue

def main():
    if input:=st.chat_input("问吧."):
        #st.text(f"你输入了: {input}")
        st.session_state.messages.append({"role": "user", "content": input})
        with st.chat_message("user"):
            st.markdown(input)
        ai_response = []
        with st.chat_message("assistant"):
            st.write_stream(agent_process(input, ai_response))
        st.session_state.messages.append({"role": "assistant", "content": "".join(ai_response)})
if __name__ == "__main__":
    main()
