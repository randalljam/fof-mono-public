import os
import json
import pandas as pd
import sqlite3
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

## START OF FILE math_analysis.py

### DATABASE CREATION
def create_database(db_name='apps/math-quiz/math-quiz_data/import_db/math-quiz.db'):
    # Delete the existing database file if it exists
    if os.path.exists(db_name):
        os.remove(db_name)
        print(f"Existing database '{db_name}' deleted.")

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Create Users table
    cursor.execute('''
        CREATE TABLE Users (
            name TEXT PRIMARY KEY
        )
    ''')

    # Create Sessions table
    cursor.execute('''
        CREATE TABLE Sessions (
            session_id TEXT PRIMARY KEY,
            session_filename TEXT,
            user_name TEXT,
            start_time TEXT,
            end_time TEXT,
            num_problems INTEGER,
            number_range_start INTEGER,
            number_range_end INTEGER,
            numbers_include TEXT,
            numbers_exclude TEXT,
            num_numbers INTEGER,
            operations TEXT,
            total_problems INTEGER,
            correct_answers INTEGER,
            average_response_time_ms INTEGER,
            FOREIGN KEY (user_name) REFERENCES Users(name)
        )
    ''')

    # Create ProblemAttempts table
    cursor.execute('''
        CREATE TABLE ProblemAttempts (
            attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            problem_id TEXT,
            problem_text TEXT,
            num1 INTEGER NULL,
            num2 INTEGER NULL,
            operation TEXT NULL,
            correct_answer REAL,
            user_answer_string TEXT,
            user_answer REAL,
            is_correct INTEGER,
            response_time_ms INTEGER,
            FOREIGN KEY (session_id) REFERENCES Sessions(session_id)
        )
    ''')

    conn.commit()
    conn.close()
    print(f"New database '{db_name}' created with necessary tables.")
    return db_name


### DATA IMPORT
def parse_problem_text(problem_text):
    # Normalize legacy display symbols (&times;, ×, &divide;, ÷) to canonical * and /
    normalized = problem_text or ''
    for old, new in (('&times;', '*'), ('×', '*'), ('&divide;', '/'), ('÷', '/')):
        normalized = normalized.replace(old, new)
    parts = normalized.split()
    if len(parts) == 3:
        try:
            num1 = int(parts[0])
            operation = parts[1]
            num2 = int(parts[2])
            return num1, operation, num2
        except ValueError:
            return None, None, None
    else:
        return None, None, None

