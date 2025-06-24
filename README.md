# Recunoasterea-Alfabetului-ASL - Proiect de Licență

Acest proiect reprezintă o soluție software completă, sub forma unei aplicații desktop cu interfață grafică (GUI), destinată recunoașterii în timp real a alfabetului static din Limbajul Semnelor American (ASL). Aplicația acoperă întregul flux de lucru al unui proiect de machine learning: colectarea datelor, crearea setului de date, antrenarea modelului și testarea interactivă.

## Tehnologii Folosite

* **Limbaj de programare:** Python 3.8+
* **Interfață Grafică (GUI):** PySide6, qt-material
* **Computer Vision:** OpenCV, MediaPipe
* **Machine Learning:** Scikit-learn, Pandas, Numpy
* **Bază de Date:** MySQL
* **Alte biblioteci:** bcrypt, joblib, mysql-connector-python

## Cerințe Preliminare

Înainte de instalare, asigurați-vă că aveți următoarele programe instalate pe sistemul dumneavoastră:
1. **Python 3.8** sau o versiune mai nouă.
2. **pip** (managerul de pachete pentru Python, de obicei inclus cu Python).
3. **Git** pentru a clona repository-ul.
4. Un **server MySQL** funcțional

## Ghid de Instalare și Rulare

Urmați acești pași pentru a configura și rula aplicația local.

### Pasul 1: Clonarea Repository-ului

Deschideți un terminal sau o consolă și rulați următoarea comandă pentru a descărca proiectul:
```bash
git clone [https://github.com/OrlandoSendroni/Recunoasterea-Alfabetului-ASL.git](https://github.com/OrlandoSendroni/Recunoasterea-Alfabetului-ASL.git)
cd Recunoasterea-Alfabetului-ASL
```

### Pasul 2: Crearea Mediului Virtual și Instalarea Dependențelor

Este o practică bună să folosiți un mediu virtual pentru a izola dependențele proiectului.
```bash
# Crearea mediului virtual
python -m venv venv

# Activarea mediului virtual
# Windows:
venv\Scripts\activate

#macOS/Linux:
source venv/bin/activate

# Instalarea tuturor bibliotecilor necesare
pip install -r requirements.txt
```

### Pasul 3: Configurarea Bazei de Date MySQL
Aplicația necesită o bază de date pentru a funcționa.

#### 3.1 Crearea bazei de date
Conectați-vă la serverul MySQL și rulați următoarea comandă SQL pentru a crea baza de date:
```sql
CREATE DATABASE asl_users_db;
```

#### 3.2 Crearea tabelului ”users”
După crearea bazei de date, rulați comanda de mai jos pentru a crea tabelul necesar pentru stocarea utilizatorilor:
```sql
USE asl_users_db;

CREATE TABLE 'users' (
  'id' int(11) NOT NULL AUTO_INCREMENT,
  'username' varchar(255) NOT NULL,
  'password_hash' varchar(255) NOT NULL,
  'salt' varchar(255) NOT NULL,
  PRIMARY KEY ('id'),
  UNIQUE KEY 'username' ('username')
);
```

#### 3.3 Configurarea conexiunii în cod
Deschideți fișierul "src/database.py" într-un editor și modificați dicționarul "DB_CONFIG" cu utilizatorul și parola dumneavoastră de MySQL.
```python
DB_CONFIG = {
  'host': 'localhost',
  'user': 'root', # Modificati aici daca este necesar
  'password': 'parola_dumneavoastra_mysql',
  'database': 'asl_users_db'
}
```

### Pasul 4: Descărcarea Modelului Pre-antrenat
Fișierul cu modelul antrenat (model.joblib) are o dimensiune prea mare pentru a fi inclus direct în acest repository. Pentru a putea utiliza funcționalitatea "4. Testeaza Modelul" imediat după instalare, un model pre-antrenat poate fi descărcat de la următorul link:

(https://drive.google.com/file/d/1zsuPT2Pc5q6J1BuYBDKOY6AF5Bi8GfD1/view?usp=drive_link)

Instrucțiuni:
1. Descărcați fișierul "model.joblib" de la linkul de mai sus.
2. Plasați fișierul descărcat în directorul rădăcină al proiectului (același loc unde se află "README.md" și folderul "src")

Dacă nu descărcați acest fișier, va trebui să generați propriul model parcurgând pașii 1,2 și 3 din aplicație (Colectare, Creare Set de Date, Antrenare).

### Pasul 5: Lansarea Aplicației
După ce toți pașii anteriori au fost finalizați, puteți lansa aplicația. Asigurați-vă că sunteți în directorul rădăcină al proiectului și că mediul virtual este activat, apoi rulați:
```bash
python src/asl_workflow_gui.py
```
Aplicația ar trebui să pornească, afișând fereastra de autentificare.
