import sys
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QMessageBox, QLabel
from PySide6.QtCore import Signal, QThread, Qt

# Importa functiile helper pentru baza de date
from database import create_user, verify_user


class RegisterWorker(QThread):
    """
    Clasa worker pentru operatiuni de inregistrare in fundal.
    """
    register_result = Signal(bool, str)  # Semnal pentru a emite rezultatul (succes, mesaj)

    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = password
    
    def run(self):
        """
        Metoda executata cand thread-ul este pornit.
        """
        success, message = create_user(self.username, self.password)
        self.register_result.emit(success, message)



class LoginWorker(QThread):
    """
    Clasa worker pentru operatiuni de autentificare in fundal.
    """
    login_result = Signal(bool, str)  # Semnal pentru a emite rezultatul (succes, mesaj)

    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = password

    def run(self):
        success, message = verify_user(self.username, self.password)
        self.login_result.emit(success, message)

class RegisterDialog(QDialog):

    registration_successful = Signal()  # Semnal pentru a anunta succesul inregistrarii

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Inregistrare Utilizator")
        self.setFixedSize(350, 250)  # Seteaza dimensiunea ferestrei

        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nume utilizator")
        form_layout.addRow("Utilizator:", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Parola")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Parola:", self.password_input)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirma Parola")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Confirma Parola:", self.confirm_password_input)

        main_layout.addLayout(form_layout)

        self.register_button = QPushButton("Inregistreaza")
        self.register_button.clicked.connect(self.handle_register)
        main_layout.addWidget(self.register_button)

        self.status_label = QLabel("Introduceti numele de utilizator si parola.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)
    
    def set_inputs_enabled(self, enabled):
        """
        Activeaza sau dezactiveaza campurile de introducere si butonul de inregistrare.
        """
        self.username_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.confirm_password_input.setEnabled(enabled)
        self.register_button.setEnabled(enabled)
    
    def handle_register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        confirm_password = self.confirm_password_input.text().strip()

        if not username or not password or not confirm_password:
            QMessageBox.warning(self, "Eroare", "Te rog sa completezi toate campurile.")
            return
        if password != confirm_password:
            QMessageBox.warning(self, "Eroare", "Parolele nu se potrivesc.")
            return
        if len(password) < 8:
            QMessageBox.warning(self, "Eroare", "Parola trebuie sa aiba cel putin 8 caractere.")
            return
        
        self.status_label.setText("Inregistrare in curs...")
        self.set_inputs_enabled(False)

        self.register_worker = RegisterWorker(username, password)
        self.register_worker.register_result.connect(self.on_register_result)
        self.register_worker.start()
    
    def on_register_result(self, success, message):
        self.set_inputs_enabled(True)

        if success:
            QMessageBox.information(self, "Succes", message)
            self.registration_successful.emit()  # Emit semnalul de succes
            self.accept()  # Inchide dialogul
        else:
            QMessageBox.critical(self, "Eroare Inregistrare", message)
            self.status_label.setText("Eroare. Introdu credentialele din nou.")

class LoginDialog(QDialog):

    authentication_successful = Signal(str)  # Semnal pentru a anunta succesul autentificarii

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Autentificare Utilizator")
        self.setFixedSize(350, 250)  # Seteaza dimensiunea ferestrei

        self.username_logged_in = None

        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nume utilizator")
        form_layout.addRow("Utilizator:", self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Parola")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Parola:", self.password_input)

        main_layout.addLayout(form_layout)
        
        self.login_button = QPushButton("Autentifica")
        self.login_button.clicked.connect(self.handle_login)
        main_layout.addWidget(self.login_button)
        

        self.create_account_label = QLabel(
            'Nu ai cont? <a href="#">Creeaza un cont apasand aici</a>'
        )
        self.create_account_label.setOpenExternalLinks(False) # Nu deschide link-ul in browser
        self.create_account_label.linkActivated.connect(self.open_register_dialog)
        self.create_account_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.create_account_label)

        self.status_label = QLabel("Introduceti numele de utilizator si parola.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)
    
    def set_inputs_enabled(self, enabled):
        """
        Activeaza sau dezactiveaza campurile de introducere si butonul de autentificare.
        """
        self.username_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.login_button.setEnabled(enabled)
    
    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Eroare", "Te rog sa completezi toate campurile.")
            return

        self.status_label.setText("Autentificare in curs...")
        self.set_inputs_enabled(False)

        self.login_worker = LoginWorker(username, password)
        self.login_worker.login_result.connect(self.on_login_result)
        self.login_worker.start()
    
    def on_login_result(self, success, message):
        self.set_inputs_enabled(True)

        if success:
            QMessageBox.information(self, "Succes", message)
            self.username_logged_in = self.username_input.text().strip()
            self.authentication_successful.emit(self.username_logged_in)  # Emit semnalul de succes
            self.accept()  # Inchide dialogul
        else:
            QMessageBox.critical(self, "Eroare Autentificare", message)
            self.status_label.setText("Eroare. Introdu credentialele din nou.")
    
    def open_register_dialog(self):

        self.set_inputs_enabled(False)  # Dezactiveaza campurile de autentificare

        register_dialog = RegisterDialog(self)
        register_dialog.registration_successful.connect(self.on_registration_successful)
        register_dialog.exec_()  # Deschide dialogul de inregistrare

        self.set_inputs_enabled(True)  # Reactiva campurile de autentificare dupa inchiderea dialogului

    def on_registration_successful(self, username, password):
        
        QMessageBox.information(self, "Inregistrare", f"Contul '{username}' a fost creat cu succes!")

        self.username_input.setText(username)  # Pre-populeaza numele de utilizator
        self.status_label.setText("Cont nou creat. Te poti autentifica acum.")

        

