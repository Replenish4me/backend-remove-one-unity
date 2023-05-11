import boto3
import json
import pymysql
import os

def lambda_handler(event, context):
    
    # Leitura dos dados da requisição
    token = event['token']
    produto_id = event['produto_id']
    
    # Conexão com o banco de dados
    secretsmanager = boto3.client('secretsmanager')
    response = secretsmanager.get_secret_value(SecretId=f'replenish4me-db-password-{os.environ.get("env", "dev")}')
    db_password = response['SecretString']
    rds = boto3.client('rds')
    response = rds.describe_db_instances(DBInstanceIdentifier=f'replenish4medatabase{os.environ.get("env", "dev")}')
    endpoint = response['DBInstances'][0]['Endpoint']['Address']
    # Conexão com o banco de dados
    with pymysql.connect(
        host=endpoint,
        user='admin',
        password=db_password,
        database='replenish4me'
    ) as conn:
    
        # Verificação da sessão ativa no banco de dados
        with conn.cursor() as cursor:
            sql = "SELECT usuario_id FROM SessoesAtivas WHERE id = %s"
            cursor.execute(sql, (token,))
            result = cursor.fetchone()
            
            if result is None:
                response = {
                    "statusCode": 401,
                    "body": json.dumps({"message": "Sessão inválida"})
                }
                return response
            
            usuario_id = result[0]
            
            # Verificação se o produto já está no carrinho
            sql = "SELECT id, quantidade FROM CarrinhoCompras WHERE usuario_id = %s AND produto_id = %s"
            cursor.execute(sql, (usuario_id, produto_id))
            result = cursor.fetchone()
            
            if result is None:
                response = {
                    "statusCode": 400,
                    "body": json.dumps({"message": "Produto não encontrado no carrinho"})
                }
                return response
            
            carrinho_id = result[0]
            quantidade = result[1]
            
            # Remoção de uma unidade do produto do carrinho
            if quantidade == 1:
                sql = "DELETE FROM CarrinhoCompras WHERE id = %s"
                cursor.execute(sql, (carrinho_id,))
            else:
                quantidade -= 1
                sql = "UPDATE CarrinhoCompras SET quantidade = %s WHERE id = %s"
                cursor.execute(sql, (quantidade, carrinho_id))
            
            conn.commit()

    # Retorno da resposta da função
    response = {
        "statusCode": 200,
        "body": json.dumps({"message": "Produto removido do carrinho"})
    }
    return response
