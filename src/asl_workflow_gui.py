import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QMessageBox,
    QLabel, QDialog, QHBoxLayout, QTextEdit
    )
from PySide6.QtCore import QThread, Signal, Qt, Slot # Pentru threading
from qt_material import apply_stylesheet # Pentru stilizare

import subprocess
import os

from auth_dialog import LoginDialog # Importa dialogul de autentificare
from capture_window import CaptureWindow # Importa fereastra de capturare a imaginilor
from dataset_worker import DatasetCreationWorker # Importa worker-ul pentru crearea setului de date
from model_training_worker import ModelTrainingWorker # Importa worker-ul pentru antrenarea modelului
from test_window_worker import InferenceWindow


# Clasa principala a aplicatiei GUI
class ASLWorkflowApp(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username  # Retine numele de utilizator autentificat
        self.setWindowTitle("ASL WORKFLOW GUI")
        self.setGeometry(100, 100, 800, 600)

        self.setVisible(False)
        self.init_ui()
    
    def init_ui(self):
        # Layout vertical pentru butoane
        layout = QVBoxLayout()

        layout.addStretch(1)

        # Label pentru a afisa numele de utilizator autentificat
        self.welcome_label = QLabel(f"Bine ai venit, {self.username}!")
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.welcome_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(self.welcome_label)

        # Layout pentru butoane
        buttons_layout = QVBoxLayout()

      

        # Buton pentru colectarea imaginilor
        self.btn_collect = QPushButton("1. Colecteaza Imagini")
        self.btn_collect.clicked.connect(self.start_collect_imgs) # Conecteaza butonul la o functie
        self.btn_collect.setFixedSize(250, 50)
        buttons_layout.addWidget(self.btn_collect, alignment=Qt.AlignmentFlag.AlignCenter)

        # Buton pentru crearea setului de date
        self.btn_create_dataset = QPushButton("2. Creeaza setul de date")
        self.btn_create_dataset.clicked.connect(self.start_create_dataset)
        self.btn_create_dataset.setFixedSize(250, 50)
        buttons_layout.addWidget(self.btn_create_dataset, alignment=Qt.AlignmentFlag.AlignCenter)

        # Buton pentru antrenarea modelului
        self.btn_train = QPushButton("3. Antreneaza Modelul")
        self.btn_train.clicked.connect(self.start_train_model)
        self.btn_train.setFixedSize(250, 50)
        buttons_layout.addWidget(self.btn_train, alignment=Qt.AlignmentFlag.AlignCenter)

        # Buton pentru testarea modelului
        self.btn_test = QPushButton("4. Testeaza Modelul")
        self.btn_test.clicked.connect(self.start_testing)
        self.btn_test.setFixedSize(250, 50)
        buttons_layout.addWidget(self.btn_test, alignment=Qt.AlignmentFlag.AlignCenter)

        buttons_layout.addStretch(1)  # Adauga un stretch la final pentru a centra butoanele

        centered_buttons_container = QHBoxLayout()
        centered_buttons_container.addStretch(1)  # Stretch la stanga
        centered_buttons_container.addLayout(buttons_layout)  # Adauga layout-ul de butoane centrat
        centered_buttons_container.addStretch(1)  # Stretch la dreapta

        layout.addLayout(centered_buttons_container)
        
        layout.addStretch(1)

        self.process_log_text = QTextEdit()
        self.process_log_text.setReadOnly(True)
        self.process_log_text.setPlaceholderText("Log-urile procesului vor aparea aici")
        layout.addWidget(self.process_log_text)

        #Buton pentru curatarea log-ului
        self.btn_clear_log = QPushButton("Curata Log")
        self.btn_clear_log.clicked.connect(self.process_log_text.clear)
        self.btn_clear_log.setFixedSize(150, 30)
        layout.addWidget(self.btn_clear_log, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.setLayout(layout)

    # Functiile de slot care vor fi apelate la apasarea butoanelor
    def start_collect_imgs(self):
        self.process_log_text.append("Fereastra de colectare imagini este deschisa...")
        self.set_buttons_enabled(False)

        self.capture_window = CaptureWindow(self) # Creeaza o fereastra de capturare a imaginilor
        self.capture_window.collection_finished.connect(self.on_collection_finished)
        self.capture_window.exec()
    
    @Slot()
    def on_collection_finished(self):
        """Slot Apelat cand CaptureWindow este inchisa."""
        
        self.process_log_text.append("Colectare imagini finalizata.")
        self.set_buttons_enabled(True)  # Reactivam butoanele
    
    def start_create_dataset(self):
        self.process_log_text.append("Creare set de date in curs...")
        self.set_buttons_enabled(False)

        self.dataset_worker = DatasetCreationWorker()
        # self.dataset_worker.log_message.connect(self.status_label.setText) # Afiseaza mesajele log in status_label
        self.dataset_worker.progress_update.connect(
            lambda p: self.process_log_text.append(f"Procesare imagini: {p}% completat...")
        )
        self.dataset_worker.finished.connect(self.on_dataset_creation_finished)
        self.dataset_worker.start()

    @Slot(bool, str)
    def on_dataset_creation_finished(self, success, message):
        self.set_buttons_enabled(True)  # Reactivam butoanele
        if success:
            QMessageBox.information(self, "Succes", message)
            self.process_log_text.append("Setul de date a fost creat cu succes!")
        else:
            QMessageBox.critical(self, "Eroare", message)
            self.process_log_text.append("Eroare in timpul crearii setului de date.")
    
    def start_train_model(self):
        self.set_buttons_enabled(False)
        self.process_log_text.clear()
        self.process_log_text.append("Incepe antrenarea modelului...")

        self.training_worker = ModelTrainingWorker()
        self.training_worker.finished.connect(self.on_model_training_finished)
        self.training_worker.start()
    
    @Slot(bool, str, dict)
    def on_model_training_finished(self, success, message, evaluation_results):
        self.set_buttons_enabled(True)
        if success:
            QMessageBox.information(self, "Succes", message)

            # Mesaj principal de succes
            self.process_log_text.append(f"<p style='color: lightgreen;'><b>{message}</b></p>")
            self.process_log_text.append("<hr>") # Linie de separare

            # Titlu pentru rezultate
            self.process_log_text.append("<h3 style='color: lightblue;'>REZULTATE ANTRENAMENT MODEL:</h3>")

            # Acuratețea
            accuracy = evaluation_results.get('accuracy', 'N/A')
            self.process_log_text.append(f"<p><b>Acuratețe:</b> <span style='color: yellow;'>{accuracy}</span></p>")

            # Raportul de clasificare
            classification_report = evaluation_results.get('classification_report', 'N/A')
            self.process_log_text.append("<p><b>Raport de Clasificare:</b></p>")
            self.process_log_text.append(f"<pre style='background-color: #333; padding: 10px; border-radius: 5px;'>{classification_report}</pre>")

        
           
            self.process_log_text.append("<hr>") # Linie de separare finală

        else:
            QMessageBox.critical(self, "Eroare Antrenare", message)
            self.process_log_text.append(f"<p style='color: red;'><b>A apărut o eroare la antrenarea modelului: {message}</b></p>")


    def start_testing(self):
        self.process_log_text.append("<p style='color: orange;'>Pornire testare model")
        self.set_buttons_enabled(False)

        self.inference_window = InferenceWindow(self)
        self.inference_window.inference_finished.connect(self.on_testing_finished)
        self.inference_window.exec()
    
    @Slot()
    def on_testing_finished(self):
        self.set_buttons_enabled(True)
        self.process_log_text.append("<p style='color: lightgreen;'> Testarea modelului a fost oprita.</p>")
    
   
        
    # Functii de slot pentru a gestiona rezultatele thread-ului
    def on_script_finished(self, success, script_name, message):
        self.set_buttons_enabled(True) # Reactivam butoanele
        if success:
            QMessageBox.information(self, "Succes", f"Procesul '{script_name}' s-a incheiat cu succes!")
            self.process_log_text.append("Gata.")
        else:
            QMessageBox.critical(self, "Eroare", f"A aparut o eroare: {message}")
            self.process_log_text.append("Eroare in timpul procesului.")
    
    def on_script_error(self, error_message):
        self.set_buttons_enabled(True)
        QMessageBox.critical(self, "Eroare", f"A aparut o eroare: {error_message}")
        self.process_log_text.append("Eroare in timpul procesului.")
    
    def set_buttons_enabled(self, enable):
        self.btn_collect.setEnabled(enable)
        self.btn_create_dataset.setEnabled(enable)
        self.btn_train.setEnabled(enable)
        self.btn_test.setEnabled(enable)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_lightgreen.xml')  # Aplicam tema dark_blue
    
    # 1. Creeaza si afiseaza dialogul de autentificare
    auth_dialog = LoginDialog()

    logged_in_username = None  # Variabila pentru a retine numele de utilizator autentificat

   

    # 4. Ruleaza dialogul de autentificare in mod modal (blocheaza alte interactiuni pana la inchidere)
    # dialog.exec() returneaza QDialog.Accepted daca a fost inchis cu accept(), QDialog.Rejected altfel

    if auth_dialog.exec() == QDialog.Accepted:
       logged_in_username = auth_dialog.username_logged_in if hasattr(auth_dialog, 'username_logged_in') else "Utilizator"
       
       main_window = ASLWorkflowApp(logged_in_username)
       main_window.show()

       sys.exit(app.exec())
    else:
        sys.exit(0)