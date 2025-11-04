
# Cotizador local — This is Bravo (MVP)
Ejecuta un cotizador local en tu notebook con Streamlit.

## Requisitos
- Python 3.10+
- macOS/Windows/Linux

## Instalación
```bash
cd bravo_cotizador_app
python -m venv .venv
source .venv/bin/activate  # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Uso
1. Pega un brief en el campo de texto.
2. Ajusta variables (tipo de cliente, urgencia, etc.).
3. Presiona **Analizar brief y calcular** para ver los tres escenarios.
4. El catálogo editable está en `catalog.json`.

## Notas
- El detector de módulos (parser) es básico (keywords). Más adelante podemos integrar un modelo local (Llama/Mistral) o una API para mejorar la comprensión.
- Todo corre local. No se sube nada a ningún servidor.
