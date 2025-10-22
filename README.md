<p align="center">
  <a>
    <img width="700" height="400" src="https://github.com/user-attachments/assets/bf7cd75b-a9a5-4cfd-a281-8a3b6a4927c8" />
  </a>
</p>
<h1 align="center">Keeper - Gestão de Consumíveis de TI | Desenvolvido em Flask</h1>
<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img alt="Flask" src="https://img.shields.io/badge/-Flask-000000?style=flat-square&logo=flask&logoColor=white" />
  <img alt="HTML5" src="https://img.shields.io/badge/-HTML5-E34F26?style=flat-square&logo=html5&logoColor=white" />
  <img alt="CSS" src="https://img.shields.io/badge/CSS-239120?style=flat-square&logo=css3&logoColor=white" />
  <img alt="Javascript" src="https://img.shields.io/badge/Javascript-FF0000?style=flat-square&logo=javascript&logoColor=white" />
  <img alt="Sqlite3" src="https://img.shields.io/badge/Sqlite-BD00FF?style=flat-square&logo=sqlite&logoColor=white" />
</p>
<br>

### v1.0.0:
Release inicial do **Keeper**

## 🧠 Sobre o Keeper
 
<p align="center">

O Keeper é um sistema de controle de estoque voltado para insumos e periféricos de TI (toners, cilindros, cabos, componentes etc.).
Foi desenvolvido para oferecer visão em tempo real dos materiais disponíveis e facilitar o monitoramento de consumo pela equipe técnica e administrativa.

<br> Com uma interface moderna estilo “Painel de TV”, o Keeper entrega uma experiência visual de fácil leitura, pensada para exibição em ambientes corporativos, como salas de suporte ou centros de operação. </p>

### ⚙️ Funcionalidades
#### 🔐 Tela de Login

<p align="center">
  <img src="https://github.com/user-attachments/assets/85e4fb8a-2efa-4b51-94bb-1601107688b8" width="600" />

</p>

A autenticação é feita via banco SQLite, utilizando hash seguro com `werkzeug.security`. O sistema possui controle de sessão e roles de usuário (admin / comunicação).

### 📦 Painel de Estoque
<p align="center">
  <img src="https://github.com/user-attachments/assets/7d81b566-d203-4a44-81ef-9001cd1518cd" width="600" />
</p>

O painel exibe os itens cadastrados com:

- Nome, tipo e descrição do item

- Quantidade atual em estoque

- Barra de progresso com indicadores visuais de nível:

  - 🔴 Vermelho: baixo (<3)

  - 🟡 Amarelo: médio (4–6)

  - 🟢 Verde: normal (≥7)

O layout é totalmente responsivo e otimizado para exibição contínua (modo TV corporativa).

### 📦 Registrar Entrada/Saída
<p align="center">
  <img width="600" src="https://github.com/user-attachments/assets/8dee03dd-2c12-4482-bad5-7d012d5ef33f" />
</p>
A tela de Registro de Movimentações é o coração operacional do Keeper.
Ela permite que o time de TI registre, em tempo real, toda movimentação de materiais — seja entrada (reposição de estoque) ou saída (uso, substituição ou manutenção).

<br>⚡ Funcionalidades principais:

- Seleção rápida de item: o usuário escolhe o item no dropdown filtrado pelo nome ou tipo (ex: Toner, Cilindro, Cabo, etc).

- Modo de operação: o usuário define se é uma entrada ou saída.

- Controle de quantidade: campo numérico com validação para impedir retiradas acima do estoque disponível.

- Registro automático de data e hora, com identificação do usuário autenticado responsável pela operação.

- Atualização instantânea no estoque principal, refletindo o novo total em tempo real.

<br>🧾 Histórico de movimentações:

Abaixo do formulário, é exibida uma tabela paginada que exibe as 5 últimas movimentações realizada pelo usuário, contendo:

- Tipo de operação (Entrada / Saída)

- Nome do item

- Quantidade movimentada

- Usuário responsável

- Data e hora

Essa visão garante transparência total do fluxo de materiais e facilita a auditoria do consumo — evitando desvios, perdas e inconsistências no inventário.

### 🛠️ Módulo Administrativo
Os administradores podem:

- Cadastrar novos itens com descrição,tipo e atualizar ou remover itens existentes
  <p align="center">
    <img width="400" src="https://github.com/user-attachments/assets/8d484b47-48f8-4654-8261-c4621bd64dcb" />
  
- Cadastrar as localizações dos setores da unidade, para melhor controle de destino dos consumíveis.
  <p align="center">
     <img width="400" src="https://github.com/user-attachments/assets/60ad0808-b66b-442a-86d0-55b892e74097" />
  </p>
- Cadastrar novos usuários que utilizaram o sistema, com perfil Admin ou Operador.
  <p align="center">
    <img width="400" src="https://github.com/user-attachments/assets/51c36f72-179f-49fc-9ece-cd64e92251f7" />
  <p/>

### 📝 Relatórios
#### **Relatório de Entrada/Saída**
<p align="center">
  <img width="600" src="https://github.com/user-attachments/assets/87765a77-c2c5-4868-b753-aea1f66a907a" />
</p> 

- Exibe uma listagem detalhada de todas as movimentações realizadas no sistema.
- Permite exportação em Excel 

### 🧰 Tecnologias utilizadas

- Backend: Python + Flask
- Frontend: HTML5, CSS3, JavaScript
- Banco de Dados: SQLite3

### 🚀 Inicialização
```
# Criar ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Iniciar o servidor Flask
flask run
```
Na primeira execução, o Keeper detecta se o banco **SQLite** existe.
Se não existir, ele cria automaticamente usando o arquivo **schema.sql** e popula o usuário padrão:
```
Usuário: admin
Senha: keeper
```

### 🧑‍💻 Autor
Nikolas — Analista de Software
<br>Desenvolvido com ❤️ e Flask para otimizar a gestão de TI corporativa.