def import_json_to_db(json_folder_path, db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Iterate over all JSON files in the folder
    for filename in os.listdir(json_folder_path):
        if filename.endswith('.json'):
            filepath = os.path.join(json_folder_path, filename)
            with open(filepath, 'r') as json_file:
                data = json.load(json_file)
                # Import user data
                user_data = data['user']
                name = user_data.get('name', 'Unknown')

                # Insert or ignore user
                cursor.execute('''
                    INSERT OR IGNORE INTO Users (name)
                    VALUES (?)
                ''', (name,))

                # Import session data
                session_data = data['session']
                session_id = session_data['id']
                start_time = session_data['start_time']
                end_time = session_data['end_time']
                settings = session_data.get('settings', {})
                summary = session_data.get('summary', {})

                # Insert or ignore session
                cursor.execute('''
                    INSERT OR IGNORE INTO Sessions (
                        session_id, session_filename, user_name, start_time, end_time, num_problems,
                        number_range_start, number_range_end, numbers_include, numbers_exclude,
                        num_numbers, operations, total_problems, correct_answers, average_response_time_ms
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_id, filename, name, start_time, end_time,
                    settings.get('num_problems'),
                    settings.get('number_range', [0, 0])[0],
                    settings.get('number_range', [0, 0])[1],
                    json.dumps(settings.get('numbers_include', [])),
                    json.dumps(settings.get('numbers_exclude', [])),
                    settings.get('num_numbers'),
                    json.dumps(settings.get('operations', [])),
                    summary.get('total_problems'),
                    summary.get('correct_answers'),
                    summary.get('average_response_time_ms')
                ))

                # Import problems data
                for problem in session_data.get('problems', []):
                    num1, operation, num2 = parse_problem_text(problem['problem_text'])
                    
                    # Insert or ignore problem attempt
                    cursor.execute('''
                        INSERT OR IGNORE INTO ProblemAttempts (
                            session_id, problem_id, problem_text, num1, num2, operation,
                            correct_answer, user_answer_string, user_answer, is_correct, response_time_ms
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        session_id,
                        problem['id'],
                        problem['problem_text'],
                        num1,
                        num2,
                        operation,
                        problem['correct_answer'],
                        problem['user_answer_string'],
                        problem['user_answer'],
                        1 if problem['is_correct'] else 0,
                        problem['response_time_ms']
                    ))

    conn.commit()
    conn.close()
    print(f"Data from JSON files in '{json_folder_path}' imported into '{db_name}'.")

    # New code to print table statistics
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Count users
    cursor.execute("SELECT COUNT(*) FROM Users")
    user_count = cursor.fetchone()[0]
    print(f"Number of users in the Users table: {user_count}")

    # Count sessions
    cursor.execute("SELECT COUNT(*) FROM Sessions")
    session_count = cursor.fetchone()[0]
    print(f"Number of sessions in the Sessions table: {session_count}")

    # Count problem attempts
    cursor.execute("SELECT COUNT(*) FROM ProblemAttempts")
    attempt_count = cursor.fetchone()[0]
    print(f"Number of problem attempts in the ProblemAttempts table: {attempt_count}")

    conn.close()


if __name__ == "__main__":
    db_name =  create_database()
    json_folder = 'apps/math-quiz/math-quiz_data/import_db'
    import_json_to_db(json_folder, db_name)

    # db_name = 'math_assessment.db'
    # user_sessions = get_user_sessions(db_name)
    # print("User Sessions:")
    # print(user_sessions)

    # problems_data = get_problems_data(db_name)
    # print("\nProblems Data:")
    # print(problems_data.head())

    # db_name = 'math_assessment.db'
    # problems_df = get_problems_data(db_name)
    # number_range = (0, 9)
    # operation_filter = '+'
    # generate_heatmap(problems_df, number_range, operation_filter)

    # run_interface()



# --- OLD CODE BELOW THIS LINE ---
# Reference only — do not call. This section targets an outdated schema
# (Users.grade, user_id, a Problems table that doesn't exist in the current DB)
# and run_interface() uses tk/ttk without importing tkinter.

def parse_question(question_str):
    # Split the question into components
    parts = question_str.split()
    if len(parts) == 3:
        num1 = int(parts[0])
        operation = parts[1]
        num2 = int(parts[2])
    else:
        # Handle more complex cases if necessary
        num1, operation, num2 = 0, '', 0
    return num1, operation, num2

### DATA RETRIEVAL
def get_user_sessions(db_name, user_id=None):
    conn = sqlite3.connect(db_name)
    query = '''
        SELECT Sessions.session_id, Sessions.start_time, Sessions.end_time, Users.name, Users.grade
        FROM Sessions
        JOIN Users ON Sessions.user_id = Users.user_id
    '''
    if user_id:
        query += f" WHERE Users.user_id = '{user_id}'"

    sessions_df = pd.read_sql_query(query, conn)
    conn.close()
    return sessions_df

def get_problems_data(db_name, session_ids=None, user_id=None, operations=None):
    conn = sqlite3.connect(db_name)
    query = '''
        SELECT Problems.*, Users.name, Users.grade
        FROM Problems
        JOIN Sessions ON Problems.session_id = Sessions.session_id
        JOIN Users ON Sessions.user_id = Users.user_id
    '''
    conditions = []
    if session_ids:
        session_ids_str = ','.join([f"'{sid}'" for sid in session_ids])
        conditions.append(f"Problems.session_id IN ({session_ids_str})")
    if user_id:
        conditions.append(f"Users.user_id = '{user_id}'")
    if operations:
        operations_str = ','.join([f"'{op}'" for op in operations])
        conditions.append(f"Problems.operation IN ({operations_str})")

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    problems_df = pd.read_sql_query(query, conn)
    conn.close()
    return problems_df


### DATA VISUALIZATION
def generate_heatmap(problems_df, number_range, operation_filter, show_incorrect_border=True):
    # Filter data based on operation
    if operation_filter != 'All':
        problems_df = problems_df[problems_df['operation'] == operation_filter]

    # Prepare data for heatmap
    num1_range = range(number_range[0], number_range[1] + 1)
    num2_range = range(number_range[0], number_range[1] + 1)
    heatmap_data = pd.DataFrame(index=num1_range, columns=num2_range, dtype=float)

    # Calculate average response times
    for num1 in num1_range:
        for num2 in num2_range:
            subset = problems_df[(problems_df['num1'] == num1) & (problems_df['num2'] == num2)]
            if not subset.empty:
                average_response_time = subset['response_time_ms'].mean()
                heatmap_data.at[num1, num2] = average_response_time
            else:
                heatmap_data.at[num1, num2] = np.nan

    # Create the heatmap
    plt.figure(figsize=(10, 8))
    sns.set()
    ax = sns.heatmap(
        heatmap_data,
        annot=True,
        fmt='.0f',
        cmap='RdYlGn_r',
        cbar_kws={'label': 'Average Response Time (ms)'},
        linewidths=0.5,
        linecolor='gray',
        square=True
    )

    # Set axis labels and titles
    ax.set_xlabel('Second Number (num2)')
    ax.set_ylabel('First Number (num1)')
    ax.set_title(f'Heatmap of Average Response Times ({operation_filter})')

    # Annotate cells with the problem equations
    for text in ax.texts:
        num1 = int(text.get_position()[1] + 0.5)
        num2 = int(text.get_position()[0] + 0.5)
        equation = f"{num1} {operation_filter} {num2}"
        text.set_text(equation)

    # Highlight cells with incorrect answers
    if show_incorrect_border:
        for num1 in num1_range:
            for num2 in num2_range:
                subset = problems_df[(problems_df['num1'] == num1) & (problems_df['num2'] == num2)]
                if not subset.empty and subset['is_correct'].min() == 0:
                    # Draw red border
                    ax.add_patch(plt.Rectangle((num2_range.index(num2), num1_range.index(num1)), 1, 1,
                                               fill=False, edgecolor='red', lw=2))

    plt.show()


### USER INTERFACE
def run_interface():
    db_name = 'math_assessment.db'

    # Initialize main window
    root = tk.Tk()
    root.title("Math Assessment Visualization")

    # Create frames
    control_frame = ttk.Frame(root, padding="10")
    control_frame.grid(row=0, column=0, sticky='W')
    control_frame.columnconfigure(0, weight=1)

    # Session selection
    ttk.Label(control_frame, text="Session Selection:").grid(row=0, column=0, sticky='W')
    session_option = tk.StringVar(value='All Sessions')
    session_options = ['All Sessions', 'Last Session', 'Last N Sessions']
    session_menu = ttk.OptionMenu(control_frame, session_option, session_option.get(), *session_options)
    session_menu.grid(row=1, column=0, sticky='W')

    # Number of sessions input
    n_sessions_var = tk.IntVar(value=1)
    n_sessions_entry = ttk.Entry(control_frame, textvariable=n_sessions_var)
    n_sessions_label = ttk.Label(control_frame, text="Number of Sessions:")
    n_sessions_label.grid(row=2, column=0, sticky='W')
    n_sessions_entry.grid(row=3, column=0, sticky='W')

    # Operation selection
    ttk.Label(control_frame, text="Operation Filter:").grid(row=4, column=0, sticky='W')
    operation_var = tk.StringVar(value='+')
    operation_options = ['+', '-', '*', '/', '^', 'All']
    operation_menu = ttk.OptionMenu(control_frame, operation_var, operation_var.get(), *operation_options)
    operation_menu.grid(row=5, column=0, sticky='W')

    # Number range selection
    ttk.Label(control_frame, text="Number Range:").grid(row=6, column=0, sticky='W')
    number_range_var = tk.StringVar(value='0-9')
    number_range_options = ['0-5', '0-9', '0-20']
    number_range_menu = ttk.OptionMenu(control_frame, number_range_var, number_range_var.get(), *number_range_options)
    number_range_menu.grid(row=7, column=0, sticky='W')

    # Generate heatmap button
    generate_button = ttk.Button(control_frame, text="Generate Heatmap", command=lambda: generate())
    generate_button.grid(row=8, column=0, sticky='W', pady=10)

    # Status label
    status_label = ttk.Label(control_frame, text="")
    status_label.grid(row=9, column=0, sticky='W')

    def generate():
        # Get user selections
        session_choice = session_option.get()
        n_sessions = n_sessions_var.get()
        operation_filter = operation_var.get()
        number_range_str = number_range_var.get()
        number_range = tuple(map(int, number_range_str.split('-')))

        # Retrieve sessions
        sessions_df = get_user_sessions(db_name)
        if session_choice == 'Last Session':
            session_ids = [sessions_df['session_id'].iloc[-1]]
        elif session_choice == 'Last N Sessions':
            session_ids = sessions_df['session_id'].tail(n_sessions).tolist()
        else:
            session_ids = sessions_df['session_id'].tolist()

        # Retrieve problems data
        problems_df = get_problems_data(db_name, session_ids=session_ids)
        if problems_df.empty:
            status_label.config(text="No data available for the selected options.")
            return

        # Generate heatmap
        generate_heatmap(problems_df, number_range, operation_filter)
        status_label.config(text="Heatmap generated.")

    root.mainloop()

