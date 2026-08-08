import os
import json
import zipfile
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from pinecone import Pinecone as PineconePinecone
from chalicelib.fileops import get_heading_from_file, do_ffop,do_ffop_on_folder,move_files_with_suffix,heading_only_ffop, sub_suffix_in_file,any_func_on_folder
from chalicelib.config import PINECONE_API_KEY, OPENAI_API_KEY


client = OpenAI(api_key=OPENAI_API_KEY)

### QRAG VECTOR DB CREATION
'''
These vector db wrapper functions are used manually and are not called by the rag_bots functions. (RT 6-10-2024)
Pinecone indexes can be seen in the pinecone.io portal > go to Serverless in UL
'''
def generate_embedding(text, model="text-embedding-3-small"):  # DS, cat 1
    """ 
    Generates an embedding vector for the provided text using the specified OpenAI embeddings model.

    :param text: string of text to generate an embedding for.
    :param model: string of the OpenAI embeddings model to use. Default is "text-embedding-3-large".
    :return: list of floats representing the embedding vector.

    :category: cat 1
    :heading: QRAG VECTOR DB CREATION
    :usage: print(generate_embedding("Example text"))
    """

    response = client.embeddings.create(input=text,
    model=model)
    embedding = response.data[0].embedding
    return embedding

# TODO replace recursive with include_subfolders
# TODO Replace folder path with list of folder paths
# TODO Deal with suffix_include having the extension(.md) vs not - consider fixing get_files_in_folder() to handle both cases
def generate_vectors_qa(folder_paths, suffix_include, include_subfolders=True):  # DS, cat 3e
    """ 
    Generates vectors from markdown files in the specified folder paths.

    :param folder_paths: list of strings of the paths to the folders containing markdown files.
    :param include_subfolders: boolean indicating whether to search for markdown files in subfolders. Default is True.
    :return: list of dictionaries, each containing an id, values, and metadata for a block of text.

    :category: 3e
    :heading: QRAG VECTOR DB CREATION
    :usage: print(generate_vectors(["/path/to/markdown/folder1", "/path/to/markdown/folder2"]))
    """
    from primary.fileops import get_files_in_folder, get_timestamp
    from primary.structured import get_blocks_from_file, get_all_fields_from_block

    vectors = []  # Consider renaming this. it's the list of all the dicts with the fields from the blocks
    total_files = 0
    num_vectors = 0
    for folder_path in folder_paths:
        file_paths = get_files_in_folder(folder_path, suffix_include=suffix_include, include_subfolders=include_subfolders)
        total_files += len(file_paths)
        for path in file_paths:
            blocks = get_blocks_from_file(path)
            block_num = 0
            for block in blocks:
                fields = get_all_fields_from_block(block)
                file_name_with_extension = os.path.basename(path)  # Get file name with extension
                fields['SOURCE'] = file_name_with_extension  # Use file name with extension as the SOURCE
                vector_id = (os.path.splitext(file_name_with_extension)[0] + "_" + str(block_num)).replace(" ", "_")
                embedding = generate_embedding(fields['QUESTION'])  # Main call to generate embeddings
                timestamp, _ = get_timestamp(fields['QUESTION'])  # Extract timestamp from the question
                if timestamp:
                    fields['TIMESTAMP'] = timestamp  # Add timestamp to the metadata fields
                vector = {'id': vector_id, 'values': embedding, 'metadata': fields}  # Create the vector schema
                vectors.append(vector)
                num_vectors += 1
                block_num += 1
            print('Vectorized file:' + file_name_with_extension)
    print(f"Vectors generated for {total_files} files - number of vectors: {num_vectors}")
    return vectors

def vectors_to_json(vectors, file_path, zip_only=True):
    """
    Converts a list of dictionaries into a JSON file and optionally zips it. Deletes the original JSON file if archived.

    :param vectors: list of dictionaries to be converted.
    :param file_path: name of the JSON file to be created before zipping.
    :param zip_only: boolean indicating whether to zip and delete the JSON file. Default is True.
    :return: None.
    """

    try:
        # Write the JSON data to a file
        with open(file_path, 'w') as json_file:
            json.dump(vectors, json_file, indent=4)
        print(f"Successfully created {file_path}.")

        if zip_only:
            # Create a zip file containing the JSON file
            zip_file_path = file_path.replace('.json', '.zip')
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(file_path, os.path.basename(file_path))
            print(f"Successfully created {zip_file_path}.")

            # Delete the original JSON file
            os.remove(file_path)
            print(f"Successfully deleted {file_path}.")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def json_to_vectors(file_path):
    try:
        with open(file_path, 'r') as json_file:
            vectors = json.load(json_file)
        print(f"Successfully loaded {file_path}.")
        return vectors
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return []

