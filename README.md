# AERONET Data Analysis

Este projeto realiza análise de disponibilidade de dados da rede AERONET (Aerosol Robotic Network), processando dados de diferentes níveis de qualidade e gerando visualizações e métricas.

## Estrutura do Projeto

```
.
├── config.py              # Configurações do projeto
├── data_processor.py      # Processamento de dados
├── main.py               # Script principal
├── utils.py              # Funções utilitárias
├── visualizer.py         # Geração de visualizações
├── requirements.txt      # Dependências do projeto
├── AOD_data_lvl10/       # Dados de nível 1.0
├── AOD_data_lvl15/       # Dados de nível 1.5
└── AOD_data_lvl20/       # Dados de nível 2.0
```

## Requisitos

- Python 3.6+
- pandas
- numpy
- matplotlib
- chardet

## Instalação

### Usando ambiente virtual (recomendado)

1. Clone o repositório:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Crie e ative um ambiente virtual:
```bash
# No Windows
python -m venv venv
venv\Scripts\activate

# No Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

### Instalação direta

1. Clone o repositório:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Instale as dependências:
```bash
pip install pandas numpy matplotlib chardet
```

## Uso

Execute o script principal:
```bash
python main.py
```

O script irá:
1. Processar os dados de cada nível de qualidade
2. Gerar visualizações (distribuições de frequência, boxplots)
3. Calcular métricas de disponibilidade
4. Salvar resultados e gráficos
5. Exibir um relatório com:
   - Cidades que atendem aos critérios de disponibilidade
   - Resumo de todas as cidades
   - Lista de arquivos vazios
   - Log de erros (se houver)

## Configuração

As configurações do projeto podem ser ajustadas no arquivo `config.py`:

- `DATA_DIRS`: Diretórios dos diferentes níveis de qualidade
- `MIN_MEASUREMENTS_PER_DAY`: Mínimo de medições por dia (padrão: 8)
- `MIN_VALID_DAYS_PERCENTAGE`: Percentual mínimo de dias válidos (padrão: 30%)
- Configurações de visualização (cores, tamanhos, etc.)

## Estrutura dos Dados

Os arquivos de dados devem estar organizados em diretórios por nível de qualidade (1.0, 1.5, 2.0) e seguir o formato padrão AERONET:
- Arquivos texto (.txt)
- Separados por vírgula
- Cabeçalho na linha 6
- Colunas obrigatórias: 'Date(dd:mm:yyyy)', 'AOD_500nm'

## Saída

O script gera:
1. Gráficos de distribuição de frequência por cidade
2. Boxplots de medições válidas
3. Gráficos de dias representativos
4. Relatório de resultados no terminal
5. Log de erros (se houver)

## Tratamento de Erros

O script identifica e reporta:
- Arquivos vazios ou sem dados
- Erros de processamento
- Colunas ausentes
- Problemas de codificação

## Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes. 