import time
import streamlit as st

def type_text(
    text: str,
    container,
    typing_speed: float = 0.035,
    pre_delay: float = 0.6
):
    """
    Types text into a Streamlit container with a short delay.
    
    text: string to type
    container: st.empty() or st.container()
    typing_speed: seconds per character
    pre_delay: pause before typing starts
    """

    # Initial thinking pause
    container.markdown("…")
    time.sleep(pre_delay)

    typed = ""
    for char in text:
        typed += char
        container.markdown(typed)
        time.sleep(typing_speed)

    return typed
