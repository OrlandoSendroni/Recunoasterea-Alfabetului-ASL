import os 
import cv2
import time
import numpy as np
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QMessageBox,
    QWidget, QGridLayout
)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import (
    Qt, QTimer, QThread, Signal, Slot,
    QWaitCondition, QMutex
)

DATA_DIR = "./data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Configurari pentru colectarea imaginilor
collection_modes = [
    {"name": "mana_dreapta_lumina_buna", "prefix": "md_lb"},
    {"name": "mana_dreapta_lumina_slaba", "prefix": "md_ls"}
]
batch_size = 1000
cooldown = 0.025

def ensure_class_dir(class_id):
    class_dir = os.path.join(DATA_DIR, str(class_id))
    if not os.path.exists(class_dir):
        os.makedirs(class_dir)
    return class_dir

def get_existing_images_count(class_id, mode_prefix):
    class_dir = ensure_class_dir(class_id)
    count = 0
    if not os.path.exists(class_dir):
        return 0
    for filename in os.listdir(class_dir):
        if filename.startswith(mode_prefix) and filename.endswith('.jpg') and not filename.endswith('_flipped.jpg'):
            count += 1
    return count

def get_next_image_number(class_id, mode_prefix):
    class_dir = ensure_class_dir(class_id)
    if not os.path.exists(class_dir):
        return 0
    
    max_num = -1

    for filename in os.listdir(class_dir):
        if filename.startswith(mode_prefix) and filename.endswith('.jpg') and not filename.endswith('_flipped.jpg'):
            try:
                num_str = filename.replace(mode_prefix + '_', '').replace('.jpg', '')
                num = int(num_str)
                max_num = max(max_num, num)
            except ValueError:
                continue
    return max_num + 1 if max_num != -1 else 0

def get_total_images_for_class(class_id):
    total = 0
    for mode in collection_modes:
        count = get_existing_images_count(class_id, mode["prefix"])
        total += count * 2 # Original + Flipped
    return total

def get_class_completion_status(class_id):
    status = {}
    for mode in collection_modes:
        count = get_existing_images_count(class_id, mode["prefix"])
        total_count = count * 2
        status[mode["name"]] = f"{count}/{batch_size} originale ({total_count}/{batch_size * 2} totale)"
    return status

def save_image_with_flip(frame, class_dir, filename_base):
    
    original_path = os.path.join(class_dir, f"{filename_base}.jpg")
    cv2.imwrite(original_path, frame)
    flipped_frame = cv2.flip(frame, 1)
    flipped_path = os.path.join(class_dir, f"{filename_base}_flipped.jpg")
    cv2.imwrite(flipped_path, flipped_frame)
    return original_path, flipped_path


