# 🤖 Filtro e Adaptador de Currículos (Job Matcher)

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Scikit-Learn](https://img.shields.io/badge/scikit--learn-%23F7931E.svg?style=for-the-badge&logo=scikit-learn&logoColor=white)
![Status](https://img.shields.io/badge/status-conclu%C3%ADdo-brightgreen)

Este é um script em Python que automatiza a busca por vagas de emprego e adapta o currículo do candidato para cada oportunidade encontrada.

## 🎯 O problema que ele resolve
Procurar emprego e personalizar o currículo para cada vaga é um processo demorado e repetitivo. Este script filtra vagas com base em requisitos específicos (localização, tipo de contrato, palavras-chave), calcula a compatibilidade (match) e gera uma versão do currículo destacando as habilidades que mais combinam com a vaga.

## 🛠️ Tecnologias utilizadas
- **Python 3.8+**
- **Scikit-Learn (TF-IDF)**: Para calcular a similaridade semântica entre o texto do currículo e a descrição da vaga.
- **python-docx**: Para gerar o currículo final no formato Word (.docx).
- **Regex (Expressões Regulares)**: Para detecção de tipos de contrato (rejeitando vagas exclusivamente PJ) e localizações.

## ⚙️ Funcionalidades
- Filtra vagas por palavras-chave e similaridade (TF-IDF).
- Rejeita automaticamente vagas que são exclusivamente PJ (Pessoa Jurídica).
- Filtra vagas pela localização desejada (ex: São Luís - MA).
- Gera um relatório em CSV (`relatorio.csv`) com as vagas aprovadas, rejeitadas e o motivo da rejeição.
- Cria um currículo personalizado em `.docx` para cada vaga aprovada.

## 🔒 Privacidade e Segurança (LGPD)
Este repositório utiliza o arquivo `curriculo_base.json` apenas como **exemplo** (com dados fictícios). 
O arquivo `.gitignore` já está configurado para impedir o vazamento acidental de dados pessoais e dos relatórios gerados.

**Para usar o script localmente com seus dados reais:**
1. Clone o repositório no seu computador.
2. Edite o `curriculo_base.json` com seus dados e o `vagas.csv` com as vagas.
3. Execute o script. (O Git vai ignorar suas alterações e não vai enviar seus dados para a internet).

## 🚀 Como rodar o projeto
1. Clone o repositório:
   ```bash
   git clone https://github.com/DeathWingg/filtro-vagas-python.git
