# ===== START OF FILE core/dbgen.py =====
# Library of functions and execution code to generate databases

import os
import json
import sqlite3
import csv

from core.fileops import *

### EXCHANGES SQLITE DB
def create_exchanges_db(db_path):
    """
    Create a SQLite database with the required schema for indexing exchanges.
    If the database doesn't exist, it will be created.
    If the database exists but the 'exchanges' table doesn't, the table will be created.
    If both the database and 'exchanges' table exist, no changes will be made to the structure.

    :param db_path: Path to the SQLite database file.
    :return: None
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exchanges (
                filename TEXT PRIMARY KEY,  -- Use filename as the unique identifier
                date_PT TEXT,               -- Extracted date in Pacific time from file name
                time_PT TEXT,               -- Extracted time in Pacific time from file name
                user_question TEXT,         -- Include user question from JSON
                userNiceName TEXT,          -- Unhashed user name (PII version only)
                userIPAddress TEXT,         -- Unhashed IP address (PII version only)
                inputUserEmail TEXT,        -- Unhashed email (PII version only)
                hmac_user_id TEXT,          -- HMAC user ID from JSON
                local_file_path TEXT,       -- Relative local path to the file
                hashedNiceName TEXT,        -- From user_context
                hashedIPAddress TEXT,       -- From user_context
                hashedEmail TEXT            -- From user_context
            )
        ''')
        conn.commit()
        print(f"Database '{db_path}' checked/created with table 'exchanges'.")
    except sqlite3.Error as e:
        print(f"SQLite error during database operation: {e}")
    finally:
        conn.close()
def mtest_create_exchanges_db():
    db_path = 'exchanges.db'
    create_exchanges_db(db_path)

def index_exchanges_in_db(root_folder, exclude_subfolders=None):
    """
    Traverse the local folder structure starting from root_folder,
    extract metadata from each JSON file, and store it in the SQLite database.

    :param root_folder: Root local folder to start indexing from.
    :param exclude_subfolders: List of subfolder names to exclude from indexing. Defaults to None.
    :return: The relative path to the SQLite database file.
    """
    from core.fileops import get_files_in_folder

    if exclude_subfolders is None:
        exclude_subfolders = []

    # Get all JSON files in the folder and subfolders, excluding specified subfolders
    json_files = get_files_in_folder(root_folder, include_subfolders=True, suffixpat_include='.json')
    json_files = [f for f in json_files if not any(subfolder in f for subfolder in exclude_subfolders)]

    db_path = os.path.join(root_folder, 'exchanges.db')
    
    # Ensure the database and table are created
    create_exchanges_db(db_path)  # Call the function to create the table if it doesn't exist

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    new_records = 0
    updated_records = 0
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract metadata
            filename = os.path.basename(file_path)
            # Extract date and time from filename
            if filename.startswith('qrag-exch_') and filename.endswith('.json'):
                date_time_part = filename[10:-5]  # Remove 'qrag-exch_' prefix and '.json' suffix
                date_PT, time_PT = date_time_part.split('_')
                time_PT = f"{time_PT[:2]}:{time_PT[2:4]}:{time_PT[4:]}"  # Format time as HH:MM:SS
            else:
                date_PT, time_PT = None, None
            user_id = data['metadata'].get('user_id')
            local_file_path = file_path  # Full local path to the file
            user_question = data['content'].get('user_question')

            # Get user context data
            user_context = data['metadata'].get('user_context', {})
            hashedNiceName = user_context.get('hashedNiceName', '')
            hashedIPAddress = user_context.get('hashedIPAddress', '')
            hashedEmail = user_context.get('hashedEmail', '')

            # Use the user_id directly as HMAC user ID
            hmac_user_id = user_id

            # Insert or update the record
            cursor.execute('''
                INSERT OR REPLACE INTO exchanges (filename, date_PT, time_PT, user_question, hmac_user_id, local_file_path,
                 hashedNiceName, hashedIPAddress, hashedEmail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (filename, date_PT, time_PT, user_question, hmac_user_id, local_file_path,
                  hashedNiceName, hashedIPAddress, hashedEmail))
            if cursor.rowcount > 0:
                new_records += 1
            else:
                updated_records += 1

        except Exception as e:
            print(f"Error processing file '{file_path}': {e}")

    conn.commit()
    conn.close()
    print(f"Indexing complete. New records: {new_records}, Updated records: {updated_records}")
    return db_path
def mtest_index_exchanges_in_db():
    root_folder = 'exchanges/deutsch_qrag'  # Replace with your root folder
    exclude_subfolders = None  # ['not-reviewed']
    db_path = index_exchanges_in_db(root_folder, exclude_subfolders)
    print(f"SQLite database created at: {db_path}")

def view_all_exchanges(db_path):
    """
    Retrieve and print all records from the exchanges table.

    :param db_path: Path to the SQLite database file.
    :return: None
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM exchanges")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        conn.close()
def mtest_view_all_exchanges():
    db_path = 'exchanges/deutsch_qrag/exchanges.db'
    view_all_exchanges(db_path)

