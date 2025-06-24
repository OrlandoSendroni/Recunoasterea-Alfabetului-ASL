import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from PySide6.QtCore import QThread, Signal


class ModelTrainingWorker(QThread):
    
    log_message = Signal(str)
    # Emite (succes: bool, message: str, evaluation_result: dict)
    # evaluation_result este un dictionar cu rezultatele evaluarii modelului
    finished = Signal(bool, str, dict)

    def __init__(self):
        super().__init__()
        self.running = True


    def run(self):
        self.log_message.emit("Incepem antrenarea modelului...")

        evaluation_results = {}

        try:
            # Verificam daca dataset.csv exista
            if not os.path.exists('dataset.csv'):
                self.finished.emit(False, "Fisierul 'dataset.csv' nu exista. Asigurati-va ca ati creat dataset-ul in prealabil.", evaluation_results)
                return
            
            # Incarcam datele din 'dataset.csv'
            df = pd.read_csv('dataset.csv')

            if df.empty:
                self.finished.emit(False, "Fisierul 'data.csv' este gol. Asigurati-va ca ati creat dataset-ul in prealabil.", evaluation_results)
                return
            
            if 'label' not in df.columns:
                self.finished.emit(False, "Coloana 'label' nu exista in 'datset.csv'. Asigurati-va ca ati creat dataset-ul corect.", evaluation_results)
                return
            
            # Separarea caracteristicilor si a etichetelor
            X = df.drop(columns=['label'])
            y = df['label'].values

            if len(np.unique(y)) < 2:
                self.finished.emit(False, "Setul de date contine mai putin de 2 clase. Antrenarea modelului necesita cel putin 2 clase diferite.", evaluation_results)
                return
            
            if X.shape[0] < 2: # Avem nevoie de cel putin 2 exemple pentru antrenare
                self.finished.emit(False, "Setul de date contine prea putine exemple pentru antrenare.", evaluation_results)
                return
            
            self.log_message.emit("Setul de date incarcat cu succes. Incepem antrenarea modelului...")

            # Impartirea setului de date in antrenare si testare
            try:
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=True, stratify=y)
            except ValueError as e:
                self.finished.emit(False, f"Eroare la impartirea setului de date: {str(e)}", evaluation_results)
                return

            # Initializarea si antrenarea modelului
            self.log_message.emit("Antrenam modelul...")
            
            model = RandomForestClassifier(
                n_estimators = 200,
                max_depth = 20,
                min_samples_split = 5,
                random_state = 42,
                n_jobs = -1
            )
            model.fit(X_train, y_train)
            self.log_message.emit("Modelul a fost antrenat cu succes.")

            # Predictii si evaluare pe setul de testare
            y_pred = model.predict(X_test)

            score = accuracy_score(y_test, y_pred)
            classification_rep = classification_report(y_test, y_pred, zero_division=0) # zero_division=0 pentru a evita erorile la clase cu 0 exemple
            confusion_mat = confusion_matrix(y_test, y_pred)

            evaluation_results['accuracy'] = f"{score * 100:.2f}%"
            evaluation_results['classification_report'] = classification_rep
            evaluation_results['confusion_matrix'] = str(confusion_mat) # convertim la string pentru a putea fi trimis prin signal

            self.log_message.emit(f"Acuratetea modelului: {evaluation_results['accuracy']}")
            self.log_message.emit(f"Raport de clasificare:\n{evaluation_results['classification_report']}")
            self.log_message.emit(f"Matricea de confuzie:\n{evaluation_results['confusion_matrix']}")

            # Salvarea modelului antrenat
            joblib.dump(model, 'model.joblib')
            self.log_message.emit("Modelul a fost salvat in 'model_a.joblib'.")

            self.finished.emit(True, "Antrenarea modelului a fost finalizata cu succes.", evaluation_results)
        except Exception as e:
            self.log_message.emit(f"A aparut o eroare la antrenarea modelului: {str(e)}")
            self.finished.emit(False, f"A aparut o eroare la antrenarea modelului: {str(e)}", evaluation_results)

    def stop(self):
           self.running = False     