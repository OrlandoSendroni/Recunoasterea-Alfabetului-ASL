import mysql.connector
import bcrypt

# CONFIGURARE BAZA DE DATE

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Sendroni21@',
    'database': 'asl_users_db'
}

def create_user(username, password):
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

        # Insereaza utilizatorul in baza de date
        # Decodeaza hash-ul si salt-ul la string pentru a le stoca in VARCHAR
        query = "INSERT INTO users (username, password_hash, salt) VALUES (%s, %s, %s)"
        cursor.execute(query, (username, hashed_password.decode('utf-8'), salt.decode('utf-8')))
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Contul a fost creat cu succes."
    except mysql.connector.Error as err:
        if err.errno == 1062: # Cod de eroare pentru duplicarea cheii (utilizator deja existent)
            return False, "Utilizatorul exista deja."
        return False, f"Eroare la crearea contului: {err}"
    except Exception as e:
        return False, f"O eroare neasteptata a aparut: {str(e)}"

def verify_user(username, password):
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        query = "SELECT password_hash FROM users WHERE username = %s"
        cursor.execute(query, (username, ))
        result = cursor.fetchone() # Fetchone returneaza o tupla (password_hash, ) sau None

        cursor.close()
        conn.close()

        if result:
            stored_hash = result[0].encode('utf-8') # Hash-ul este stocat ca string, deci trebuie sa-l convertim inapoi la bytes

            # Compara parola introdusa cu hash-ul stocat folosind bcrypt.checkpw
            # bcrypt.checkpw se ocupa de extragerea salt-ului din stored_hash
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                return True, "Autentificare reusita."
            else:
                return False, "Parola incorecta."
        else:
            return False, "Utilizatorul nu exista."
    except mysql.connector.Error as err:
        return False, f"Eroare la autentificare: {err}"
    except Exception as e:
        return False, f"O eroare neasteptata a aparut: {str(e)}"