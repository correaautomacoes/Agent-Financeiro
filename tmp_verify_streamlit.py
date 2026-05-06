try:
    import streamlit
    print('streamlit version:', streamlit.__version__)
except Exception as e:
    print('ERROR:', type(e).__name__, e)
