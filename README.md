# SafePack

Sistema web desenvolvido como projeto acadêmico para auxiliar no **gerenciamento e rastreamento de encomendas em condomínios**.

## 📋 Sobre o projeto

O SafePack foi desenvolvido durante a graduação em Ciência da Computação como uma solução para organizar o recebimento, registro e acompanhamento de encomendas em ambientes condominiais.

A proposta do sistema é centralizar as informações das encomendas e facilitar o controle por parte dos responsáveis pelo condomínio, proporcionando uma forma mais organizada de registrar e acompanhar os pedidos recebidos.

O projeto foi desenvolvido em equipe como parte das atividades acadêmicas da graduação.

## 🎯 Objetivo

Desenvolver uma aplicação web capaz de auxiliar no gerenciamento de encomendas em condomínios, proporcionando maior organização no registro e acompanhamento das entregas.

## ⚙️ Principais funcionalidades

- Cadastro e gerenciamento de encomendas;
- Registro de informações das entregas;
- Consulta de encomendas;
- Gerenciamento das informações por meio de uma aplicação web;
- Comunicação entre front-end, API e banco de dados;
- Validação das informações fornecidas pelo usuário.

## 🏗️ Arquitetura

O projeto utiliza uma arquitetura baseada em uma aplicação web com comunicação entre as diferentes camadas do sistema:

```text
┌─────────────────────┐
│      Front-end      │
│ HTML / CSS / JS     │
│     Bootstrap       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│      Back-end       │
│       FastAPI       │
│       Python        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│       Banco         │
│     PostgreSQL      │
│      Supabase       │
└─────────────────────┘
```

## 🛠️ Tecnologias utilizadas

### Back-end
- Python
- FastAPI
- SQLAlchemy
- APIs REST

### Front-end
- HTML5
- CSS3
- JavaScript
- Bootstrap

### Banco de dados
- PostgreSQL
- Supabase

## 📁 Estrutura do projeto

A estrutura do projeto é organizada separando os principais componentes da aplicação:

```text
SafePack/
├── backend/
├── frontend/
├── database/
├── requirements.txt
└── README.md
```

> A estrutura acima representa a organização conceitual do projeto. Consulte os diretórios disponíveis no repositório para a estrutura atualizada.

## 🚀 Como executar

### 1. Pré-requisitos

Para executar o projeto localmente, é necessário ter instalado:

- Python 3.x
- Git
- Acesso ao banco de dados PostgreSQL utilizado pelo projeto

### 2. Clonar o repositório

```bash
git clone https://github.com/leo-bergamo/safepack.git
cd safepack
```

### 3. Criar um ambiente virtual

```bash
python -m venv venv
```

No Windows:

```bash
venv\Scripts\activate
```

No Linux/macOS:

```bash
source venv/bin/activate
```

### 4. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 5. Configurar as variáveis de ambiente

As credenciais e informações de conexão com o banco de dados **não devem ser armazenadas diretamente no código ou publicadas no GitHub**.

Configure as variáveis de ambiente necessárias de acordo com a estrutura do projeto.

### 6. Executar a aplicação

A forma de inicialização pode variar conforme a configuração do projeto. Para uma aplicação FastAPI, por exemplo:

```bash
uvicorn main:app --reload
```

Após iniciar o servidor, a aplicação poderá ser acessada pelo endereço local informado pelo FastAPI.

## 🧪 Testes

Durante o desenvolvimento foram realizados testes relacionados à comunicação com a API, validação de endpoints, integração com o banco de dados e funcionamento das principais funcionalidades da aplicação.

## 🎓 Contexto acadêmico

O SafePack foi desenvolvido como **projeto acadêmico durante a graduação em Ciência da Computação**, com o objetivo de aplicar na prática conhecimentos relacionados ao desenvolvimento de sistemas, APIs, banco de dados e integração entre diferentes componentes de uma aplicação.

## 👥 Autoria

Projeto desenvolvido em equipe durante a graduação.

**Leonardo Bergamo**  
Ciência da Computação

## 📌 Status

Projeto acadêmico desenvolvido durante a graduação.

---

⭐ Projeto desenvolvido para fins educacionais e acadêmicos.
