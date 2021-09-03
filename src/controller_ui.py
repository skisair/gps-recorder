import streamlit as st
import streamlit.components.v1 as stc

'''
h	左へ1歩移動する。
j	下へ1歩移動する。
k	上へ1歩移動する。
l	右へ1歩移動する。
y	左上へ1歩移動する。
u	右上へ1歩移動する。
b	左下へ1歩移動する。
n	右下へ1歩移動する。
'''


def main():
    stc.html('<img width="200" alt="test" src="https://cafe-mickey.com/coffee-life/wp-content/uploads/2021/02/image.gif">')

    st.slider('LR', min_value=0, max_value=2, value=1, step=1)


    if st.button('Top button'):
        # 最後の試行で上のボタンがクリックされた
        st.write('Clicked')
    else:
        # クリックされなかった
        st.write('Not clicked')

    if st.button('Bottom button'):
        # 最後の試行で下のボタンがクリックされた
        st.write('Clicked')
    else:
        # クリックされなかった
        st.write('Not clicked')

if __name__ == '__main__':
    main()