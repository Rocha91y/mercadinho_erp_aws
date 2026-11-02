# 🤖 GitHub Actions Workflows

Esta pasta armazena os arquivos de especificação de pipelines (fluxos de automação) em formato YAML executados pelo GitHub Actions.

## 📄 Workflows Existentes

### `deploy.yml`
- **Função:** Sincronização e Deploy automático de arquivos para a nuvem AWS.
- **Gatilho (Trigger):** É disparado a cada `push` realizado na branch `main`.
- **Destino:** Envia os dados e scripts atualizados para o bucket S3 `projeto-mercadinho-erp` no diretório `legado/`.
- **Credenciais:** Utiliza as secrets `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY` cadastradas no repositório.

## 🛠️ Como Funciona o Enviar (Sync)

O pipeline executa os seguintes passos principais:
1. Faz checkout do código do repositório.
2. Autentica na AWS usando as chaves configuradas nos Secrets.
3. Executa o comando `aws s3 sync . s3://projeto-mercadinho-erp/legado/` ignorando pastas internas do Git (`.git` e `.github`).