# --- Thread pentru Camera ---
class CameraThread(QThread):
    frame_ready = Signal(np.ndarray) # Emite un frame OpenCV (numpy array)
    log_message = Signal(str) # Emite mesaje de log pentru QTextEdit

    def __init__(self):
        super().__init__()
        self.running = True
        self.cap = None

    def run(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.log_message.emit("Eroare la deschiderea camerei!")
            self.running = False
            return
        
        self.log_message.emit("Camera deschisă cu succes!")
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                self.frame_ready.emit(frame)
            else:
                self.log_message.emit("Eroare la citirea frame-ului!")
                time.sleep(0.1) 
        
        if self.cap:
            self.cap.release()
            self.log_message.emit("Camera eliberata.")
    
    def stop(self):
        self.running = False
        self.wait()  # Asteapta ca thread-ul sa se termine


class ImageProcessingThread(QThread):

    log_message = Signal(str)
    status_update = Signal(int, str, int) # (class_id, mode_name, total_images)
    process_finished = Signal(int) # Emite clasa ID cand procesarea este terminata

    def __init__(self):
        super().__init__()
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()
        self.is_capturing = False
        self.current_frame = None
        self.running = True

        # Stari initiale
        self.current_class = 0
        self.current_mode_index = 0
        self.current_mode = collection_modes[self.current_mode_index]
        self.current_count = 0
        self.timer_start = 0
    
    def run(self):
        self.log_message.emit("Thread de procesare imagini pornit.")

        self.current_count = get_existing_images_count(self.current_class, self.current_mode["prefix"])
        self.log_message.emit(f"Clasa initiala '{self.current_class}' are {self.current_count} imagini.")
        self.status_update.emit(self.current_class, self.current_mode["name"], self.current_count)

        while self.running:
            self.mutex.lock()
            if not self.is_capturing and self.running:
                self.wait_condition.wait(self.mutex)
            self.mutex.unlock()

            if not self.running: # Iesim din bucla daca thread-ul nu mai ruleaza
                break

            current_time = time.time()
            if self.is_capturing and (current_time - self.timer_start >= cooldown):
                if self.current_frame is not None:
                    try:
                        class_dir = ensure_class_dir(self.current_class)
                        next_img_num = get_next_image_number(self.current_class, self.current_mode["prefix"])
                        filename_base = f"{self.current_mode['prefix']}_{next_img_num}"

                        original_path, flipped_path = save_image_with_flip(self.current_frame, class_dir, filename_base)
                        self.current_count += 1
                        self.log_message.emit(f"Imagine salvata: {original_path} si {flipped_path}")
                        self.status_update.emit(self.current_class, self.current_mode["name"], self.current_count)

                        if self.current_count >= batch_size:
                            self.log_message.emit(f"Mod '{self.current_mode['name']}' completat pentru clasa {self.current_class}.")
                            self.is_capturing = False
                            self.process_finished.emit(self.current_class)  # Notificam GUI-ul ca procesarea este terminata)

                            # Trecem automat la urmatorul mod
                            self.current_mode_index += 1
                            if self.current_mode_index < len(collection_modes):
                                self.current_mode = collection_modes[self.current_mode_index]
                                self.current_count = get_existing_images_count(self.current_class, self.current_mode["prefix"])
                                self.log_message.emit(f"Am trecut la modul: {self.current_mode['name']}")
                                self.log_message.emit(f"Imagini existente pentru acest mode: {self.current_count}")
                            else:
                                self.log_message.emit(f"TOATE MODURILE COMPLETATE pentru clasa {self.current_class}.")
                                total_for_class= get_total_images_for_class(self.current_class)
                                self.log_message.emit(f"Total imagini pentru clasa {self.current_class}: {total_for_class}")
                                self.log_message.emit("Apasati (n) pentru a trece la urmatoarea clasa.")

                    except Exception as e:
                        self.log_message.emit(f"Eroare la salvarea imaginii: {str(e)}")
                    self.timer_start = current_time
                else:
                    self.log_message.emit("Asteapta un frame de la camera...")
                    time.sleep(0.01)
            time.sleep(0.001)  # Previne utilizarea excesiva a CPU
    

    @Slot(np.ndarray)
    def receive_frame(self, frame):
        """Slot pentru a primi frame-uri de la CameraThread"""
        self.current_frame = frame
    
    def start_capture(self):
        self.mutex.lock()
        self.is_capturing = True
        self.timer_start = time.time()
        self.wait_condition.wakeAll() # Trezeste thread-ul de procesare
        self.mutex.unlock()
        self.log_message.emit("Capturare pornita.")
        self.status_update.emit(self.current_class, self.current_mode["name"], self.current_count)
    

    def stop_capture(self):
        self.mutex.lock()
        self.is_capturing = False
        self.mutex.unlock()
        self.log_message.emit("Capturare oprita.")
        self.status_update.emit(self.current_class, self.current_mode["name"], self.current_count)
    
    def next_mode(self):
        self.stop_capture()
        self.current_mode_index = (self.current_mode_index + 1) % len(collection_modes)
        self.current_mode = collection_modes[self.current_mode_index]
        self.current_count = get_existing_images_count(self.current_class, self.current_mode["prefix"])
        self.log_message.emit(f" Schimbat la modul: {self.current_mode['name']}")
        self.log_message.emit(f"Imagini existente pentru acest mod: {self.current_count}")
        self.status_update.emit(self.current_class, self.current_mode["name"], self.current_count)

    def next_class(self):
        self.stop_capture()
        self.current_class += 1
        self.current_mode_index = 0
        self.current_mode = collection_modes[self.current_mode_index]
        self.current_count = get_existing_images_count(self.current_class, self.current_mode["prefix"])
        self.log_message.emit(f"Schimbat la clasa: {self.current_class}")
        self.log_message.emit(f"Imagini existente pentru clasa {self.current_class}: {self.current_count}")
        ensure_class_dir(self.current_class)  # Asigura ca directorul clasei exista
        self.status_update.emit(self.current_class, self.current_mode["name"], self.current_count)
    
    def prev_class(self):
        self.stop_capture()
        
        if self.current_class > 0:
            self.current_class -= 1
            self.current_mode_index = 0
            self.current_mode = collection_modes[self.current_mode_index]
            self.current_count = get_existing_images_count(self.current_class, self.current_mode["prefix"])
            self.log_message.emit(f"Schimbat la clasa: {self.current_class}")
            self.log_message.emit(f"Imagini existente pentru clasa {self.current_class}: {self.current_count}")
            self.status_update.emit(self.current_class, self.current_mode["name"], self.current_count)
        else:
            self.log_message.emit("Nu se poate merge la clasa anterioara, deja la clasa 0.")
    
    def reset_current_mode_count(self):
        
        self.stop_capture()
        class_dir = ensure_class_dir(self.current_class)
        prefix = self.current_mode["prefix"]
        deleted_count = 0
        if os.path.exists(class_dir):
            for filename in os.listdir(class_dir):
                if filename.startswith(prefix) and filename.endswith('.jpg'):
                    os.remove(os.path.join(class_dir, filename))
                    deleted_count += 1
        
        self.current_count = 0
        self.log_message.emit(f"Toate imaginile pentru modul '{self.current_mode['name']}' au fost sterse.")
        self.log_message.emit(f"Au fost sterse {deleted_count} imagini.")
        self.status_update.emit(self.current_class, self.current_mode["name"], self.current_count)
    
    def show_status(self):
        self.log_message.emit(f"\n=== STATUS CLASA {self.current_class} ===")
        status = get_class_completion_status(self.current_class)
        for mode_name, count in status.items():
            self.log_message.emit(f"{mode_name}: {count}")
        total_images = get_total_images_for_class(self.current_class)
        total_needed = len(collection_modes) * batch_size * 2
        self.log_message.emit(f"Total imagini: {total_images}/{total_needed} pentru clasa {self.current_class}")
        self.log_message.emit("=============================\n")
    
    def shutdown(self):
        self.running = False
        self.wait_condition.wakeAll()
        self.wait()

class CaptureWindow(QDialog):

    collection_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Colectare Imagini")
        self.setGeometry(100, 100, 1000, 700)

    

        self.camera_thread = CameraThread()
        self.processing_thread = ImageProcessingThread()

        self.init_ui()
        
        self.connect_threads()

        self.processing_thread.start()
        self.camera_thread.start()

        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        self.log_text.append("Sistem de captura pentru setul de date.")
        self.log_text.append(f"Pentru fiecare clasa se vor colect {batch_size * 2} imagini (originale + flip) per mod.")
        self.log_text.append("TOTAL: 4000 imagini per clasa.")
        self.log_text.append("\nFoloseste butoanele de control de mai jos.")

    def init_ui(self):
        
        main_layout = QVBoxLayout()

        # Zona pentu camera
        self.camera_label = QLabel("Se incarcă camera...")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setFixedSize(640, 480)
        self.camera_label.setStyleSheet("background-color: black; border: 1px solid gray;")
        main_layout.addWidget(self.camera_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Zona pentru statusuri
        status_layout = QHBoxLayout()
        self.status_capture_label = QLabel("Stare: Pauza")
        self.status_class_label = QLabel(f"Clasa: {self.processing_thread.current_class}")
        self.status_mode_label = QLabel(f"Mod: {self.processing_thread.current_mode['name']}")
        self.status_count_label = QLabel(f"Imagini: {self.processing_thread.current_count}/{batch_size}")

        status_layout.addWidget(self.status_capture_label)
        status_layout.addStretch(1)
        status_layout.addWidget(self.status_class_label)
        status_layout.addStretch(1)
        status_layout.addWidget(self.status_mode_label)
        status_layout.addStretch(1)
        status_layout.addWidget(self.status_count_label)

    
        main_layout.addLayout(status_layout)

        # Zona pentru log-uri (QTextEdit)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(100)
        main_layout.addWidget(self.log_text)

        # Zona pentru butoanele de control
        controls_layout = QGridLayout()

        self.btn_toggle_capture = QPushButton("Start/Pauza Captura")
        self.btn_toggle_capture.clicked.connect(self.toggle_capture)
        controls_layout.addWidget(self.btn_toggle_capture, 0, 0)

        self.btn_next_mode = QPushButton("Urmatorul Mod")
        self.btn_next_mode.clicked.connect(self.processing_thread.next_mode)
        controls_layout.addWidget(self.btn_next_mode, 0, 1)

        self.btn_next_class = QPushButton("Urmatoarea Clasa")
        self.btn_next_class.clicked.connect(self.processing_thread.next_class)
        controls_layout.addWidget(self.btn_next_class, 0, 2)

        self.btn_prev_class = QPushButton("Clasa Anterioara")
        self.btn_prev_class.clicked.connect(self.processing_thread.prev_class)
        controls_layout.addWidget(self.btn_prev_class, 1, 0)

        self.btn_reset_mode = QPushButton("Reset Mod Curent")
        self.btn_reset_mode.clicked.connect(self.processing_thread.reset_current_mode_count)
        controls_layout.addWidget(self.btn_reset_mode, 1, 1)

        self.btn_show_status = QPushButton("Arata Status Clasa")
        self.btn_show_status.clicked.connect(self.processing_thread.show_status)
        controls_layout.addWidget(self.btn_show_status, 1, 2)

        main_layout.addLayout(controls_layout)

        self.setLayout(main_layout)
    
    def connect_threads(self):
        # Conecteaza semnalele camerei la sloturile GUI-ului
        self.camera_thread.frame_ready.connect(self.display_frame)
        self.camera_thread.log_message.connect(self.log_text.append)

        # Conecteaza semnalele de procesare la sloturile GUI-ului
        self.processing_thread.log_message.connect(self.log_text.append)
        self.processing_thread.status_update.connect(self.update_status_labels)
        self.processing_thread.process_finished.connect(self.on_process_finished)

        # Conecteaza frame-urile de la camera la thread-ul de procesare
        self.camera_thread.frame_ready.connect(self.processing_thread.receive_frame)
    
    @Slot(np.ndarray)
    def display_frame(self, frame):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.camera_label.width(), self.camera_label.height(), Qt.AspectRatioMode.KeepAspectRatio)
        self.camera_label.setPixmap(QPixmap.fromImage(p))
    
    @Slot(np.ndarray)
    def update_status_labels(self, current_class, current_mode_name, current_count):
        self.status_class_label.setText(f"Clasa: {current_class}")
        self.status_mode_label.setText(f"Mod: {current_mode_name}")
        self.status_count_label.setText(f"Imagini: {current_count}/{batch_size}")  
        self.status_capture_label.setText("Stare: Captura" if self.processing_thread.is_capturing else "Stare: Pauza") 

    def toggle_capture(self):
        if self.processing_thread.is_capturing:
            self.processing_thread.stop_capture()
            self.status_capture_label.setText("Stare: Pauza")
            self.btn_toggle_capture.setText("Start Captura")
        else:
            self.processing_thread.start_capture()
            self.status_capture_label.setText("Stare: Captura")
            self.btn_toggle_capture.setText("Pauza Captura")
    
    def on_process_finished(self):
        QMessageBox.information( self, "Colectare Terminata", "Un mod a fost completat. Apasa 'Urmatorul Mod' pentru a continua.")
        self.btn_toggle_capture.setText("Start Captura")
    
    def closeEvent(self, event):
        reply = QMessageBox.question(self, "Inchide Aplicatia", "Sigur doresti sa inchizi aplicatia?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.camera_thread.stop()
            self.processing_thread.shutdown()
            event.accept()
            self.collection_finished.emit()
        else:
            event.ignore()