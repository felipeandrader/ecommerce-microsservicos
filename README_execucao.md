# E-Commerce Distribuído (Microsserviços)

Este projeto implementa uma arquitetura de microsserviços para um mini e-commerce, aplicando conceitos de sistemas distribuídos como replicação de dados (Consistência Forte), comunicação assíncrona (RabbitMQ), tolerância a falhas (Heartbeat/Gateway) e autenticação segura (JWT).

## 🛠 Tecnologias Utilizadas
* **Backend:** Python 3 (FastAPI, Uvicorn, SQLAlchemy)
* **Bancos de Dados:** PostgreSQL (2 réplicas para Produtos, 1 para Usuários, 1 para Pedidos)
* **Mensageria:** RabbitMQ
* **Infraestrutura:** Docker e Docker Compose

---

## 🚀 Instruções de Execução (macOS / Linux/ windows)

Para executar o projeto localmente, certifique-se de ter o **Docker Desktop** e o **Python 3** instalados na sua máquina.

### Passo 1: Subir a Infraestrutura (Bancos e Filas)
Abra o seu terminal na pasta raiz do projeto e inicie os contêineres em segundo plano:

```bash
docker-compose up -d
```
*Aguarde cerca de 10 a 15 segundos após a execução para que o PostgreSQL conclua o "cold start" e crie os bancos de dados internos.*

### Passo 2: Iniciar os Microsserviços
Como o sistema é distribuído, cada serviço roda em sua própria porta. **Abra 4 abas diferentes no seu terminal** e execute os comandos abaixo em cada uma delas (certifique-se de estar na raiz do projeto antes de começar):

**Aba 1 - Serviço de Usuários (Porta 5001):**
```bash
cd users
pip3 install -r requirements.txt
python3 -m uvicorn main:app --port 5001
```

**Aba 2 - Serviço de Produtos (Porta 5002):**
```bash
cd ../products
pip3 install -r requirements.txt
python3 -m uvicorn main:app --port 5002
```

**Aba 3 - Serviço de Pedidos (Porta 5003):**
```bash
cd ../orders
pip3 install -r requirements.txt
python3 -m uvicorn main:app --port 5003
```

**Aba 4 - API Gateway (Porta 8000 - Ponto de Entrada Principal):**
```bash
cd ../gateway
pip3 install -r requirements.txt
python3 -m uvicorn main:app --port 8000
```

---

## 🧪 Como Testar a Aplicação

Todas as requisições devem ser feitas EXCLUSIVAMENTE para a porta **8000** (API Gateway). O gateway se encarregará de rotear para as portas corretas.

**1. Acesso de Administrador (Criação Dinâmica)**
Para facilitar os testes, criamos um gatilho dinâmico. Envie um `POST` para criar uma conta e utilize o e-mail `admin@teste.com`. O sistema identificará o e-mail e concederá privilégios de `admin` automaticamente.
* `POST http://127.0.0.1:8000/users/register`

**2. Obter o JWT**
* `POST http://127.0.0.1:8000/users/login` (Use as credenciais criadas acima para receber o Token JWT).

**3. Criar e Listar Produtos (Replicação em Ação)**
* Adicione o Token JWT recebido no cabeçalho `Authorization: Bearer <token>`.
* `POST http://127.0.0.1:8000/products` (Verifique que o item foi persistido nas duas réplicas).
* `GET http://127.0.0.1:8000/products` (O Gateway alterna a leitura via Round-Robin).

**4. Criar Pedido (RabbitMQ)**
* `POST http://127.0.0.1:8000/orders` informando o `product_id`.
* Você pode conferir a mensagem assíncrona chegando na fila acessando o painel do RabbitMQ no seu navegador em `http://localhost:15672` (Usuário: `user` | Senha: `password`).

**5. Teste de Tolerância a Falhas (Heartbeat)**
* Encerre a aba do terminal que está rodando o "Serviço de Pedidos" (`CTRL+C`).
* Aguarde até 10 segundos para o Gateway registrar a falha crítica no log.
* Tente fazer uma chamada `GET http://127.0.0.1:8000/orders/1`.
* O Gateway interceptará e retornará o erro `503 Service Unavailable`.

---

### Encerramento
Para parar o ambiente, digite `CTRL+C` nas 4 abas do terminal onde os serviços Python estão rodando e, na raiz do projeto, desligue a infraestrutura com:

```bash
docker-compose down
```