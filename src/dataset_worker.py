import os
import pandas as pd
import mediapipe as mp
import cv2
from PySide6.QtCore import QThread, Signal

class DatasetCreationWorker(QThread):
    log_message = Signal(str)
    progress_update = Signal(int) #Emite procentul de progres
    finished = Signal(bool, str) # Emite (succes, mesaj)

    def __init__(self):
        super().__init__()
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.3)
        self.DATA_DIR = "./data" # Directorul cu imaginile colectate
        self.running = True
    
    def run(self):
        self.log_message.emit("Incepem crearea dataset-ului...")
        data = []
        labels = []

        try:
            # Ne asiguram ca DATA_DIR exista si nu este gol
            if not os.path.exists(self.DATA_DIR) or not os.listdir(self.DATA_DIR):
                self.finished.emit(False, f"Directorul de date '{self.DATA_DIR}' nu exista sau este gol.")
                return

            class_dirs = [d for d in os.listdir(self.DATA_DIR) if os.path.isdir(os.path.join(self.DATA_DIR, d))]
            
            if not class_dirs:
                self.finished.emit(False, "Nu s-au gasit clase in directorul de date.")
                return
            
            total_images_to_process = 0
            for d in class_dirs:
                total_images_to_process += len([f for f in os.listdir(os.path.join(self.DATA_DIR,d)) if f.endswith('.jpg')])

            if total_images_to_process == 0:
                self.finished.emit(False, "Nu exista imagini in directorul specificat.")
                return    
            
            processed_images_count = 0

            for dir_name in class_dirs:
                if not self.running: # Verificam daca thread-ul ar trebui sa se opreasca
                    self.finished.emit(False, "Procesare set de date intrerupta.")
                    return
                
                current_class_path = os.path.join(self.DATA_DIR, dir_name)

                image_files = sorted([f for f in os.listdir(current_class_path) if f.endswith('.jpg')])

                for img_filename in image_files:
                    if not self.running:
                        self.finished.emit(False, "Procesare set de date intrerupta.")
                        return

                    full_img_path = os.path.join(current_class_path, img_filename)
                    img = cv2.imread(full_img_path)
                    if img is None:
                        self.log_message.emit(f"Nu s-a putut incarca imaginea: {full_img_path}")
                        continue
                    
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    results = self.hands.process(img_rgb)

                    if results.multi_hand_landmarks:
                        hand_landmarks = results.multi_hand_landmarks[0]
                        data_aux = []

                        base_x = hand_landmarks.landmark[0].x
                        base_y = hand_landmarks.landmark[0].y
                        base_z = hand_landmarks.landmark[0].z

                        for lm in hand_landmarks.landmark:
                            x = lm.x - base_x
                            y = lm.y - base_y
                            z = lm.z - base_z
                            data_aux.extend([x, y, z])
                        
                        data.append(data_aux)
                        labels.append(dir_name)
                    else:
                        self.log_message.emit(f"Avertizare: Nu s-au detectat maini in imaginea {img_filename}.")
                    
                    processed_images_count += 1
                    if total_images_to_process > 0:
                        progress = int((processed_images_count / total_images_to_process) * 100)
                        self.progress_update.emit(progress)
                    
                    self.log_message.emit(f"Procesat: {img_filename} din clasa '{dir_name}'.")
            
            if not data:
                self.finished.emit(False, "Nu s-au putut extrage date din imagini")
                return
            
            columns = [f"{coord}{i}" for i in range(21) for coord in ['x', 'y', 'z']]
            df = pd.DataFrame(data, columns=columns)
            df['label'] = labels

            df.to_csv('datasetpo.csv', index=False)

            self.finished.emit(True, "Setul de date a fost creat cu succes. ")
        except Exception as e:
            self.finished.emit(False, f"A aparut o eroare la crearea setului de date: {str(e)}")
    
    def stop(self):
        self.running = False
