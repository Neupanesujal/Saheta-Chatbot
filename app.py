import streamlit as st
import PyPDF2

from main import Chatbot

st.set_page_config(page_title="Saheta - Document Chatbot", page_icon="🐺", layout="wide")

def display_pdf(uploaded_file):
    """Display PDF preview"""
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    num_pages = len(pdf_reader.pages)
    

    page_number = st.number_input(
        "Select page", 
        min_value=1, 
        max_value=num_pages, 
        value=1,
        key="pdf_page_number"
    )
    
    
    page = pdf_reader.pages[page_number-1]
    text = page.extract_text()
    
    
    st.markdown("### PDF Preview")
    st.markdown("""
        <style>
            .pdf-preview {
                background-color: white;
                padding: 1.5rem;
                border-radius: 0.5rem;
                border: 1px solid #ddd;
                height: 300px;
                overflow-y: auto;
                font-family: monospace;
                white-space: pre-wrap;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f'<div class="pdf-preview">{text}</div>', unsafe_allow_html=True)
    st.markdown(f"Page {page_number} of {num_pages}")


if "chatbot" not in st.session_state:
    st.session_state.chatbot = None
if "messages" not in st.session_state:
    st.session_state.messages = []


left_col, right_col = st.columns([2, 1])

with left_col:
    st.title("🐺 Saheta - Document Q&A Chatbot")
    
    
    uploaded_file = st.file_uploader(label="Upload your PDF file", type=["pdf"])

   
    if uploaded_file is not None:
        if st.session_state.chatbot is None or st.session_state.current_file != uploaded_file.name:
            with st.spinner("Processing document..."):
                try:
                    st.session_state.chatbot = Chatbot(pdf_file=uploaded_file, user_info_dir="user_info")
                    st.session_state.current_file = uploaded_file.name
                    st.success("Document uploaded and processed successfully.")
                except Exception as e:
                    st.error(f"Error processing document: {str(e)}")
                    st.session_state.chatbot = None

    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    
    if st.session_state.chatbot:
        if prompt := st.chat_input("Ask me anything about the document"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = st.session_state.chatbot.ask(prompt)
                    st.markdown(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        st.write("Please upload a PDF file to start chatting.")


with right_col:
    
    if uploaded_file:
        display_pdf(uploaded_file)
        uploaded_file.seek(0)  # Reset file pointer after reading
    
    
    st.title("User Information")
    
    name = st.text_input("Your Name")
    phone = st.text_input("Phone Number")
    email = st.text_input("Email Address")
    appointment_date = st.text_input("Appointment Date")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Capture Info") and st.session_state.chatbot:
            result = st.session_state.chatbot.set_user_info(
                name=name, 
                phone=phone, 
                email=email, 
                appointment_date=appointment_date
            )
            st.toast(result)
    
    with col2:
        if st.button("Save Info") and st.session_state.chatbot:
            result = st.session_state.chatbot.save_captured_info()
            st.toast(result)