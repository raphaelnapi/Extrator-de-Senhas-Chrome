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

O Google Chrome utiliza a cifra **AES 256** com modo de operação **GCM** para criptografar essas senhas. A chave fica armazenada no arquivo Local State, que é um arquivo texto que contém dados estruturados em JSON (*javascript object notation*). A chave está em os_crypt.encrypted_key criptografada com DPAPI (Data Protection API) do Windows.
![Imagem da chave encrypted_key no arquivo Local State](https://i.postimg.cc/TPf0Tpwb/encrypted-key-Local-State.jpg)

**A DPAPI do Windows utiliza credenciais do usuário logado para criptografar/descriptografar dados. Dessa forma só conseguiremos descriptografar os_crypt.encrypted_key estando logado no usuário do Windows.**

Dentro do arquivo Local State, a chave os_crypt.encrypted_key está codificada em Base64. Ao decodificar seu valor com Base64 vamos observar que os 5 primeiros caracteres serão DPAPI, fazendo referência ao recurso utilizado para a criptografia da chave que vem em seguida a esses 5 caracteres.

Com a chave obtida através da descriptografia com a DPAPI do os_crypt.encrypted_key, é possível descriptografar o campo *password_value* da tabela *logins* do arquivo Login Data. Deve-se observar que os 3 primeiros bytes do password_value referem-se a uma versão, possivelmente versão do algoritmo de criptografia do Google Chrome, *v10*, são desprezíveis para fins de descriptografia. Os próximos 12 bytes correspondem ao vetor de inicialização (IV) que será utilizado de parâmetro para a descriptografia com AES. Os demais bytes correspondem ao password criptografado.

Após descriptografia utilizando AES 256 com modo de operação GCM, com o IV obtido no campo password_value, chave obtida no os_crypt.encrypted_key através DPAPI, o resultado será o password em claro e uma TAG utilizada pelo Google para verificação da descriptografia, essa TAG serão os últimos 16 bytes do resultado da descriptografia, então o que nos interessa como password em claro são os primeiros bytes (excluindo os últimos 16).

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

### Arquivos analisados para a extração de senhas (Local State e Login Data)
Definimos variáveis para os arquivos que vamos acessar para realizar a extração das senhas
```
local_state_file_path = f"{os.environ.get('USERPROFILE')}\\AppData\\Local\\Google\\Chrome\\User Data\\Local State" 
login_data_file_path = f"{os.environ.get('USERPROFILE')}\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Login Data"
```

### Encontrando a chave AES a partir de os_crypt.encrypted_key utilizando DPAPI
Carregamos os dados JSON do arquivo Local State e decodificamos o valor de os_crypt.encrypted_key com Base64. No resultado desprezaremos os 5 primeiros bytes que são os caracteres "DPAPI" fazendo referência ao recurso utilizado para criptografia, os demais bytes são a chave AES que vamos descriptografar com a DPAPI do Windows (necessário estar logado com o usuário do Windows).

```
with open(local_state_file_path, "r") as file:
    json_data = json.load(file)

key_b64 = json_data['os_crypt']['encrypted_key']
key = base64.b64decode(key_b64)
key = key[5:] #remove a string DPAPI que indica a forma que a chave foi gerada (utilizando API do Windows)
key = win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
```

### Acesso ao banco de dados SQLite Login Data
Acessamos o banco de dados SQLite que está no arquivo Login Data e executamos uma *QUERY* para retornar apenas os campos que nos interessam: *action_url*, *username_value* e *password_value* da tabela **logins**.

```
db_con = sqlite3.connect(login_data_file_path)
db_cur = db_con.cursor()
db_cur.execute("SELECT action_url, username_value, password_value FROM logins")
```

### Iteração (loop) entre os resultados da QUERY ao banco de dados SQLite
Faremos uma iteração (loop) pelos resultados da QUERY que executamos. Os dados de cada resultado da QUERY estarão em um array de forma que o índice '0' corresponde ao campo *action_url*, o índice '1' corresponde ao campo *username_value* e o índice 2 corresponde ao campo *password_value*

```
for index, data in enumerate(db_cur.fetchall()):
    url = data[0]
    username = data[1]
    password_value = data[2]
```

Dentro da nossa iteração (loop) vamos tratar os dados do campo *password_value*. Os 3 primeiros bytes são desprezíveis para a nossa finalidade de descriptografar o password, pois tratam-se de uma versão do algoritmo de criptografia do Google Chrome. Os primeiros 12 bytes restantes são o vetor de inicialização (IV) que usaremos no AES e os demais bytes são o conteúdo da senha e sua TAG criptografados.

```
    # Dados criptografados que você quer descriptografar
    password_value = password_value[3:] #descarta v10 que indica parâmetros de criptografia do Chrome
    iv = password_value[:12] #primeiros 12 bytes são o IV
    encrypted_data = password_value[12:] #demais bytes são o CT
```

De posse da chave obtida no os_crypt.encrypted_key, do vetor de inicialização (IV) obtido no password_value e do conteúdo criptografado, passamos todos esses dados como parâmetros para descriptografar com AES 256 em modo de operação GCM.
```
    # Descriptografar
    cipher = AES.new(key, AES.MODE_GCM, iv)
    decrypted_data = cipher.decrypt(encrypted_data)
```

Por fim, o resultado obtido trará a senha em claro e a TAG da senha utilizada pelo Google Chrome. A TAG será dada pelos últimos 16 bytes do resultado descriptografado, não nos interessa. Os demais bytes compõem a senha em claro, vamos decodificá-lo com UTF-8 e teremos a senha.
```
    password = decrypted_data[:-16].decode()
    tag = decrypted_data[16:]
    print(f"Action URL: {url}\nUsername: {username}\nPassword: {password}\n\n")
    arq.write(f"{url},{username},{password}\n")
```