### WEBFLOW USERS SPECIFIC
def copy_exchanges_db_with_pii_add_column(exchanges_db_path):
    """
    Copy the exchanges database and add a column with a static value 'blank' for user_name.

    :param exchanges_db_path: Path to the exchanges SQLite database file.
    :return: Path to the new database with PII.
    """
    # Connect to the original database
    conn = sqlite3.connect(exchanges_db_path)
    cursor = conn.cursor()

    # Create a new database with 'pii-' prefix
    new_db_path = os.path.join(os.path.dirname(exchanges_db_path), f"pii-{os.path.basename(exchanges_db_path)}")
    if os.path.exists(new_db_path):
        os.remove(new_db_path)  # Remove existing file to avoid conflicts
    new_conn = sqlite3.connect(new_db_path)
    new_cursor = new_conn.cursor()

    try:
        # Get the schema of the original table
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='exchanges'")
        create_table_sql = cursor.fetchone()[0]

        # Create the table in the new database
        new_cursor.execute(create_table_sql)

        # Add the new column to the new database
        new_cursor.execute("ALTER TABLE exchanges ADD COLUMN user_name TEXT DEFAULT 'blank'")

        # Copy data from the original database to the new one
        cursor.execute("SELECT * FROM exchanges")
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        placeholders = ', '.join(['?' for _ in columns])
        new_cursor.executemany(f"INSERT INTO exchanges ({', '.join(columns)}, user_name) VALUES ({placeholders}, 'blank')", rows)

        # Commit changes
        new_conn.commit()
        print(f"Created new database with PII at: {new_db_path}")
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        # Close connections
        conn.close()
        new_conn.close()

    return new_db_path