def validate_vectors(vector_list):  # DS, cat 1
    """ 
    Validates that each vector in the list has the required fields and correct data types.

    :param vector_list: list of dictionaries, each representing a vector with an id, values, and metadata.
    :return: None. Raises ValueError if validation fails.

    :category: 1
    :heading: QRAG VECTOR DB CREATION
    :usage: validate_vectors(list_of_vectors)
    """
    required_fields = ["question", "answer", "question name", "answer name", "topics", "stars", "source"]
    for vector in vector_list:
        if not isinstance(vector.get('id'), str):
            raise ValueError(f"Missing or invalid 'id' in vector. It should be a string.")
        if not isinstance(vector.get('values'), list) or not all(isinstance(i, float) for i in vector.get('values', [])):
            raise ValueError(f"Missing or invalid 'values' in vector. It should be a list of floats.")
        if 'metadata' not in vector or not isinstance(vector['metadata'], dict):
            raise ValueError(f"Missing or invalid 'metadata' in vector. It should be a dictionary.")
        for field in required_fields:
            if field not in vector['metadata']:
                raise ValueError(f"Missing required field '{field}' in vector metadata.")
    print("All vectors have required fields and correct format.")

def upsert_vectors(vectors, pinecone_index_name, new_index=True):  # DS, cat 5
    """ 
    Upserts vectors into a Pinecone index in batches of 100, creating the index if it does not exist and if new_index is True.

    :param vectors: list of dictionaries, each representing a vector to be upserted.
    :param index_name: string of the name of the Pinecone index.
    :param new_index: boolean indicating whether to create a new index if it does not exist. Default is True.
    :return: None.

    :category: 5
    :heading:QRAG VECTOR DB CREATION
    :usage: upsert_vectors(list_of_vectors, 'index_name', new_index=True)
    """
    pc = PineconePinecone(api_key=PINECONE_API_KEY)
    if new_index:
        if pinecone_index_name not in pc.list_indexes().names():
            pc.create_index(
                name=pinecone_index_name, 
                dimension=1536, 
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-west-2')
            )
    index = pc.Index(pinecone_index_name)
    
    # Break up the vectors list into chunks of 100
    for i in range(0, len(vectors), 100):
        batch = vectors[i:i+100]
        index.upsert(vectors=batch)

# TODO Add zips
# TODO update to accept folder_paths as argument
# TODO Need to come up with better plan for managing fields. currently using lang chain and not set up to handle fields per block
# Fields per block are problematic becuase we dont want to vectorize block by block.
'''
VRAG is a different pipeline than QRAG, and currently does not support custom metadata. (RT 6-10-2024)
VRAG Is set up to mainly accept unstructured documents, and QRAG only accepts structured input documents.
'''
def create_vrag_pinecone_db_langchain(folder_path, index_name, suffix_include = None):    # DS cat 5
    """ 
    Establishes a Pinecone database using documents from the directory of markdown files. 
    If pinecone index name already exists, new vectors are added to the existing db. 

    :param folder_path: string of the path leading to the Obsidian vault.
    :param index_name: string of the designated name for the Pinecone index. 
    :return: None

    :category: 5
    :heading: LANGCHAIN RAG VECTOR DB CREATION
    :usage: create_rag_pinecone_db('/path/to/obsidian/vault', 'my_index')
    """ 
    from primary.fileops import any_func_on_folder, do_ffop_on_folder, move_files_with_suffix, heading_only_ffop, sub_suffix_in_file
    # Set OpenAI and Pinecone API keys
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

    # Initialize Pinecone
    pc = PineconePinecone(api_key=PINECONE_API_KEY)

    # Generate Pinecone index if it doesn't exist
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name, 
            dimension=1536, 
            metric='cosine',
            spec=ServerlessSpec(cloud='aws',region='us-west-2')
        )

    temp_folder_path = os.path.join(folder_path, "temp_transcripts")
    os.makedirs(temp_folder_path, exist_ok=True)

    do_ffop_on_folder(heading_only_ffop, folder_path, '### transcript',suffix_new='_temp',suffix_include = suffix_include)
    move_files_with_suffix(folder_path,temp_folder_path,'_temp')
    any_func_on_folder(sub_suffix_in_file,temp_folder_path , '')

    print(f"SUCCESS: Extracted transcript sections to temporary files in {temp_folder_path}")
    # Load documents from Obsidian vault
    loader = ObsidianLoader(temp_folder_path)
    docs = loader.load()
    print(f"SUCCESS: Loaded {len(docs)} documents from {folder_path}")
    import shutil
    shutil.rmtree(temp_folder_path)
    print(f"CLEANUP: Removed temporary files from {temp_folder_path}")

    # Split documents into chunks
    target_chunk_size = 1000
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=target_chunk_size, chunk_overlap=0)
    all_splits = text_splitter.split_documents(docs)
    print(f"SUCCESS: Split {len(docs)} documents into {len(all_splits)} splits with a target chunk size of {target_chunk_size}")

    # Populate vector store in Pinecone cloud database
    print("PROCESS: Populating vector store in Pinecone cloud database.")
    Pinecone.from_documents(documents=all_splits, embedding=OpenAIEmbeddings(), index_name=index_name)
    print(f"SUCCESS: Populated and saved vector store in Pinecone cloud database.")

