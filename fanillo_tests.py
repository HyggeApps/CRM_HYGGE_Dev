import streamlit as st
import time

if "todo" not in st.session_state:
    st.session_state.todo = ""

st.json(st.session_state)

def add_todo_callback(todo_id: str):
    name = st.session_state[f"form_{todo_id}__title"]
    description = st.session_state[f"form_{todo_id}__description"]
    date = st.session_state[f"form_{todo_id}__date"]
    st.session_state['todo'] = f"{name}-{description}-{date}"

def todo_edit_form(todo_id: str):
    with st.container(border=True):
        st.subheader(f"Edit todo {todo_id}")
        with st.form(f"form_{todo_id}", enter_to_submit=False, border=False):
            st.text_input("Title", key=f"form_{todo_id}__title")	
            st.text_area("Description", key=f"form_{todo_id}__description")
            st.date_input("Date", key=f"form_{todo_id}__date")

            st.form_submit_button("Add todo",
                    type="primary",
                    on_click=add_todo_callback,
                    args=(todo_id,))

        st.write(st.session_state.todo)

todo_edit_form('teste')
todo_edit_form('teste2')