# get users csv file by downloading from Webflow
def add_users_table_to_db(cursor, users_csv_path):
    """
    Add a users table to the database from a CSV file.

    :param cursor: SQLite cursor object.
    :param users_csv_path: Path to the users CSV file.
    """
    # Read the CSV file to get the column names
    with open(users_csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        csv_columns = next(reader)

    # Create the 'users' table in the database with all CSV columns
    create_users_table_sql = f'''
        CREATE TABLE IF NOT EXISTS users (
            {', '.join([f'"{col}" TEXT' for col in csv_columns])}
        )
    '''
    cursor.execute(create_users_table_sql)

    # Read the users CSV file and insert data into the 'users' table
    with open(users_csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        users_data = [tuple(row.values()) for row in reader]

    placeholders = ', '.join(['?' for _ in csv_columns])
    insert_sql = f'''
        INSERT OR REPLACE INTO users ({', '.join([f'"{col}"' for col in csv_columns])})
        VALUES ({placeholders})
    '''
    cursor.executemany(insert_sql, users_data)
def add_username_column_to_exchanges(cursor):
    """
    Add a username column to the exchanges table and populate it with usernames
    from the users table based on the HMAC User ID, excluding 'default' user IDs.

    :param cursor: SQLite cursor object.
    """
    try:
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(exchanges)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'user_name' not in columns:
            # Add the new column to the exchanges table
            cursor.execute("ALTER TABLE exchanges ADD COLUMN user_name TEXT DEFAULT 'NA'")
            print("Added user_name column to exchanges table.")
        else:
            print("user_name column already exists in exchanges table.")

        # Update the user_name column based on HMAC User ID, excluding 'default'
        cursor.execute("""
            UPDATE exchanges
            SET user_name = (
                SELECT "Name"
                FROM users
                WHERE users."HMAC User ID" = exchanges.hmac_user_id
            )
            WHERE EXISTS (
                SELECT 1
                FROM users
                WHERE users."HMAC User ID" = exchanges.hmac_user_id
            )
            AND exchanges.hmac_user_id != 'default'
        """)
        print(f"Updated {cursor.rowcount} rows in the exchanges table.")

        # Debug: Check contents of exchanges table after update
        cursor.execute("SELECT hmac_user_id, user_name FROM exchanges LIMIT 5")
        print("Sample data from exchanges table after update:")
        for row in cursor.fetchall():
            print(row)

    except sqlite3.Error as e:
        print(f"SQLite error while adding or updating user_name column: {e}")
def copy_exchanges_db_with_user_pii(exchanges_db_path, users_csv_path):
    """
    Copy the exchanges database, add a table with user PII from the users CSV file,
    and add a username column to the exchanges table.

    :param exchanges_db_path: Path to the exchanges SQLite database file.
    :param users_csv_path: Path to the users CSV file.
    :return: Path to the new database with PII.
    """
    # Connect to the original database
    conn = sqlite3.connect(exchanges_db_path)
    cursor = conn.cursor()

    # Create a new database with 'pii-' prefix
    new_db_path = os.path.join(os.path.dirname(exchanges_db_path), f"pii-{os.path.basename(exchanges_db_path)}")
    if os.path.exists(new_db_path):
        os.remove(new_db_path)  # Remove existing file to avoid conflicts
    new_conn = sqlite3.connect(new_db_path)
    new_cursor = new_conn.cursor()

    try:
        # Get the schema of the original table
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='exchanges'")
        create_table_sql = cursor.fetchone()
        if not create_table_sql:
            raise ValueError("exchanges table not found in the original database")
        
        create_table_sql = create_table_sql[0]

        # Create the table in the new database
        new_cursor.execute(create_table_sql)
        print("Created exchanges table in the new database")

        # Copy data from the original database to the new one
        cursor.execute("SELECT * FROM exchanges")
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        # print(f"Number of rows to copy: {len(rows)}")
        # print(f"Columns: {columns}")

        if not rows:
            print("Warning: No rows found in the original exchanges table")
        else:
            placeholders = ', '.join(['?' for _ in columns])
            insert_sql = f"INSERT INTO exchanges ({', '.join(columns)}) VALUES ({placeholders})"
            new_cursor.executemany(insert_sql, rows)
            print(f"Copied {new_cursor.rowcount} rows to the new database")

        # Add users table to the new database
        add_users_table_to_db(new_cursor, users_csv_path)

        # Add username column to the exchanges table
        add_username_column_to_exchanges(new_cursor)

        # Commit changes
        new_conn.commit()
        print(f"Created new database with PII at: {new_db_path}")
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        print(f"Error occurred on line: {e.__traceback__.tb_lineno}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        print(f"Error occurred on line: {e.__traceback__.tb_lineno}")
    finally:
        # Close connections
        conn.close()
        new_conn.close()

    return new_db_path

def add_hmac_user_id_to_users_csv(users_csv_path):
    """
    Add a column for the HMAC User ID to the CSV file, appearing after the Email column.
    The HMAC is generated from the email address.

    :param users_csv_path: Path to the users CSV file.
    :return: Boolean indicating success or failure
    """
    from core.aws import generate_hmac_hash, USERS_HMAC_SECRET_KEY

    try:
        # Read the CSV file
        with open(users_csv_path, mode='r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader)
            
            # Insert new column header for HMAC User ID
            headers.insert(3, 'HMAC User ID')
            
            # Prepare data with HMAC User ID
            updated_rows = [headers]
            for row in reader:
                email = row[2]  # Assuming email is in the third column (index 2)
                # Generate HMAC for email using the existing function
                hmac_user_id = generate_hmac_hash(email, USERS_HMAC_SECRET_KEY)
                # Insert HMAC User ID into the row
                row.insert(3, hmac_user_id)
                updated_rows.append(row)
        
        # Write the updated data back to the CSV
        with open(users_csv_path, mode='w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(updated_rows)
        
        row_count = len(updated_rows) - 1  # Subtract 1 to exclude the header row
        print(f"Successfully added HMAC User ID to CSV. The file contains {row_count} rows.")
        return True
    except Exception as e:
        print(f"Failed to add HMAC User ID to CSV: {str(e)}")
        return False

def run_mtests_exchanges():
    pass
#if __name__ == "__main__":
    # mtest_create_exchanges_db()
    # mtest_index_exchanges_in_db()
    #mtest_view_all_exchanges()
    #mtest_generate_hmac_hash()
    add_hmac_user_id_to_users_csv("exchanges/deutsch_qrag/pii-users.csv")


### USER HASH LOG SPECIFIC
CURRENT_USER_HASH_LOG_FILE_PATH = 'exchanges/pii_user_hash_log_2024-12-17.csv'
USER_NICENAME_EXCLUDE_PREFIXES = []#['TEST', 'Test', 'Randy']
USER_NICENAME_INCLUDE_EXACT = ['Randy Real']
def save_user_hash_log_from_s3(users_hash_log_file_key, output_dir='exchanges'):
    """
    Get the user hash log from S3 and save it to the output directory.

    :param users_hash_log_file_key: str, key of the file in S3 bucket
    :param output_dir: str, directory to save the downloaded file
    :return output_path: str, full local path of saved user hash log file, or None if failed
    """
    from core.aws import get_s3_object
    bucket = "[S3-BUCKET]"
    s3_path = None  # files are in the root of the bucket
    
    # Set parse_json=False since we're downloading a CSV file
    s3_object = get_s3_object(bucket, users_hash_log_file_key, s3_path, parse_json=False, verbose=True)

    if s3_object:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save raw content to file in output directory
        output_path = os.path.join(output_dir, users_hash_log_file_key)
        with open(output_path, 'w') as f:
            f.write(s3_object)  # Write raw content instead of using json.dump
        print(f"Saved user hash log to: {output_path}")
        return output_path
    else:
        print(f"Error: User hash log with key '{users_hash_log_file_key}' save failed.")
        return None
def mrun_save_user_hash_log_from_s3():
    pass
#if __name__ == "__main__":
    users_hash_log_file_key = os.path.basename(CURRENT_USER_HASH_LOG_FILE_PATH)
    save_user_hash_log_from_s3(users_hash_log_file_key)

def download_exchanges_from_s3(bucket="[S3-BUCKET]", s3_path="exchanges", local_dir="exchanges", verbose=False):
    """
    Download all exchange JSON files from S3 to a local directory, skipping existing files.

    :param bucket: str, name of the S3 bucket
    :param s3_path: str, path prefix in the S3 bucket
    :param local_dir: str, local directory to save downloaded files
    :param verbose: bool, whether to print verbose output
    :return: list of downloaded file paths
    """
    from core.aws import list_s3_files, get_s3_object
    
    # Create exchange_jsons subfolder
    json_dir = os.path.join(local_dir, 'exchange_jsons')
    os.makedirs(json_dir, exist_ok=True)
    
    # Get list of existing local files
    existing_files = set(os.listdir(json_dir))
    
    # Get list of all JSON files in the S3 path
    json_files = list_s3_files(bucket, s3_path, file_extension='.json')
    
    downloaded_files = []
    skipped_files = 0
    
    for json_file in json_files:
        try:
            local_path = os.path.join(json_dir, json_file)
            
            # Skip if file already exists locally
            if json_file in existing_files:
                skipped_files += 1
                verbose_print(verbose, f"Skipping existing file: {json_file}")
                continue
            
            # Get JSON content from S3
            json_content = get_s3_object(bucket, json_file, s3_path)
            if json_content:
                # Save JSON content to local file
                with open(local_path, 'w', encoding='utf-8') as f:
                    json.dump(json_content, f, indent=2)
                
                downloaded_files.append(local_path)
                verbose_print(verbose, f"Downloaded new file: {json_file} -> {local_path}")
            else:
                print(f"Failed to download: {json_file}")
        except Exception as e:
            print(f"Error downloading {json_file}: {e}")
    
    print(f"Exchange JSONs from S3: {len(json_files)} total files")
    print(f"- {skipped_files} existing files skipped")
    print(f"- {len(downloaded_files)} new files downloaded")
    print(f"Files saved to: {json_dir}")
    
    return downloaded_files

def create_user_hash_db(db_path):
    """
    Create a SQLite database for the user hash log system.

    :param db_path: Path to the SQLite database file.
    :return: None
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_hashes (
                timestamp TEXT,
                userNiceName TEXT,
                hashed_userNiceName TEXT,
                userIPAddress TEXT,
                hashed_userIPAddress TEXT,
                inputUserEmail TEXT,
                hashed_inputUserEmail TEXT,
                emailListSignupChecked TEXT,
                eventType TEXT,
                privacyConsent TEXT
            )
        ''')
        conn.commit()
        print(f"Database '{db_path}' checked/created with table 'user_hashes'.")
    except sqlite3.Error as e:
        print(f"SQLite error during database operation: {e}")
    finally:
        conn.close()
def import_user_hash_log(db_path, user_hash_log_path):
    """
    Import user hash log CSV data into the SQLite database.

    :param db_path: Path to the SQLite database file.
    :param user_hash_log_path: Path to the user hash log CSV file.
    :return: None
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # First ensure the table exists
        create_user_hash_db(db_path)
        
        # Read and import the CSV data
        with open(user_hash_log_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                cursor.execute('''
                    INSERT INTO user_hashes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['timestamp'],
                    row['userNiceName'],
                    row['hashed_userNiceName'],
                    row['userIPAddress'],
                    row['hashed_userIPAddress'],
                    row['inputUserEmail'],
                    row['hashed_inputUserEmail'],
                    row['emailListSignupChecked'],
                    row['eventType'],
                    row['privacyConsent']
                ))
        
        conn.commit()
        print(f"Successfully imported user hash log data from {user_hash_log_path}")
    except Exception as e:
        print(f"Error importing user hash log: {e}")
    finally:
        conn.close()
def create_exchanges_db_with_user_hashes(exchanges_db_path, user_hash_log_path=CURRENT_USER_HASH_LOG_FILE_PATH, 
                                       user_nicename_exclude_prefixes=USER_NICENAME_EXCLUDE_PREFIXES, 
                                       user_nicename_include_exact=USER_NICENAME_INCLUDE_EXACT, 
                                       exclude_null_nicename=True,
                                       add_only=False):
    """
    Create a new database combining exchanges and user hash data, with the exchanges table
    sorted in reverse alphabetical order by filename. Filters exchanges based on userNiceName
    exclusion/inclusion lists.
    
    :param exchanges_db_path: Path to the original exchanges database.
    :param user_hash_log_path: Path to the user hash log CSV file.
    :param user_nicename_exclude_prefixes: List of prefixes to exclude.
    :param user_nicename_include_exact: List of exact names to include.
    :param exclude_null_nicename: bool, whether to exclude entries with NULL userNiceName.
    :param add_only: bool, if True only adds new entries to existing PII database.
    :return: Path to the new database.
    """
    # Create new database path
    new_db_path = os.path.join(os.path.dirname(exchanges_db_path), 
                               f"pii-{os.path.basename(exchanges_db_path)}")
    
    if add_only and os.path.exists(new_db_path):
        # Get the most recent filename from existing PII database
        with sqlite3.connect(new_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT filename FROM exchanges ORDER BY filename DESC LIMIT 1")
            result = cursor.fetchone()
            if result:
                most_recent_filename = result[0]
                print(f"Most recent filename in PII database: {most_recent_filename}")
            else:
                print("No existing entries found in PII database")
                most_recent_filename = None
    else:
        most_recent_filename = None
        if os.path.exists(new_db_path):
            os.remove(new_db_path)

    # Copy original exchanges database to new database
    if not add_only or not os.path.exists(new_db_path):
        with sqlite3.connect(exchanges_db_path) as src_conn, sqlite3.connect(new_db_path) as dest_conn:
            src_conn.backup(dest_conn)

    try:
        # Import user hash data into new database
        import_user_hash_log(new_db_path, user_hash_log_path)

        with sqlite3.connect(new_db_path) as conn:
            cursor = conn.cursor()
            
            # Create the exclude condition using LIKE for prefix matching
            exclude_conditions = " AND ".join([
                f"u.userNiceName NOT LIKE '{prefix}%'" 
                for prefix in user_nicename_exclude_prefixes
            ])
            
            # Create the include condition for exact matches
            include_conditions = " OR ".join([
                f"u.userNiceName = '{exact}'" 
                for exact in user_nicename_include_exact
            ])
            
            # Add filename filter for add_only mode
            filename_filter = f"AND e.filename > '{most_recent_filename}'" if most_recent_filename else ""
            
            # Combine conditions for the WHERE clause
            where_clause = f"""
                WHERE (
                    {f'u.userNiceName IS NOT NULL AND' if exclude_null_nicename else ''}
                    (
                        ({exclude_conditions})
                        OR ({include_conditions})
                    )
                )
                {filename_filter}
            """ if USER_NICENAME_EXCLUDE_PREFIXES else (
                f"WHERE u.userNiceName IS NOT NULL {filename_filter}" if exclude_null_nicename else filename_filter
            )

            if add_only:
                # Create temporary table for new filtered entries
                cursor.execute(f"""
                    CREATE TEMPORARY TABLE new_entries AS 
                    SELECT DISTINCT e.* 
                    FROM exchanges e
                    LEFT JOIN (
                        SELECT hashed_userNiceName, userNiceName, MIN(rowid) as first_occurrence
                        FROM user_hashes
                        GROUP BY hashed_userNiceName, userNiceName
                    ) u ON u.hashed_userNiceName = e.hashedNiceName
                    {where_clause}
                    ORDER BY filename DESC
                """)
                
                # Insert new entries into existing table
                cursor.execute("""
                    INSERT INTO exchanges 
                    SELECT * FROM new_entries
                """)
                
                # Drop temporary table
                cursor.execute("DROP TABLE new_entries")
            else:
                # Create a new table with filtered and sorted rows
                cursor.execute(f"""
                    CREATE TABLE new_exchanges AS 
                    SELECT DISTINCT e.* 
                    FROM exchanges e
                    LEFT JOIN (
                        SELECT hashed_userNiceName, userNiceName, MIN(rowid) as first_occurrence
                        FROM user_hashes
                        GROUP BY hashed_userNiceName, userNiceName
                    ) u ON u.hashed_userNiceName = e.hashedNiceName
                    {where_clause}
                    ORDER BY filename DESC
                """)
                
                # Replace the original table with the filtered and sorted one
                cursor.execute("DROP TABLE exchanges")
                cursor.execute("ALTER TABLE new_exchanges RENAME TO exchanges")
            
            # Create an index on filename if it doesn't exist
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_filename ON exchanges(filename DESC)")
            
            # Update exchanges table with user information
            cursor.execute("""
                UPDATE exchanges SET 
                    userNiceName = (
                        SELECT userNiceName 
                        FROM user_hashes 
                        WHERE user_hashes.hashed_userNiceName = exchanges.hashedNiceName
                        LIMIT 1
                    ),
                    userIPAddress = (
                        SELECT userIPAddress 
                        FROM user_hashes 
                        WHERE user_hashes.hashed_userIPAddress = exchanges.hashedIPAddress
                        LIMIT 1
                    ),
                    inputUserEmail = (
                        SELECT inputUserEmail 
                        FROM user_hashes 
                        WHERE user_hashes.hashed_inputUserEmail = exchanges.hashedEmail
                        LIMIT 1
                    )
            """)
            
            # Get and print statistics
            cursor.execute("SELECT COUNT(*) FROM exchanges")
            total_rows = cursor.fetchone()[0]
            print(f"Total exchanges after filtering: {total_rows}")
            
            conn.commit()
            print(f"{'Updated' if add_only else 'Created'} PII database at: {new_db_path}")
            return new_db_path
    except Exception as e:
        print(f"Error {'updating' if add_only else 'creating'} PII database: {e}")
        return None

def get_s3_path_for_corpus(folder_name):
    """
    Get the S3 path for a given corpus folder name.

    :param folder_name: str, name of the folder (e.g., 'qrag_deutsch')
    :return: str, corresponding S3 path with trailing slash
    """
    # Extract the corpus name after 'qrag_'
    if not folder_name.startswith('exchanges/qrag_'):
        raise ValueError(f"Invalid folder name format: {folder_name}")
    
    corpus = folder_name.split('qrag_')[1]
    
    # Map corpus to S3 path (always include trailing slash)
    s3_paths = {
        'deutsch': 's3-qrag-deutsch/',
        'pv-evac': 's3-qrag-pv-evac/',
        'fda-c19-townhalls': 's3-qrag-fda-townhalls/',
        'sovereign-child': 's3-qrag-sovereign-child/'
    }
    
    if corpus not in s3_paths:
        raise ValueError(f"Unknown corpus: {corpus}")
    
    return s3_paths[corpus]
def process_exchanges_folder(exchanges_folder, add_only=False):
    """
    Process an exchanges folder, creating or updating the exchanges database.
    
    :param exchanges_folder: str, path to the exchanges folder (e.g., 'exchanges/qrag_deutsch')
    :param add_only: bool, if True only adds new entries to existing PII database
    """
    try:
        # Get S3 path for this corpus
        s3_path = get_s3_path_for_corpus(exchanges_folder)
        
        # Create the folder if it doesn't exist
        os.makedirs(exchanges_folder, exist_ok=True)
        
        # Get folder name for database naming
        folder_name = os.path.basename(exchanges_folder)
        
        # Paths for databases
        db_path = os.path.join(exchanges_folder, f'exchanges_{folder_name}.db')
        pii_db_path = os.path.join(exchanges_folder, f'pii-exchanges_{folder_name}.db')
        
        # Create backup of existing databases with _PREV suffix
        if os.path.exists(db_path):
            prev_db_path = db_path.replace('.db', '_PREV.db')
            print(f"Creating backup of regular database: {prev_db_path}")
            import shutil
            shutil.copy2(db_path, prev_db_path)
            
        if os.path.exists(pii_db_path):
            prev_pii_db_path = pii_db_path.replace('.db', '_PREV.db')
            print(f"Creating backup of PII database: {prev_pii_db_path}")
            import shutil
            shutil.copy2(pii_db_path, prev_pii_db_path)

        # Download new exchanges from S3 into exchange_jsons subfolder
        print(f"Downloading exchanges from S3 path: {s3_path}")
        downloaded_files = download_exchanges_from_s3(
            bucket="[S3-BUCKET]",
            s3_path=s3_path,
            local_dir=exchanges_folder
        )
        
        if not downloaded_files:
            print(f"No new exchanges found for {exchanges_folder}")
        
        # Get the user hash log path
        user_hash_log_path = os.path.join(os.path.dirname(exchanges_folder), 
                                         os.path.basename(CURRENT_USER_HASH_LOG_FILE_PATH))
        
        # Always download the latest user hash log
        print("Downloading latest user hash log from S3...")
        user_hash_log_path = save_user_hash_log_from_s3(
            os.path.basename(CURRENT_USER_HASH_LOG_FILE_PATH),
            os.path.dirname(exchanges_folder)
        )
        
        if not user_hash_log_path:
            print("Error: Failed to download user hash log. Cannot proceed with PII database creation.")
            return
            
        # Create or update the exchanges database using the exchange_jsons subfolder
        json_folder = os.path.join(exchanges_folder, 'exchange_jsons')
        temp_db_path = os.path.join(json_folder, 'exchanges.db')
        
        print("Creating new exchanges database...")
        index_exchanges_in_db(json_folder)  # This creates the DB in json_folder
        
        # Move the database to the correct location with the right name
        if os.path.exists(temp_db_path):
            os.rename(temp_db_path, db_path)
            print(f"Moved database to: {db_path}")
        
        # Create the PII version of the database
        print(f"{'Updating' if add_only else 'Creating'} PII version of database with user hash data...")
        pii_db_path = create_exchanges_db_with_user_hashes(db_path, user_hash_log_path, add_only=add_only)
        
        if pii_db_path:
            print(f"Successfully processed {exchanges_folder}")
            print(f"Regular database: {db_path}")
            print(f"PII database: {pii_db_path}")
        else:
            print(f"Error creating PII database for {exchanges_folder}")
            
    except Exception as e:
        print(f"Error processing {exchanges_folder}: {e}")
        raise
        print(f"Error processing {exchanges_folder}: {e}")
        raise
    
def mrun_process_exchanges_folders():
    pass
if __name__ == "__main__":
    #cur_exchanges_folders = ['exchanges/qrag_deutsch', 'exchanges/qrag_fda-c19-townhalls', 'exchanges/qrag_pv-evac', 'exchanges/qrag_sovereign-child']
    #cur_exchanges_folders = ['exchanges/qrag_deutsch']
    #cur_exchanges_folders = ['exchanges/qrag_fda-c19-townhalls']
    #cur_exchanges_folders = ['exchanges/qrag_pv-evac']
    cur_exchanges_folders = ['exchanges/qrag_sovereign-child']
    for cur_exchanges_folder in cur_exchanges_folders:
        process_exchanges_folder(cur_exchanges_folder)



def process_exchanges_folder_old(exchanges_folder):
    """
    Process a QRag corpus folder by downloading new exchanges from S3 and updating the database.

    :param exchanges_folder: str, path to the exchanges folder (e.g., 'exchanges/qrag_deutsch')
    """
    try:
        # Get S3 path for this corpus
        s3_path = get_s3_path_for_corpus(exchanges_folder)
        
        # Create the folder if it doesn't exist
        os.makedirs(exchanges_folder, exist_ok=True)
        
        # Get folder name for database naming
        folder_name = os.path.basename(exchanges_folder)
        
        # Download new exchanges from S3 into exchange_jsons subfolder
        print(f"Downloading exchanges from S3 path: {s3_path}")
        downloaded_files = download_exchanges_from_s3(
            bucket="[S3-BUCKET]",
            s3_path=s3_path,
            local_dir=exchanges_folder
        )
        
        if not downloaded_files:
            print(f"No new exchanges found for {exchanges_folder}")
            return
        
        # Get the user hash log path
        user_hash_log_path = os.path.join(os.path.dirname(exchanges_folder), 
                                         os.path.basename(CURRENT_USER_HASH_LOG_FILE_PATH))
        
        # Check if we need to download the user hash log
        if not os.path.exists(user_hash_log_path):
            print("Downloading user hash log from S3...")
            save_user_hash_log_from_s3(
                os.path.basename(CURRENT_USER_HASH_LOG_FILE_PATH),
                os.path.dirname(exchanges_folder)
            )
        
        # Path for the exchanges database with folder name
        db_path = os.path.join(exchanges_folder, f'exchanges_{folder_name}.db')
        
        # Create or update the exchanges database using the exchange_jsons subfolder
        json_folder = os.path.join(exchanges_folder, 'exchange_jsons')
        if not os.path.exists(db_path):
            print("Creating new exchanges database...")
            index_exchanges_in_db(json_folder)  # Point to exchange_jsons subfolder
        else:
            print("Updating existing exchanges database...")
            index_exchanges_in_db(json_folder)  # Point to exchange_jsons subfolder
        
        # Create the PII version of the database
        print("Creating PII version of database with user hash data...")
        pii_db_path = create_exchanges_db_with_user_hashes(db_path, user_hash_log_path)
        
        if pii_db_path:
            print(f"Successfully processed {exchanges_folder}")
            print(f"Regular database: {db_path}")
            print(f"PII database: {pii_db_path}")
        else:
            print(f"Error creating PII database for {exchanges_folder}")
            
    except Exception as e:
        print(f"Error processing {exchanges_folder}: {e}")
        raise


# ===== END OF FILE core/dbgen.py =====
