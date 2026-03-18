# Guia de Publicação - Painel Digital

Este guia explica como colocar o sistema em funcionamento para uso real.

## Opção 1: Rede Local (Mais Comum)
Ideal para escritórios ou clínicas onde o painel e o totem ficam no mesmo local.

### 1. Preparação do Servidor
Escolha um computador para ser o "servidor" (pode ser o mesmo que exibe o painel).
1. Instale o **Python 3.10+** (baixe em python.org).
2. Abra o terminal (cmd ou powershell no Windows) na pasta do projeto.
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

### 2. Iniciar o Sistema
Execute o comando:
```bash
python app.py
```
O sistema estará rodando em `http://localhost:4001`.

### 3. Acessar de Outros Computadores
Para abrir o Totem ou o Painel em outros aparelhos (TVs, Tablets):
1. Descubra o **IP Local** do computador servidor (ex: `192.168.1.50`).
2. Nos outros aparelhos, digite no navegador:
   - **Painel**: `http://192.168.1.50:4001/`
   - **Totem**: `http://192.168.1.50:4001/totem.html`
   - **Admin**: `http://192.168.1.50:4001/admin.html`

---

## 🔊 Som Automático em TVs (Modo Kiosk)
Navegadores modernos bloqueiam o som se não houver um clique inicial. Para que a TV fale as senhas automaticamente ao ligar, siga estas dicas:

### Dica 1: Atalho de Inicialização (Recomendado)
No computador que liga na TV, crie um atalho do **Chrome** ou **Edge** com este comando:
```bash
chrome.exe --autoplay-policy=no-user-gesture-required "http://localhost:4001/"
```
Isso força o navegador a permitir o som sem que ninguém precise clicar na tela.

### Dica 2: Ativação Manual Única
Se não puder usar atalhos, basta clicar uma única vez no botão **"Áudio Ativado"** no topo esquerdo do painel. O sistema lembrará dessa escolha para as próximas vezes que a página for recarregada.

---

## Opção 2: Nuvem (Render / Railway)
Ideal para acesso remoto via internet.

1. Crie uma conta no [Render.com](https://render.com) ou [Railway.app](https://railway.app).
2. Conecte seu repositório GitHub.
3. Configure o comando de início: `gunicorn app:app`.
4. **Importante**: Como o banco de dados é SQLite, os dados serão perdidos se o servidor reiniciar, a menos que você configure um "Disk/Volume" persistente no Render.

---

## Opção 3: Docker (Windows Server 2022)
Ideal para servidores profissionais com isolamento e reinicialização automática.

### 1. Preparação
1. Certifique-se de que o **Docker Desktop** ou o **Docker Engine** esteja instalado no Windows Server 2022.
2. Garanta que o serviço Docker esteja rodando.

### 2. Publicação
1. Copie todos os arquivos do projeto para uma pasta no servidor (ex: `C:\Sistemas\PainelDigital`).
2. Abra o **PowerShell** como Administrador nesta pasta.
3. Execute o comando para construir e iniciar o container:
   ```powershell
   docker-compose up -d --build
   ```
4. O sistema estará disponível em `http://IP_DO_SERVIDOR:4001`.

### 3. Vantagens do Docker
- **Persistência**: O banco de dados (`database.db`) e os vídeos (`uploads/`) estão mapeados em volumes, então seus dados não são perdidos ao atualizar o container.
- **Auto-início**: O sistema sobe sozinho caso o servidor seja reiniciado.
- **Isolamento**: Não é necessário instalar Python ou dependências diretamente no Windows Server.

---

## Dicas Importantes
- **Voz**: O navegador bloqueia som automático. Ao abrir o painel (`index.html`), clique em qualquer lugar da tela ou no botão de ativação para habilitar a chamada por voz.
- **Volumes**: Se for usar Docker, os arquivos `database.db` e a pasta `uploads/` devem existir na pasta local antes do primeiro comando para evitar problemas de permissão.
- **Segurança**: Para uso em internet aberta, altere a `secret_key` no topo do arquivo `app.py`.
- **Portas**: Se a porta 4001 estiver ocupada, você pode alterá-la no arquivo `docker-compose.yml` na seção `ports: - "NOVA_PORTA:4001"`.
