import time
import streamlit as st
from agent.react_agent import ReactAgent
import os
import json
from datetime import datetime

# 标题
#设置页面配置
st.set_page_config(
    page_title="智能客服",
    page_icon="🤖",
    #布局
    layout="wide",
    #侧边栏状态
    initial_sidebar_state="expanded",
    menu_items={}
)

# 生成会话标识
def generate_session_name():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# 保存会话信息函数
def save_session():
    if st.session_state.current_session:
        # 构建新的会话对象
        session_data = {
            "current_session": st.session_state.current_session,
            "message": st.session_state.message
        }

        # 如果sessions目录不存在，则创建
        if not os.path.exists("sessions"):
            os.makedirs("sessions")

        # 保存会话信息到文件
        with open(f"sessions/{st.session_state.current_session}.json", "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

# 加载所有会话列表信息
def load_sessions():
    session_list = []
    # 加载sessions目录下所有json文件
    if os.path.exists("sessions"):
        file_list = os.listdir("sessions")
        for filename in file_list:
            if filename.endswith(".json"):
                session_list.append(filename[:-5])
    return session_list

# 加载指定会话信息
def load_session(session_name):
    try:
        if os.path.exists(f"sessions/{session_name}.json"):
            # 读取会话数据
            with open(f"sessions/{session_name}.json", "r", encoding="utf-8") as f:
                session_data = json.load(f)
                st.session_state.current_session = session_name
                st.session_state.message = session_data["message"]
    except Exception as e:
        st.error(f"加载会话{session_name}失败！: {e}")

# 删除指定会话信息
def delete_session(session_name):
    try:
        if os.path.exists(f"sessions/{session_name}.json"):
            os.remove(f"sessions/{session_name}.json")
        # 如果删除的是当前会话，则需要更新消息列表
        if session_name == st.session_state.current_session:
            st.session_state.message = []
            st.session_state.current_session = generate_session_name()

    except Exception as e:
        st.error(f"删除会话{session_name}失败！: {e}")

if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()

if "message" not in st.session_state:
    st.session_state["message"] = []

# 会话标识
if 'current_session' not in st.session_state:
    now = generate_session_name()
    st.session_state.current_session = now

# 展示聊天记录
st.text(f"会话名称:{st.session_state.current_session}")

for message in st.session_state["message"]:
    st.chat_message(message["role"]).write(message["content"])

# 用户输入提示词
prompt = st.chat_input()

# 左侧侧边栏
with st.sidebar:
    st.markdown("<div style='font-size:26px; font-weight:bold; margin-bottom:10px;'>扫地机器人智能客服</div>", unsafe_allow_html=True)

    # 新建会话
    if st.button("新建会话", width="stretch", icon="🔄"):
        # 1.保存当前会话信息
        save_session()

        # 2.创建新的会话
        st.session_state.message = []
        st.session_state.current_session = generate_session_name()
        save_session()
        st.rerun()

    # 会话历史
    st.text("会话历史")
    session_list = load_sessions()
    for session in session_list:
        col1, col2 = st.columns([4, 1])
        with col1:
            # 加载会话信息
            # 三元运算符：如果条件为真，则返回第一个表达式的值；否则，返回第二个表达式的值 -->语法：值1 if 条件 else 值2
            button_type: str = "primary" if session == st.session_state.current_session else "secondary"
            if st.button(session, width="stretch", icon="📃", key=f"load_{session}", type=button_type):
                load_session(session)
                st.rerun()
        with col2:
            # 删除会话信息
            if st.button("", width="stretch", icon="🗑️", key=f"delete_{session}"):
                delete_session(session)
                st.rerun()


if prompt:
    st.chat_message("user").write(prompt)
    st.session_state["message"].append({"role": "user", "content": prompt})

    response_messages = []
    with st.spinner("智能客服思考中。。。"):
        history = st.session_state["message"][:-1]
        res_stream = st.session_state["agent"].execute_stream(prompt, history)

        def capture(generator, cache_list):

            for chunk in generator:
                cache_list.append(chunk)
                for char in chunk:
                    time.sleep(0.01)
                    yield char

        st.chat_message("assistant").write_stream(capture(res_stream, response_messages))
        st.session_state["message"].append({"role": "assistant", "content": response_messages[-1]})

        # 保存会话信息
        save_session()
        st.rerun()














