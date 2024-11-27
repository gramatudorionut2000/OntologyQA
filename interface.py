import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit,
                            QFrame)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from rdflib import Graph, Namespace
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class UnionLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background-color: #c41e3a;
                padding: 5px 10px;
                border-radius: 10px;
                font-weight: bold;
            }
        """)

class SearchBox(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                padding-left: 45px;
                border: 2px solid #4a4a4a;
                border-radius: 20px;
                background-color: #3b3b3b;
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #c41e3a;
            }
        """)
        self.setPlaceholderText("Ask a question about labor organizations...")

class CustomButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet("""
            QPushButton {
                padding: 12px 25px;
                background-color: #c41e3a;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d4364f;
            }
            QPushButton:pressed {
                background-color: #a01830;
            }
        """)

class AnswerDisplay(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QTextEdit {
                background-color: #3b3b3b;
                color: #ffffff;
                border: 2px solid #4a4a4a;
                border-radius: 15px;
                padding: 15px;
                font-size: 14px;
                line-height: 1.6;
            }
        """)
        self.setReadOnly(True)

class InfoCard(QFrame):
    def __init__(self, title, content):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: #3b3b3b;
                border-radius: 15px;
                padding: 15px;
            }
        """)
        layout = QVBoxLayout(self)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #c41e3a; font-size: 16px; font-weight: bold;")
        content_label = QLabel(content)
        content_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        layout.addWidget(title_label)
        layout.addWidget(content_label)

class LaborQAApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Labor Movement Knowledge Base")
        self.setMinimumSize(1000, 800)
        
        print("Loading ontology...")
        self.g = Graph()
        self.g.parse("labor_ontology_with_qa_v2.owl", format="xml")
        self.qa_ns = Namespace("http://example.org/labor/qa/")
        self.g.bind("qa", self.qa_ns)
        
        # Extract questions and answers
        self.qa_pairs = self.extract_qa_pairs()
        
        # Initialize TF-IDF
        self.tfidf = TfidfVectorizer(stop_words='english')
        if self.qa_pairs:
            self.question_vectors = self.tfidf.fit_transform([q['question'] for q in self.qa_pairs])
        else:
            print("Warning: No QA pairs found in the ontology")
            self.question_vectors = None
        
        self.setup_ui()
        
    def extract_qa_pairs(self):
        qa_pairs = []
        question_pred = self.qa_ns.questionText
        answer_pred = self.qa_ns.answerText
        
        for s, p, o in self.g.triples((None, question_pred, None)):
            answer = self.g.value(s, answer_pred)
            if answer:
                qa_pairs.append({
                    'question': str(o),
                    'answer': str(answer)
                })
        
        print(f"Extracted {len(qa_pairs)} QA pairs from ontology")
        return qa_pairs
    
    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
        """)
        
        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #c41e3a;
                border-radius: 15px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        
        title = QLabel("Labor Movement Knowledge Base")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 32px;
            color: #ffffff;
            font-weight: bold;
            padding: 20px;
        """)
        
        subtitle = QLabel("Explore the history and organizations of the labor movement")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 16px;
            color: #ffffff;
            padding-bottom: 20px;
        """)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addWidget(header_frame)
        
        # Search section
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: #3b3b3b;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        search_layout = QVBoxLayout(search_frame)
        
        search_title = QLabel("Ask a Question")
        search_title.setStyleSheet("""
            font-size: 20px;
            color: #ffffff;
            font-weight: bold;
            margin-bottom: 10px;
        """)
        search_layout.addWidget(search_title)
        
        input_layout = QHBoxLayout()
        self.question_input = SearchBox()
        self.question_input.returnPressed.connect(self.search_answer)
        
        search_button = CustomButton("Search")
        search_button.clicked.connect(self.search_answer)
        
        input_layout.addWidget(self.question_input)
        input_layout.addWidget(search_button)
        search_layout.addLayout(input_layout)
        
        main_layout.addWidget(search_frame)
        
        # Answer section
        answer_frame = QFrame()
        answer_frame.setStyleSheet("""
            QFrame {
                background-color: #3b3b3b;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        answer_layout = QVBoxLayout(answer_frame)
        
        answer_title = QLabel("Answer")
        answer_title.setStyleSheet("""
            font-size: 20px;
            color: #ffffff;
            font-weight: bold;
            margin-bottom: 10px;
        """)
        answer_layout.addWidget(answer_title)
        
        self.answer_display = AnswerDisplay()
        answer_layout.addWidget(self.answer_display)
        
        main_layout.addWidget(answer_frame)
        
        # Info section
        info_layout = QHBoxLayout()
        
        db_info = InfoCard(
            "Knowledge Base Status",
            f"Loaded {len(self.qa_pairs)} questions and answers"
        )
        info_layout.addWidget(db_info)
        
        usage_info = InfoCard(
            "How to Use",
            "Type your question in natural language and press Enter or click Search"
        )
        info_layout.addWidget(usage_info)
        
        main_layout.addLayout(info_layout)
    
    def search_answer(self):
        question = self.question_input.text().strip()
        if not question:
            return
            
        if not self.qa_pairs:
            self.answer_display.setText("No questions available in the knowledge base.")
            return
        
        existing_match = next((qa for qa in self.qa_pairs if qa['question'].lower() == question.lower()), None)
        if existing_match:
            self.display_answer(existing_match['answer'], 1.0, existing_match['question'])
            return
        
        # Calculate TF-IDF similarity
        question_vector = self.tfidf.transform([question])
        similarities = cosine_similarity(question_vector, self.question_vectors).flatten()
        max_similarity = max(similarities)
        max_index = np.argmax(similarities)
        
        if max_similarity > 0.55:
            best_match = self.qa_pairs[max_index]
            self.display_answer(best_match['answer'], max_similarity, best_match['question'])
        else:
            self.answer_display.setText("Sorry, I lack information about that topic.")
    
    def display_answer(self, answer, similarity, matched_question):
        formatted_answer = (
            f"{answer}\n\n"
            f"{'='*50}\n"
            f"Matched Question: {matched_question}\n"
            f"Confidence: {similarity:.1%}"
        )
        self.answer_display.setText(formatted_answer)

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont('Segoe UI', 10))
    window = LaborQAApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()