#!/bin/bash
# Script para iniciar o servidor local do Painel Digital
# Requer Python 3 disponível no sistema

echo "🚀 Iniciando Painel Digital - Paulo Afonso..."
echo "📍 Acesse seu painel em: http://localhost:4001"
echo "🌐 Outros aparelhos na rede podem acessar via seu IP na porta 4001."
echo "--------------------------------------------------------"

# Abrir o painel e o admin no navegador padrão (opcional)
open "http://localhost:4001/index.html"
open "http://localhost:4001/admin.html"

# Iniciar o servidor backend (Python Flask) que serve os arquivos e a API
python3 app.py
