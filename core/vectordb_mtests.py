# ===== START OF FILE core/vectordb_mtests.py =====
# Library for manual testing of vectordb functions

from core.vectordb import *

if True:
    pass
if __name__ == "__main__":        
    cur_file_path = ""


### QRAG VECTOR DB CREATION
def mtest_create_qrag_vector_db():
    pass
#if __name__ == "__main__":  
    cur_folder_paths = ['tests/test_data_files/vectordb']
    create_qrag_vectordb(cur_folder_paths ,'dd-qrag-test', suffixpat_include = '_qafixed')

def mtest_create_vectordb_vrag_langchain():
    pass
#if __name__ == "__main__":  
    cur_folder_paths = ['tests/test_data_files/vectordb']
    create_vectordb_vrag_langchain(cur_folder_paths,'dd-vrag-test-newjson', suffixpat_include='_vrb', skip_pinecone=True)

    # cur_folder_paths = ['data/deutsch/f8_done_qafixed_and_vrb', 'data/deutsch/f8_qafixed_talks','data/deutsch/f8_vrb_talks_only']
    # create_vectordb_vrag_langchain(cur_folder_paths,'dd-transcripts-vrag', suffixpat_include='_vrb', skip_pinecone=False)

def mtest_update_pinecone_index_list_md():
    pass
#if __name__ == "__main__":  
    update_pinecone_index_list_md()

def mtest_upsert_vectors_pinecone():
    pass
# if __name__ == "__main__":  
    # unzip file to get json first
    upsert_vectors_pinecone(json_to_vectors('vjson-pc_pinecone-index-name_datetimestamp.json'), 'my_vector_index_name')

### OLD TEST CODE for generate_vectors (USE PINCONE PORTAL INSTEAD)
    # vectors = generate_vectors('tests/test_data_files/vectordb')
    # print(vectors)
    # vectors_to_json(vectors)
    # pp = pprint.PrettyPrinter(indent=4)
    # pp.pprint(format_vectors(vectors))
    # upsert_vectors(vectors, 'mtest')

### OLD EXECUTION CODE from .py file       
    # vectors = generate_vectors('data/dd/f8_done_qafixed_and_vrb')
    # vectors_to_json(vectors, file_name='dd_vectors3.json', archive=False)
    # upsert_vectors(json_to_vectors('dd_vectors3.json'), 'qragnospace')
    # create_qrag_vector_db('data/deutsch/f8_done_qafixed_and_vrb', '')
    # create_vrag_pinecone_db('data/deutsch/f8_done_qafixed_and_vrb','vrag-test')
    # create_vrag_pinecone_db('data/floodlamp_fda/townhalls/f4_md_cleaned_manualedits', 'fda-townhalls-vrag-test1', suffix_include='_cleaned')


# ===== END OF FILE core/vectordb_mtests.py =====
