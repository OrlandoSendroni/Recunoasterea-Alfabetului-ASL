import cv2
import joblib
import mediapipe as mp
import numpy as np
from PySide6.QtWidgets import ( QDialog, QVBoxLayout, QHBoxLayout,
                                QLabel, QPushButton, QTextEdit, QMessageBox,
                                QApplication
)

from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import ( QThread, Signal, Slot,
                            QTimer, Qt
)


class InferenceWorker(QThread):

    frame_ready = Signal(np.ndarray) # Emite frame-ul procesat (cu detectii) catre GUI
    log_message = Signal(str) # Emite mesaje de log (ex: erori, status)
    prediction_info = Signal(str, float) # Emite caracterul prezis si confidenta
    finished = Signal() # Emite cand thread-ul se termina

    def __init__(self):
        super().__init__()
        self.running = True
        self.model = None
        self.mp_hands = mp.solutions.hands
        self.hands = None
        self.labels_dict = {
            0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F', 6: 'G', 7: 'H', 8: 'I', 9: 'K',
            10: 'L', 11: 'M', 12: 'N', 13: 'O', 14: 'P', 15: 'Q', 16: 'R', 17: 'S', 18: 'T',
            19: 'U', 20: 'V', 21: 'W', 22: 'X', 23: 'Y'
        }
        self.color_dict = {
            'A': (0, 255, 0), 'B': (255, 0, 0), 'C': (0, 0, 255), 'D': (255, 255, 0), 'E': (0, 255, 255), 'F': (255, 0, 255),
            'G': (255, 128, 0), 'H': (128, 255, 0), 'I': (0, 128, 255), 'K': (128, 0, 255), 'L': (255, 128, 255),
            'M': (128, 128, 0), 'N': (0, 128, 128), 'O': (128, 0, 128), 'P': (255, 255, 255), 'Q': (0, 0, 0), 'R': (192, 192, 192),
            'S': (128, 128, 128), 'T': (255, 0, 128), 'U': (0, 255, 128), 'V': (128, 255, 255),
            'W': (255, 128, 128), 'X': (128, 0, 0), 'Y': (0, 0, 128)
        }
    
    def run(self):
        self.log_message.emit("Incarcare model pentru verificare...")
        try:
            self.model = joblib.load('./model.joblib')
            self.log_message.emit(f"Model incarcat cu succes: {type(self.model)}")
        except Exception as e:
            self.log_message.emit(f"Eroare la incarcarea modelului: {e}")
            self.finished.emit()
            return

        # Initializare detector maini
        self.hands = self.mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.3)

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.log_message.emit("Eroare la deschiderea camerei web!")
            self.finished.emit()
            return

        self.log_message.emit("Pornire fereastra")

        while self.running:
            ret, frame = cap.read()
            if not ret:
                self.log_message.emit("Eroare la citirea frame-ului de la camera")
                break

            H, W, _ = frame.shape
            frame_rgb =cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(frame_rgb)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Desenam landmark-urile mainii
                    mp.solutions.drawing_utils.draw_landmarks(
                        frame,
                        hand_landmarks,
                        self.mp_hands.HAND_CONNECTIONS,
                        mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                        mp.solutions.drawing_styles.get_default_hand_connections_style()
                    )

                    data_aux = []
                    x_ = []
                    y_ = []

                    if len(hand_landmarks.landmark) > 0:
                        base_x = hand_landmarks.landmark[0].x
                        base_y = hand_landmarks.landmark[0].y
                        base_z = hand_landmarks.landmark[0].z

                    for lm in hand_landmarks.landmark:
                        x_.append(lm.x)
                        y_.append(lm.y)
                        x = lm.x - base_x
                        y = lm.y - base_y
                        z = lm.z - base_z
                        data_aux.extend([x, y, z])
                    
                    if x_ and y_:
                        x1 = int(min(x_) * W)
                        y1 = int(min(y_) * H)
                        x2 = int(max(x_) * W)
                        y2 = int(max(y_) * H)

                        try:
                            data_aux = np.asarray(data_aux).reshape(1, -1)

                            if data_aux.shape[1] != self.model.n_features_in_:
                                self.log_message.emit(f"Atentie: Se asteapta {self.model.n_features_in_} caracteristici, dar s-au gasit {data_aux.shape[1]}")
                                continue

                            probabilities = self.model.predict_proba(data_aux)
                            prediction = self.model.predict(data_aux)
                            predicted_label = int(prediction[0])

                            predicted_character = self.labels_dict.get(predicted_label, 'Necunoscut')
                            confidence = probabilities[0][predicted_label]

                            cv2.rectangle(frame, (x1, y1), (x2, y2), self.color_dict.get(predicted_character, (150, 150, 150)), 4)

                            # Adauga eticheta
                            label_text = f"{predicted_character} ({confidence:.2f})"
                            cv2.putText(frame, label_text, (x1, y1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1.3,
                                        self.color_dict.get(predicted_character, (150, 150, 150)), 3,
                                        cv2.LINE_AA)

                            #Emite informatii catre GUI
                            self.prediction_info.emit(predicted_character, float(confidence))
                        except Exception as e:
                            self.log_message.emit(f"Eroare la predictie: {e}")
                            continue
            self.frame_ready.emit(frame)

        cap.release()
        self.log_message.emit("Camera eliberata. Thread-ul va fi oprit")
    
    def stop(self):
        self.running = False
    

class InferenceWindow(QDialog):
    inference_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Testare Model in Timp Real")
        self.setGeometry(100, 100, 800, 600)
        self.setModal(True)

        self.inference_worker = InferenceWorker()
        self.init_ui()
        self.connect_signals()

        self.inference_worker.start()

        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.setInterval(30)
        self.ui_update_timer.timeout.connect(self.process_gui_events)
        self.ui_update_timer.start()

    def init_ui(self):
        main_layout = QVBoxLayout()

        self.camera_feed_label = QLabel("Se incarca feed-ul camerei...")
        self.camera_feed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_feed_label.setFixedSize(640, 480)
        self.camera_feed_label.setStyleSheet("background-color: black; border: 1px solid gray;")
        main_layout.addWidget(self.camera_feed_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.prediction_info_label = QLabel("Predictie: N/A | Confidenta: N/A")
        self.prediction_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prediction_info_label.setStyleSheet("font-size: 18px; font-weight: bold; color: lightblue;")
        main_layout.addWidget(self.prediction_info_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(80)
        main_layout.addWidget(self.log_text)

        self.close_button = QPushButton("Opreste si Inchide")
        self.close_button.clicked.connect(self.close)
        main_layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(main_layout)
    
    def connect_signals(self):
        self.inference_worker.frame_ready.connect(self.display_frame)
        self.inference_worker.log_message.connect(self.log_text.append)
        self.inference_worker.prediction_info.connect(self.update_prediction_info)
        self.inference_worker.finished.connect(self.on_inference_finished)
    
    @Slot(np.ndarray)
    def display_frame(self, frame):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.camera_feed_label.width(), self.camera_feed_label.height(),
                                        Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.camera_feed_label.setPixmap(QPixmap.fromImage(p))

    
    @Slot(str, float)
    def update_prediction_info(self, character, confidence):
        self.prediction_info_label.setText(f"Predictie: {character} | Confidenta: {confidence:.2f}")

    @Slot()
    def on_inference_finished(self):
        self.log_text.append("InferenceWorker a finalizat")
        QMessageBox.information(self, "Inferenta terminata", "Modelul fost oprit din testare")
        self.close()
    
    def process_gui_events(self):
        QApplication.processEvents()
    
    def closeEvent(self, event):
        reply = QMessageBox.question(self, "Inchide Fereastra", "Sigur doresti sa opresti testarea si sa inchizi fereastra?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.inference_worker.stop()
            self.ui_update_timer.stop()
            event.accept()
            self.inference_finished.emit()
        else:
            event.ignore()
