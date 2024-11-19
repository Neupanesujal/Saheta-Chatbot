import os
import re
import json
from typing import Dict, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain.vectorstores import FAISS
from langchain.document_loaders import PyPDFLoader
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

from datetime import datetime, timedelta
import dateparser
import tempfile

class Chatbot:
    def __init__(self, pdf_file, user_info_dir: str = "user_info"):
        self.user_info_dir = user_info_dir
        os.makedirs(self.user_info_dir, exist_ok=True)
        
        # Process the uploaded PDF file
        if pdf_file:
            self._process_uploaded_file(pdf_file)
        
        self.user_info: Dict[str, Optional[str]] = {
            "name": None,
            "phone": None,
            "email": None,
            "appointment_date": None
        }

    def _process_uploaded_file(self, pdf_file):
        """Process the uploaded PDF file and initialize RAG components"""
        try:
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:

                tmp_file.write(pdf_file.getvalue())
                tmp_file_path = tmp_file.name

            
            loader = PyPDFLoader(tmp_file_path)
            documents = loader.load()

            
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=100)
            split_documents = text_splitter.split_documents(documents)

            
            embedding_model = OllamaEmbeddings(model="llama3.2:1b")
            self.vectorstore = FAISS.from_documents(split_documents, embedding_model)
            self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})

            
            self.llm = Ollama(model="llama3.2:1b")

            self.prompt_template = """
            You are a helpful and conversational AI assistant providing information from the document to the user question.
            Context: {context}
            Question: {question}
            Answer:
            """
            prompt = PromptTemplate(template=self.prompt_template, input_variables=["context", "question"])
            self.rag_chain = RetrievalQA.from_chain_type(
                retriever=self.retriever, 
                llm=self.llm, 
                chain_type_kwargs={"prompt": prompt}
            )

            
            os.unlink(tmp_file_path)

        except Exception as e:
            raise Exception(f"Error processing PDF file: {str(e)}")

    def set_user_info(self, name: str = None, phone: str = None, email: str = None, appointment_date: str = None) -> str:
        """Set user information with validation"""
        validation_results = []
        
        if name is not None and name.strip():
            self.user_info['name'] = name.strip()
        
        if phone is not None and phone.strip():
            if self._validate_phone(phone):
                self.user_info['phone'] = phone.strip()
            else:
                validation_results.append("Invalid phone number")
        
        if email is not None and email.strip():
            if self._validate_email(email):
                self.user_info['email'] = email.strip()
            else:
                validation_results.append("Invalid email")
        
        if appointment_date is not None and appointment_date.strip():
            parsed_date = self._date_extraction_tool(appointment_date)
            if parsed_date:
                self.user_info['appointment_date'] = parsed_date
        
        if not validation_results:
            return "Information captured successfully"
        return " and ".join(validation_results)

    def save_captured_info(self) -> str:
        """Save captured user information to JSON file"""
        try:
            if not all(self.user_info.values()):
                return "Cannot save: Ensure all fields are filled correctly"

            
            filename = re.sub(r'[^\w\-_\. ]', '_', self.user_info['name'])
            filepath = os.path.join(self.user_info_dir, f"{filename}.json")

            
            data_to_save = {
                **self.user_info,
                "timestamp": datetime.now().isoformat()
            }

            
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    existing_data = json.load(f)
                if isinstance(existing_data, dict):
                    existing_data = [existing_data]
                existing_data.append(data_to_save)
                data_to_save = existing_data

            
            with open(filepath, 'w') as f:
                if isinstance(data_to_save, list):
                    json.dump(data_to_save, f, indent=4)
                else:
                    json.dump([data_to_save], f, indent=4)

            return "Information saved successfully"
        except Exception as e:
            return f"Error saving information: {str(e)}"

    def _validate_email(self, email: str) -> bool:
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_regex, email))

    def _validate_phone(self, phone: str) -> bool:
        cleaned_phone = re.sub(r'\D', '', phone)
        return len(cleaned_phone) >= 10 and len(cleaned_phone) <= 14
    
    def _date_extraction_tool(self, appointment_date: str) -> str:
        try:
            parsed_date = dateparser.parse(appointment_date)
            if parsed_date:
                return parsed_date.strftime(r"%Y-%m-%d")
            return None
        except Exception:
            return None

    def ask(self, question: str) -> str:
        return self.rag_chain.run(question)