# Classificação INI-C via gbXML

Ferramenta em Streamlit que recebe um arquivo gbXML exportado do Revit, gera os modelos real e de referência pelo método de simulação da INI-C (Portaria Inmetro 309/2022, Anexo C.I), simula os dois no EnergyPlus e mostra a classificação geral e a da envoltória. Tipologia educacional.

## Como usar

1. Envie o gbXML e o arquivo climático (.epw).
2. Na barra lateral, escolha a zona bioclimática, o nível de ensino e informe o CEER do sistema de projeto.
3. Clique em **Processar gbXML e gerar o modelo real**.
4. Revise a lista de sombreamentos que saem na referência.
5. Clique em **Gerar referência, simular e classificar**.
6. Baixe os modelos real e de referência (.osm), os IDFs, os CSVs e o pacote completo para conferência.

## Publicar na web (GitHub + Streamlit Community Cloud)

### 1. Criar o repositório no GitHub

1. Entre em https://github.com e clique em **New repository**.
2. Nome sugerido: `ferramenta-inic-gbxml`. Marque **Private** se não quiser o código público.
3. Clique em **Create repository**.
4. Na página do repositório, clique em **uploading an existing file**.
5. Arraste todo o conteúdo desta pasta (os arquivos `.py`, `requirements.txt`, `packages.txt`, `README.md`, `.gitignore` e a pasta `.streamlit`). Os arquivos `app_inic.py`, `requirements.txt` e `packages.txt` precisam ficar na raiz do repositório.
6. Clique em **Commit changes**.

A pasta `.streamlit` começa com ponto e pode ficar oculta no Windows. Se o upload pelo navegador não pegar a pasta, crie o arquivo direto no GitHub: **Add file > Create new file**, nome `.streamlit/config.toml`, e cole o conteúdo do arquivo local.

### 2. Publicar no Streamlit Community Cloud

1. Entre em https://share.streamlit.io com a mesma conta do GitHub e autorize o acesso aos repositórios.
2. Clique em **Create app** e escolha **Deploy a public app from GitHub** (o app pode ficar privado depois).
3. Preencha:
   - Repository: `seu-usuario/ferramenta-inic-gbxml`
   - Branch: `main`
   - Main file path: `app_inic.py`
4. Em **Advanced settings**, escolha **Python 3.12**.
5. Clique em **Deploy**. A primeira instalação leva alguns minutos.
6. Para restringir o acesso, abra **Settings > Sharing** no app e deixe só os e-mails convidados.

Na primeira simulação o app baixa o EnergyPlus 24.2.0 (cerca de 190 MB, versão usada pelo OpenStudio 3.9.0) e guarda no servidor. Depois de reiniciar o app, ele baixa de novo na primeira simulação.

### 3. Atualizar o app

Qualquer arquivo alterado no repositório (pelo botão de editar do GitHub ou por novo upload) atualiza o app automaticamente em poucos segundos.

## Rodar no computador (Windows)

1. Ambiente conda com Python 3.12: `conda create -n bimbem python=3.12` e `pip install -r requirements.txt`.
2. Instale o OpenStudio 3.9.0 em `C:\openstudio-3.9.0`.
3. Dê dois cliques em `rodar_app.bat`.

No Windows o app usa o OpenStudio CLI. No servidor Linux, sem o CLI, ele usa o EnergyPlus direto, com o mesmo modelo traduzido pelo OpenStudio. Os resultados são iguais nos dois caminhos.

## Cuidados

- No Streamlit Community Cloud os arquivos enviados ficam em servidores externos enquanto o app roda. Não envie projetos sob sigilo sem autorização do cliente.
- O servidor gratuito tem memória e processamento limitados. Edifícios grandes podem levar bastante tempo para simular ou exceder o limite.
- O tamanho máximo de upload está em 200 MB (`.streamlit/config.toml`).

## Estrutura

| Arquivo | Função |
|---|---|
| `app_inic.py` | Interface Streamlit |
| `energyplus_runner.py` | Download do EnergyPlus e simulação direta no servidor |
| `00` a `10` | Geração do modelo real a partir do gbXML |
| `wall_modifier.py`, `roof_modifier.py`, `floor_modifier.py`, `glazing_modifier.py`, `skylight_remover.py`, `shade_remover.py`, `lighting_modifier.py` | Modelo de referência (Tabelas A.2 e A.9) |
| `12_run_simulation.py` | Configurações de simulação do Anexo C.I |
| `13`, `14_a`, `14_b`, `14_c` | Consumos, RedCEP, RedCgTT e classificação |
| `ALTERACOES.md` | Linhas alteradas em relação aos scripts originais |
