import os
import shutil
import tempfile
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from utils.file_handler import pdf_loader, txt_loader, listdir_with_allowed_type, get_file_md5_hex
from utils.logger_handler import logger
from utils.config_handler import chroma_conf
from utils.path_tool import get_abs_path
from model.factory import embedding_model
from langchain_text_splitters import RecursiveCharacterTextSplitter

class VectorStoreService:
    def __init__(self):
        self.persist_dir = get_abs_path(chroma_conf["persist_directory"])
        os.makedirs(self.persist_dir, exist_ok=True)

        if os.path.exists(os.path.join(self.persist_dir, "index.faiss")):
            # FAISS 在 Windows 上不支持中文路径：先复制到临时目录再加载
            tmp_dir = os.path.join(tempfile.gettempdir(), "faiss_tmp")
            os.makedirs(tmp_dir, exist_ok=True)
            for fname in ("index.faiss", "index.pkl"):
                shutil.copy2(os.path.join(self.persist_dir, fname), os.path.join(tmp_dir, fname))
            self.vector_store = FAISS.load_local(
                tmp_dir, embedding_model, allow_dangerous_deserialization=True
            )

        else:
            self.vector_store = None

        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
            length_function=len,
        )

    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_conf["k"]})

    def load_document(self):
        """
        从数据文件夹内读入数据文件，转为向量存入向量库
        要计算文件的 MD5值做去重
        :return:None
        """

        def check_md5_hex(md5_for_check: str):
            if not os.path.exists(get_abs_path(chroma_conf["md5_hex_store"])):
                open(get_abs_path(chroma_conf["md5_hex_store"]), "w", encoding="utf-8").close()
                return False   # md5没处理过

            with open(get_abs_path(chroma_conf["md5_hex_store"]), "r", encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line == md5_for_check:
                        return True   # md5处理过

                return False   # md5处理过

        def save_md5_hex(md5_for_save: str):
            with open(get_abs_path(chroma_conf["md5_hex_store"]), "a", encoding="utf-8") as f:
                f.write(md5_for_save + "\n")

        def get_file_documents(read_path: str):
            if read_path.endswith("txt"):
                return txt_loader(read_path)

            if read_path.endswith("pdf"):
                return pdf_loader(read_path)

            return []

        allowed_files_path = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        for path in allowed_files_path:
            # 获取文件 md5
            md5_hex = get_file_md5_hex(path)

            if check_md5_hex(md5_hex):
                logger.info(f"[加载知识库]{path}内容已存在知识库内，跳过")
                continue

            try:
                documents: list[Document] = get_file_documents(path)
                if not documents:
                    logger.warning(f"[加载知识库]{path}内没有有效文本内容，跳过")
                    continue

                split_document: list[Document] = self.spliter.split_documents(documents)

                if not split_document:
                    logger.warning(f"[加载知识库]{path}分片后没有有效文本内容，跳过")
                    continue

                # 将内容存入向量库
                if self.vector_store is None:
                    self.vector_store = FAISS.from_documents(split_document, embedding_model)
                else:
                    self.vector_store.add_documents(split_document)

                # FAISS 在 Windows 上不支持中文路径：先存到临时目录再复制回知识库目录
                tmp_dir = os.path.join(tempfile.gettempdir(), "faiss_tmp")
                os.makedirs(tmp_dir, exist_ok=True)
                self.vector_store.save_local(tmp_dir)
                for fname in ("index.faiss", "index.pkl"):
                    shutil.copy2(os.path.join(tmp_dir, fname), os.path.join(self.persist_dir, fname))

                # 记录已经处理好的文件的 md5，避免重复处理
                save_md5_hex(md5_hex)

                logger.info(f"[加载知识库]{path}成功")

            except Exception as e:
                # exc_info为 True会记录详细的报错堆栈，如果为 False仅记录报错信息本身
                logger.error(f"[加载知识库]{path}加载失败：{str(e)}", exc_info=True)
                continue

if __name__ == "__main__":
    vs = VectorStoreService()
    vs.load_document()
    retriever = vs.get_retriever()

    res = retriever.invoke("迷路")
    for r in res:
        print(r.page_content)
        print("-"*20)






