# TODO add a zip of the source files and sync with naming of pinecone_index and vectors zip
# TODO Consider putting date time inside, so that all files created with the execution share a date time, but it doesnt need to be passed in
def create_qrag_vector_db(folder_paths, suffix_include, pinecone_index_name, export_json = True):
    # pinecone_index_name may only contain hyphens '-' and not underscores '_'
    # if the same pinecone_index_name is used (regardless if different datetime), the vectors will be added but not duplicated
    # cannot rename pinecone_index_name once create - would have to recreate with upsert
    from primary.fileops import get_current_datetime_filefriendly, zip_files_in_folders
        
    vectors = generate_vectors_qa(folder_paths, suffix_include)
    v_path = 'bots/vzips/'
    datetime = get_current_datetime_filefriendly()
    vsources_file_path = v_path + 'vsources_' + pinecone_index_name + '_' + datetime + '.zip'
    zip_files_in_folders(folder_paths, suffix_include, vsources_file_path, include_subfolders=True)
    if export_json:
        vjsonzip_file_path = f"{v_path}vjson-pc_{pinecone_index_name}_{datetime}.json"
        vectors_to_json(vectors, vjsonzip_file_path)  # outputs a zipped version of a json file with all of the vectors
    upsert_vectors(vectors, pinecone_index_name)


### EXECUTION CODE
if __name__ == "__main__":
    from primary.fileops import get_files_in_folder
    cur_folder_paths = ['data/deutsch/f8_done_qafixed_and_vrb', 'data/deutsch/f8_qafixed_talks']
    cur_suffix_include = '_qafixed'  # change for the suffix, use None to do all files
    cur_pinecone_index_name = 'deutsch-transcript-qrag'  # change for the corpus and bot type
    
    for folder in cur_folder_paths:
        file_count = len(get_files_in_folder(folder, suffix_include=cur_suffix_include, suffix_exclude=None, include_subfolders=True))
        print(f"Folder: {folder} contains {file_count} files.")
    user_input = input("Do you want to continue? (yes/no): ")
    if user_input.lower() not in ['yes', 'y']:
        exit()

    create_qrag_vector_db(cur_folder_paths, cur_suffix_include, cur_pinecone_index_name, export_json = True)

# To upload vectors in json, use:
    # upsert_vectors(json_to_vectors(vjson-pc_pinecone-index-name_datetimestamp.json), pinecone_index_name)

# LOG
    # bots/vzips/vjson-pc_deutsch-transcript-qrag_2024-06-10_145208.zip (same as 140000)
    # Vectors generated for 75 files - number of vectors: 1194

    # bots/vzips/vjson-pc_deutsch-transcript-qrag_2024-06-10_140000.zip
    # https://deutsch-transcript-qrag-6sqzb0u.svc.apw5-4e34-81fa.pinecone.io
