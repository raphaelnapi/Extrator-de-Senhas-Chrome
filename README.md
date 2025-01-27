# Extrator de Senhas do Google Chrome (para Windows)
Script em Python para extrair senhas armazenadas pelo Google Chrome no Windows para fins de estudo ou forense

Os registros são exibidos no console e armazenados em um arquivo CSV.
Cada registro contém: URL, username e password.

## Como o Google Chrome armazena as senhas?
O Google Chrome armazena as senhas em um banco de dados SQLite no caminho: `C:\Users\[nome do usuário]\AppData\Local\Google\Chrome\User Data\Default\Login Data` na tabela `logins`.

Abaixo as tabelas do arquivo Login Data
![Imagem das Tabelas do banco de dados Login Data](https://i.postimg.cc/cHDXrYXP/tabelas-Login-Data.jpg)

Abaixo a tabela logins do arquivo Login Data com as colunas que nos interessam já filtradas `action_url, username_value, password_value`:
![Imagem da tabela logins](https://i.postimg.cc/TPf90QsZ/tabela-logins-filtrada.jpg)

Observe que o campo `password_value` é do tipo BLOB (*binary large object*). Nesse campo as senhas estão armazenadas como dados binários (byte a byte) criptografadas.

O Google Chrome utiliza a cifra **AES 256** com modo **GCM** para criptografar essas senhas. A chave fica armazenada no arquivo Local State, que é um arquivo texto que contém dados organizados em JSON (*javascript object notation*). A chave está em os_crypt.encrypted_key.

## Explicação do código

### Bibliotecas utilizadas
```
# Nativas:
import sqlite3
import os
import base64
import json

# Do PIP
import win32crypt
from Crypto.Cipher import AES
```

Para utilizar a biblioteca win32crypt precisamos instalar o pacote pywin32 com o PIP. Essa biblioteca será utilizada para acessar uma API do Windows chamada Data Protection API. E para utilizar a classe AES, que será necessária para descriptografar as senhas, utilizaremos o pacote pycryptodome.
Utilizaremos os seguintes comandos:
```
pip install pywin32
pip install pycryptodome
```

###
