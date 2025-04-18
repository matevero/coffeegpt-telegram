import sqlite3

def create_user_table():
    # Conecta ao banco de dados 'usuarios.db'. Se não existir, será criado.
    conn = sqlite3.connect('usuarios.db')
    c = conn.cursor()
    
    # Cria a tabela 'usuarios', se ainda não existir.
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            user_id INTEGER PRIMARY KEY,
            nome TEXT,
            preferencias TEXT
        )
    ''')
    
    # Salva as mudanças e fecha a conexão.
    conn.commit()
    conn.close()

create_user_table()
print("Tabela criada com sucesso!")
