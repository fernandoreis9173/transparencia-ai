from connection import get_connection


def main():
    print("🔌 Testando conexão com PostgreSQL...")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        current_database(),
                        current_user,
                        inet_server_addr(),
                        inet_server_port();
                """)

                result = cur.fetchone()

                print("\n✅ CONEXÃO REALIZADA COM SUCESSO!")
                print(f"Banco: {result[0]}")
                print(f"Usuário: {result[1]}")
                print(f"Servidor: {result[2]}")
                print(f"Porta: {result[3]}")

    except Exception as e:
        print("\n❌ ERRO DE CONEXÃO")
        print(e)


if __name__ == "__main__":
    main()